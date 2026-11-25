# AGENTS.md

ARTEMIS：一个基于 Python 3.12+ 的自主多模态智能体，用于驱动真实的 Android 设备。项目附带一个
MCP 服务器（供 IDE 使用）、一个 Angular Showcase UI，以及一个 FastAPI 管理控制台。

## 环境与命令

使用 `uv` —— 绝不要直接用裸的 `pip`/`python`。`.venv` 和 `uv.lock` 是唯一事实来源。

```bash
make install          # uv sync --dev
make setup            # install + build-ui + precommit-install
make test             # 确定性测试套件；无需设备、凭据或云端
make lint             # ruff format --check -> ruff check -> quality ratchet
make format
make typecheck        # pyright --project pyright-core.json  （不是整个仓库）
make build-ui         # cd apps/showcase_ui && npm install && npm run build
make doctor           # 设备、ADB、工具链、配置诊断
```

单个测试：`uv run pytest tests/unit/test_cli.py::TestThing::test_case -q`。
运行某个包目录：`uv run pytest tests/tools -q`。修复 lint 错误时：`uv run ruff check <path>`。

`make typecheck` 只检查 `pyright-core.json` 中列出的约 10 个受保护模块。不要因为它通过就认为
整个仓库都具备类型安全。

## 测试分层（不要破坏这一点）

- `pytest.ini_options.testpaths` = `tests/unit`、`tests/tools`、`packages/artemis-client/tests`。
- 默认的 `addopts` 会排除标记 `integration, e2e, cloud, manual, android` —— 默认测试套件必须保持
  自包含（hermetic），在没有设备或 API 密钥的情况下也能收集（collectable）。
- `tests/conftest.py` 会按目录自动附加 `integration`/`e2e` 标记；其他标记
  （`android`、`cloud`、`manual`）必须显式添加。任何需要外部状态的测试都必须带有标记。
- 受门禁（gated）的测试套件：`make test-integration`（跨组件，可能需要配置模型凭据）、
  `make test-device`（Android/端到端，需要已连接且已授权的设备或模拟器）、`make test-all`（收集所有
  测试树，适用于完整配置的维护者环境）。任何需要外部状态的测试都必须带相应标记，且在依赖不可用时
  仍可安全收集（collectable）。

## 不易察觉的 CI 关卡

`.github/workflows/ci.yml` 在 ubuntu + windows 上按以下顺序运行：

1. `python scripts/check_dependency_sources.py` —— **如果 `uv.lock` 中有任何条目不是 PyPI
   `files.pythonhosted.org`，或 `package-lock.json` 中有任何条目不是 `registry.npmjs.org`，就会
   失败**。禁止使用私有/镜像源。
2. `uv sync --dev --locked` —— 因此依赖变更必须提交重新生成的 `uv.lock`。
3. `ruff format --check .`、`ruff check .`，然后是 `scripts/quality_ratchet.py`，再是 pyright。

Pre-commit 运行相同的 ruff 检查，外加 `quality-ratchet`。

**质量棘轮（Quality ratchet）**：如果 `except Exception`/`BaseException` 处理器、静默的宽泛
（broad）处理器，或 `# type: ignore` 注释的数量超过 `.quality-baseline.json` 中的计数
（当前为 754 / 0 / 18），`scripts/quality_ratchet.py` 就会失败。绝不要增加这些计数；不要在无关的
改动中"清理"已有的技术债。

## 代码风格（与默认配置不同）

Ruff 配置位于 `pyproject.toml`：行宽 100、双引号、`select = [E,F,TID,UP]`，
并且 **`ban-relative-imports = "all"` —— 始终使用绝对导入**（`from artemis.x import y`）。
E501/E402/E712/F401/F841 被忽略。

`pytest` 的 `pythonpath` 包含 `.`、`apps`、`apps/admin_console` —— 管理控制台的导入从这些根目录
以绝对路径解析。

## 目录结构

- `artemis/interfaces/cli/main.py` —— Typer 应用，即 `artemis` 控制台脚本。命令包括：`run`、
  `ui`、`init`、`doctor`、`batch`、`mcp`、`server`、`trace`、`helper`、`restart|stop|status`。
  `python -m artemis.main "<goal>"` 会被规范化为 `run "<goal>"`。
- `artemis/agents/` —— planner、operator、checker、explorer、flash、summarizer、validator 等。
- `artemis/graph/` —— LangGraph `StateGraph` 编排（`state.py`、`checkpoints.py`）。
- `artemis/drivers/` —— `android/`、`cloud/`、`mock/`，通过 `factory.py` 统一管理。测试中优先
  使用 mock driver（`tests/conftest.py::mock_driver`）。
- `artemis/runtime/` —— ADB 端点、设备池/锁、服务器生命周期、trace 存储。
- `artemis/config/` —— 单一配置入口（`paths.py`、`llm.py`、`agent.py`）以及环境变量常量。
  `artemis/config/paths.py` 决定可变状态是写入仓库还是操作系统用户目录；源码检出（source
  checkout）会将其保留在仓库内（`traces/`、`scratch/`）。
- `third_party/mobile_use/` —— 从 `minitap-ai/mobile-use` v3.6.3 ** vendored**（仅包含用到的
  部分）。`artemis/_legacy_imports.py` 是针对旧导入路径的 meta-path 兼容层；不要为它添加 stub。
