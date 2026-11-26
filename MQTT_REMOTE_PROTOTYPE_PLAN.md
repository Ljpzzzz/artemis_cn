# ARTEMIS 远程原型：MQTT 远程 ADB 通道实施计划

> 配套架构分析见 `ARCHITECTURE_ANALYSIS.md`。本文只描述改动方案。

## Context（为什么要做）

ARTEMIS 当前只通过本地 ADB 驱动真机（`AndroidAdbDriver` → `adbutils` → `device.shell()`）。要把它做成远程原型，让用户能把点击/截图等操作经 MQTT 发给远端设备上的 agent、由远端执行真机 ADB 并回传结果。

约束（来自用户）：
- **与本地 ADB 兼容**：默认行为完全不变。
- **用户可选**：仅通过环境变量 / `.env` 切换，不加 CLI 参数、不加 UI。
- **改动尽量小**：复用现有抽象与接缝，不重构。

关键发现：仓库里**没有任何 MQTT 代码**，但已有一套现成的"换底层 client、不改上层"范式——`ARTEMIS_CLOUD_MODE=1` 在 `artemis/drivers/factory.py:34-72` 注入 `RemoteAdbClient` / `RemoteUIAutomatorClient`，仍返回 `AndroidAdbDriver`。MQTT 照此实现即可把改动压到最小。

## 核心决策

**注入式 `MqttAdbClient` + `MqttUIAutomatorClient`，仍返回 `AndroidAdbDriver`；不新建 `MqttDeviceDriver`。**

理由：`BaseDeviceDriver` 有 16 个抽象方法，`AndroidAdbDriver`（`adb_driver.py:72-507`）已实现命令构建、三级文本输入、keycode 映射、层级解析/过滤和"失败返回 False/Error 字符串"的错误语义。新建 driver 要复制约 400 行且行为会漂移。注入式方案让 agent、controller、tools、Checker、Flash/Pro 全链路零改动。

两个必须命中的现有接缝：
- `artemis/tools/command_tool.py:704-706`、`1088` 用 `hasattr(adb_client, "_bridge")` 判定虚拟 ADB 路径 → **`MqttAdbClient` 的属性必须命名为 `_bridge`**，则这两处零改动。
- `AndroidAdbDriver.get_screen_data()`（`adb_driver.py:132-158`）用 duck typing 读 `ui_adb_client.get_screen_data()` 返回对象的 `.base64/.width/.height/.hierarchy_xml/.elements` → `MqttUIAutomatorClient` 返回同形状对象即可，天然绕过 Accessibility Helper 和 `adb forward`。

## 架构与协议

```
本机 ARTEMIS                                远端设备 agent
ctx.adb_client = MqttAdbClient         scripts/mqtt_device_agent.py
ctx.ui_adb_client = MqttUI...           订阅 request → adbutils/uiautomator2 执行
factory → AndroidAdbDriver                    → publish 到 reply_to
  └ device.shell() [asyncio.to_thread]
       └ MqttBridge.execute_sync ──publish──┘
```

- 依赖：`paho-mqtt>=2.1.0,<3.0`，**只加到主包** `pyproject.toml`；`packages/artemis-client/` 保持零依赖。`uv lock` 重生成（`uv sync --dev --locked` 要求）。CI 依赖来源检查要求 PyPI 官方源。
- Topic：`{prefix}/{device_id}/request`（QoS 1），响应 `{prefix}/{device_id}/response/{client_id}`（`client_id = artemis-{uuid8}`，避免多客户端串扰）。默认 prefix `artemis/rpc`。
- 契约复用 `tests/integration/test_remote_adb.py:44-54,136-146` 中 cloud bridge 的形状：`execute_sync(action, payload) -> dict`，响应字段 `status/output` 或 `base64/hierarchy_xml/width/height`。
- 请求信封：`{v,id,device_id,action,payload,reply_to,timeout_ms}`；用 `id` 关联 `threading.Event`，超时抛具体异常。
- MVP action：`shell`、`screenshot`、`get_screen_data`、`get_state`、`window_size`、`current_app`、`set_clipboard`（打通 `input_text` Tier 1 中文输入）。
- 远端 agent 只回传 XML，不解析 elements；本机复用 `parse_hierarchy_xml_to_elements`（`third_party/mobile_use/clients/ui_automator_client.py`）。

