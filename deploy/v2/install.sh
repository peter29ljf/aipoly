#!/usr/bin/env bash
# aipoly v2 —— 无 Web UI，Telegram 为唯一控制面。
#
# 这个脚本只做一件事：把「谁能读私钥」这个问题交给操作系统来回答。
# 旧版所有组件都以 root 运行，分层形同虚设；这里每个组件一个用户，
# 私钥文件只有 aipoly-core 能读，agent 连目录都进不去。
#
# 幂等，可重复执行。
set -euo pipefail

APP=/opt/aipoly          # 代码：root 所有，服务只读
STATE=/var/lib/aipoly    # 运行态：策略文档、持仓、数据库
SECRETS=/etc/aipoly      # 凭证：每个文件只对一个用户开放
LOGS=/var/log/aipoly

echo "==> 创建服务用户（均为 --system --no-create-home，不可登录）"
for u in aipoly-core aipoly-mcp aipoly-agent aipoly-bot; do
	if ! id "$u" &>/dev/null; then
		useradd --system --no-create-home --shell /usr/sbin/nologin "$u"
		echo "    + $u"
	else
		echo "    = $u（已存在）"
	fi
done

echo "==> 目录骨架"
install -d -o root       -g root        -m 755 "$APP"
install -d -o aipoly-core -g aipoly-core -m 750 "$STATE"
install -d -o root       -g root        -m 755 "$SECRETS"
install -d -o root       -g root        -m 755 "$LOGS"

# 策略运行态：core 写入，agent 需要读写策略文档 → 用组共享
install -d -o aipoly-core -g aipoly-agent -m 770 "$STATE/strategies"
install -d -o aipoly-core -g aipoly-core  -m 700 "$STATE/data"

echo "==> 凭证文件（不存在则建空壳，权限先收紧）"
# 关键：每个 .env 只对一个用户可读。私钥那个文件 agent 无论如何读不到。
new_secret() {  # new_secret <文件> <属组>
	local f="$SECRETS/$1" g="$2"
	[ -e "$f" ] || : > "$f"
	chown root:"$g" "$f"
	chmod 640 "$f"
	echo "    $f  root:$g 640"
}
new_secret wallet.env   aipoly-core    # PRIVATE_KEY / WALLET_ADDRESS / CLOB 凭证
new_secret mcp.env      aipoly-mcp     # AIPM_TOKEN
new_secret telegram.env aipoly-bot     # TELEGRAM_BOT_TOKEN / TELEGRAM_ADMIN_IDS
new_secret claude.env   aipoly-agent   # CLAUDE_CODE_OAUTH_TOKEN

echo "==> 日志目录"
for u in core mcp agent bot; do
	install -d -o "aipoly-$u" -g "aipoly-$u" -m 750 "$LOGS/$u"
done

echo
echo "==> 权限自检：agent 能否读到私钥？"
if sudo -u aipoly-agent test -r "$SECRETS/wallet.env" 2>/dev/null; then
	echo "    ❌ 失败 —— agent 可以读私钥，安装不正确"
	exit 1
else
	echo "    ✅ 读不到（这正是本次重构的全部意义）"
fi

echo "==> core 能否读到私钥？"
sudo -u aipoly-core test -r "$SECRETS/wallet.env" \
	&& echo "    ✅ 能读（下单需要）" \
	|| { echo "    ❌ 读不到，core 无法下单"; exit 1; }

echo
echo "完成。下一步：填 $SECRETS/*.env，然后 systemctl enable --now aipoly-core aipoly-bot"