- `mcp_server/` —— MCP 服务器（`python -m mcp_server`）；`mcp_server/rules.md` 是随 IDE 分发的、
  面向用户的智能体行为准则。
- `apps/showcase_ui/` —— Angular 22（Node 22.22.3）。`apps/admin_console/` —— FastAPI 管理后台。
- `packages/artemis-client/` —— 零依赖的远程客户端；目标是 **Python >=3.10**，与主包不同。请
  保持它不依赖任何第三方库。
- `config/artemis.jsonc` —— 智能体/模型的源配置，由 `setup.py` 暂存（stage）到 wheel 中。
  `artemis/resources/` 是构建产物，不要手动编辑。

## 执行架构：Flash 与 Pro

两种 profile 的差异决定了改动落在哪些文件，动手前先确认目标是哪条路径：

- **Flash**（`--profile flash`，~3–5s/步）：无图编排的 reactive observe-think-act 循环，由
  `artemis/agents/flash/runner.py` 驱动。无任务计划、无执行前安全检查、无 Checker、无最终报告、
  无 ADB shell。默认无轮次上限（`agent.flash.max_turns=0`），靠历史压缩而非截断控制上下文；与 Pro
  共享 transcript ledger（`T+mm:ss` 时钟、截图折叠为视觉摘要、旧步骤分块为 era，可经
  `search_history`/`replay_steps` 召回）。
- **Pro**（`--profile pro`，~15–40s/步）：`artemis/graph/` 的 LangGraph 多智能体图。**Planner**
  维护活的 Markdown 任务计划（含 `verify`/`assert` 检查项）；**Operator** 用完整工具集执行；Explorer
  感知层的 `flash`/`pro`/`ultra` 层级是**用户设置**（`config/artemis.jsonc` 的
  `pro.explorer.mode`/`flash.explorer_mode` 或 `--explorer-pro-mode`），**智能体不能自己选择**。
  单动作经过执行前 Safety Net（XML 优先、像素兜底），多动作 fast-action burst 连发对抗延迟；被阻断
  的动作产生 execution incident，由 Operator 自己在后续动作中恢复，**没有独立的修复 agent**。只读
  **Checker** 做 checkpoint 与退出审查（`--verification-level`: `off`/`final`（默认）/`checkpoints`/
  `strict`）。支持 100+ 步长任务、`[Loop:continuous]` 监控。

两者共享的历史压缩在 `artemis/memory/`：旧截图替换为视觉摘要、已完成步骤压缩为可检索块，阈值由
`agent.memory.*` 控制。

## 四大入口

- **CLI**：`uv run artemis run "<goal>"`（`--profile flash|pro`），直接在终端执行；
  `python -m artemis.main "<goal>"` 被规范化为 `run`。
- **Web UI**：`uv run artemis ui` → `http://localhost:8000`（Showcase UI + Admin Console）；生命周期用
  `artemis restart|stop|status` 管理。
- **MCP 服务器**：`python -m mcp_server`，让 IDE（Antigravity/Claude Code/Windsurf/Codex 等）通过
  MCP 驱动真机；`artemis mcp --install <client>` 安装配置，`--generate-config <client>` 输出片段。
- **Python SDK**：`packages/artemis-client`，零第三方依赖，目标 **Python >=3.10**（与主包不同），
  作为远程客户端嵌入 pytest/CI；保持它不依赖任何第三方库。

## 智能体行为规则与设备助手

- `mcp_server/rules.md` 是随 IDE 分发的**用户侧行为准则**（主动探索、Flash/Pro 路由、延迟补偿、
  "动态定位优先、坐标兜底"的定位模式）。`artemis mcp --install claude` 会装到
  `~/.claude/rules/artemis.md` —— **只装一处**，Claude Code 同时加载 `CLAUDE.md` 与
  `rules/*.md`，重复会浪费上下文。
- 首个任务会在设备上安装 **Artemis Accessibility Helper**（读取屏幕布局，不占用 UiAutomation 连接）；
  `artemis helper install|status|uninstall` 管理。`.env` 里 `ARTEMIS_HIERARCHY_BACKEND=uiautomator`
  改用 UIAutomator2，`ARTEMIS_HELPER_AUTO_INSTALL=false` 禁止自动安装。Helper 中途失败会自动回退到
  UIAutomator2，并在任务时间线/MCP 状态/最终报告中说明。

## 打包/特殊情况

如果缺少 Angular 的 dist 目录，`setup.py` 会在构建时报错 —— 因此在 `uv build` 之前先运行
`make build-ui`。wheel 会打包 `config/artemis.jsonc` 和 `artemis/resources/showcase_ui`。
可选的 Cython 编译通过 `USE_CYTHON=1` 选择启用。

## 运行时注意事项

- 将 `.env.example` 复制为 `.env`；设置至少一个提供商密钥（`GEMINI_API_KEY`/`GOOGLE_API_KEY`、
  `OPENAI_API_KEY`、`ANTHROPIC_API_KEY` 等）。
- 默认 profile 来自 `ARTEMIS_DEFAULT_PROFILE`（仓库默认：`flash`）；两条路径的差异见上文「执行架构」。
- `.roo/mcp.json` 是一个已提交的 IDE MCP 配置，指向当前检出的 `.venv`；可以安全地重新生成，
  但在 Windows 上要保持它指向 `.venv/Scripts/python.exe`。

## 文档

`README.md` / `README_CN.md`、`CONTRIBUTING.md`、`mcp_server/README.md`。`docs/` 仅存放图片。