## 必须改动（按文件）

| # | 文件 | 改动 |
|---|---|---|
| 1 | `pyproject.toml` / `uv.lock` | 加 `paho-mqtt` 依赖并重生成锁文件 |
| 2 | `artemis/config/constants.py` | 新增 `ENV_ARTEMIS_MQTT_*` 常量与默认值 |
| 3 | `artemis/config/__init__.py` | 按现有约定 import + `__all__` 导出 |
| 4 | `artemis/config/settings.py:113-122` | `Settings` 增加 MQTT 字段（pydantic-settings 自动读 env/.env） |
| 5 | `.env.example` | 增加注释掉的 MQTT 配置块 |
| 6 | **新增** `artemis/config/remote_device.py` | `is_remote_device_mode()` / `remote_transport()` / `create_remote_clients(device_id)` 单一抽象，统一 cloud 与 MQTT 的 client 构造 |
| 7 | `artemis/drivers/factory.py:34-72` | cloud 分支前插入 MQTT 分支（MQTT 优先）：注入 clients 后仍走 `return AndroidAdbDriver(...)`；原 cloud 的 `if` 改 `elif` |
| 8 | `third_party/mobile_use/sdk/agent.py:142,150,170-184` | 三处：跳过 `which("adb")` 检查、device_id 解析、client 初始化改为 `create_remote_clients()`。**已验证必须改**：否则本地 client 被初始化，factory 注入不生效 |
| 9 | `artemis/runtime/awake_service.py:95` | `ARTEMIS_CLOUD_MODE` 判断改用 `is_remote_device_mode()`，避免本机跑 `adb shell svc power stayon usb` 失败刷屏 |

明确**不改**：`adb_driver.py`、`drivers/base.py`、`context.py`、`command_tool.py`、`screen_client_factory.py`、`device_pool.py`、`adb_server_connection.py`、`data_engine/engine.py`。

## 新增文件

生产代码：
- `artemis/transport/__init__.py`、`artemis/transport/mqtt/__init__.py`
- `artemis/transport/mqtt/errors.py` — `MqttRpcError` / `MqttRpcTimeoutError` / `MqttRpcResponseError` / `MqttConnectionError`（均为 `RuntimeError` 子类）
- `artemis/transport/mqtt/mqtt_bridge.py` — `MqttBridge`：`execute_sync(action, payload, timeout_seconds=None) -> dict`，懒连接、QoS 1、`threading.Event` 关联、`close()` 幂等
- `artemis/transport/mqtt/mqtt_client.py` — `MqttAdbDevice` / `MqttAdbClient`（含 `_bridge`）/ `MqttScreenData` / `MqttUIAutomatorClient`
- `scripts/mqtt_device_agent.py` — 远端参考 agent（仅依赖 paho-mqtt + adbutils + uiautomator2）

测试：
- `tests/unit/test_mqtt_bridge.py` — fake `mqtt.Client`，验证 envelope/correlation/超时/ERROR/_bridge 标记；不打 marker，hermetic
- `tests/unit/test_mqtt_driver_factory.py` — 验证返回 `AndroidAdbDriver`、clients 注入、默认/cloud/mock 分支不受影响
- `tests/integration/test_mqtt_remote.py` — `[integration, cloud]` marker，`importorskip("paho.mqtt")`，无 broker 时 skip

## 关键实现要点

