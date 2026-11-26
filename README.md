<p align="center">
  <img src="./docs/assets/artemis-banner.png?v=7" alt="ARTEMIS Banner" width="100%" />
</p>

<p align="center">
  <strong>Let AI assistants and test suites use real phones like a human.</strong>
</p>

<p align="center">
  <a href="./README.md"><b>English</b></a> •
  <a href="./README_CN.md">中文文档</a> •
  <a href="#quick-start">Quick Start</a> •
  <a href="#web-console">Web Console</a> •
  <a href="#configuration">Configuration</a> •
  <a href="#mcp-setup">MCP Setup</a> •
  <a href="#development">Development</a>
</p>

<p align="center">
  <a href="https://www.python.org/downloads/"><img src="https://img.shields.io/badge/Python-3.12+-3776AB.svg?logo=python&logoColor=white" alt="Python 3.12+"></a>
  <a href="LICENSE"><img src="https://img.shields.io/badge/License-Apache%202.0-blue.svg" alt="License: Apache-2.0"></a>
  <a href="https://modelcontextprotocol.io/"><img src="https://img.shields.io/badge/MCP-Native%20Server-8A2BE2.svg" alt="MCP Native"></a>
  <a href="https://github.com/google-research/android_world"><img src="https://img.shields.io/badge/AndroidWorld-99%25%2B%20SOTA-success.svg" alt="AndroidWorld SOTA"></a>
</p>

## What is ARTEMIS

ARTEMIS is an autonomous multimodal agent that drives real Android devices from natural-language goals. It runs on a connected phone or emulator, combines accessibility hierarchies, OCR and vision models for element locating, and supports two execution profiles: a fast reactive **Flash** loop and a planning/verification **Pro** graph.

This checkout carries a set of local customizations on top of upstream ARTEMIS:

- **Chinese by default** — the whole Web UI and all user-facing agent output default to Simplified Chinese, switchable to English with one setting.
- **In-browser model configuration** — edit the global API endpoint and per-node models from the Web Console, no manual file editing.
- **OpenAI-compatible endpoints everywhere** — Hopper and Object Detector can run on qwen (or any OpenAI-compatible model) without a Google API key.
- **My Notes and My Tasks** — user-authored notes and reusable task templates with groups, persisted in a backend JSON file.

## Core highlights

- **Cross-app automation**: execute test flows and everyday tasks on Android from natural-language instructions.
- **Multimodal targeting**: element indices first, with coordinate and visual fallbacks for custom Canvas/Compose/Flutter UIs.
- **IDE diagnostics**: an MCP server lets Antigravity, Claude Code and Windsurf drive devices and collect Logcat and screenshots.
- **Flash execution**: observe-think-act loop with async history summaries, typically ~3–5 s per step.
- **Pro exploration**: pre-action checks and recovery for blocked actions; long-running exploratory and stability tests.
- **AndroidWorld**: 99%+ task completion on Google Research's 100+ multi-step benchmark.

## Quick start

Connect an Android device (USB Debugging enabled) or emulator. The one-click launcher installs ADB, scrcpy, FFmpeg and Python (`uv`) dependencies, and offers to mount the MCP server and `rules.md` into detected IDEs.

```bash
# macOS / Linux
git clone https://github.com/google/artemis.git && cd artemis
./start.sh

# Windows PowerShell
git clone https://github.com/google/artemis.git
cd artemis
.\start.bat
```

