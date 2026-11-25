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

import { language, setLanguage, translate } from './translations';

describe('translations', () => {
  afterEach(() => setLanguage('en'));

  it('defaults to English (identity) so unit specs keep source strings', () => {
    setLanguage('en');
    expect(language()).toBe('en');
    expect(translate('Any unknown string')).toBe('Any unknown string');
  });

  it('normalizes zh variants to zh-CN', () => {
    setLanguage('zh');
    expect(language()).toBe('zh-CN');
    setLanguage('ZH-CN');
    expect(language()).toBe('zh-CN');
  });

  it('interpolates params and passes unknown keys through', () => {
    setLanguage('en');
    expect(translate('Hello {name}', { name: 'Artemis' })).toBe('Hello Artemis');
    setLanguage('zh-CN');
    expect(translate('Still unknown {x}', { x: 1 })).toBe('Still unknown 1');
  });
});
