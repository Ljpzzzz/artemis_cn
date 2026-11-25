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

"""Schemas for user-authored notes and custom task groups (JSON persistence)."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field

Profile = Literal["flash", "pro"]
TaskCategory = Literal["flash", "pro", "cross_app", "monitor", "all"]


class NoteCreate(BaseModel):
    """Create a global note."""

    title: str = Field(min_length=1, max_length=200)
    content: str = Field(default="", max_length=100_000)


class NoteUpdate(BaseModel):
    """Partial update of a global note."""

    title: str | None = Field(default=None, min_length=1, max_length=200)
    content: str | None = Field(default=None, max_length=100_000)


class Note(BaseModel):
    """A persisted global note."""

    id: str
    title: str
    content: str
    updated_at: float


class TaskCreate(BaseModel):
    """Create a custom task inside a group."""

    title: str = Field(min_length=1, max_length=200)
    description: str = Field(default="", max_length=1000)
    goal: str = Field(min_length=1, max_length=4000)
    profile: Profile = "flash"
    category: TaskCategory = "all"
    tag: str = Field(default="", max_length=80)
    expected_output: str = Field(default="", max_length=8000)
    source_session_id: str | None = Field(default=None, max_length=200)


class TaskUpdate(BaseModel):
    """Partial update of a custom task."""

    title: str | None = Field(default=None, min_length=1, max_length=200)
    description: str | None = Field(default=None, max_length=1000)
    goal: str | None = Field(default=None, min_length=1, max_length=4000)
    profile: Profile | None = None
    category: TaskCategory | None = None
    tag: str | None = Field(default=None, max_length=80)
    expected_output: str | None = Field(default=None, max_length=8000)


class Task(BaseModel):
    """A persisted custom task template."""

    id: str
    title: str
    description: str
    goal: str
    profile: Profile
    category: TaskCategory
    tag: str
    expected_output: str
    source_session_id: str | None = None


class TaskGroupCreate(BaseModel):
    """Create a custom task group."""

    name: str = Field(min_length=1, max_length=120)


class TaskGroupUpdate(BaseModel):
    """Rename a custom task group."""

    name: str = Field(min_length=1, max_length=120)


class TaskGroup(BaseModel):
    """A persisted group of custom tasks."""

    id: str
    name: str
    tasks: list[Task] = Field(default_factory=list)
