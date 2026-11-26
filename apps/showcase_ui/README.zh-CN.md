# ✨ Artemis 展示与用户工作区 UI

一个使用 **Angular 19** 和 **SCSS** 构建的现代、高颜值展示与交互前端，用于呈现 Artemis 移动端自主智能体。

## 🎨 视觉设计亮点

* **极光辉光动态效果**：带有平滑渐变的环境背景光。
* **玻璃拟态美学**：半透明磨砂玻璃面板，搭配细腻边框。
* **实时双栏工作区**：
  - **左栏（`app-agent-stream`）**：实时流式展示智能体的思考步骤、任务计划拆解、工具动作和状态。
  - **右栏（`app-chat-interface`）**：自然语言聊天输入侧栏，带交互式反馈和状态标签。

## 🚀 如何运行

### 前置条件
- Node.js（>= 18）
- 后端 API 运行于 `http://localhost:8000`（通过 `apps/admin_console` 或 `artemis ui`）

### 开发服务器
```bash
cd apps/showcase_ui
npm install
npm start
```
这会在 **`http://localhost:4200/`** 上运行 `ng serve --proxy-config proxy.conf.json`。

### 生产构建
```bash
npm run build
```
构建产物输出到 `dist/`，可由 `apps.admin_console` 或 `artemis ui` 静态托管。
