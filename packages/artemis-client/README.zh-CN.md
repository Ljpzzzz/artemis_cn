# Artemis 客户端

`artemis-client` 是运行在开发者机器上的远程 Python SDK。它通过 HTTP 与设备主机上的 Artemis 守护进程通信，不包含任何 ADB、设备驱动、智能体、LLM 或图像处理代码。

运行时依赖：**零**。HTTP、JSON 和异步适配器仅使用 Python 标准库。

## 安装

从本地检出安装：

```powershell
uv add --editable C:\path\to\artemis\packages\artemis-client
```

从 Git 仓库子目录安装：

```powershell
uv add "artemis-client @ git+https://github.com/google/artemis.git#subdirectory=packages/artemis-client"
```

## 连接设备主机

当前的 Artemis 守护进程管理 API 不含内置远程认证。请勿将其端口直接暴露到公网。在初期推广阶段，请通过 SSH 隧道连接：

```powershell
ssh -L 8000:127.0.0.1:8000 user@artemis-host
```

然后将 SDK 连接到本地隧道端点：

```python
from artemis_client import ArtemisClient

client = ArtemisClient("http://127.0.0.1:8000")
```

生产环境中，请在守护进程前放置反向代理，强制启用 HTTPS 和 bearer-token 认证，并只暴露任务相关的 API。

## 使用

```python
import asyncio
import os

from artemis_client import ArtemisClient


async def main() -> None:
    client = ArtemisClient(
        os.environ["ARTEMIS_BASE_URL"],
        token=os.environ.get("ARTEMIS_TOKEN"),
    )

    handle = await client.submit(
        "打开设置中的电池页面并查看电池百分比",
        profile="flash",
        device_serial="emulator-5554",
    )
    print("已入队:", handle.task_id)

    result = await client.wait_for_task(handle.task_id, timeout=600)
    if not result.succeeded:
        raise RuntimeError(result.error or result.status)


asyncio.run(main())
```

也可以在一次调用中提交任务并等待完成：

```python
result = await client.run("打开 Android 设置并检查 Wi-Fi 状态")
```

主要方法：

- `health()` — 快速检查服务器和调度器是否存活。
- `readiness()` — 运行完整的设备和工具链诊断，可能耗时较长。
- `capabilities()` — 协商 API 能力，并对旧版服务器做降级处理。
- `list_devices()` — 列出主机上可用的设备。
- `submit()` — 提交幂等任务并立即返回。
- `get_task()` — 获取任务。
- `wait_for_task()` — 等待任务进入终态。
- `run()` — 提交任务并等待完成。
- `stop()` — 停止单个任务。

默认情况下，`submit()` 在客户端生成 UUID，并作为当前服务器的 `session_id` 发送。网络重试会复用同一个 `task_id`，防止服务器创建重复任务。

## 兼容性

0.1 版本支持以下当前的 Artemis 守护进程端点：

- `POST /api/run`
- `GET /api/sessions/{session_id}`
- `GET /api/status`
- `POST /api/stop`
- `GET /api/devices`
- `GET /api/system/readiness`

能力发现会先尝试未来的 `GET /api/v1/capabilities` 端点。如果旧版服务器返回 404，SDK 会使用已知的基础能力集。

架构与协议演进计划参见 [DESIGN.md](DESIGN.md)。
