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
    from backend.claude_runner import run_claude, is_locked

    alerts = get_all_active_alerts()
    if not alerts:
        return

    # 用 asyncio.to_thread 避免 blocking requests 调用卡住事件循环
    from backend.api_client import get_midpoint

    token_ids = list({a["token_id"] for a in alerts})
    prices: dict[str, float] = {}
    for tid in token_ids:
        try:
            mid = await asyncio.to_thread(get_midpoint, tid)
            if mid is not None:
                prices[tid] = mid
        except Exception as e:
            logger.warning("get_midpoint failed for %s: %s", tid[:20], e)

    for alert in alerts:
        tid = alert["token_id"]
        mid = prices.get(tid)
        if mid is None:
            logger.debug("Alert %d: no price for token %s, skipping", alert["id"], tid[:20])
            continue

        fired = False
        if alert["direction"] == "above" and mid >= alert["target"]:
            fired = True
        elif alert["direction"] == "below" and mid <= alert["target"]:
            fired = True

        if not fired:
            continue

        sid = alert["sid"]

        # 策略正在运行时跳过（不消耗警报，等下次轮询再试）
        if is_locked(sid):
            logger.info(
                "Alert %d fired (price=%.4f) but strategy %s is locked — will retry next poll",
                alert["id"], mid, sid,
            )
            continue

        # 先标记为已触发，再启动 Claude（防止重复触发）
        mark_fired(alert["id"], mid)
        logger.info(
            "Alert %d fired: sid=%s token=%s... price=%.4f target=%.4f %s",
            alert["id"], sid, tid[:16], mid, alert["target"], alert["direction"],
        )

        started = await run_claude(
            sid, trigger="alert",
            extra={"alert_id": alert["id"], "fired_price": mid},
        )
        if not started:
            logger.warning("Alert %d: run_claude returned False for sid=%s", alert["id"], sid)
