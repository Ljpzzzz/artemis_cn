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

"""Surgical edits to the LLM provider/model blocks of artemis.jsonc.

The config file is heavily commented, and the repository has no JSONC dumper.
A full parse + dump would destroy every comment, so this module edits only the
target blocks in-place, preserving all other bytes (including comments and
line endings). String/comment state is tracked while locating brace boundaries
so a ``http://`` inside a JSON string is never mistaken for a ``//`` comment.
"""

from __future__ import annotations

import os
from pathlib import Path
import re
import tempfile

__all__ = [
    "PROVIDERS",
    "JsoncEditError",
    "read_model_config",
    "replace_llm_provider_model",
    "write_model_config",
]

PROVIDERS = frozenset({"google", "openai", "anthropic", "openrouter", "xai", "ollama", "custom"})


class JsoncEditError(ValueError):
    """Raised when a config edit would be invalid or cannot be located."""


def _validate(updates: dict[str, dict[str, str]]) -> None:
    allowed_keys = {"default", "hopper", "object_detector"}
    for key, fields in updates.items():
        if key not in allowed_keys:
            raise JsoncEditError(f"Unknown config key: {key}")
        if not isinstance(fields, dict):
            raise JsoncEditError(f"Fields for {key} must be an object")
        for field, value in fields.items():
            if field not in ("provider", "model"):
                raise JsoncEditError(f"Unknown field: {field}")
            if not isinstance(value, str):
                raise JsoncEditError(f"{key}.{field} must be a string")
            if field == "provider" and value.strip().lower() not in PROVIDERS:
                raise JsoncEditError(f"Invalid provider: {value}")
            if field == "model" and (
                not value.strip() or '"' in value or "\n" in value or "\r" in value
            ):
                raise JsoncEditError(f"Invalid model name: {value!r}")


def _find_block(text: str, key: str, *, within: tuple[int, int] | None = None) -> tuple[int, int]:
    """Return (start, end) char offsets of the object following ``"key": {``."""
    search_start, search_end = within if within else (0, len(text))
    pattern = re.compile(r'"' + re.escape(key) + r'"\s*:\s*\{')
    m = pattern.search(text, search_start, search_end)
    if m is None:
        raise JsoncEditError(f"Config key not found: {key}")
    open_brace = m.end() - 1

    depth = 0
    i = open_brace
    in_string = False
    in_line_comment = False
    in_block_comment = False
    escaped = False
    while i < len(text):
        c = text[i]
        nxt = text[i + 1] if i + 1 < len(text) else ""
        if in_line_comment:
            if c in ("\n", "\r"):
                in_line_comment = False
            i += 1
            continue
        if in_block_comment:
            if c == "*" and nxt == "/":
                in_block_comment = False
                i += 2
                continue
            i += 1
            continue
        if in_string:
            if escaped:
                escaped = False
            elif c == "\\":
                escaped = True
            elif c == '"':
                in_string = False
            i += 1
            continue
        # normal
        if c == "/":
            if nxt == "/":
                in_line_comment = True
                i += 2
                continue
            if nxt == "*":
                in_block_comment = True
                i += 2
                continue
        if c == '"':
            in_string = True
            i += 1
            continue
        if c == "{":
            depth += 1
        elif c == "}":
            depth -= 1
            if depth == 0:
                return open_brace, i + 1
        i += 1
    raise JsoncEditError(f"Unbalanced braces for config key: {key}")


def _replace_field(block: str, field: str, value: str) -> str | None:
    """Replace ``"field": "..."`` inside a block. Returns None if not found."""
    pattern = re.compile(r'("' + field + r'"\s*:\s*)"[^"]*"')
    if pattern.search(block):
        return pattern.sub(lambda m: m.group(1) + '"' + value + '"', block, count=1)
    return None


def replace_llm_provider_model(text: str, updates: dict[str, dict[str, str]]) -> str:
    """Return ``text`` with provider/model updated for the requested blocks.

    ``updates`` maps a config key (``default`` / ``hopper`` / ``object_detector``)
    to a dict of ``{"provider": ..., "model": ...}``. Only supplied fields are
    changed; all other content (comments, fallback, line endings) is preserved.
    """
    _validate(updates)
    result = text

    for key in ("default", "hopper", "object_detector"):
        fields = updates.get(key)
        if not fields:
            continue
        # Re-resolve offsets each iteration: earlier edits may shift char positions.
        span = None
        if key in ("hopper", "object_detector"):
            span = _find_block(result, "nodes")
        start, end = _find_block(result, key, within=span)
        block = result[start:end]
        for field, value in fields.items():
            updated = _replace_field(block, field, value)
            if updated is None:
                raise JsoncEditError(f"Config key {key} has no '{field}' field")
            block = updated
        result = result[:start] + block + result[end:]

    # Guard: the result must still parse.
    try:
        load_jsonc_from_string(result)
    except ValueError as exc:
        raise JsoncEditError(f"Edited config is not valid JSONC: {exc}") from exc
    return result


def _strip_comments(text: str) -> str:
    """Strip // and /* */ comments while respecting JSON string literals.

    The vendored ``strip_json_comments`` is regex-based and would corrupt a
    string containing ``http://``; this scanner tracks string state instead.
    """
    out = []
    i = 0
    n = len(text)
    in_string = False
    escaped = False
    while i < n:
        c = text[i]
        nxt = text[i + 1] if i + 1 < n else ""
        if in_string:
            out.append(c)
            if escaped:
                escaped = False
            elif c == "\\":
                escaped = True
            elif c == '"':
                in_string = False
            i += 1
            continue
        if c == '"':
            in_string = True
            out.append(c)
            i += 1
            continue
        if c == "/" and nxt == "/":
            while i < n and text[i] not in ("\n", "\r"):
                i += 1
            continue
        if c == "/" and nxt == "*":
            i += 2
            while i + 1 < n and not (text[i] == "*" and text[i + 1] == "/"):
                i += 1
            i = min(i + 2, n)
            continue
        out.append(c)
        i += 1
    return "".join(out)


def load_jsonc_from_string(text: str):
    """Parse JSONC from a string (load_jsonc only accepts a file)."""
    import json

    return json.loads(_strip_comments(text))


def read_model_config(config_path: Path) -> dict:
    """Read the config and return merged provider/model for the editor."""
    parsed = load_jsonc_from_string(config_path.read_text(encoding="utf-8", newline=""))
    default = dict(parsed.get("default") or {})
    nodes = parsed.get("nodes") or {}
    result = {}
    for key in ("default", "hopper", "object_detector"):
        base = default if key == "default" else {**default, **(nodes.get(key) or {})}
        result[key] = {
            "provider": base.get("provider"),
            "model": base.get("model"),
        }
    return result


def write_model_config(config_path: Path, updates: dict[str, dict[str, str]]) -> dict:
    """Atomically apply provider/model updates, preserving comments/line endings."""
    with open(config_path, encoding="utf-8", newline="") as fh:
        original = fh.read()
    edited = replace_llm_provider_model(original, updates)
    # Atomic write in the same directory so os.replace stays on one filesystem.
    fd, tmp_name = tempfile.mkstemp(
        dir=str(config_path.parent), prefix=".artemis-cfg-", suffix=".tmp"
    )
    try:
        with os.fdopen(fd, "w", encoding="utf-8", newline="") as fh:
            fh.write(edited)
        os.replace(tmp_name, config_path)
    except OSError:
        try:
            os.unlink(tmp_name)
        except OSError:
            pass
        raise
    return read_model_config(config_path)
