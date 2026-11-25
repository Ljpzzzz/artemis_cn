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

"""Tests for surgical JSONC provider/model edits."""

from pathlib import Path

import pytest

from artemis.config.jsonc_edit import (
    JsoncEditError,
    read_model_config,
    replace_llm_provider_model,
    write_model_config,
)

SAMPLE = """{
  // top-level comment
  "default": {
    "provider": "google", // inline
    "model": "gemini-3.8-flash",
    "fallback": { "provider": "google", "model": "gemini-3.7-flash" }
  },
  "presets": {
    "hopper": { "provider": "google", "model": "should-not-change" }
  },
  "nodes": {
    "hopper": {
      "provider": "google",
      "model": "gemini-3.5-flash-lite",
      "fallback": { "provider": "google", "model": "gemini-3.1-flash-lite" }
    },
    "object_detector": {
      "provider": "google",
      "model": "gemini-robotics-er-2-preview"
    }
  }
}
"""


def test_replaces_only_target_blocks_and_preserves_comments():
    out = replace_llm_provider_model(
        SAMPLE,
        {
            "default": {"provider": "openai", "model": "qwen"},
            "hopper": {"provider": "anthropic", "model": "claude"},
        },
    )
    assert "// top-level comment" in out
    assert "// inline" in out
    assert "should-not-change" in out  # presets untouched
    assert '"model": "gemini-3.7-flash"' in out  # fallback untouched
    assert '"model": "gemini-3.1-flash-lite"' in out
    assert '"model": "qwen"' in out
    assert '"model": "claude"' in out
    assert '"provider": "anthropic"' in out
    # object_detector untouched
    assert '"model": "gemini-robotics-er-2-preview"' in out


def test_partial_update_only_changes_supplied_field():
    out = replace_llm_provider_model(SAMPLE, {"default": {"provider": "openai"}})
    assert '"provider": "openai"' in out
    assert '"model": "gemini-3.8-flash"' in out


def test_no_update_returns_identical_text():
    assert replace_llm_provider_model(SAMPLE, {}) == SAMPLE


def test_http_in_string_is_not_treated_as_comment():
    text = SAMPLE.replace('"model": "gemini-3.8-flash"', '"model": "http://example.com/model"')
    out = replace_llm_provider_model(text, {"default": {"provider": "openai"}})
    assert '"model": "http://example.com/model"' in out
    assert '"provider": "openai"' in out


def test_invalid_provider_rejected():
    with pytest.raises(JsoncEditError):
        replace_llm_provider_model(SAMPLE, {"default": {"provider": "evil"}})


def test_invalid_model_rejected():
    with pytest.raises(JsoncEditError):
        replace_llm_provider_model(SAMPLE, {"default": {"model": 'bad"name'}})


def test_unknown_key_rejected():
    with pytest.raises(JsoncEditError):
        replace_llm_provider_model(SAMPLE, {"bogus": {"provider": "openai"}})


def test_missing_block_rejected():
    with pytest.raises(JsoncEditError):
        replace_llm_provider_model('{"default": {}}', {"hopper": {"provider": "openai"}})


def test_write_and_read_roundtrip_preserves_crlf(tmp_path: Path):
    cfg = tmp_path / "artemis.jsonc"
    cfg.write_text(SAMPLE.replace("\n", "\r\n"), encoding="utf-8", newline="")
    result = write_model_config(
        cfg,
        {
            "hopper": {"provider": "openai", "model": "qwen-hop"},
            "object_detector": {"provider": "google", "model": "gemini-er"},
        },
    )
    written = cfg.read_text(encoding="utf-8", newline="")
    assert "\r\n" in written
    assert "// top-level comment" in written
    assert result["hopper"] == {"provider": "openai", "model": "qwen-hop"}
    assert result["object_detector"] == {"provider": "google", "model": "gemini-er"}
    # default derived from itself
    assert result["default"]["provider"] == "google"


def test_read_model_config_merges_default_into_nodes(tmp_path: Path):
    cfg = tmp_path / "artemis.jsonc"
    cfg.write_text(SAMPLE, encoding="utf-8", newline="")
    result = read_model_config(cfg)
    assert result["default"] == {"provider": "google", "model": "gemini-3.8-flash"}
    assert result["hopper"] == {"provider": "google", "model": "gemini-3.5-flash-lite"}
