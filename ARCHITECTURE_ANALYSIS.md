# ARTEMIS 项目架构分析

> 基于源码探索整理（2026-11-26），路径与行号对应当前检出。用途：为"MQTT 远程原型"方案提供架构依据。
> 本文只描述现状，不包含改动建议；改动方案见 `MQTT_REMOTE_PROTOTYPE_PLAN.md`（如已生成）。

## 1. 系统总览

ARTEMIS 是一个用 Python 3.12+ 编写的自主多模态智能体，通过 ADB 驱动真实 Android 设备。它同时提供 MCP 服务器、Angular Showcase UI 和 FastAPI 管理控制台。

四大入口最终汇聚到同一套 Agent / Driver 栈：

| 入口 | 实现 | 说明 |
|---|---|---|
| CLI | `artemis/interfaces/cli/main.py:56` 注册 `run`；`commands/run.py` | 默认经 Daemon 提交任务，失败回退本地 |
| Web UI | `uv run artemis ui` → `localhost:8000` | Showcase UI + Admin Console |
| MCP Server | `python -m mcp_server` | IDE 通过 stdio / SSE 调用工具 |
| Python SDK | `packages/artemis-client/` | 零第三方依赖，目标 Python >=3.10 |

`python -m artemis.main "<goal>"` 会被规范化为 `run "<goal>"`（`artemis/main.py:40-47`：首个 token 不是已注册命令时自动补 `run`）。

## 2. 分层架构：两套并列的抽象

设备操作链路上存在两套抽象，不要混淆：

| 层 | 抽象 | 坐标系 | 面向 |
|---|---|---|---|
| Actor 层 | `Actuator` Protocol（`artemis/mcp/actuators/base.py:40-113`） | 归一化 0–1000 | Agent 工具，返回 `ActionResult` |
| Device 层 | `BaseDeviceDriver` ABC（`artemis/drivers/base.py:69`） | 物理像素 | 真正发 ADB 命令 |

两者由 `UnifiedMobileController`（`third_party/mobile_use/controllers/unified_controller.py:33-183`）桥接，负责归一化↔像素转换与 API 适配。

完整的调用链（以 click 为例）：

```
Agent (Flash runner / Pro Operator)
  → McpActionExecutor.execute()        artemis/mcp/action_executor.py:116-150
    → ActionSession.call()             artemis/mcp/action_session.py:216-245
      → build_action_server            artemis/mcp/action_server.py:69-90
        → AdbActuator.click()          artemis/mcp/actuators/adb.py:160-170
          → UnifiedMobileController.tap_at()   third_party/.../unified_controller.py:46-64
            → AndroidAdbDriver.tap()   artemis/drivers/android/adb_driver.py:229-252
              → adbutils AdbDevice.shell("input tap x y")
                → 真机
```

观测路径（screenshot）：`session.observe()` → `observe_screen`（`action_server.py:94-119`）→ `controller.get_screen_data()` → `AndroidAdbDriver.get_screen_data()`（`adb_driver.py:121-227`）→ UIAutomator 或 `device.screenshot()` → `ScreenData`。

另有一条仍存在的旧路径：`artemis/tools/base.py` 的 `ArtemisTool.execute(driver, ctx, ...)`，由 `to_langchain_tool()` 调 `get_driver(ctx)`。

## 3. 驱动层

### 3.1 工厂：`artemis/drivers/factory.py:34-72`

没有注册表/装饰器，是硬编码 if/else：

1. **Cloud 模式**：`ARTEMIS_CLOUD_MODE=1` → 注入 `ctx.adb_client = RemoteAdbClient()`、`ctx.ui_adb_client = RemoteUIAutomatorClient(...)`（来自可选外部包 `cloud_service.virtualization`），**但仍返回 `AndroidAdbDriver`**。
2. **Mock 模式**：`mobile_platform == "mock"` 或 `ARTEMIS_MOCK_DRIVER=1` → `MockDeviceDriver`。
3. **默认**：`AdbClient(host=settings.ADB_HOST, port=settings.ADB_PORT)` → `AndroidAdbDriver`。

`get_driver(ctx)`（L75-80）缓存实例到 `ctx._active_driver`（`artemis/context.py:177`）。这个字段和 `ctx.adb_client` / `ctx.ui_adb_client` / `ctx.actuator` 都是预留的注入 seam。

### 3.2 抽象接口：`artemis/drivers/base.py`

`BaseDeviceDriver(ABC)` 的 16 个抽象方法：

- 属性：`device_id`、`screen_size`
- 生命周期：`connect()`、`disconnect()`
- 观测：`get_screen_data(skip_settling=False) -> ScreenData`
- 交互：`tap`、`long_press`、`swipe`、`swipe_direction`、`input_text`、`press_key`
- 应用：`launch_app`、`stop_app`、`get_current_package`
- 系统：`execute_shell(command, timeout_seconds=15.0) -> str`
- 录像：`start_video_recording`、`stop_video_recording`

基类提供具体实现（自动继承）：`wait_for_delay`、`tap_normalized`、`swipe_normalized`（0–1000 → 像素）、`find_element`、`tap_element`。

