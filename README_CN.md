<p align="center">
  <img src="./docs/assets/artemis-banner-cn.png?v=7" alt="ARTEMIS Banner" width="100%" />
</p>

<p align="center">
  <strong>让 AI 助手与测试套件像人一样直接操作真机。</strong>
</p>

<p align="center">
  <a href="./README.md">English</a> •
  <a href="./README_CN.md"><b>中文文档</b></a> •
  <a href="#quick-start">快速上手</a> •
  <a href="#web-console">Web 控制台</a> •
  <a href="#configuration">配置</a> •
  <a href="#mcp-setup">MCP 接入</a> •
  <a href="#development">开发</a>
</p>

<p align="center">
  <a href="https://www.python.org/downloads/"><img src="https://img.shields.io/badge/Python-3.12+-3776AB.svg?logo=python&logoColor=white" alt="Python 3.12+"></a>
  <a href="LICENSE"><img src="https://img.shields.io/badge/License-Apache%202.0-blue.svg" alt="License: Apache-2.0"></a>
  <a href="https://modelcontextprotocol.io/"><img src="https://img.shields.io/badge/MCP-Native%20Server-8A2BE2.svg" alt="MCP Native"></a>
  <a href="https://github.com/google-research/android_world"><img src="https://img.shields.io/badge/AndroidWorld-99%25%2B%20SOTA-success.svg" alt="AndroidWorld SOTA"></a>
</p>

## ARTEMIS 是什么

ARTEMIS 是一个自主多模态智能体，通过自然语言目标驱动真实的 Android 设备。它运行在已连接的手机或模拟器上，结合无障碍树、OCR 与视觉模型进行元素定位，并提供两种执行模式：快速响应的 **Flash** 循环与带规划校验的 **Pro** 图编排。

本仓库在 ARTEMIS 上游基础上包含以下本地定制：

- **默认中文**——整个 Web 界面与所有面向用户的智能体输出默认简体中文，一个配置即可切回英文。
- **网页端配置模型**——直接在 Web 控制台编辑全局 API 端点与各节点模型，无需手工改文件。
- **全链路 OpenAI 兼容端点**——Hopper 与目标检测器可运行在 qwen（或任意 OpenAI 兼容模型）上，无需 Google API key。
- **我的笔记与我的任务**——用户自建笔记与可复用任务模板（含分组），持久化到后端 JSON 文件。

## 核心亮点

- **跨 App 自动化**：根据自然语言指令，在 Android 上执行测试流程和日常任务。
- **多模态定位**：优先使用元素索引，对自绘界面提供坐标和视觉定位兜底。
- **IDE 内诊断**：通过 **MCP 协议**，让 Antigravity、Claude Code、Windsurf 操作测试设备，收集 Logcat 输出和截图。
- **Flash 执行**：观察、思考、执行循环与异步历史摘要，单步通常约 **3–5 秒**。
- **Pro 探索**：单个动作执行前校验目标，支持对受阻动作的恢复；适用于长时间探索与稳定性测试。
- **AndroidWorld**：在 Google Research 的 100+ 多步任务基准上取得 **99%+ 任务完成率**。

## 快速上手

连接 Android 实体机（开启 **USB 调试**）或模拟器。一键启动脚本会自动安装 ADB、scrcpy、FFmpeg 与 Python（`uv`）依赖，并询问是否把 MCP 服务与 `rules.md` 挂载到你使用的 IDE。

```bash
# macOS / Linux
git clone https://github.com/google/artemis.git && cd artemis
./start.sh

# Windows PowerShell
git clone https://github.com/google/artemis.git
cd artemis
.\start.bat
```

> PowerShell 默认不会从当前目录查找可执行脚本——使用 `.\start.bat`（末尾不要加 `\`）。CMD 中使用 `start.bat`。

启动脚本会打开 `http://localhost:8000`。也可以直接用命令行运行任务：

```bash
uv run artemis run "打开系统设置并告诉我当前电量" --profile flash
```

