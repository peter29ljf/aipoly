#!/usr/bin/env bash
# 重启单个 MCP 服务器，始终从 data/mcp.env 加载完整环境变量。
# 用法: bash restart_mcp.sh <poly_trade|portfolio|scheduler|sweep|strategy_doc>
#
# 不要手动拼接 `MCP_PORT=... AIPM_TOKEN=... python3 -m mcp_servers.X.server` 命令行——
# 这正是本脚本要杜绝的错误来源（漏传 token / 漏传 AIPM_TRADE_MODE）。
set -e
cd "$(dirname "$0")"

declare -A PORTS=(
  [poly_trade]=8101
  [portfolio]=8102
  [scheduler]=8103
  [sweep]=8104
  [strategy_doc]=8105
)

NAME="$1"
if [ -z "$NAME" ] || [ -z "${PORTS[$NAME]:-}" ]; then
  echo "用法: bash restart_mcp.sh <${!PORTS[@]// /|}>" >&2
  echo "可选: ${!PORTS[@]}" >&2
  exit 1
fi

if [ ! -f data/mcp.env ]; then
  echo "错误: data/mcp.env 不存在。请先运行一次 'bash start.sh' 完整启动一次系统。" >&2
  exit 1
fi

set -a
source data/mcp.env
set +a

PORT="${PORTS[$NAME]}"
export MCP_PORT="$PORT"

# 杀掉占用该端口的旧进程（可能有多个残留 PID）
OLD_PIDS=$(lsof -ti:"$PORT" 2>/dev/null || true)
if [ -n "$OLD_PIDS" ]; then
  echo "Stopping old $NAME (PID(s): $(echo "$OLD_PIDS" | tr '\n' ' ')) on port $PORT..."
  echo "$OLD_PIDS" | xargs -r kill -9 2>/dev/null || true
  sleep 1
fi

echo "Starting $NAME on port $PORT (AIPM_TRADE_MODE=${AIPM_TRADE_MODE:-<unset>})..."
nohup .venv/bin/python3 -m "mcp_servers.$NAME.server" > "/tmp/${NAME}_mcp.log" 2>&1 &
NEW_PID=$!
sleep 2

if kill -0 "$NEW_PID" 2>/dev/null; then
  echo "$NAME started (PID $NEW_PID). Log: /tmp/${NAME}_mcp.log"
else
  echo "$NAME failed to start — check /tmp/${NAME}_mcp.log" >&2
  tail -n 20 "/tmp/${NAME}_mcp.log" >&2
  exit 1
fi
