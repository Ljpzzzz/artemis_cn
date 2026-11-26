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

"""Fixtures for App tests driven through the Artemis remote SDK.

The suite is safe to collect without a device or a daemon: it skips cleanly
when required environment variables are missing.  Point it at a device host
via ARTEMIS_BASE_URL (see README.md in this directory).
"""

from __future__ import annotations

import os

import pytest

from artemis_client import ArtemisClient

# 被测 App 的包名。改成你自己的 App。
APP_PACKAGE = os.getenv("APP_PACKAGE", "com.example.myapp")

# 可选：APK 在【设备主机】上的路径（不是测试机本地路径）。
# daemon 会在任务开始前自动安装它。留空则假设 App 已预装。
APK_PATH = os.getenv("APK_PATH") or None

# 可选：指定设备 serial；留空由设备主机自动选择空闲设备。
DEVICE_SERIAL = os.getenv("DEVICE_SERIAL") or None

# 默认 profile：flash 快（冒烟），pro 带计划+Checker（关键路径）。
DEFAULT_PROFILE = os.getenv("ARTEMIS_PROFILE", "flash")


def pytest_collection_modifyitems(items: list[pytest.Item]) -> None:
    """Skip App tests when no Artemis host is configured (safe collection)."""
    if os.getenv("ARTEMIS_BASE_URL"):
        return
    skip = pytest.mark.skip(reason="ARTEMIS_BASE_URL not set; skipping App tests")
    for item in items:
        item.add_marker(skip)


@pytest.fixture(scope="session")
def app_package() -> str:
    return APP_PACKAGE


@pytest.fixture(scope="session")
def client() -> ArtemisClient:
    """Remote SDK client connected to the Artemis daemon on the device host."""
    return ArtemisClient(
        os.environ["ARTEMIS_BASE_URL"],
        token=os.getenv("ARTEMIS_TOKEN"),
        device_serial=DEVICE_SERIAL,
        default_profile=DEFAULT_PROFILE,  # type: ignore[arg-type]
    )


@pytest.fixture(scope="session")
def common_kwargs() -> dict:
    """Arguments applied to every task: lock the App and auto-install the APK."""
    kwargs: dict = {"locked_app_package": APP_PACKAGE}
    if APK_PATH:
        kwargs["app_path"] = APK_PATH
    return kwargs