运行任务前，请在 `.env` 中至少配置一个提供商密钥（见[配置](#configuration)）。

<a id="web-console"></a>
## Web 控制台

通过 `uv run artemis ui` 启动（8000 被占用时用 `--port <端口>`）。生命周期命令：`uv run artemis restart|stop|status`。

控制台有 **主页**（设置向导 + 任务启动）与 **工作区**（实时智能体流、任务队列、笔记）两个视图。所有文案均已汉化，语言由下述 `language` 配置决定。

### AI 模型设置（默认进入自定义配置）

设置向导的 AI 模型区块默认打开 **自定义配置** 卡片，提供可编辑字段，保存即写入文件：

| 字段 | 存储位置 | 说明 |
|---|---|---|
| `OPENAI_BASE_URL` | `.env` | 全局 OpenAI 兼容端点地址 |
| `OPENAI_API_KEY` | `.env` | 默认掩码显示；打开时从 `.env` 读取当前值 |
| 默认模型（provider + model） | `config/artemis.jsonc` | 应用于所有节点，除非单独覆盖 |
| Hopper（应用名解析） | `config/artemis.jsonc` | 仅 provider + model |
| 目标检测器（视觉定位） | `config/artemis.jsonc` | 仅 provider + model |

JSONC 编辑只更新目标块，**保留全部注释**。由于运行中的进程会缓存 LLM 配置，改动需重启服务才能生效——界面会显示"需要重启"提示并提供重启按钮。

> 目标检测器依赖像素级坐标定位。改用非 ER 视觉模型可能降低点击精度，切换后请用真实任务验证。

### 我的笔记

**笔记与计划** 面板有两个范围：

- **会话笔记**（只读）：当前会话中由智能体 `save_note` 工具生成的笔记。
- **我的笔记**（可编辑）：全局的用户自建笔记，可在界面上新建、编辑、删除。保存在 `traces/user_workspace.json`。

### 我的任务

推荐任务区除「全部 / Flash / Pro / 多应用 / 监控」外，新增 **我的任务** 分类。在该分类下可以：

- 创建**任务分组**；
- 向分组添加**自定义任务**（标题、目标、profile、标签）；
- 将已执行的会话保存为可复用模板（目标 + profile，并记录来源会话 ID）。

自定义任务会被转换成与内置推荐相同的结构，因此点击卡片即可把目标与 profile 填入任务输入框。用户数据保存在 `traces/user_workspace.json`，其中不会存储 API 密钥或设备序列号。

REST 端点：`GET/POST /api/workspace`、`PUT/DELETE /api/workspace/notes/{id}`，以及 `/api/workspace/task-groups/...` 用于分组与任务的增删改查。

<a id="configuration"></a>
## 配置

将 `.env.example` 复制为 `.env`，并至少配置一个提供商密钥。本仓库的 `config/artemis.jsonc` 默认使用 OpenAI 兼容的 qwen 端点（`OPENAI_BASE_URL` + `OPENAI_API_KEY`）。

### 语言

```jsonc
"agent": {
  "language": "zh-CN"   // "zh-CN"（默认）或 "en"
}
```

`ARTEMIS_LANGUAGE=en` 可在运行时覆盖 JSONC 的值。它同时控制 Web 界面文案与所有面向用户的智能体输出（最终答复、思考、里程碑文字、校验结论、委员会辩论）。机器可读标记——如 `- [ ]`、`[Loop]`、`- verify:`、`- assert:` 等计划语法、枚举值、工具名与 JSON 键——在两种语言下都保持 ASCII 英文。

### 运行模式

- `--profile flash`：快速响应循环，无图编排，无任务计划与最终报告。默认值，来自 `ARTEMIS_DEFAULT_PROFILE`。
- `--profile pro`：多智能体图，含 Planner、Operator、Safety Net 与 Checker。

完整的架构、入口、测试分层与智能体规则见 [AGENTS.md](./AGENTS.md)。

## 四种入口

- **CLI**：`uv run artemis run "<目标>"`（`--profile flash|pro`）。
- **Web UI**：`uv run artemis ui` → `http://localhost:8000`。
- **MCP 服务器**：`python -m mcp_server`；`uv run artemis mcp --install <client>`。
- **Python SDK**：`packages/artemis-client`，零第三方依赖，目标 Python >=3.10。

<a id="mcp-setup"></a>
<details>
<summary><b>Codex / Antigravity / Claude Code / Windsurf MCP 配置</b></summary>

<br>

ARTEMIS 内置原生 MCP 服务器。一键安装：

```bash
uv run artemis mcp --install antigravity
uv run artemis mcp --install all
```

手动配置示例，Codex（`~/.codex/config.toml`）：

```toml
[mcp_servers.artemis]
command = "/path/to/artemis/.venv/bin/python"
args = ["-m", "mcp_server"]
cwd = "/path/to/artemis"

[mcp_servers.artemis.env]
PYTHONUNBUFFERED = "1"
PYTHONPATH = "/path/to/artemis"
```

将 `mcp_server/rules.md` 挂载到你的 IDE 规则中，可获得移动端测试思维准则（主动探索、Flash/Pro 路由、"动态优先、坐标兜底"的定位模式）。Claude Code：`artemis mcp --install claude` 会安装到 `~/.claude/rules/artemis.md`，只安装到一处即可。

详见 [mcp_server/README.md](./mcp_server/README.md)。

</details>

<details>
<summary><b>Python SDK 示例</b></summary>

<br>

```bash
uv add "artemis-client @ git+https://github.com/google/artemis.git#subdirectory=packages/artemis-client"
```

```python
import asyncio
from artemis_client import ArtemisClient

async def main():
    client = ArtemisClient("http://artemis-host:8000", default_profile="flash")
    result = await client.run("打开系统设置，验证电池页面没有崩溃弹窗")
    assert result.succeeded, f"执行失败: {result.error or result.status}"
    print(f"通过 | 设备: {result.device_serial} | trace: {result.trace_id}")

asyncio.run(main())
```

</details>

## ARTEMIS 会在手机上安装什么

首次在某台设备上执行任务时，ARTEMIS 会安装 **Artemis Accessibility Helper**：一个用于读取屏幕布局的小型无障碍服务，不占用 UiAutomation 连接。手机上会出现折叠的"Artemis test helper is running"通知以及"设置 > 无障碍"中的新条目，都是它。它只监听手机本机，不向外发送数据。

- 预先安装：`uv run artemis helper install`
- 查看状态：`uv run artemis helper status` / `uv run artemis doctor`
- 移除：`uv run artemis helper uninstall`
- 改用 UIAutomator2：在 `.env` 中设置 `ARTEMIS_HIERARCHY_BACKEND=uiautomator`
- 禁止自动安装：在 `.env` 中设置 `ARTEMIS_HELPER_AUTO_INSTALL=false`

<a id="development"></a>
## 开发

使用 `uv`——不要直接用裸的 `pip`/`python`。`.venv` 与 `uv.lock` 是唯一事实来源。

```bash
make install       # uv sync --dev
make setup         # install + build-ui + precommit-install
make test          # 确定性测试套件，无需设备与凭据
make lint          # ruff format --check -> ruff check -> quality ratchet
make format
make typecheck     # pyright --project pyright-core.json
make build-ui      # Angular 构建
make doctor        # 设备 / ADB / 工具链诊断
```

单个测试：`uv run pytest tests/unit/test_cli.py::TestThing::test_case -q`。
运行某个包目录：`uv run pytest tests/tools -q`。

受门禁的测试套件：`make test-integration`（可能需要模型凭据）、`make test-device`（需要已连接且已授权的设备）、`make test-all`（完整环境）。

> Angular CLI 要求 Node >= 24.15。若系统 Node 版本较低，可通过
> `npm exec --yes --package=node@24.15.0 -- node ./node_modules/@angular/cli/bin/ng.js build` 构建。

### 架构要点

- `artemis/agents/` —— planner、operator、checker、explorer、flash、summarizer、validator。
- `artemis/graph/` —— LangGraph `StateGraph` 编排。
- `artemis/drivers/` —— android / cloud / mock，由 `factory.py` 统一管理。
- `artemis/runtime/` —— ADB 端点、设备池/锁、服务器生命周期、trace 存储。
- `artemis/config/` —— 统一配置入口与环境变量常量。
- `apps/showcase_ui/` —— Angular 22 控制台；`apps/admin_console/` —— FastAPI 后端。
- `apps/admin_console/services/user_workspace_service.py` —— 我的笔记 / 我的任务的 JSON 持久化。
- `artemis/config/jsonc_edit.py` —— 保留注释的 JSONC 编辑。
- `packages/artemis-client/` —— 零依赖远程客户端（Python >=3.10）。
- `third_party/mobile_use/` —— vendored 的 mobile-use v3.6.3 子集。

## 基准评测

ARTEMIS 在 Google Research 的 [AndroidWorld](https://github.com/google-research/android_world) 基准评测（20+ 款应用、100+ 多步任务）中取得 **99%+ 任务完成率**。

## 开源许可证

基于 [Apache License 2.0](LICENSE) 开源。第三方代码位于 `third_party/` 下，每个上游项目一个子目录，各自附带 `LICENSE` 与 `METADATA`。

## 致谢

本项目源自 [google/artemis](https://github.com/google/artemis)，基于 Apache License 2.0 开源。