- `MqttBridge.execute_sync()`：发布后用 `pending.event.wait(timeout)`；`_on_message` 按 `id` 找 pending 并 `event.set()`；`finally` 清理 `_pending`。**只用具体异常元组**（如 `except (ValueError, UnicodeDecodeError)`），不用 `except Exception` / `# type: ignore`（质量棘轮基线 754/0/18 不能推高）。
- `MqttAdbClient.device(serial)` 返回 `MqttAdbDevice`；`MqttUIAutomatorClient.get_screen_data()` 返回 `MqttScreenData(base64, hierarchy_xml, elements, width, height)`，其中 elements 来自 XML 解析，使 `adb_driver.py:178-192` 不再发二次 RPC。
- `MqttUIAutomatorClient.set_clipboard()` 转发 `set_clipboard` action，`disconnect()` 关闭 bridge（被 `AndroidAdbDriver.disconnect()` 调用）。
- bridge 用模块级缓存（key = host/port/device_id/client_id），确保多处 `create_remote_clients()` 拿到同一实例。
- `factory.py` 中 MQTT 与 cloud 互斥，MQTT 优先，避免 import 缺失的可选包 `cloud_service`。

## 兼容性

| 场景 | 行为 |
|---|---|
| 未设 `ARTEMIS_MQTT_MODE`（默认） | 新分支全不执行、模块 lazy import，本地 ADB 行为零变化 |
| `ARTEMIS_MQTT_MODE=1` | 注入 MQTT clients，仍用 `AndroidAdbDriver`；command_tool 自动走虚拟 ADB 分支 |
| broker 不可达 / action ERROR / 超时 | 具体异常被 driver 既有 `except Exception` 转成 `False` / `"Error: ..."`，语义与设备离线一致 |
| 切回本地 | 去掉 env 或设 `0`，重启即可；bridge 不写文件，无残留 |

已知 MVP 限制：视频录制依赖本地 scrcpy（会 warn 跳过）；`install/push/pull` 未实现；设备不动态发现，需显式配置 `ARTEMIS_MQTT_DEVICE_ID`（或复用 `ADB_DEVICE_SERIAL`）。

## 实施步骤

**阶段 A — MVP 闭环**：依赖/配置三件套 + `remote_device.py` → `errors.py`/`mqtt_bridge.py`/`mqtt_client.py` → factory/agent/awake_service 接线 → 远端 agent 脚本 → 单元测试 → 本地 broker 手工端到端。

**阶段 B — 增强**：`install/push/pull` base64 action；`mcp/adb_server.py` MQTT 分支打通 MCP 设备工具；`on_disconnect` 指数退避重连（只对读命令重试，tap 非幂等）；`device_pool.py` 动态设备枚举；`screenrecord` action 补录像。

## 验证

```bash
# 门禁（必须全绿）
make test
make lint
make typecheck
python scripts/quality_ratchet.py
python scripts/check_dependency_sources.py
```

端到端：远端机器运行 `python scripts/mqtt_device_agent.py --device <serial> --broker <host>`；本机 `.env` 设 `ARTEMIS_MQTT_MODE=1`、`ARTEMIS_MQTT_BROKER_HOST=<host>`、`ARTEMIS_MQTT_DEVICE_ID=<serial>`；`uv run artemis run "打开设置并截图" --profile flash`，确认日志出现 `[ADB] input tap ...`、trace 截图正常、远端 agent 打印收到的 action；关闭 env 重跑对比行为一致。

## 风险

- **延迟/超时**：MQTT RTT + 远端执行比本地毫秒级 ADB 慢，`ARTEMIS_MQTT_TIMEOUT_SECONDS` 需按 flash profile 步预算调优；MVP 不做动作重试（tap 非幂等）。
- **截图大 payload**：1080×2400 PNG base64 约 1-3MB，远端用 JPEG 压缩，broker 需调大 `max_packet_size`；分片/对象存储留到阶段 B。
- **重连**：用 `OSError`/`TimeoutError`/paho 返回码，不用宽泛 handler，避免质量棘轮回归。
- **vendored 文件**：`sdk/agent.py` 改动限定为 3 处小分支 + `remote_device.py` 调用。
