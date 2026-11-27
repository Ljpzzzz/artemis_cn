#!/usr/bin/env bash
# 先提交本地改动，再把 ARTEMIS 项目部署到云端服务器。
# 本地在 Windows Git Bash 中运行：bash scripts/deploy_to_cloud.sh [提交信息]
# 云端目录：/root/crm/app/artemis_cn/
set -euo pipefail

# ====== 可修改配置 ======
CLOUD_HOST="${CLOUD_HOST:-193.112.112.199}"
CLOUD_USER="${CLOUD_USER:-root}"
CLOUD_PORT="${CLOUD_PORT:-22}"
CLOUD_DIR="${CLOUD_DIR:-/root/crm/app/artemis_cn}"
TUNNEL_PORT="${TUNNEL_PORT:-15037}"   # 反向隧道落地端口

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
LOCAL_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"
PKG="/tmp/artemis_deploy.tar.gz"

SSH="ssh -p $CLOUD_PORT -o StrictHostKeyChecking=accept-new $CLOUD_USER@$CLOUD_HOST"
SCP="scp -P $CLOUD_PORT -o StrictHostKeyChecking=accept-new"

echo "本地目录: $LOCAL_DIR"
echo "目标:     $CLOUD_USER@$CLOUD_HOST:$CLOUD_DIR"

# 0. 连通性检查（非致命，仅提示）
echo ""
echo "[0/7] 检查 SSH 连通性..."
if $SSH -o BatchMode=yes -o ConnectTimeout=10 true >/dev/null 2>&1; then
  echo "  免密登录 OK"
else
  echo "  未检测到免密登录。建议先配置密钥，否则后续会多次要求输入密码："
  echo "    ssh-keygen -t ed25519"
  echo "    ssh-copy-id -p $CLOUD_PORT $CLOUD_USER@$CLOUD_HOST"
fi

# 1. 提交本地改动（.env 已被 gitignore，不会提交密钥）
echo ""
echo "[1/7] 提交本地改动..."
cd "$LOCAL_DIR"
if [ -n "$(git status --porcelain)" ]; then
  COMMIT_MSG="${1:-deploy: sync working tree before cloud deployment}"
  git add -A
  git commit -m "$COMMIT_MSG"
  echo "  已提交: $(git rev-parse --short HEAD) $COMMIT_MSG"
else
  echo "  工作树干净，无需提交"
fi

# 2. 推送到远端（origin）
echo ""
echo "[2/7] 推送到 origin..."
BRANCH="$(git rev-parse --abbrev-ref HEAD)"
if git status -sb | grep -q '\[ahead'; then
  git push origin "$BRANCH"
  echo "  已推送 $BRANCH 到 origin"
else
  echo "  本地没有领先的提交，无需推送"
fi

# 3. 本地打包（排除大目录/缓存/可变状态）
echo ""
echo "[3/7] 打包项目..."
tar -czf "$PKG" \
  --exclude='./.venv' \
  --exclude='./node_modules' \
  --exclude='./.git' \
  --exclude='./.pytest_cache' \
  --exclude='./.ruff_cache' \
  --exclude='*/__pycache__' \
  --exclude='*.pyc' \
  --exclude='./traces' \
  --exclude='./scratch' \
  --exclude='./*.tar.gz' \
  -C "$LOCAL_DIR" .
ls -lh "$PKG"

# 4. 上传并解压
echo ""
echo "[4/7] 上传到云端..."
$SCP "$PKG" "$CLOUD_USER@$CLOUD_HOST:/tmp/artemis_deploy.tar.gz"

echo ""
echo "[5/7] 解压到 $CLOUD_DIR ..."
$SSH "mkdir -p '$CLOUD_DIR' && tar -xzf /tmp/artemis_deploy.tar.gz -C '$CLOUD_DIR' && rm -f /tmp/artemis_deploy.tar.gz"

# 6. 云端部署（系统依赖、Python/前端依赖、构建、端点配置）
echo ""
echo "[6/7] 云端安装依赖与构建..."
$SSH bash -s -- "$CLOUD_DIR" "$TUNNEL_PORT" <<'REMOTE'
set -euo pipefail
APP_DIR="$1"
TUNNEL_PORT="$2"

echo "--- 系统信息 ---"
head -3 /etc/os-release

echo "--- 安装 adb ---"
if command -v apt-get >/dev/null 2>&1; then
  apt-get update -qq && apt-get install -y -qq android-tools-adb
elif command -v yum >/dev/null 2>&1; then
  yum install -y android-tools
elif command -v dnf >/dev/null 2>&1; then
  dnf install -y android-tools
else
  echo "未识别包管理器，请手动安装 adb。"
fi
adb version 2>/dev/null || echo "警告: adb 未就绪"

echo "--- 安装 uv ---"
if ! command -v uv >/dev/null 2>&1; then
  curl -LsSf https://astral.sh/uv/install.sh | sh
  export PATH="$HOME/.local/bin:$HOME/.cargo/bin:$PATH"
fi
uv --version

echo "--- Node 版本（build-ui 需要 Node 22）---"
node --version 2>/dev/null || echo "警告: 未安装 Node，前端构建将失败"

echo "--- Python 依赖 ---"
cd "$APP_DIR"
uv sync --dev

echo "--- 构建前端 UI ---"
cd "$APP_DIR/apps/showcase_ui"
npm install
npm run build

echo "--- 配置 ADB 端点（反向隧道端口 $TUNNEL_PORT）---"
cd "$APP_DIR"
if [ -f .env ]; then
  sed -i "s|^ADB_HOST=.*|ADB_HOST=127.0.0.1|" .env
  sed -i "s|^ADB_PORT=.*|ADB_PORT=$TUNNEL_PORT|" .env
  grep -q '^ADB_HOST=' .env || echo "ADB_HOST=127.0.0.1" >> .env
  grep -q '^ADB_PORT=' .env || echo "ADB_PORT=$TUNNEL_PORT" >> .env
else
  echo "ADB_HOST=127.0.0.1" > .env
  echo "ADB_PORT=$TUNNEL_PORT" >> .env
fi
grep '^ADB_' .env

echo "云端部署完成: $APP_DIR"
REMOTE

# 7. 后续提示
echo ""
echo "[7/7] 部署完成"
echo ""
echo "下一步：在公司电脑（手机所在机器）建立反向隧道，保持终端常开："
echo "  ssh -N -R ${TUNNEL_PORT}:127.0.0.1:5037 ${CLOUD_USER}@${CLOUD_HOST}"
echo ""
echo "云端验证："
echo "  adb -H 127.0.0.1 -P ${TUNNEL_PORT} devices -l"
echo "  cd ${CLOUD_DIR} && uv run artemis run \"打开设置并截图\" --profile flash"
rm -f "$PKG"
