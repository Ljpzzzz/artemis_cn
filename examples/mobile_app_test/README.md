# 用 ARTEMIS 做手机 App 自动化测试（模板）

这套模板演示如何把 ARTEMIS 当作**移动端自动化框架**来测你自己的 App：
你写一句自然语言 goal（操作 + 要验证的结果），ARTEMIS 在真机/模拟器上自主完成
"定位元素 → 点击/输入 → 观察屏幕 → 判断结果"，pytest 只对返回结果做断言。

无需 Appium、无需写 selector（靠视觉 + 无障碍层级定位）。

## 架构

- **设备主机**：连着手机/模拟器，运行完整 ARTEMIS + daemon（`uv run artemis ui` 或后台常驻）。
- **测试机**：只装零依赖的 `artemis-client`，通过 HTTP 把任务交给设备主机。

## 1. 准备

设备主机：
```bash
# 连好设备（USB 调试）或启动模拟器，配好 .env 里的模型密钥
uv run artemis doctor          # 确认设备/ADB/工具链正常
uv run artemis ui              # 启动 daemon（含管理后台），监听 8000
```

测试机安装 SDK（零第三方依赖，Python >=3.10）：
```bash
uv add "artemis-client @ git+https://github.com/google/artemis.git#subdirectory=packages/artemis-client"
```

## 2. 配置环境变量

daemon 无内置鉴权，不要直接暴露公网端口，用 SSH 隧道：
```bash
ssh -L 8000:127.0.0.1:8000 user@artemis-host
```

然后（测试机）：
```bash
export ARTEMIS_BASE_URL=http://127.0.0.1:8000   # 必填，否则用例自动 skip
export APP_PACKAGE=com.example.myapp            # 被测 App 包名
export APK_PATH=/opt/apks/myapp.apk             # 可选：APK 在【设备主机】上的路径
export DEVICE_SERIAL=emulator-5554              # 可选：指定设备
export TEST_USER=test@example.com               # 业务用例账号
export TEST_PASSWORD=123456
# export ARTEMIS_TOKEN=xxx                       # 若前面挂了带鉴权的反向代理
# export ARTEMIS_PROFILE=flash                   # 全局默认 profile
```

`APK_PATH` 是**设备主机上的路径**（daemon 负责安装），不是测试机本地路径。
若 App 已预装，留空即可。

## 3. 运行

```bash
cd examples/mobile_app_test
uv run pytest -q
```

未设置 `ARTEMIS_BASE_URL` 时全部用例安全 skip，不会尝试连设备。

## 4. 关键写法

- **goal 要可验证**：末尾要求"只回答 X 或 Y"，`result.output` 就成了可断言的结构化结果。
  例：`...只回答 'HOME' 或 'FAILED'` → `assert_output_contains(result, "HOME")`。
- **锁定被测 App**：`locked_app_package` 防止 agent 中途跳到桌面或其它 App。
- **profile 选择**：大量冒烟用 `flash`（~3-5s/步）；关键路径用 `pro` + `verification_level="strict"`
  让 Checker 逐步审查（~15-40s/步）。
- **失败排查**：断言失败信息带 `trace_id`，到设备主机 Web UI `/admin` 回放每步截图与思考过程。

## 5. 可用参数（`client.run()` / `client.submit()`）

| 参数 | 用途 |
|---|---|
| `goal` | 自然语言操作 + 验证要求 |
| `profile` | `flash` / `pro` |
| `device_serial` | 指定设备 |
| `locked_app_package` | 锁定被测 App |
| `app_path` | APK 路径（设备主机上） |
| `expected_output` | 期望输出描述 |
| `verification_level` | Pro 专属：`off`/`final`/`checkpoints`/`strict` |
| `explorer_mode` | Pro 感知层级：`flash`/`pro`/`ultra` |

`TaskResult` 断言字段：`succeeded`、`status`、`output`、`error`、`trace_id`、`turns`、`raw`。

## 6. CI 集成提示

这类测试依赖真机与 daemon，属于慢速/需外部状态，应单独 job 运行，不要并入 hermetic 单测。
```yaml
- name: App tests via Artemis
  env:
    ARTEMIS_BASE_URL: http://127.0.0.1:8000
    APP_PACKAGE: com.example.myapp
  run: uv run pytest examples/mobile_app_test -q
```
失败时把 trace 截图、agent output 作为 CI artifact 收集。
