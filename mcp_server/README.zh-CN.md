# 🔌 ARTEMIS 通用 MCP 服务器

本目录包含 **ARTEMIS** 的**模型上下文协议（Model Context Protocol，MCP）**服务器。它将移动设备自动化能力暴露给 **Antigravity**、**Cursor**、**Claude Code**、**OpenClaw**、**Windsurf**、**CodeBuddy Code**、**WorkBuddy** 和 **OpenCode** 等客户端。

## 🏗️ 架构

```
mcp_server/
├── __init__.py           # 包导出（mcp、main）
├── base.py               # 共享的 FastMCP 实例
├── server.py             # 服务器入口（stdio / sse）
├── rules.md              # 面向 IDE 的 AI 智能体测试思维与系统提示词规则
├── background/           # 后台进程执行
│   └── task_runner.py    # Artemis Agent 子进程运行器
├── notifiers/            # 多环境通知适配器
│   ├── base.py           # BaseNotifier 抽象类
│   ├── agentapi.py       # Jetski / Antigravity AgentAPI 通知器（含会话排序与缓存）
│   ├── desktop.py        # 原生操作系统桌面通知（macOS/Linux/Windows，默认启用）
│   ├── script.py         # 通用脚本 / 命令钩子通知器（ARTEMIS_NOTIFY_CMD）
│   ├── webhook.py        # OpenClaw / CI / Discord / Slack webhook 通知器
│   ├── file.py           # 文件审计记录器（notifications.jsonl）
│   └── composite.py      # 多渠道通知分发器
├── tools/                # 模块化的标准 MCP 工具
│   ├── task_runner.py    # mobile_run_task
│   ├── task_manager.py   # mobile_manage_task
│   ├── device_state.py   # mobile_get_device_state
│   ├── inspect_trace.py  # mobile_inspect_trace
│   └── diagnose.py       # mobile_diagnose
└── utils/                # 环境与设备工具
    ├── device_utils.py   # 跨平台的 ADB 与模拟器解析器
    └── env_utils.py      # Python 解释器与进程管理器
```

追踪状态存储（traces 目录布局与 `status.json` 生命周期）位于中立的基础包 `artemis/runtime/trace_store.py` 中，由 MCP 服务器、管理控制台以及派生出的工作进程共享。

## 🔔 多平台通知与唤醒支持

当你通过 `mobile_run_task` 启动一个异步移动测试时，Artemis MCP 会将任务作为分离的后台进程运行，以免阻塞 AI 智能体。在任务完成或失败时，Artemis 会跨**所有可用的通知渠道**分发警报，使人类开发者和 AI 智能体都能在不同平台上立即收到通知：

| 平台 / 环境 | 主要通知机制 | 工作原理与配置 |
| :--- | :--- | :--- |
| **Antigravity / Jetski** | **响应式唤醒（`AgentApiNotifier`）** | 自动检测并缓存活跃的 IDE 会话凭据（`ANTIGRAVITY_LS_ADDRESS`、`ANTIGRAVITY_CSRF_TOKEN`），按创建时间对候选进程排序以避免陈旧的 PID，并调用 `agentapi send-message` 直接在对话中唤醒智能体。 |
| **Cursor / Windsurf / VS Code / Cline / Roo Code** | **原生桌面通知（`DesktopNotifier`）+ 文件审计（`FileNotifier`）** | 在 macOS（`osascript`）、Linux（`notify-send`）和 Windows（`powershell`）上**默认启用**。弹出系统通知横幅，告知开发者任务完成还是失败。AI 智能体检查 `<trace_dir>/status.json` 或使用 `mobile_manage_task(action="status")`。可通过 `ARTEMIS_DESKTOP_NOTIFY=false` 关闭。 |
| **Claude Code / Desktop** | **原生桌面通知 + 文件审计** | 后台执行结束时通过系统桌面通知横幅提醒用户，同时在 `notifications.jsonl` 中维护完整的 JSONL 审计日志。 |
| **OpenClaw / Slack / Discord / CI/CD** | **HTTP Webhook（`WebhookNotifier`）** | 向通过 `OPENCLAW_WEBHOOK_URL`、`MCP_NOTIFICATION_WEBHOOK` 或 `ARTEMIS_WEBHOOK_URL` 配置的自定义端点发送结构化的 JSON POST 负载。 |
| **通用自定义 IDE / CLI 钩子** | **自定义脚本钩子（`ScriptNotifier`）** | 在环境中设置 `ARTEMIS_NOTIFY_CMD="my-script --title '{title}' --message '{message}' --trace-id '{trace_id}'"`，即可在事件完成时执行任意自定义命令或脚本。 |

