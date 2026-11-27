# ARTEMIS 远程 ADB 连接手册

> 适用：手机与运行 ARTEMIS 的主机不在同一台机器、不在同一局域网，或主机在云端、手机在公司内网（NAT 后）的场景。
> 本文只描述操作，不改动项目代码。所有方案最终都落到同一个配置：`ADB_HOST` / `ADB_PORT` 指向一个能访问到「插着手机的那台 adb server」的地址。

## 0. 核心原理

ARTEMIS **不直接连手机**，它连的是 ADB server：

- 驱动工厂用 `AdbClient(host=settings.ADB_HOST, port=settings.ADB_PORT)`（`artemis/drivers/factory.py:61-64`）。
- 设备枚举、shell、截图等操作都经这个 ADB server 转发到手机（`artemis/runtime/device_pool.py`）。
- 默认 `ADB_HOST=127.0.0.1`、`ADB_PORT=5037`（`artemis/config/settings.py:113-122`、`.env.example:18-21`）。

因此问题的本质是：**让 ARTEMIS 主机能够访问到手机所在机器的 `127.0.0.1:5037`**。下面所有方案都是围绕这一点做 TCP 转发。

### 关键约定：用非 5037 端口

远程方案统一使用 **`15037`（或其它非 5037 端口）**，原因：

- `AdbEndpoint.is_local_default` 要求 `host ∈ {127.0.0.1, localhost, ::1}` **且 port == 5037** 才判为 `local`（`artemis/runtime/adb_endpoint.py:87-93`）。
- 用 15037 会被识别为 `remote`，于是 `restart_adb_server()`、`launch_emulator()`、`connect_wireless_adb()` 都会跳过或拒绝（`artemis/core/diagnostics/engine.py:302-311,360,399`），**不会误杀远端机器上的 adb server**。
- 避开本机可能已存在的本地 adb server 端口冲突。

### 通用前置条件

- 手机所在机器（下称 **phone-host**）安装 Android Platform Tools，开启 USB 调试并授权，`adb devices` 显示 `device`。
- **两端 adb 版本必须一致**，否则探测报 `version mismatch`（`artemis/core/diagnostics/adb_server_connection.py:267-271`）。
- ARTEMIS 主机（下称 **artemis-host**）不要裸奔 daemon 的 8000 端口——管理 API 无内置鉴权（`packages/artemis-client/README.md:24-29`）。
- Admin API 的写接口要求 loopback 或显式开关（`apps/admin_console/routers/system.py:36-68`），改配置优先在 artemis-host 本机改 `.env`。

## 1. 场景决策

| 场景 | 网络关系 | 推荐方案 |
|---|---|---|
| A | 手机 USB 插在 artemis-host 本机 | 默认配置，无需隧道 |
| B | 手机插在另一台机器，artemis-host 能主动连到它（同局域网/可直连） | **SSH 正向隧道**（§2）或直连 |
| C | artemis-host 在云端，手机插在公司电脑（NAT 后，无入站） | **SSH 反向隧道**（§3）或 **frp**（§4） |

## 2. 场景 B：SSH 正向隧道（artemis-host 主动连出）

拓扑：artemis-host --- SSH ---> phone-host:5037

### 2.1 建立隧道

在 **artemis-host** 上执行，保持终端常开：

```bash
ssh -N -L 15037:127.0.0.1:5037 user@phone-host
```

> 命令里的 `127.0.0.1:5037` 是 **phone-host 自己**的 adb server 地址，不是 artemis-host 的。

验证：`adb -H 127.0.0.1 -P 15037 devices -l` 应列出手机。

### 2.2 配置 ARTEMIS

```ini
# artemis-host 的 .env
ADB_HOST=127.0.0.1
ADB_PORT=15037
```

或本机调用 Admin API（先探测再激活）：

```bash
curl -X POST http://localhost:8000/api/system/adb/server/probe \
  -H "Content-Type: application/json" \
  -d '{"host":"127.0.0.1","port":15037}'

curl -X POST http://localhost:8000/api/system/adb/server/connect \
  -H "Content-Type: application/json" \
  -d '{"host":"127.0.0.1","port":15037,"persist":true}'
```

