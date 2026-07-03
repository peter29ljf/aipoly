#!/usr/bin/env bash
# 一键启动 aipolymarket：后端 + 所有 MCP 服务器
set -e
cd /root/aipoly

export PATH="$HOME/.local/bin:$PATH"

BACKEND_PORT="${BACKEND_PORT:-8010}"
export BACKEND_PORT

echo "=== aipolymarket ==="
echo "Backend port: $BACKEND_PORT"

# 安装依赖（如未安装）
if ! .venv/bin/python3 -c "import fastapi" 2>/dev/null; then
  echo "Installing Python dependencies..."
  .venv/bin/pip install -r requirements.txt -q
fi

# 先启动后端（生成 .token）
echo "Starting backend..."
BACKEND_PORT="$BACKEND_PORT" .venv/bin/python3 -m uvicorn backend.main:app \
  --host 0.0.0.0 --port "$BACKEND_PORT" \
  --log-level info &
BACKEND_PID=$!
echo "Backend PID: $BACKEND_PID"

# 等待后端就绪并生成 token
sleep 4
TOKEN=$(cat data/.token 2>/dev/null || echo "")

# 生成集中式 MCP 环境变量文件（唯一真源，含密钥，已加入 .gitignore）
cat > data/mcp.env <<EOF
AIPM_TOKEN=$TOKEN
API_BASE=http://127.0.0.1:$BACKEND_PORT
STRATEGY_ID=
AIPM_TRADE_MODE=live
EOF

set -a
source data/mcp.env
set +a

# 启动 MCP 服务器（env 已通过 mcp.env 导出，无需再逐行内联）
echo "Starting MCP servers..."
MCP_PORT=8101 .venv/bin/python3 -m mcp_servers.poly_trade.server &
MCP_PORT=8102 .venv/bin/python3 -m mcp_servers.portfolio.server &
MCP_PORT=8103 .venv/bin/python3 -m mcp_servers.scheduler.server &
MCP_PORT=8104 .venv/bin/python3 -m mcp_servers.sweep.server &
MCP_PORT=8105 .venv/bin/python3 -m mcp_servers.strategy_doc.server &

echo ""
echo "================================================================"
echo " aipolymarket 已启动"
echo "================================================================"
echo "  后端 API:     http://localhost:$BACKEND_PORT"
echo "  API 文档:     http://localhost:$BACKEND_PORT/docs"
if [ -d "frontend/dist" ]; then
  echo "  前端 UI:      http://localhost:$BACKEND_PORT"
elif [ -d "frontend/node_modules" ]; then
  echo "  开发前端:     cd frontend && npm run dev  (http://localhost:5173)"
fi
echo ""
echo "  MCP 服务器:"
echo "    poly_trade:   http://localhost:8101/sse"
echo "    portfolio:    http://localhost:8102/sse"
echo "    scheduler:    http://localhost:8103/sse"
echo "    sweep:        http://localhost:8104/sse"
echo "    strategy_doc: http://localhost:8105/sse"
echo "================================================================"
echo ""
echo "按 Ctrl+C 停止所有服务。"

cleanup() {
  echo "Stopping all services..."
  kill 0
}
trap cleanup EXIT INT TERM
wait