## 🧠 AI 智能体行为规则（`rules.md`）

在将 ARTEMIS 连接到 **Antigravity**、**Claude Code**、**Cursor** 或 **Windsurf** 等 AI 编程助手时，向助手提供特定领域的测试规范对于生成可靠的测试代码至关重要。

附带的 [`rules.md`](./rules.md) 文件包含**移动测试思维（ARTEMIS 集成）**指南。它教会 AI 智能体如何正确地与 ARTEMIS 协作：

1. **可运行代码原则与主动探索**：指示 AI 绝不猜测或臆造 UI 跳转。相反，在编写测试脚本之前，必须先通过 ARTEMIS MCP 工具（`mobile_run_task` 等）探索实时应用，以发现并验证真实的交互路径。
2. **Flash 与 Pro 路由策略**：引导 AI 对快速、直接的 UI 操作选择 **Flash**（默认无步数上限），对需要持久计划、经验证的检查点、轮询循环或 ADB / 视频 / 日志诊断的任务选择 **Pro**。
3. **延迟与时序补偿**：厘清 AI 探索延迟（例如模型决策间隔）与最终测试代码确定性时序要求之间的区别。
4. **"动态定位优先、坐标兜底"的定位模式**：教会 AI 优先使用动态 UI 定位器（资源 ID、OCR 文本、语义）以增强布局适应性，同时实现绝对坐标回退以获得最大的执行可靠性。
5. **环境自诊断**：告知 AI 每当工具报错或用户说 ARTEMIS 不工作时，首先调用 `mobile_diagnose`，以及如何根据返回的修复列表采取行动（自行运行本地命令、将设备提示转达给用户、绝不通过聊天传递 API 密钥、配置变更后重新加载 MCP 服务器）。

### 全局规则与 MCP 是如何安装的

当你运行 `uv run artemis mcp --install all`（或指定某个 IDE，如 `--install cursor`、`--install claude` 等）时，安装程序会**自动同步全局 MCP 服务器配置和全局测试规则**到相应的用户主目录（不会在工作区中创建项目级规则文件）：

* **Antigravity / Jetski**：自动将全局规则安装到 `~/.gemini/rules/artemis.md`。
* **Cursor**：自动安装带 YAML frontmatter 的全局规则文件到 `~/.cursor/rules/artemis.mdc`。
* **Claude Code / Desktop**：自动将全局规则安装到 `~/.claude/rules/artemis.md`。
* **Windsurf**：自动将全局规则安装到 `~/.codeium/windsurf/rules/artemis.md`。
* **VS Code**：自动将全局规则安装到 `~/.vscode/rules/artemis.md`。
* **Cline / Roo Code**：自动将全局规则安装到 `~/.cline/rules/artemis.md` 和 `~/.roo/rules/artemis.md`。
* **OpenClaw**：自动将全局规则安装到 `~/.openclaw/rules/artemis.md`。
* **CodeBuddy Code**：自动将全局规则安装到 `~/.codebuddy/rules/artemis.md`。
* **WorkBuddy**：自动将全局规则安装到 `~/.workbuddy/AGENTS.md`。
* **OpenCode**：自动将全局规则安装到 `~/.config/opencode/AGENTS.md`。

*（注意：如果你偏好手动配置，也可以将 [`rules.md`](./rules.md) 的内容复制到 IDE 的系统提示词或全局规则设置中。）*

