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

import { Pipe, PipeTransform } from '@angular/core';
import { translate } from './translations';

/**
 * Translate an English UI string. The language is fixed before first render,
 * so a pure pipe is safe and avoids re-evaluating on every change-detection pass.
 */
@Pipe({ name: 't' })
export class TranslationPipe implements PipeTransform {
  transform(key: string, params?: Record<string, string | number>): string {
    return translate(key, params);
  }
}