> PowerShell does not search the current directory for executable scripts — use `.\start.bat` (no trailing `\`). In CMD use `start.bat`.

The launcher opens `http://localhost:8000`. You can also run a task directly:

```bash
uv run artemis run "Open Settings and tell me the battery level" --profile flash
```

Before running a task, set at least one provider key in `.env` (see [Configuration](#configuration)).

<a id="web-console"></a>
## Web Console

Start the console with `uv run artemis ui` (use `--port <n>` if 8000 is taken). Lifecycle commands: `uv run artemis restart|stop|status`.

The console has two views — **Home** (setup guide + task launcher) and **Workspace** (live agent stream, task queue, notes). All copy is localized; the language follows the `language` setting described below.

### AI Model Setup (custom configuration by default)

The setup guide's AI Model section opens on the **Custom Configuration** card. It provides editable fields, all persisted on save:

| Field | Stored in | Notes |
|---|---|---|
| `OPENAI_BASE_URL` | `.env` | Global OpenAI-compatible endpoint base URL |
| `OPENAI_API_KEY` | `.env` | Masked by default; values are loaded from `.env` on open |
| Default model (provider + model) | `config/artemis.jsonc` | Applied to all nodes unless overridden |
| Hopper (app-name resolver) | `config/artemis.jsonc` | provider + model only |
| Object Detector (visual grounding) | `config/artemis.jsonc` | provider + model only |

The JSONC editor updates only the target blocks and **preserves all comments**. Because the running process caches LLM config, a server restart is required for changes to take effect — the UI shows a "restart required" hint with a restart button.

> Object Detector relies on pixel-level coordinate grounding. A non-ER vision model may reduce tap accuracy — verify with real tasks when switching away from an ER model.

### My Notes

The **Notes & Plans** panel has two scopes:

- **Session Notes** (read-only): notes generated by the agent's `save_note` tool for the current session.
- **My Notes** (editable): global, user-authored notes. Create, edit and delete notes from the UI. Stored in `traces/user_workspace.json`.

### My Tasks

The recommendation area includes a **My Tasks** category alongside All / Flash / Pro / Multi-App / Monitor. In this category you can:

- create **task groups**;
- add **custom tasks** (title, goal, profile, tag) to a group;
- save an executed session as a reusable template (its goal + profile, with the source session id recorded).

Custom tasks are flattened into the same shape as built-in suggestions, so clicking a card fills the goal and profile into the launcher. User data lives in `traces/user_workspace.json`; no API keys or device serials are stored there.

REST endpoints: `GET/POST /api/workspace`, `PUT/DELETE /api/workspace/notes/{id}`, and `/api/workspace/task-groups/...` for group and task CRUD.

<a id="configuration"></a>
## Configuration

Copy `.env.example` to `.env` and set at least one provider key. This checkout's `config/artemis.jsonc` uses an OpenAI-compatible qwen endpoint by default (`OPENAI_BASE_URL` + `OPENAI_API_KEY`).

### Language

```jsonc
"agent": {
  "language": "zh-CN"   // "zh-CN" (default) or "en"
}
```

`ARTEMIS_LANGUAGE=en` overrides the JSONC value at runtime. It controls both the Web UI copy and all user-facing agent text (final answers, thoughts, plan milestones, checker verdicts, committee debate). Machine-readable tokens — plan syntax such as `- [ ]` / `[Loop]` / `- verify:` / `- assert:`, enum values, tool names and JSON keys — stay ASCII in either language.

### Profiles

- `--profile flash`: fast reactive loop, no graph, no task plan or final report. Default, from `ARTEMIS_DEFAULT_PROFILE`.
- `--profile pro`: multi-agent graph with Planner, Operator, Safety Net and Checker.

See [AGENTS.md](./AGENTS.md) for the full architecture, entry points, test layers and agent rules.

## Entry points

- **CLI**: `uv run artemis run "<goal>"` (`--profile flash|pro`).
- **Web UI**: `uv run artemis ui` → `http://localhost:8000`.
- **MCP server**: `python -m mcp_server`; `uv run artemis mcp --install <client>`.
- **Python SDK**: `packages/artemis-client`, zero third-party dependencies, Python >=3.10.

<a id="mcp-setup"></a>
<details>
<summary><b>MCP setup for Codex / Antigravity / Claude Code / Windsurf</b></summary>

<br>

ARTEMIS ships a native MCP server. One-click install:

```bash
uv run artemis mcp --install antigravity
uv run artemis mcp --install all
```

Manual configuration, e.g. Codex (`~/.codex/config.toml`):

```toml
[mcp_servers.artemis]
command = "/path/to/artemis/.venv/bin/python"
args = ["-m", "mcp_server"]
cwd = "/path/to/artemis"

[mcp_servers.artemis.env]
PYTHONUNBUFFERED = "1"
PYTHONPATH = "/path/to/artemis"
```

Mount `mcp_server/rules.md` into your IDE rules for the mobile-testing mindset (active exploration, Flash/Pro routing, dynamic-first coordinate-fallback locating). Claude Code: `artemis mcp --install claude` installs to `~/.claude/rules/artemis.md` — install to one location only.

See [mcp_server/README.md](./mcp_server/README.md) for details.

</details>

<details>
<summary><b>Python SDK example</b></summary>

<br>

```bash
uv add "artemis-client @ git+https://github.com/google/artemis.git#subdirectory=packages/artemis-client"
```

```python
import asyncio

from artemis_client import ArtemisClient


async def main():
    client = ArtemisClient("http://artemis-host:8000", default_profile="flash")
    result = await client.run("Open Settings and verify the battery page has no crash dialogs")
    assert result.succeeded, f"Failed: {result.error or result.status}"
    print(f"Passed | device: {result.device_serial} | trace: {result.trace_id}")


asyncio.run(main())
```

</details>

## What ARTEMIS installs on the phone

The first task on a device installs the **Artemis Accessibility Helper**, an accessibility service that reads screen layout without taking the UiAutomation connection. You will see a collapsed "Artemis test helper is running" notification and a Settings > Accessibility entry; both are the helper. It listens only on the device and sends nothing elsewhere.

- Pre-install: `uv run artemis helper install`
- Status: `uv run artemis helper status` / `uv run artemis doctor`
- Remove: `uv run artemis helper uninstall`
- Use UIAutomator2 instead: `ARTEMIS_HIERARCHY_BACKEND=uiautomator` in `.env`
- Disable auto-install: `ARTEMIS_HELPER_AUTO_INSTALL=false` in `.env`

<a id="development"></a>
## Development

Use `uv` — never bare `pip`/`python`. `.venv` and `uv.lock` are the source of truth.

```bash
make install       # uv sync --dev
make setup         # install + build-ui + precommit-install
make test          # hermetic deterministic suite (no device or credentials)
make lint          # ruff format --check -> ruff check -> quality ratchet
make format
make typecheck     # pyright --project pyright-core.json
make build-ui      # Angular build
make doctor        # device / ADB / toolchain diagnostics
```

Single test: `uv run pytest tests/unit/test_cli.py::TestThing::test_case -q`.
A package: `uv run pytest tests/tools -q`.

Gated suites: `make test-integration` (may need model credentials), `make test-device` (attached authorized device), `make test-all` (fully provisioned environment).

> The Angular CLI requires Node >= 24.15. If the system Node is older, run the build via
> `npm exec --yes --package=node@24.15.0 -- node ./node_modules/@angular/cli/bin/ng.js build`.

### Architecture notes

- `artemis/agents/` — planner, operator, checker, explorer, flash, summarizer, validator.
- `artemis/graph/` — LangGraph `StateGraph` orchestration.
- `artemis/drivers/` — android / cloud / mock via `factory.py`.
- `artemis/runtime/` — ADB endpoints, device pool/lock, server lifecycle, trace storage.
- `artemis/config/` — single config entry plus env constants.
- `apps/showcase_ui/` — Angular 22 console; `apps/admin_console/` — FastAPI backend.
- `apps/admin_console/services/user_workspace_service.py` — JSON persistence for My Notes / My Tasks.
- `artemis/config/jsonc_edit.py` — comment-preserving JSONC edits.
- `packages/artemis-client/` — zero-dependency remote client (Python >=3.10).
- `third_party/mobile_use/` — vendored subset of mobile-use v3.6.3.

## Benchmarks

ARTEMIS achieves 99%+ completion on Google Research's [AndroidWorld](https://github.com/google-research/android_world) benchmark (20+ apps, 100+ multi-step tasks).

## License

Apache License 2.0. Third-party code lives under `third_party/`, one directory per upstream project with its own `LICENSE` and `METADATA`.

## Acknowledgments

This project is derived from [google/artemis](https://github.com/google/artemis), licensed under the Apache License 2.0.