## 🛠️ MCP 工具概览

* **`mobile_run_task`**：异步启动一个自主移动自动化任务（`Flash` 或 `Pro` 模式），可通过 `device_serial` 指定目标设备。Pro 运行可通过 `verification_level`（`off` | `final` | `checkpoints` | `strict` —— Checker 的审查力度）和 `explorer_mode`（`flash` | `pro` | `ultra` —— Operator 的感知深度）进行调优。
* **`mobile_manage_task`**：管理任务生命周期（`status`、`stop`、`inject_instruction`），返回任务状态和分配的 `device_serial`。在 `inject_instruction` 时传入 `release_loop=True` 可优雅地结束 `[Loop:continuous]` 监控任务 —— 解锁循环里程碑完成状态的是这个显式信号，而不是"请停止"之类的措辞。
* **`mobile_get_device_state`**：实时观察器（`screenshot` 或 OCR+XML `hierarchy`），可指定 `device_serial`。
* **`mobile_inspect_trace`**：精细的追踪检查、可视化动作覆盖层、智能体推理过程，以及 `device_serial` 跟踪。
* **`mobile_diagnose`**：面向 IDE 的环境诊断工具。复用 `artemis doctor` 和 Web 控制台设备向导背后的就绪探针（Python 运行时、配置、LLM 凭据、ADB / 设备 / RSA 密钥 / 模拟器、视频工具链），外加 MCP 主机探针（服务器解释器与项目 `.venv`、检测到的 MCP 客户端、`.env` 位置、traces 目录、守护进程端口冲突）。返回 `verdict`（`ready` | `degraded` | `blocked`）、一份可供 AI 智能体按顺序执行的 `next_steps` 修复列表（可自行运行的单行 `Run:` 命令 vs 面向用户的 `Guidance:` 指引）、经过脱敏的逐项检查详情、`tasks` 中持有或等待设备的任务、日志路径，以及最近失败的任务及其 `recent_errors`。可选的深度检查：`verify_credentials=true`（实时校验 API 密钥，约 12 秒，结果在 `credentials` 中）、`probe_device=true`（端到端截图 + UIAutomator 层级，约 20 秒，结果在 `device_probe` 中）、`launch_avd="<name>"`（在后台启动已安装的 AVD；约 60 秒后重新运行）。`attempt_fix=true` 会应用安全的自修复（重新生成损坏的 ADB 密钥、重启 ADB 服务器、清除崩溃运行器遗留的陈旧设备锁 / 队列票据）。

### 📱 设备选择与多设备执行

ARTEMIS 支持跨多个已连接的 Android 设备和模拟器并行执行：

1. **直接指定设备**：显式提供 `device_serial`（例如 `device_serial="63191FDKX00062"` 或 `device_serial="emulator-5554"`）。每设备执行锁允许不同设备并行运行。
2. **自动选择设备**：省略 `device_serial`，让 ARTEMIS 从设备池中自动选择一个可用的就绪设备。

* **用户选择优先**：当连接了多个设备 / 模拟器时，AI 智能体应优先询问用户要在哪个设备上运行。
* **设备诊断**：随时通过 `adb devices` 或 `adb devices -l` 检查已连接的硬件、授权状态和序列号。

## 🚀 如何运行与配置

### CLI 执行

```bash
# 通过 stdio 启动服务器
python -m mcp_server

# 或者通过 Artemis CLI
uv run artemis mcp
```

### IDE 配置

#### 一键自动安装（推荐）

运行自动安装程序来检测并配置你的 IDE/智能体，也可指定单个目标，例如 `codebuddy`、`workbuddy` 或 `opencode`：

```bash
uv run artemis mcp --install all
# 或者专门为 Antigravity 安装：
uv run artemis mcp --install antigravity
```

#### 手动生成 JSON 配置

运行 `uv run artemis mcp --generate-config antigravity`（或 `all`），即可输出可直接使用的配置 JSON，其中已解析好 `.venv` 的 Python 路径和项目路径。