`ScreenData`（`base.py:52-66`）：`screenshot_bytes`、`screenshot_base64`、`ui_hierarchy_xml`、`ui_elements`、`width`、`height`、`timestamp`、`platform`。

错误约定：设备级失败捕获后返回 `False` / `"Error: {e}"` 字符串，不向上抛异常。

### 3.3 三个实现

- **`AndroidAdbDriver`**（`adb_driver.py:72-507`，主实现）：`device` 属性（L100-104）懒解析 `adb_client.device(serial=...)`；所有命令走 `asyncio.to_thread(self.device.shell, cmd)`。`get_screen_data()` 三级截图策略（UIAutomator → PIL → 1x1 PNG 兜底）+ 层级解析过滤；`input_text()` 三级 fallback（剪贴板 → ADBKeyboard → native `input text`）；`press_key()` 用 `ANDROID_KEYCODE_MAP`（L38-47）。录像使用 scrcpy + ffmpeg（L438-507）。
- **`MockDeviceDriver`**（`artemis/drivers/mock/mock_driver.py:26-198`）：生成假 PNG/XML，记录 `action_history` 供测试断言。
- **`CloudDeviceDriver`**（`artemis/drivers/cloud/cloud_driver.py:25-117`）：**未接线的桩**，全仓库无调用方，不要基于它扩展。

`android/`、`cloud/`、`mock/` 三个子目录没有 `__init__.py`（隐式命名空间包）。

## 4. ADB 连接、寻址与并发

### 4.1 两级寻址

- `AdbEndpoint(host, port)`（`artemis/runtime/adb_endpoint.py:45-102`）：ADB **server** 的网络地址，默认 `127.0.0.1:5037`。`is_local_default` / `mode` 属性区分 local/remote（L87-93）。
- `device_id` / `serial`：该 server 上枚举出的设备序列号。
- `AdbTarget(endpoint, serial)`（L116-132）把 serial 绑定到发现它的 endpoint，`lock_scope` / `lock_key` 用于锁隔离。

`AdbSession`（L135-161）生成带显式 `-H/-P` 的 adb 命令，`adb_command()`（L171-173）是便捷封装。

### 4.2 设备发现

`artemis/runtime/device_pool.py:102-124` 通过 `adb devices -l` 枚举（调用裸 `adb`，继承环境中的 `ADB_HOST/PORT/SERVER_SOCKET`）。缓存 TTL 1s，选择逻辑 `_pick_device()`（L448-474）：显式 serial 优先 → 第一个 idle → 第一个 ready → 任意 attached。全局单例 `device_pool`（L477-478）。

### 4.3 设备锁

`artemis/runtime/device_lock.py:83-107`：锁 ID 归一化后为 `{scope}__{device}`，scope 默认取 `ARTEMIS_ADB_ENDPOINT_ID`，因此**同名 serial 在不同 ADB server 上是不同的锁**。支持 `global` / `per_device` 并发模式。

### 4.4 远程 ADB server（已有完整机制）

`artemis/core/diagnostics/adb_server_connection.py:45-56` 的 `AdbServerConnectionManager` 提供探测、激活、持久化到 `.env`、环境变量同步（`_activate` L296-326）。Admin API 在 `apps/admin_console/routers/system.py:148-224`：`/api/system/adb/connect`（WiFi ADB）、`/server/{connect,probe,local}`。WiFi ADB 强制要求当前端点是本地（`engine.py:397-414`）。

## 5. 配置体系

| 文件 | 职责 |
|---|---|
| `artemis/config/settings.py:93-154` | `Settings`（pydantic-settings，自动读环境变量与 `.env`）；设备地址字段 `ADB_HOST/PORT/DEVICE_SERIAL` 在 L113-122 |
| `artemis/config/constants.py:30-53,106-107` | 环境变量名常量与默认值；已有 `ARTEMIS_CLOUD_MODE` 等 cloud 常量 |
| `artemis/config/paths.py:39-41,81-83,149-196` | 源码检出 vs 用户目录；`.env` 与配置文件的解析顺序 |
| `config/artemis.jsonc` | agent/LLM 配置（311 行），**没有任何设备/连接相关键** |
| `artemis/config/core/engine.py:55-115` | `CascadingConfigEngine` 五层级联 + 变量插值 |

`.env` 通过 `settings.py:50-55` 双路径 `load_dotenv` 加载；写入用 `dotenv.set_key`（`adb_server_connection.py:305-311`）。`.env.example:18-29` 是模板。

## 6. 现有"远程"机制（三套，互不相同）

| 机制 | 入口 | 协议 | 状态 |
|---|---|---|---|
| Daemon 调度 | CLI/MCP/SDK 默认路径 | HTTP REST + SSE | 完整实现、默认启用 |
| `ARTEMIS_CLOUD_MODE=1` | driver factory / SDK agent | 可选包 `cloud_service.virtualization` 的 RPC bridge | 项目内只有调用点，实现不在仓库 |
| `CloudDeviceDriver` | 无 | 声称 Cloud Gateway RPC | 桩代码，未接线 |

### 6.1 Daemon 任务模型