请求体字段：`host`、`port`（默认 5037）、`persist`（默认 true），见 `apps/admin_console/routers/system.py:167-172`。`probe` 不改状态，`connect` 激活并写回 `.env`（`artemis/core/diagnostics/adb_server_connection.py:80-123,305-326`）。

### 2.3 保活

长期运行建议：

```bash
autossh -M 0 -N -o "ServerAliveInterval=30" -o "ServerAliveCountMax=3" \
  -L 15037:127.0.0.1:5037 user@phone-host
```

## 3. 场景 C：SSH 反向隧道（公司电脑主动连出）

拓扑：公司电脑 -- SSH -R ---> 云端 artemis-host，云端 `127.0.0.1:15037` 反向指向公司电脑的 `127.0.0.1:5037`。

云端有公网 IP，公司电脑在 NAT 后无入站，所以必须由公司电脑主动发起连接。

### 3.1 建立隧道

在 **公司电脑（phone-host）** 上执行：

```bash
ssh -N -R 15037:127.0.0.1:5037 user@<云端公网IP>
```

前提：

- 云端运行 sshd，公司电脑可用密钥登录；公司防火墙允许**出站 SSH（22）**。
- 公司电脑上 `adb devices` 能看到手机。

### 3.2 配置 ARTEMIS

云端 `.env`：

```ini
ADB_HOST=127.0.0.1
ADB_PORT=15037
```

### 3.3 保活

```bash
autossh -M 0 -N -o "ServerAliveInterval=30" -o "ServerAliveCountMax=3" \
  -R 15037:127.0.0.1:5037 user@<云端IP>
```

云端 sshd 可加 `ClientAliveInterval 30` 防空闲断连。Windows 公司电脑可用计划任务/服务包裹 `ssh -N -R ...`。

### 3.4 安全要点

- 云端给该账号最小权限：仅公钥认证、`AllowTcpForwarding remote`、`PermitOpen 127.0.0.1:5037`、`PermitTTY no`。
- **不要开 `GatewayPorts yes`**：ssh 默认只绑云端 `127.0.0.1`，ARTEMIS 本机连即可；开了反而把公司 adb server 暴露公网。

## 4. 场景 C：frp 反向代理

同样是公司电脑主动连出，但用 frp 做四层 TCP 转发（adb 是私有 TCP 协议，**HTTP 反向代理不适用**）。frp 自带心跳与自动重连，长期运行比裸 SSH 更省心。

### 4.1 普通 tcp 模式

**云端跑 `frps`，`frps.toml`：**

```toml
bindPort = 7000
auth.method = "token"
auth.token = "换成随机强token"
```

**公司电脑跑 `frpc`，`frpc.toml`：**

```toml
serverAddr = "<云端公网IP>"
serverPort = 7000
auth.method = "token"
auth.token = "换成相同token"

[[proxies]]
name = "adb"
type = "tcp"
localIP = "127.0.0.1"
localPort = 5037
remotePort = 15037
```

**云端 ARTEMIS 配置：**

```ini
ADB_HOST=127.0.0.1
ADB_PORT=15037
```

防火墙放行 `7000`（frpc 连入）；`15037` 建议只放行本机/可信来源，因为普通模式下 frps 的 `remotePort` 默认绑 `0.0.0.0`。

### 4.2 STCP 模式（更安全，两端都不暴露公网端口）

云端也跑一个 frpc 作为 visitor，两端都不开 `remotePort` 入站，只经 frps 信令中转。适合对公网暴露面要求严格的场景。

**公司电脑 frpc（被访问端）：**

```toml
serverAddr = "<云端公网IP>"
serverPort = 7000
auth.method = "token"
auth.token = "换成相同token"

[[proxies]]
name = "adb"
type = "stcp"
secretKey = "另一个随机强key"
localIP = "127.0.0.1"
localPort = 5037
```

**云端 frpc（visitor）：**

```toml
serverAddr = "127.0.0.1"
serverPort = 7000
auth.method = "token"
auth.token = "换成相同token"

[[visitors]]
name = "adb_visitor"
type = "stcp"
serverName = "adb"
secretKey = "另一个随机强key"
bindAddr = "127.0.0.1"
bindPort = 15037
```

云端 ARTEMIS 仍配 `ADB_HOST=127.0.0.1`、`ADB_PORT=15037`。此模式云端防火墙只需放行 frps 的 7000（且可限制为公司电脑来源）。

