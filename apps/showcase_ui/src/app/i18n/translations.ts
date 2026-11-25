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

import { signal } from '@angular/core';
import { ZH_CN } from './zh-cn';

export type UiLanguage = 'en' | 'zh-CN';

declare global {
  interface Window {
    __ARTEMIS_LANGUAGE__?: string;
  }
}

/**
 * Module-level language store. Defaults to 'en' so unit tests that import
 * formatters directly (without running main.ts) keep their English source
 * strings. The browser bootstrap sets it to the configured language before
 * first render.
 */
export const language = signal<UiLanguage>('en');

const DICTIONARIES: Record<UiLanguage, Record<string, string>> = {
  en: {},
  'zh-CN': ZH_CN,
};

/** Set the active UI language (also updates the document language attribute). */
export function setLanguage(value: string | undefined | null): void {
  const normalized = String(value ?? '').trim().toLowerCase();
  language.set(normalized === 'zh-cn' || normalized === 'zh' ? 'zh-CN' : 'en');
  if (typeof document !== 'undefined') {
    document.documentElement.lang = language();
  }
}

/** Initialize from the server-injected global. Defaults to Chinese. */
export function initLanguageFromServer(): void {
  const injected = typeof window !== 'undefined' ? window.__ARTEMIS_LANGUAGE__ : undefined;
  setLanguage(injected ?? 'zh-CN');
}

/**
 * Translate an English source string. Unknown keys pass through unchanged, so
 * English mode is the identity and untranslated strings never render blank.
 * `{param}` placeholders are replaced from `params`.
 */
export function translate(key: string, params?: Record<string, string | number>): string {
  const dict = DICTIONARIES[language()];
  let result = dict[key] ?? key;
  if (params) {
    for (const [name, value] of Object.entries(params)) {
      result = result.replaceAll(`{${name}}`, String(value));
    }
  }
  return result;
}
