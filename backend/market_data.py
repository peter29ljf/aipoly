"""价格监控后台任务：每 30s 轮询活跃警报的 token midpoint，触发时启动 Claude 运行。"""

import asyncio
import logging

logger = logging.getLogger(__name__)

POLL_INTERVAL = 30  # seconds


async def price_monitor_loop():
    """在 FastAPI lifespan 中作为后台任务启动。"""
    logger.info("Price monitor started (interval=%ds)", POLL_INTERVAL)
    while True:
        try:
            await _check_alerts()
        except Exception:
            logger.exception("Price monitor error")
        await asyncio.sleep(POLL_INTERVAL)


async def _check_alerts():
    from backend.alerts_db import get_all_active_alerts, mark_fired
    from backend.api_client import get_midpoint
    from backend.claude_runner import run_claude

    alerts = get_all_active_alerts()
    if not alerts:
        return

    token_ids = list({a["token_id"] for a in alerts})
    prices: dict[str, float] = {}
    for tid in token_ids:
        mid = get_midpoint(tid)
        if mid is not None:
            prices[tid] = mid

    for alert in alerts:
        tid = alert["token_id"]
        mid = prices.get(tid)
        if mid is None:
            continue

        fired = False
        if alert["direction"] == "above" and mid >= alert["target"]:
            fired = True
        elif alert["direction"] == "below" and mid <= alert["target"]:
            fired = True

        if fired:
            mark_fired(alert["id"], mid)
            logger.info("Alert %d fired: token=%s price=%.4f target=%.4f %s",
                        alert["id"], tid, mid, alert["target"], alert["direction"])
            await run_claude(alert["sid"], trigger="alert", extra={"alert_id": alert["id"], "fired_price": mid})
