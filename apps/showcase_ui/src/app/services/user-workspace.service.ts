/**
 * Copyright 2026 Google LLC
 *
 * Licensed under the Apache License, Version 2.0 (the "License");
 * you may not use this file except in compliance with the License.
 * You may obtain a copy of the License at
 *
 *     http://www.apache.org/licenses/LICENSE-2.0
 *
 * Unless required by applicable law or agreed to in writing, software
 * distributed under the License is distributed on an "AS IS" BASIS,
 * WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
 * See the License for the specific language governing permissions and
 * limitations under the License.
 */

import { HttpClient } from '@angular/common/http';
import { Injectable, computed, inject, signal } from '@angular/core';
import { Observable, tap } from 'rxjs';
import { SmartSuggestion } from '../core/data/smart-tasks.data';

export interface MyNote {
  id: string;
  title: string;
  content: string;
  updated_at: number;
}

export interface MyTask {
  id: string;
  title: string;
  description: string;
  goal: string;
  profile: 'flash' | 'pro';
  category: 'flash' | 'pro' | 'cross_app' | 'monitor' | 'all';
  tag: string;
  expected_output: string;
  source_session_id?: string | null;
}

export interface MyTaskGroup {
  id: string;
  name: string;
  tasks: MyTask[];
}

export interface WorkspaceData {
  notes: MyNote[];
  task_groups: MyTaskGroup[];
}

export interface TaskTemplateInput {
  title: string;
  description: string;
  goal: string;
  profile: 'flash' | 'pro';
  category: 'flash' | 'pro' | 'cross_app' | 'monitor' | 'all';
  tag: string;
  expected_output: string;
  source_session_id?: string | null;
}

@Injectable({ providedIn: 'root' })
export class UserWorkspaceService {
  private http = inject(HttpClient);

  public myNotes = signal<MyNote[]>([]);
  public myTaskGroups = signal<MyTaskGroup[]>([]);
  public loading = signal<boolean>(false);

  /** Flatten custom tasks into SmartSuggestion so applySuggestion() works unchanged. */
  public customSuggestions = computed<SmartSuggestion[]>(() => {
    const out: SmartSuggestion[] = [];
    for (const group of this.myTaskGroups()) {
      for (const task of group.tasks) {
        out.push({
          id: `custom:${task.id}`,
          title: task.title,
          description: task.description,
          goal: task.goal,
          profile: task.profile,
          category: task.category === 'all' ? 'flash' : task.category,
          tag: group.name + (task.tag ? ` · ${task.tag}` : ''),
          apps: [],
          requiredPackages: [],
          priority: 100,
          expectedOutput: task.expected_output,
          groupId: group.id,
          sourceSessionId: task.source_session_id || undefined
        });
      }
    }
    return out;
  });

  public loadAll(): Observable<WorkspaceData> {
    this.loading.set(true);
    return this.http.get<WorkspaceData>('/api/workspace').pipe(
      tap({
        next: (data) => {
          this.myNotes.set(data?.notes || []);
          this.myTaskGroups.set(data?.task_groups || []);
          this.loading.set(false);
        },
        error: () => this.loading.set(false)
      })
    );
  }

  // ---- notes -------------------------------------------------------------

  public createNote(title: string, content: string): Observable<MyNote> {
    return this.http.post<MyNote>('/api/workspace/notes', { title, content }).pipe(
      tap(() => this.loadAll().subscribe())
    );
  }

  public updateNote(id: string, title: string, content: string): Observable<MyNote> {
    return this.http.put<MyNote>(`/api/workspace/notes/${id}`, { title, content }).pipe(
      tap(() => this.loadAll().subscribe())
    );
  }

  public deleteNote(id: string): Observable<any> {
    return this.http.delete(`/api/workspace/notes/${id}`).pipe(
      tap(() => this.loadAll().subscribe())
    );
  }

  // ---- groups ------------------------------------------------------------

  public createGroup(name: string): Observable<MyTaskGroup> {
    return this.http.post<MyTaskGroup>('/api/workspace/task-groups', { name }).pipe(
      tap(() => this.loadAll().subscribe())
    );
  }

  public renameGroup(id: string, name: string): Observable<MyTaskGroup> {
    return this.http.put<MyTaskGroup>(`/api/workspace/task-groups/${id}`, { name }).pipe(
      tap(() => this.loadAll().subscribe())
    );
  }

  public deleteGroup(id: string): Observable<any> {
    return this.http.delete(`/api/workspace/task-groups/${id}`).pipe(
      tap(() => this.loadAll().subscribe())
    );
  }

  // ---- tasks -------------------------------------------------------------

  public createTask(groupId: string, input: TaskTemplateInput): Observable<{ group: MyTaskGroup; task: MyTask }> {
    return this.http.post<{ group: MyTaskGroup; task: MyTask }>(
      `/api/workspace/task-groups/${groupId}/tasks`, input
    ).pipe(tap(() => this.loadAll().subscribe()));
  }

  public updateTask(groupId: string, taskId: string, input: Partial<TaskTemplateInput>): Observable<MyTask> {
    return this.http.put<MyTask>(`/api/workspace/task-groups/${groupId}/tasks/${taskId}`, input).pipe(
      tap(() => this.loadAll().subscribe())
    );
  }

  public deleteTask(groupId: string, taskId: string): Observable<any> {
    return this.http.delete(`/api/workspace/task-groups/${groupId}/tasks/${taskId}`).pipe(
      tap(() => this.loadAll().subscribe())
    );
  }
}
