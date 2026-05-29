"""scheduler MCP：定时任务管理（端口 8103）。"""

import json
import os
import sys

sys.path.insert(0, "/root/aipolymarket")

from fastmcp import FastMCP
from mcp_servers._common import api_post, api_get, api_delete, sid as _env_sid

mcp = FastMCP("scheduler")


def _sid(strategy_id: str) -> str:
    return strategy_id.strip() or _env_sid()


@mcp.tool()
def schedule_task(cron: str, strategy_id: str = "", job_id: str = "") -> str:
    """创建 cron 定时任务，到时自动触发 Claude 运行本策略。
    - strategy_id: 策略目录名（如 'strategy-2'），必须传入
    - cron: '分 时 日 月 周'（5 字段，UTC 时区）
      示例：'5 9 * * *' = 每天 UTC 09:05"""
    try:
        payload: dict = {"sid": _sid(strategy_id), "cron": cron}
        if job_id:
            payload["job_id"] = job_id
        result = api_post("/_internal/schedule/cron", payload)
        return json.dumps(result, ensure_ascii=False)
    except Exception as e:
        return json.dumps({"error": str(e)})


@mcp.tool()
def schedule_once(run_at: str, strategy_id: str = "", job_id: str = "") -> str:
    """创建一次性延迟任务。
    - strategy_id: 策略目录名，必须传入
    - run_at: ISO8601 UTC 时间字符串，如 '2026-06-01T09:00:00+00:00'"""
    try:
        payload: dict = {"sid": _sid(strategy_id), "run_at": run_at}
        if job_id:
            payload["job_id"] = job_id
        result = api_post("/_internal/schedule/once", payload)
        return json.dumps(result, ensure_ascii=False)
    except Exception as e:
        return json.dumps({"error": str(e)})


@mcp.tool()
def list_tasks(strategy_id: str = "") -> str:
    """列出当前策略的所有定时任务。strategy_id 为策略目录名。"""
    try:
        result = api_get(f"/_internal/schedule/{_sid(strategy_id)}")
        return json.dumps(result, ensure_ascii=False)
    except Exception as e:
        return json.dumps({"error": str(e)})


@mcp.tool()
def cancel_task(job_id: str) -> str:
    """取消指定定时任务。"""
    try:
        result = api_delete(f"/_internal/schedule/{job_id}")
        return json.dumps(result, ensure_ascii=False)
    except Exception as e:
        return json.dumps({"error": str(e)})


if __name__ == "__main__":
    port = int(os.environ.get("MCP_PORT", "8103"))
    mcp.run(transport="sse", host="0.0.0.0", port=port)
