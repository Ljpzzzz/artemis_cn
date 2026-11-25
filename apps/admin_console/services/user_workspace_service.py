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

"""Persistence for user-authored notes and custom task groups.

Data lives in a single JSON file under the traces directory. All access is
guarded by a re-entrant lock and writes are atomic (temp file + os.replace) so
a crash never leaves a half-written document.
"""

from __future__ import annotations

import json
import os
from pathlib import Path
import threading
import time
from typing import Any
from uuid import uuid4

from artemis.config import TRACES_PATH
from third_party.mobile_use.utils.logger import get_logger

logger = get_logger(__name__)

# Module-level so tests can point persistence at tmp_path.
WORKSPACE_PATH: Path = Path(TRACES_PATH) / "user_workspace.json"

MAX_NOTES = 200
MAX_GROUPS = 50
MAX_TASKS_PER_GROUP = 100
MAX_FILE_BYTES = 2 * 1024 * 1024


class WorkspaceError(ValueError):
    """Raised for invalid or over-cap workspace operations."""


def _empty_doc() -> dict[str, Any]:
    return {"version": 1, "notes": [], "task_groups": []}


class UserWorkspaceService:
    """CRUD over a single JSON document, safe for the single-worker console."""

    def __init__(self) -> None:
        self._lock = threading.RLock()

    @property
    def path(self) -> Path:
        return WORKSPACE_PATH

    def _load_unlocked(self) -> dict[str, Any]:
        path = WORKSPACE_PATH
        if not path.exists():
            return _empty_doc()
        try:
            raw = path.read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError) as exc:
            logger.warning(f"Cannot read workspace file {path}: {exc}")
            return _empty_doc()
        if len(raw.encode("utf-8")) > MAX_FILE_BYTES:
            logger.warning(f"Workspace file {path} exceeds size cap; ignoring")
            return _empty_doc()
        try:
            doc = json.loads(raw)
        except (json.JSONDecodeError, ValueError) as exc:
            backup = path.with_name(f"{path.name}.corrupt-{int(time.time())}")
            try:
                path.replace(backup)
                logger.warning(f"Corrupt workspace file renamed to {backup}: {exc}")
            except OSError:
                logger.warning(f"Could not rename corrupt workspace file {path}: {exc}")
            return _empty_doc()
        if not isinstance(doc, dict):
            return _empty_doc()
        doc.setdefault("version", 1)
        doc.setdefault("notes", [])
        doc.setdefault("task_groups", [])
        if not isinstance(doc["notes"], list):
            doc["notes"] = []
        if not isinstance(doc["task_groups"], list):
            doc["task_groups"] = []
        return doc

    def _save_unlocked(self, doc: dict[str, Any]) -> None:
        path = WORKSPACE_PATH
        path.parent.mkdir(parents=True, exist_ok=True)
        payload = json.dumps(doc, ensure_ascii=False, indent=2)
        if len(payload.encode("utf-8")) > MAX_FILE_BYTES:
            raise WorkspaceError("Workspace data exceeds the size limit")
        tmp = path.with_name(f".{path.name}.{uuid4().hex}.tmp")
        try:
            with open(tmp, "w", encoding="utf-8", newline="") as fh:
                fh.write(payload)
                fh.flush()
                os.fsync(fh.fileno())
            os.replace(tmp, path)
        except OSError:
            try:
                tmp.unlink()
            except OSError:
                pass
            raise

    # ---- aggregate --------------------------------------------------------

    def get_all(self) -> dict[str, Any]:
        with self._lock:
            doc = self._load_unlocked()
            return {"notes": doc["notes"], "task_groups": doc["task_groups"]}

    # ---- notes ------------------------------------------------------------

    def list_notes(self) -> list[dict[str, Any]]:
        return self.get_all()["notes"]

    def create_note(self, title: str, content: str) -> dict[str, Any]:
        with self._lock:
            doc = self._load_unlocked()
            if len(doc["notes"]) >= MAX_NOTES:
                raise WorkspaceError(f"At most {MAX_NOTES} notes are allowed")
            note = {
                "id": uuid4().hex,
                "title": title,
                "content": content,
                "updated_at": time.time(),
            }
            doc["notes"].append(note)
            self._save_unlocked(doc)
            return note

    def update_note(self, note_id: str, title: str | None, content: str | None) -> dict[str, Any]:
        with self._lock:
            doc = self._load_unlocked()
            for note in doc["notes"]:
                if note.get("id") == note_id:
                    if title is not None:
                        note["title"] = title
                    if content is not None:
                        note["content"] = content
                    note["updated_at"] = time.time()
                    self._save_unlocked(doc)
                    return note
        raise WorkspaceError("Note not found")

    def delete_note(self, note_id: str) -> bool:
        with self._lock:
            doc = self._load_unlocked()
            kept = [n for n in doc["notes"] if n.get("id") != note_id]
            if len(kept) == len(doc["notes"]):
                return False
            doc["notes"] = kept
            self._save_unlocked(doc)
            return True

    # ---- task groups ------------------------------------------------------

    def list_groups(self) -> list[dict[str, Any]]:
        return self.get_all()["task_groups"]

    def create_group(self, name: str) -> dict[str, Any]:
        with self._lock:
            doc = self._load_unlocked()
            if len(doc["task_groups"]) >= MAX_GROUPS:
                raise WorkspaceError(f"At most {MAX_GROUPS} groups are allowed")
            group = {"id": uuid4().hex, "name": name, "tasks": []}
            doc["task_groups"].append(group)
            self._save_unlocked(doc)
            return group

    def update_group(self, group_id: str, name: str) -> dict[str, Any]:
        with self._lock:
            doc = self._load_unlocked()
            for group in doc["task_groups"]:
                if group.get("id") == group_id:
                    group["name"] = name
                    self._save_unlocked(doc)
                    return group
        raise WorkspaceError("Task group not found")

    def delete_group(self, group_id: str) -> bool:
        with self._lock:
            doc = self._load_unlocked()
            kept = [g for g in doc["task_groups"] if g.get("id") != group_id]
            if len(kept) == len(doc["task_groups"]):
                return False
            doc["task_groups"] = kept
            self._save_unlocked(doc)
            return True

    # ---- tasks ------------------------------------------------------------

    def create_task(
        self, group_id: str, data: dict[str, Any]
    ) -> tuple[dict[str, Any], dict[str, Any]]:
        with self._lock:
            doc = self._load_unlocked()
            for group in doc["task_groups"]:
                if group.get("id") == group_id:
                    if len(group.get("tasks", [])) >= MAX_TASKS_PER_GROUP:
                        raise WorkspaceError(f"At most {MAX_TASKS_PER_GROUP} tasks per group")
                    task = {"id": uuid4().hex, **data}
                    group.setdefault("tasks", []).append(task)
                    self._save_unlocked(doc)
                    return group, task
        raise WorkspaceError("Task group not found")

    def update_task(self, group_id: str, task_id: str, changes: dict[str, Any]) -> dict[str, Any]:
        with self._lock:
            doc = self._load_unlocked()
            for group in doc["task_groups"]:
                if group.get("id") == group_id:
                    for task in group.get("tasks", []):
                        if task.get("id") == task_id:
                            task.update(changes)
                            self._save_unlocked(doc)
                            return task
        raise WorkspaceError("Task not found")

    def delete_task(self, group_id: str, task_id: str) -> bool:
        with self._lock:
            doc = self._load_unlocked()
            for group in doc["task_groups"]:
                if group.get("id") == group_id:
                    kept = [t for t in group.get("tasks", []) if t.get("id") != task_id]
                    if len(kept) == len(group.get("tasks", [])):
                        return False
                    group["tasks"] = kept
                    self._save_unlocked(doc)
                    return True
        return False


user_workspace_service = UserWorkspaceService()
