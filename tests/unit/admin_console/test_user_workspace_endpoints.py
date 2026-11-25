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

"""Endpoint tests for the user workspace (notes + custom task groups)."""

from pathlib import Path

import pytest
from httpx import ASGITransport, AsyncClient

import apps.admin_console.services.user_workspace_service as ws_mod
from apps.admin_console.server import app


@pytest.fixture
def client(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> AsyncClient:
    monkeypatch.setattr(ws_mod, "WORKSPACE_PATH", tmp_path / "user_workspace.json")
    return AsyncClient(transport=ASGITransport(app=app), base_url="http://localhost")


@pytest.mark.asyncio
async def test_workspace_crud_flow(client: AsyncClient):
    # initially empty
    res = await client.get("/api/workspace")
    assert res.status_code == 200
    assert res.json() == {"notes": [], "task_groups": []}

    # create note
    res = await client.post("/api/workspace/notes", json={"title": "T", "content": "C"})
    assert res.status_code == 201
    note_id = res.json()["id"]
    assert res.json()["title"] == "T"

    res = await client.put(f"/api/workspace/notes/{note_id}", json={"title": "T2"})
    assert res.status_code == 200 and res.json()["title"] == "T2"

    # create group + task
    res = await client.post("/api/workspace/task-groups", json={"name": "G"})
    assert res.status_code == 201
    group_id = res.json()["id"]

    res = await client.post(
        f"/api/workspace/task-groups/{group_id}/tasks",
        json={"title": "Open WeChat", "goal": "打开微信", "profile": "flash"},
    )
    assert res.status_code == 201
    task_id = res.json()["task"]["id"]
    assert res.json()["task"]["goal"] == "打开微信"

    # aggregate reflects everything
    res = await client.get("/api/workspace")
    data = res.json()
    assert data["notes"][0]["title"] == "T2"
    assert data["task_groups"][0]["tasks"][0]["id"] == task_id

    # deletes
    assert (
        await client.delete(f"/api/workspace/task-groups/{group_id}/tasks/{task_id}")
    ).status_code == 200
    assert (await client.delete(f"/api/workspace/task-groups/{group_id}")).status_code == 200
    assert (await client.delete(f"/api/workspace/notes/{note_id}")).status_code == 200


@pytest.mark.asyncio
async def test_missing_ids_return_404(client: AsyncClient):
    assert (await client.put("/api/workspace/notes/nope", json={"title": "x"})).status_code == 404
    assert (await client.delete("/api/workspace/notes/nope")).status_code == 404
    assert (
        await client.put("/api/workspace/task-groups/nope", json={"name": "x"})
    ).status_code == 404
    assert (await client.delete("/api/workspace/task-groups/nope")).status_code == 404
    assert (
        await client.post("/api/workspace/task-groups/nope/tasks", json={"title": "x", "goal": "y"})
    ).status_code == 400


@pytest.mark.asyncio
async def test_validation_rejects_empty_goal(client: AsyncClient):
    res = await client.post("/api/workspace/task-groups", json={"name": "G"})
    group_id = res.json()["id"]
    res = await client.post(
        f"/api/workspace/task-groups/{group_id}/tasks",
        json={"title": "x", "goal": ""},
    )
    assert res.status_code == 422


@pytest.mark.asyncio
async def test_no_secrets_persisted(client: AsyncClient, tmp_path: Path):
    await client.post(
        "/api/workspace/task-groups/g/tasks",
        json={"title": "x", "goal": "y", "api_key": "sk-secret"},
    )  # nonexistent group -> 400, but payload must never be stored
    path = tmp_path / "user_workspace.json"
    if path.exists():
        assert "sk-secret" not in path.read_text(encoding="utf-8")
