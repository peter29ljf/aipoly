#!/usr/bin/env bash
# 从旧机把 aipoly v2 部署到新服务器。在旧机上执行：
#
#   bash deploy/v2/deploy.sh root@<新IP>
#
# 只传源码（纯文本、都在 git 里、可审阅），不传 .venv / node_modules /
# 运行态数据 —— 旧机的泄露源至今未定位，不该把不可审阅的东西搬进干净机器。
set -euo pipefail

TARGET="${1:?用法: deploy.sh root@<host>}"
SSH_OPTS=(-o StrictHostKeyChecking=accept-new -o ConnectTimeout=15)
SRC="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"

echo "==> 传输 v2 组件（这些是本次新写的，不在 GitHub 上）"
scp "${SSH_OPTS[@]}" -q \
	"$SRC/deploy/v2/install.sh" \
	"$SRC/deploy/v2/aipoly-run-agent" \
	"$SRC/deploy/v2/main.py" \
	"$SRC/deploy/v2/aipoly-core.service" \
	"$SRC/deploy/v2/aipoly-mcp@.service" \
	"$SRC/deploy/v2/aipoly-bot.service" \
	"$SRC/deploy/v2/aipoly-bot.sudoers" \
	"$SRC/bot/telegram_bot.py" \
	"$TARGET:/tmp/"

echo "==> 远端安装"
ssh "${SSH_OPTS[@]}" "$TARGET" 'bash -euo pipefail -s' <<'REMOTE'
export DEBIAN_FRONTEND=noninteractive

echo "--> 依赖"
apt-get update -qq
apt-get install -y -qq python3-venv python3-pip curl ca-certificates sqlite3 >/dev/null
if ! command -v node >/dev/null; then
	curl -fsSL https://deb.nodesource.com/setup_22.x | bash - >/dev/null 2>&1
	apt-get install -y -qq nodejs >/dev/null
fi
command -v claude >/dev/null || npm install -g @anthropic-ai/claude-code >/dev/null 2>&1

echo "--> 用户与目录"
bash /tmp/install.sh

echo "--> 代码：从 GitHub 拉取，不经旧机文件系统"
# 旧机的泄露源至今未定位，所以交易核心从 GitHub 取，源头可审计。
# 全部 16+7 个 commit 已逐个扫描：无密钥、无动态执行、无混淆，
# 出站目标只有 clob/gamma/data-api.polymarket.com 与 api.telegram.org。
rm -rf /opt/aipoly
git clone --depth 1 https://github.com/peter29ljf/aipoly.git /opt/aipoly
rm -rf /opt/aipoly/.git /opt/aipoly/frontend /opt/aipoly/deploy
# v2 的入口替换掉 v1 的（v1 那份带 CORS 通配符、静态服务和 chat 路由）
install -o root -g root -m 644 /tmp/main.py /opt/aipoly/backend/main.py
install -d -o root -g root -m 755 /opt/aipoly/bot
install -o root -g root -m 644 /tmp/telegram_bot.py /opt/aipoly/bot/telegram_bot.py
: > /opt/aipoly/bot/__init__.py
rm -f /opt/aipoly/backend/routers/chat.py /opt/aipoly/backend/event_bus.py
# chat 路由已删，把 __init__ 里可能的引用一并去掉
sed -i '/chat/d' /opt/aipoly/backend/routers/__init__.py 2>/dev/null || true

echo "--> 运行态改指向 /var/lib（代码里用的是仓库相对路径，这里用软链接接管）"
rm -rf /opt/aipoly/strategies /opt/aipoly/data
ln -sfn /var/lib/aipoly/strategies /opt/aipoly/strategies
ln -sfn /var/lib/aipoly/data      /opt/aipoly/data

echo "--> Python 虚拟环境"
python3 -m venv /opt/aipoly/.venv
/opt/aipoly/.venv/bin/pip install -q --upgrade pip
/opt/aipoly/.venv/bin/pip install -q -r /opt/aipoly/requirements.txt
chown -R root:root /opt/aipoly          # 代码 root 所有，服务只读

echo "--> 启动器与 sudoers"
install -o root -g root -m 755 /tmp/aipoly-run-agent /usr/local/sbin/aipoly-run-agent
install -o root -g root -m 440 /tmp/aipoly-bot.sudoers /etc/sudoers.d/aipoly-bot
visudo -c >/dev/null

echo "--> systemd"
install -o root -g root -m 644 /tmp/aipoly-core.service /tmp/'aipoly-mcp@.service' \
	/tmp/aipoly-bot.service /etc/systemd/system/
systemctl daemon-reload

echo "--> 清理传输残留"
rm -f /tmp/telegram_bot.py /tmp/main.py /tmp/install.sh /tmp/aipoly-run-agent \
	/tmp/aipoly-*.service /tmp/aipoly-bot.sudoers

echo
echo "✅ 安装完成，服务尚未启动（凭证还是空的）"
REMOTE

cat <<'NEXT'

下一步（需要你提供凭证）：
  1. /etc/aipoly/wallet.env    PRIVATE_KEY / WALLET_ADDRESS / CLOB 三件套
  2. /etc/aipoly/telegram.env  TELEGRAM_BOT_TOKEN / TELEGRAM_ADMIN_IDS / AIPM_TOKEN
  3. /etc/aipoly/claude.env    CLAUDE_CODE_OAUTH_TOKEN
  4. /etc/aipoly/mcp.env       AIPM_TOKEN（与 2 中同一个值）

  然后：
    systemctl enable --now aipoly-core aipoly-mcp@{poly_trade,portfolio,scheduler,sweep,strategy_doc} aipoly-bot
NEXT