`run.py:298-463`：CLI 默认提交任务给 Daemon（`ensure_daemon_running` → `submit_task_to_daemon` → `wait_for_daemon_task`），失败回退本地；`--standalone` 跳过 Daemon。任务统一带 `ingress`（cli/mcp/sdk）、`session_id`、设备 serial，经队列与 session 管理（`apps/admin_console/services/task_queue_service.py`）。

`packages/artemis-client/` 用纯 HTTP + JSON（`transport.py:9,30-35`，标准库 `urllib`），能力协商 `/api/v1/capabilities`、幂等提交（客户端生成 UUID）、轮询兜底；唯一的推送是 SSE `/api/stream`，**没有双向长连接**。

### 6.2 Cloud 模式的可插拔契约（重要参考）

`tests/integration/test_remote_adb.py:44-54,136-146` 还原了可选包 `cloud_service` 的接口形状：

```python
device.shell(cmd)          → bridge.execute_sync("shell", {"command": cmd})
                            → {"status": "SUCCESS", "output": "..."}
RemoteUIAutomatorClient.get_screen_data()
                            → {"base64": ..., "hierarchy_xml": ..., "elements": [...]}
```

即一个 `bridge.execute_sync(action, payload) -> dict` 的 RPC 抽象，上层用 duck typing 把 `RemoteAdbDevice/Client/UIAutomatorClient` 伪装成本地对象。

该模式在多个位置有分支：
- `artemis/drivers/factory.py:39-47`（注入 client）
- `third_party/mobile_use/sdk/agent.py:142,150,170-184`（跳过 adb 检查、device_id、client 初始化）
- `third_party/mobile_use/controllers/platform_specific_commands_controller.py:34-38`
- `artemis/tools/command_tool.py:704,1088`（`hasattr(adb_client, "_bridge")` 判定虚拟 ADB 路径）
- `artemis/runtime/awake_service.py:95,155,213,224`（跳过常亮服务）
- `artemis/mcp/adb_server.py:130-148`、`artemis/data_engine/engine.py:541`（SSE 事件桥）

### 6.3 Actuator 可插拔后端

`ctx.actuator`（`artemis/context.py:183-185`）是官方预留的"换动作后端"插槽，注释明确提到可安装"robot-arm backend"。`get_action_session()`（`action_session.py:236`）与 `McpActionExecutor`（`action_executor.py:96`）都遵循"显式传参 > ctx.actuator > AdbActuator(ctx)"。但注意 `run_adb_command` 走独立 system channel（`action_manifest.py:108-112`），换 actuator 时仍需单独处理。

## 7. 质量门禁与约束

- **依赖来源**：CI 第一步 `scripts/check_dependency_sources.py` 要求 `uv.lock` 中所有包来自 PyPI（`files.pythonhosted.org`），npm 来自 `registry.npmjs.org`；`uv sync --dev --locked` 要求锁文件已提交。
- **质量棘轮**：`scripts/quality_ratchet.py` 扫描 `artemis/`、`mcp_server/`、`apps/admin_console/`、`third_party/`，`except Exception`/宽泛静默处理/`# type: ignore` 计数不得超过 `.quality-baseline.json`（**754 / 0 / 18**）。
- **代码风格**：行宽 100、双引号、`select = [E,F,TID,UP]`、**绝对导入**（`ban-relative-imports = "all"`）。
- **类型检查**：`make typecheck` 仅覆盖 `pyright-core.json` 中约 10 个受保护模块，不代表全仓库类型安全。
- **测试分层**：默认 `pytest.ini_options.testpaths` = `tests/unit`、`tests/tools`、`packages/artemis-client/tests`；`addopts` 排除 `integration, e2e, cloud, manual, android`。默认套件必须 hermetic，任何需外部状态的测试必须打标且可安全收集。

## 8. 关键文件索引

```
artemis/drivers/factory.py                    驱动选择/缓存
artemis/drivers/base.py                       驱动抽象基类
artemis/drivers/android/adb_driver.py         主 ADB 实现
artemis/controllers/unified_controller.py     控制器/坐标转换
artemis/mcp/action_executor.py                Agent 工具执行器
artemis/mcp/actuators/{base,adb,mock}.py      Actor 层后端
artemis/context.py                            注入点（adb_client/ui_adb_client/actuator）
artemis/runtime/adb_endpoint.py               ADB server 端点/目标快照
artemis/runtime/device_pool.py                设备发现
artemis/runtime/device_lock.py                设备锁
artemis/core/diagnostics/adb_server_connection.py  远程 ADB server 切换
artemis/config/settings.py                    运行时设置
artemis/config/constants.py                   环境变量常量
artemis/tools/command_tool.py                 ADB shell 工具（云模式分支）
artemis/clients/screen_client_factory.py      截图/层级后端选择
third_party/mobile_use/sdk/agent.py            SDK Agent（云模式分支）
third_party/mobile_use/controllers/unified_controller.py  上层控制器门面
third_party/mobile_use/controllers/platform_specific_commands_controller.py  设备对象访问
packages/artemis-client/                      零依赖远程客户端
tests/integration/test_remote_adb.py          cloud RPC bridge 契约
```
