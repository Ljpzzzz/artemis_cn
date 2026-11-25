# Copyright 2026 Google LLC
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""Helpers for assembling tool references into otherwise-static prompts.

Prompts stay hand-written text; only the spots that mention tools are assembled:

* **Enumeration slots** -- lists like ``(`click`, `swipe`, ... , or `wait_for_delay`)``
  are re-rendered from the actually-available tool set, so an absent tool never
  appears. With the full tool set the rendering reproduces the original wording
  byte-for-byte (ordering, backticks, Oxford ``or``/``and``), which is what the
  regression tests pin.
* **Instruction segments** -- self-contained blocks that teach one tool (e.g. the
  ``manage_app`` app-launching rule) are included only while that tool exists.

An unavailable tool therefore leaves no trace in the prompt at all -- the executable
definition of "an unimplemented tool must cost the model nothing".
"""

from collections.abc import Iterable, Sequence, Set
from functools import lru_cache

__all__ = [
    "gate_segment",
    "language_directive",
    "render_tool_enum",
    "resolve_available",
    "resolved_language_directive",
    "user_facing_text",
]

#: One shared directive appended to the system prompt of user-facing agents.
#: Machine-readable protocol tokens stay ASCII so downstream parsers are safe.
_ZH_LANGUAGE_DIRECTIVE = (
    "\n\n## 输出语言（Output Language）\n"
    "请以简体中文（Simplified Chinese）撰写所有面向用户的自然语言内容，包括：最终答复、"
    "思考过程、计划中的里程碑文字、`save_note` 笔记正文、校验结论的 evidence/suggestion、"
    "以及委员会辩论发言。\n"
    "务必保持以下机器可读标记原样为 ASCII 英文，不要翻译：计划语法 `- [ ]` / `[/]` / "
    "`[x]` / `[!]`、`[Loop]` 与 `[Loop:continuous]` 标签、`- verify:` / `- assert:` / "
    "`- assert@end:` / `- finding:` 行、枚举值 `passed` / `failed` / `inconclusive`、"
    "`on_complete` / `at_end`、`completed` / `failed`、所有工具名、参数名与 JSON 键。"
)


def language_directive(language: str) -> str:
    """Return the system-prompt directive for ``language``.

    ``zh-CN`` yields the Simplified Chinese instruction; every other value
    (including ``en``) yields an empty string so English runs pay zero tokens
    and byte-pinned English templates stay unchanged.
    """
    if str(language).strip().lower() == "zh-cn":
        return _ZH_LANGUAGE_DIRECTIVE
    return ""


@lru_cache(maxsize=1)
def _configured_language() -> str:
    """Read the configured user-facing language (function-local import avoids cycles)."""
    from artemis.config.agent import load_agent_config

    return load_agent_config().language


def resolved_language_directive() -> str:
    """Directive from the active config; cached so file I/O happens once per process.

    ``ARTEMIS_LANGUAGE`` (read by the config validator) overrides the JSONC value.
    A failure to load config falls back to English (empty directive) rather than
    crashing an agent.
    """
    try:
        return language_directive(_configured_language())
    except (OSError, ValueError):
        return ""


def user_facing_text(english: str, chinese: str) -> str:
    """Return ``chinese`` when the configured output language is zh-CN, else ``english``.

    For fixed harness-generated strings that no LLM prompt produces (so the
    language directive cannot reach them).
    """
    try:
        return chinese if str(_configured_language()).strip().lower() == "zh-cn" else english
    except (OSError, ValueError):
        return english


def render_tool_enum(
    tools: Sequence[str],
    available: Set[str],
    final_sep: str | None = None,
) -> str:
    """Renders an ordered, backticked tool enumeration limited to available tools.

    Args:
        tools: Tool names in the exact order the prompt historically used.
        available: Tools that currently exist.
        final_sep: ``"or"``/``"and"`` to join the last item Oxford-style
            (``"`a`, `b`, or `c`"``); ``None`` for a plain comma list.

    Returns:
        The rendered enumeration, or ``""`` when none of the tools are available.
    """
    ticked = [f"`{name}`" for name in tools if name in available]
    if not ticked:
        return ""
    if len(ticked) == 1:
        return ticked[0]
    if final_sep is None:
        return ", ".join(ticked)
    if len(ticked) == 2:
        return f"{ticked[0]} {final_sep} {ticked[1]}"
    return ", ".join(ticked[:-1]) + f", {final_sep} " + ticked[-1]


def gate_segment(segment: str, available: Set[str], *tools: str) -> str:
    """Returns ``segment`` when every tool it teaches is available, else ``""``."""
    if all(name in available for name in tools):
        return segment
    return ""


def resolve_available(available: Iterable[str] | None, full_set: Set[str]) -> Set[str]:
    """Normalizes an optional availability argument.

    ``None`` means "everything" -- callers that have no actuator wired yet keep
    today's output unchanged. Passing an explicit set opts into assembly.
    """
    if available is None:
        return full_set
    return frozenset(available)
