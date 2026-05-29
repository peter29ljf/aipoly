#!/usr/bin/env bash
# 启动所有 MCP 服务器（后台运行）
set -e
cd /root/aipolymarket

# 从 data/.token 加载内部 token
TOKEN=$(cat data/.token 2>/dev/null || echo "")
export AIPM_TOKEN="$TOKEN"
export API_BASE="http://127.0.0.1:8010"

echo "Starting MCP servers..."

MCP_PORT=8101 AIPM_TOKEN="$TOKEN" API_BASE="$API_BASE" \
  python3 -m mcp_servers.poly_trade.server &
echo "poly_trade MCP started on :8101 (PID $!)"

MCP_PORT=8102 AIPM_TOKEN="$TOKEN" API_BASE="$API_BASE" \
  python3 -m mcp_servers.portfolio.server &
echo "portfolio MCP started on :8102 (PID $!)"

MCP_PORT=8103 AIPM_TOKEN="$TOKEN" API_BASE="$API_BASE" \
  python3 -m mcp_servers.scheduler.server &
echo "scheduler MCP started on :8103 (PID $!)"

MCP_PORT=8104 \
  python3 -m mcp_servers.sweep.server &
echo "sweep MCP started on :8104 (PID $!)"

MCP_PORT=8105 AIPM_TOKEN="$TOKEN" API_BASE="$API_BASE" \
  python3 -m mcp_servers.strategy_doc.server &
echo "strategy_doc MCP started on :8105 (PID $!)"

echo ""
echo "All MCP servers started. Use 'kill %1 %2 %3 %4 %5' to stop."
wait
