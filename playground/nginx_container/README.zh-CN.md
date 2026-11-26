# 🌐 Artemis 入口反向代理容器

生产级、高性能的 Nginx 反向代理容器，专为在 Google Cloud 的 **Container-Optimized OS（COS）** VM 上运行 Artemis 而设计。

---

## 📌 架构与路由矩阵

该代理作为标准端口（`80` $\rightarrow$ `443`）上的单一 TLS/SSL 终止网关，动态将流量路由到常驻平台服务和按需创建的临时 Artemis 会话容器，无需重新加载或重启 Nginx：

| 路径前缀 | 目标上游 | 协议 | 用途 |
| :--- | :--- | :--- | :--- |
| `GET /healthz` | Nginx 内部 | HTTP/HTTPS | 入口健康检查探针 |
| `/` | `http://backend:8000/` | HTTP/1.1 | 静态前端单页应用（React/Vue/Angular） |
| `/api/*` | `http://backend:8000/api/*` | HTTP/1.1 / WS | 管理 API、OTP 认证校验、会话生命周期 |
| `/session/{id}/artemis/stream/*` | `http://artemis-session-{id}:8080/stream/*` | **SSE / WebSocket** | 实时智能体思考流（零缓冲，1 小时超时） |
| `/session/{id}/artemis/*` | `http://artemis-session-{id}:8080/*` | HTTP/1.1 / WS | Artemis REST API 与任务执行端点 |
| `/session/{id}/cuttlefish/*` | `http://host.docker.internal:8443/*` | **WebRTC / WS** | Cuttlefish WebRTC 信令与交互式设备控制 |

---

## 📁 文件结构

```
playground/nginx_container/
├── Dockerfile                   # 带 openssl 和健康检查的 Nginx alpine 镜像
├── docker-entrypoint.sh         # 自动生成开发证书并检查 nginx 语法
├── docker-compose.yml           # 带 artemis-net 桥接网络的 Compose 配置
├── .dockerignore
├── README.md                    # 详细运维文档
├── certs/
│   ├── generate_dev_certs.sh    # 手动生成 SSL 证书的辅助脚本
│   └── .gitkeep
├── conf/
│   ├── nginx.conf               # 主 Nginx 配置（JSON 日志、WebSocket map）
│   ├── conf.d/
│   │   ├── http_redirect.conf   # 80 端口重定向到 443 + ACME challenge
│   │   └── artemis_ssl.conf     # 443 端口 SSL server 块与动态 Docker DNS 路由
│   └── includes/
│       ├── proxy_headers.conf   # 标准转发头（Host、X-Real-IP、X-Forwarded-*）
│       ├── websocket_params.conf# WebSocket 升级头与 3600 秒超时
│       └── sse_params.conf      # SSE 流式参数（proxy_buffering off）
└── html/
    ├── index.html               # 兜底落地页
    ├── 502.json                 # 容器创建中时的 JSON 错误响应
    └── 504.json                 # 超时时的 JSON 错误响应
```

---

## 🚀 快速开始

### 1. 构建 Docker 镜像
```bash
docker build -t artemis-nginx-proxy:latest .
```

### 2. 使用 Docker Compose 运行
```bash
docker-compose up -d
```

### 3. 在 COS VM 上单独运行
```bash
# 如共享桥接网络不存在则创建
docker network create artemis-net || true

# 运行 Nginx 反向代理容器
docker run -d \
  --name artemis-nginx-proxy \
  --restart unless-stopped \
  --network artemis-net \
  --add-host host.docker.internal:host-gateway \
  -p 80:80 \
  -p 443:443 \
  -v $(pwd)/certs:/etc/nginx/certs:ro \
  artemis-nginx-proxy:latest
```

---

## 🔑 核心特性与技术亮点

### 1. 动态零重载上游解析
当用户启动新会话时，后端会在 `artemis-net` 网络上启动一个名为 `artemis-session-<session_id>` 的新 Docker 容器。

借助 Docker 内置 DNS 服务器（`127.0.0.11 valid=5s`）与基于变量的 `proxy_pass`：

```nginx
resolver 127.0.0.11 valid=5s ipv6=off;

location ~ ^/session/(?<session_id>[a-zA-Z0-9_-]+)/artemis/(?<artemis_path>.*)$ {
    set $artemis_host "artemis-session-$session_id";
    proxy_pass http://$artemis_host:8080/$artemis_path$is_args$args;
}
```

Nginx 在**请求时**解析容器主机名，因此会话容器的创建和销毁无需触碰或重新加载 Nginx 配置。

### 2. 实时流式传输（SSE 与 WebSocket）
- **SSE 流**（`/stream/*`）：使用 `proxy_buffering off;`、`proxy_cache off;` 和 `chunked_transfer_encoding on;`，使浏览器以零缓冲延迟接收智能体推理 token。
- **WebRTC 信令与 WebSocket**：使用 `map $http_upgrade $connection_upgrade`，并设置 1 小时空闲超时（`proxy_read_timeout 3600s;`）。

### 3. 自动化 SSL/TLS 管理
- **开发/预发布**：如果 `/etc/nginx/certs/` 中没有证书，容器入口脚本会自动生成自签名证书。
- **生产环境**：将 Let's Encrypt 或 GCP 托管证书挂载到 `/etc/nginx/certs/tls.crt` 和 `/etc/nginx/certs/tls.key`。

### 4. 弹性错误处理
如果请求的会话容器仍在启动或不可用，Nginx 会返回简洁的 JSON 错误响应（`502.json` / `504.json`），而不是标准的 Nginx HTML 错误页，使前端 UI 能够优雅地轮询或显示加载动画。

---

## 🧪 验证与测试

1. **验证健康端点**：
   ```bash
   curl -k https://localhost/healthz
   # 输出：OK
   ```

2. **测试动态路由**：
   ```bash
   # 启动一个模拟会话容器
   docker run -d --name artemis-session-test123 --network artemis-net hashicorp/http-echo -text="Hello from Session test123" -listen=:8080

   # 通过 Nginx 代理测试
   curl -k https://localhost/session/test123/artemis/
   # 输出：Hello from Session test123
   ```