## 5. SSH 反向隧道 vs frp 对比

两者对 ARTEMIS 上层完全等价，差别在隧道本身的运维：

| 维度 | SSH 反向隧道 `ssh -R` | frp 反向代理 |
|---|---|---|
| 部署成本 | 最低：云端通常已有 sshd，Win10+ 自带 `ssh.exe`，零安装 | 需装 `frps` + `frpc` 两个二进制，各写配置 |
| 端口暴露 | 默认只绑云端 `127.0.0.1`，天然不对外暴露 | 普通 tcp 模式绑 `0.0.0.0`，需防火墙限制；STCP 不暴露 |
| 保活/重连 | 需 `ServerAliveInterval` + `autossh`，网络切换要重连 | frpc 自带心跳与自动重连，更省心 |
| 安全性 | SSH 密钥体系成熟，`PermitOpen` 可最小权限 | token 认证；STCP 模式最安全 |
| 多设备 | 一条隧道一个端口，多条要开多个会话 | 一个 `frpc.toml` 多个 `[[proxies]]`，集中管理 |
| 可观测性 | 靠 `ssh -v`、`ss -tlnp`，较原始 | frps/frpc 日志 + 可选 dashboard |
| 性能 | 纯 TCP 转发，开销可忽略 | 同样是纯 TCP 转发，开销可忽略 |

**选择建议：**

- 临时调试 / 已有 SSH 权限 / 单台设备 → SSH 反向隧道，最快打通。
- 长期挂载 / 多设备 / 要日志和自动重连 → frp，建议直接上 STCP。

## 6. 验证（通用）

在 **artemis-host** 上执行：

```bash
# 1) 直接看 adb server 能不能枚举到手机
adb -H 127.0.0.1 -P 15037 devices -l

# 2) 看当前端点与模式（mode 应为 remote）
curl http://localhost:8000/api/system/adb/server

# 3) 探测（不改状态）
curl -X POST http://localhost:8000/api/system/adb/server/probe \
  -H "Content-Type: application/json" \
  -d '{"host":"127.0.0.1","port":15037}'

# 4) 环境诊断
uv run artemis doctor

# 5) 跑一个真实任务，确认截图与操作日志
uv run artemis run "打开设置并截图" --profile flash
```

端点接口见 `apps/admin_console/routers/system.py:175`；trace 中截图正常即链路打通。

## 7. 回退与排错

### 回退到本地

先切回本地再关隧道（避免关闭隧道后 ARTEMIS 仍指向失效端点）：

```bash
curl -X POST "http://localhost:8000/api/system/adb/server/local?persist=true"
```

或把 `.env` 改回 `ADB_HOST=127.0.0.1`、`ADB_PORT=5037` 后重启。

### 常见故障

| 现象 | 原因/处理 |
|---|---|
| `adb devices` 离线 | 隧道/代理断开；重连公司电脑的 `ssh -R` 或 `frpc`，`.env` 不用改 |
| 探测返回 `version mismatch` | 两端 adb 版本不一致，统一 Android Platform Tools 版本 |
| 探测超时 | 检查 `15037` 是否在云端监听、防火墙是否放行、token/ssh 是否通 |
| 端点显示 `local` | 用了 5037 端口；改用 15037 以避免触发本地分支 |
| 公司 adb server 被杀 | 在 5037 误用 + 点了「重启 ADB server」；改端口后在 phone-host 上 `adb start-server` |

## 8. 备选方案说明

- **`ARTEMIS_CLOUD_MODE=1`**：依赖仓库外的可选包 `cloud_service.virtualization`，项目内只有注入点（`artemis/drivers/factory.py:36-47`），实现不在本仓库。
- **MQTT 远程通道**：仓库里没有 MQTT 代码，相关方案尚未实现，暂不可用。
- **`CloudDeviceDriver`**：未接线的桩（`artemis/drivers/cloud/cloud_driver.py`），不要基于它扩展。
- **VPN（Tailscale/WireGuard）**：把两端放进同一虚拟局域网后直连 `phone-host VPN-IP:5037`。注意 adb server 默认只监听 `127.0.0.1`，需在 phone-host 上改成 `ADB_SERVER_SOCKET=tcp:0.0.0.0:5037 adb start-server` 才能被外部访问。
