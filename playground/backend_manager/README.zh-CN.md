# 🚀 Artemis Backend Manager 容器

中央编排、API 网关、认证和容器生命周期服务，用于在 Google Cloud **Container-Optimized OS（COS）** 上运行 Artemis 和 Cuttlefish。

---

## 📌 核心职责

1. **认证与 OTP 回调**：
   - 管理用户验证（`POST /api/v1/auth/otp/send` 和 `POST /api/v1/auth/otp/verify`）。
   - 签发带签名的 JWT 访问令牌，实现安全的租户隔离。
   - 为 Nginx 入口提供会话校验钩子（`/api/v1/auth/validate-session`）。

2. **Docker Socket 容器编排**：
   - 与 `/var/run/docker.sock` 通信，在共享的 `artemis-net` 桥接网络上动态创建 `artemis-session-<session_id>` 容器。
   - 注入运行时环境变量（`SESSION_ID`、`ADB_DEVICE_SERIAL`、`PORT=8080`）。
   - 自动在容器内执行 `adb connect`，将其与 Cuttlefish 模拟器配对。

3. **云编排器与 Cuttlefish 集成**：
   - 将 API 请求分派给运行在 COS 上的 Cloud Orchestrator 服务，以创建专用的 Cuttlefish AVD。
   - 绑定分配的 ADB 端口（`6520+N`）和 WebRTC 信令端口（`8443+N`）。

4. **BigQuery 映射存储**：
   - 跟踪关联 `user_id`、`session_id`、`artemis_container_id`、`cuttlefish_adb_port`、`cuttlefish_webrtc_port` 和时间戳的元数据。
   - 支持在 BigQuery 上自动创建分区表（`artemis_orchestration.sessions_registry`），并为本地开发提供内存回退方案。

5. **静态前端 UI 托管**：
   - 在 `/` 提供双栏 Web 应用（Cuttlefish WebRTC 流播放器 + Artemis 智能体思考工作区）。

6. **自动会话回收与看门狗**：
   - 后台周期任务每 30 秒检查活跃会话。
   - 当会话 TTL 过期或心跳失败时，自动销毁孤立的容器和 AVD。

---

## 📁 目录结构

```
playground/backend_manager/
├── Dockerfile                   # 带健康检查的 Python 3.12 slim 镜像
├── docker-compose.yml           # 挂载 /var/run/docker.sock 的 Compose 配置
├── requirements.txt             # FastAPI、Pydantic、Docker SDK、BigQuery、JWT
├── README.md                    # 详细文档
└── app/
    ├── main.py                  # 带 lifespan 管理器的 FastAPI 应用入口
    ├── config.py                # 环境配置设置
    ├── auth/
    │   ├── jwt_handler.py       # JWT 编解码与 get_current_user 依赖
    │   └── otp_service.py       # OTP 生成、存储与校验
    ├── services/
    │   ├── docker_service.py    # Docker socket 管理（启动/停止容器）
    │   ├── cloud_orchestrator_service.py # Cloud Orchestrator Cuttlefish 客户端
    │   ├── bigquery_service.py  # 带本地回退的 BigQuery 映射仓库
    │   └── session_manager.py   # 会话生命周期与回收总协调器
    ├── routers/
    │   ├── auth_router.py       # OTP 与 JWT 端点
    │   ├── session_router.py    # 会话创建、轮询、心跳与删除
    │   └── health_router.py     # 存活探针端点（/healthz）
    ├── schemas/
    │   ├── auth_schema.py       # 认证请求/响应 schema
    │   └── session_schema.py    # 会话与映射 schema
    └── static/
        ├── index.html           # 双栏玻璃拟态 Web 工作区
        ├── style.css            # 极光设计系统样式
        └── app.js               # 前端客户端逻辑与流式钩子
```

---

## 🔌 REST API 端点

### 认证
* `POST /api/v1/auth/otp/send` — 请求 6 位 OTP 验证码（`{"identifier": "user@example.com"}`）。
* `POST /api/v1/auth/otp/verify` — 校验 OTP 并获取签名 JWT 令牌（`{"identifier": "...", "code": "123456"}`）。
* `GET /api/v1/auth/me` — 返回当前认证用户的资料（`Authorization: Bearer <jwt>`）。
* `GET /api/v1/auth/validate-session?session_id=...` — 校验用户对特定会话的授权。

### 会话与容器管理
* `POST /api/v1/sessions/create` — 创建 Cuttlefish AVD 和 Artemis 容器，链接 ADB 并注册映射。
* `GET /api/v1/sessions` — 列出当前用户的所有活跃会话。
* `GET /api/v1/sessions/{session_id}` — 获取会话状态和反向代理流端点。
* `POST /api/v1/sessions/{session_id}/heartbeat` — 发送客户端心跳以延长会话 TTL。
* `DELETE /api/v1/sessions/{session_id}` — 终止容器并释放 Cuttlefish 实例。

### 健康探针
* `GET /healthz` — 返回 `200 OK` 及服务健康状态。

---

## ⚙️ 环境变量

| 变量 | 默认值 | 说明 |
| :--- | :--- | :--- |
| `PORT` | `8000` | 监听的 HTTP 端口 |
| `APP_ENV` | `development` | 环境模式（`development` / `production`） |
| `JWT_SECRET_KEY` | `artemis-...` | 用于签发 JWT 会话令牌的密钥 |
| `DOCKER_SOCKET_PATH` | `unix://var/run/docker.sock` | 宿主机 Docker 守护进程 socket 路径 |
| `DOCKER_NETWORK` | `artemis-net` | 用于动态容器路由的共享桥接网络 |
| `ARTEMIS_IMAGE` | `artemis:latest` | 用于创建 Artemis 实例的 Docker 镜像 |
| `CLOUD_ORCHESTRATOR_URL` | `http://host.docker.internal:1443` | Cloud Orchestrator 服务端点 |
| `CUTTLEFISH_HOST_GATEWAY` | `host.docker.internal` | ADB TCP 连接的宿主机 IP / 网关 |
| `GOOGLE_CLOUD_PROJECT` | `artemis-cloud-project` | BigQuery 数据集所在的 GCP 项目 ID |
| `USE_LOCAL_FALLBACK_DB` | `true` | BigQuery 未配置时启用内存数据库回退 |
| `SESSION_TTL_MINUTES` | `60` | 自动销毁前的默认会话存活时长 |

---

## 🚀 运行容器

### 1. 构建镜像
```bash
docker build -t artemis-backend-manager:latest .
```

### 2. 使用 Docker Compose 运行
```bash
docker-compose up -d
```

### 3. 在 COS 上使用 Docker 单独运行
```bash
docker run -d \
  --name backend \
  --restart unless-stopped \
  --network artemis-net \
  --add-host host.docker.internal:host-gateway \
  -v /var/run/docker.sock:/var/run/docker.sock \
  -p 8000:8000 \
  artemis-backend-manager:latest
```
