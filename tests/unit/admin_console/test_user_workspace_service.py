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

"""Tests for user workspace JSON persistence."""

import json
from pathlib import Path

import pytest

import apps.admin_console.services.user_workspace_service as mod
from apps.admin_console.services.user_workspace_service import (
    WorkspaceError,
    UserWorkspaceService,
)


@pytest.fixture
def workspace(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setattr(mod, "WORKSPACE_PATH", tmp_path / "user_workspace.json")
    return UserWorkspaceService()


def test_empty_by_default(workspace):
    assert workspace.get_all() == {"notes": [], "task_groups": []}


def test_note_crud(workspace):
    note = workspace.create_note("Title", "Body")
    assert note["title"] == "Title" and note["content"] == "Body"
    assert workspace.list_notes()[0]["id"] == note["id"]

    updated = workspace.update_note(note["id"], title="New", content=None)
    assert updated["title"] == "New" and updated["content"] == "Body"

    assert workspace.delete_note(note["id"]) is True
    assert workspace.delete_note(note["id"]) is False
    assert workspace.list_notes() == []


def test_group_and_task_crud(workspace):
    group = workspace.create_group("My group")
    task_data = {
        "title": "Open WeChat",
        "description": "desc",
        "goal": "打开微信",
        "profile": "flash",
        "category": "all",
        "tag": "WeChat",
        "expected_output": "",
        "source_session_id": None,
    }
    group2, task = workspace.create_task(group["id"], task_data)
    assert group2["id"] == group["id"] and task["title"] == "Open WeChat"

    assert workspace.update_task(group["id"], task["id"], {"goal": "新目标"})["goal"] == "新目标"
    assert workspace.delete_task(group["id"], task["id"]) is True
    assert workspace.update_group(group["id"], "Renamed")["name"] == "Renamed"
    assert workspace.delete_group(group["id"]) is True
    assert workspace.list_groups() == []


def test_missing_ids_raise(workspace):
    with pytest.raises(WorkspaceError):
        workspace.update_note("missing", "t", None)
    with pytest.raises(WorkspaceError):
        workspace.create_task("missing", {"title": "x"})
    with pytest.raises(WorkspaceError):
        workspace.update_group("missing", "x")


def test_persistence_survives_new_instance(tmp_path, monkeypatch):
    monkeypatch.setattr(mod, "WORKSPACE_PATH", tmp_path / "ws.json")
    svc = UserWorkspaceService()
    svc.create_note("persist me", "body")
    svc.create_group("g")

    reloaded = UserWorkspaceService()
    assert reloaded.list_notes()[0]["title"] == "persist me"
    assert reloaded.list_groups()[0]["name"] == "g"
    data = json.loads((tmp_path / "ws.json").read_text(encoding="utf-8"))
    assert data["version"] == 1


def test_corrupt_file_is_backed_up_and_returns_empty(tmp_path, monkeypatch):
    path = tmp_path / "ws.json"
    path.write_text("{not json", encoding="utf-8")
    monkeypatch.setattr(mod, "WORKSPACE_PATH", path)

    svc = UserWorkspaceService()
    assert svc.get_all() == {"notes": [], "task_groups": []}
    assert list(tmp_path.glob("ws.json.corrupt-*"))


def test_unicode_roundtrip(workspace):
    workspace.create_note("中文标题", "内容\n第二行 🎉")
    assert workspace.list_notes()[0]["content"] == "内容\n第二行 🎉"
