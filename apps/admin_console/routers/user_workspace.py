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

"""REST endpoints for user-authored notes and custom task groups."""

from __future__ import annotations

from fastapi import APIRouter, HTTPException

from apps.admin_console.schemas.user_workspace_schema import (
    NoteCreate,
    NoteUpdate,
    TaskCreate,
    TaskGroupCreate,
    TaskGroupUpdate,
    TaskUpdate,
)
from apps.admin_console.services.user_workspace_service import (
    WorkspaceError,
    user_workspace_service,
)

router = APIRouter(prefix="/api/workspace", tags=["workspace"])


def _not_found(exc: WorkspaceError) -> HTTPException:
    return HTTPException(status_code=404, detail=str(exc))


def _bad_request(exc: WorkspaceError) -> HTTPException:
    return HTTPException(status_code=400, detail=str(exc))


@router.get("")
async def get_workspace():
    """Return all user notes and custom task groups in one call."""
    return user_workspace_service.get_all()


# ---- notes ----------------------------------------------------------------


@router.get("/notes")
async def list_notes():
    return {"notes": user_workspace_service.list_notes()}


@router.post("/notes", status_code=201)
async def create_note(payload: NoteCreate):
    try:
        return user_workspace_service.create_note(payload.title, payload.content)
    except WorkspaceError as exc:
        raise _bad_request(exc) from exc


@router.put("/notes/{note_id}")
async def update_note(note_id: str, payload: NoteUpdate):
    try:
        return user_workspace_service.update_note(note_id, payload.title, payload.content)
    except WorkspaceError as exc:
        raise _not_found(exc) from exc


@router.delete("/notes/{note_id}")
async def delete_note(note_id: str):
    if not user_workspace_service.delete_note(note_id):
        raise HTTPException(status_code=404, detail="Note not found")
    return {"status": "deleted"}


# ---- task groups ----------------------------------------------------------


@router.get("/task-groups")
async def list_task_groups():
    return {"task_groups": user_workspace_service.list_groups()}


@router.post("/task-groups", status_code=201)
async def create_task_group(payload: TaskGroupCreate):
    try:
        return user_workspace_service.create_group(payload.name)
    except WorkspaceError as exc:
        raise _bad_request(exc) from exc


@router.put("/task-groups/{group_id}")
async def update_task_group(group_id: str, payload: TaskGroupUpdate):
    try:
        return user_workspace_service.update_group(group_id, payload.name)
    except WorkspaceError as exc:
        raise _not_found(exc) from exc


@router.delete("/task-groups/{group_id}")
async def delete_task_group(group_id: str):
    if not user_workspace_service.delete_group(group_id):
        raise HTTPException(status_code=404, detail="Task group not found")
    return {"status": "deleted"}


# ---- tasks ----------------------------------------------------------------


@router.post("/task-groups/{group_id}/tasks", status_code=201)
async def create_task(group_id: str, payload: TaskCreate):
    try:
        group, task = user_workspace_service.create_task(group_id, payload.model_dump())
    except WorkspaceError as exc:
        raise _bad_request(exc) from exc
    return {"group": group, "task": task}


@router.put("/task-groups/{group_id}/tasks/{task_id}")
async def update_task(group_id: str, task_id: str, payload: TaskUpdate):
    changes = payload.model_dump(exclude_unset=True)
    try:
        return user_workspace_service.update_task(group_id, task_id, changes)
    except WorkspaceError as exc:
        raise _not_found(exc) from exc


@router.delete("/task-groups/{group_id}/tasks/{task_id}")
async def delete_task(group_id: str, task_id: str):
    if not user_workspace_service.delete_task(group_id, task_id):
        raise HTTPException(status_code=404, detail="Task not found")
    return {"status": "deleted"}
