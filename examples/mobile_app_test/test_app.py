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

"""把 ARTEMIS 当作移动端自动化框架，测试你自己的 App。

你只需写一句自然语言 goal（操作 + 要验证的结果），ARTEMIS 在真机上完成
定位元素、点击/输入、观察屏幕、判断结果；pytest 只对返回的 result 做断言。
"""

from __future__ import annotations

import pytest

from artemis_client import ArtemisClient, TaskResult

pytestmark = [pytest.mark.android, pytest.mark.e2e]


def assert_succeeded(result: TaskResult) -> None:
    """断言任务流程成功；失败时带上 trace_id 便于在 /admin 回放定位。"""
    assert result.succeeded, (
        f"任务失败: status={result.status}, error={result.error}, "
        f"trace_id={result.trace_id}"
    )


def assert_output_contains(result: TaskResult, *tokens: str) -> None:
    """断言 agent 最终输出包含预期标记。

    配合 goal 末尾「只回答 X 或 Y」的写法，output 就是可断言的结构化结果。
    """
    text = str(result.output or "")
    missing = [t for t in tokens if t not in text]
    assert not missing, f"输出缺少 {missing}，实际输出: {text!r} (trace={result.trace_id})"


class TestSmoke:
    """冒烟用例：用 flash 快速验证核心页面可打开。"""

    @pytest.mark.asyncio
    async def test_launch_and_home(
        self, client: ArtemisClient, app_package: str, common_kwargs: dict
    ) -> None:
        result = await client.run(
            f"启动 App {app_package}，确认进入主页后，只回答 'HOME' 或 'FAILED'",
            expected_output="HOME 或 FAILED",
            **common_kwargs,
        )
        assert_succeeded(result)
        assert_output_contains(result, "HOME")

    @pytest.mark.asyncio
    async def test_no_crash_dialog_on_launch(
        self, client: ArtemisClient, app_package: str, common_kwargs: dict
    ) -> None:
        result = await client.run(
            f"启动 App {app_package}，检查启动后 5 秒内是否出现崩溃或 ANR 弹窗，"
            "只回答 'OK'（无弹窗）或 'CRASH'（有弹窗）",
            expected_output="OK 或 CRASH",
            **common_kwargs,
        )
        assert_succeeded(result)
        assert_output_contains(result, "OK")


class TestLogin:
    """业务流程用例：验证登录成功路径。"""

    @pytest.mark.asyncio
    async def test_login_success(
        self, client: ArtemisClient, app_package: str, common_kwargs: dict
    ) -> None:
        # 账号密码从环境变量读取，不要写死在用例里。
        import os

        user = os.environ["TEST_USER"]
        pwd = os.environ["TEST_PASSWORD"]

        result = await client.run(
            f"在 App {app_package} 中用账号 {user}、密码 {pwd} 登录，"
            "登录后只回答 'LOGGED_IN' 或 'LOGIN_FAILED'",
            expected_output="LOGGED_IN 或 LOGIN_FAILED",
            **common_kwargs,
        )
        assert_succeeded(result)
        assert_output_contains(result, "LOGGED_IN")


class TestRegression:
    """关键路径回归：用 pro + strict 让 Checker 逐步审查。"""

    @pytest.mark.asyncio
    async def test_main_flow_no_regression(
        self, client: ArtemisClient, app_package: str, common_kwargs: dict
    ) -> None:
        result = await client.run(
            f"在 App {app_package} 中依次进入设置页、关于页并返回主页，"
            "确认每一步都没有报错弹窗，最后只回答 'PASS' 或 'FAIL'",
            profile="pro",
            verification_level="strict",
            expected_output="PASS 或 FAIL",
            **common_kwargs,
        )
        assert_succeeded(result)
        assert_output_contains(result, "PASS")
