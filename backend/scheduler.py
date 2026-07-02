"""APScheduler 后台调度器：支持 cron 和一次性任务。"""

import logging
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.jobstores.sqlalchemy import SQLAlchemyJobStore
from pathlib import Path

logger = logging.getLogger(__name__)

DB_PATH = Path(__file__).resolve().parent.parent / "data" / "scheduler.db"

_scheduler: AsyncIOScheduler | None = None


def get_scheduler() -> AsyncIOScheduler:
    global _scheduler
    if _scheduler is None:
        DB_PATH.parent.mkdir(parents=True, exist_ok=True)
        jobstores = {"default": SQLAlchemyJobStore(url=f"sqlite:///{DB_PATH}")}
        _scheduler = AsyncIOScheduler(jobstores=jobstores)
    return _scheduler


def start():
    sch = get_scheduler()
    if not sch.running:
        sch.start()
        logger.info("Scheduler started")


def shutdown():
    sch = get_scheduler()
    if sch.running:
        sch.shutdown(wait=False)


async def _trigger_claude(sid: str, trigger: str = "schedule"):
    from backend.claude_runner import run_claude
    await run_claude(sid, trigger=trigger)


def add_cron_job(sid: str, cron_expr: str, job_id: str | None = None) -> str:
    """添加 cron 任务。cron_expr 格式：'分 时 日 月 周'（APScheduler 格式）。"""
    sch = get_scheduler()
    parts = cron_expr.strip().split()
    if len(parts) != 5:
        raise ValueError(f"cron 表达式需 5 个字段（分 时 日 月 周），实际: {cron_expr!r}")
    minute, hour, day, month, day_of_week = parts

    jid = job_id or f"{sid}-cron-{minute}-{hour}"
    sch.add_job(
        _trigger_claude,
        trigger="cron",
        minute=minute, hour=hour, day=day, month=month, day_of_week=day_of_week,
        args=[sid],
        id=jid,
        replace_existing=True,
        misfire_grace_time=300,
    )
    logger.info("Cron job added: %s (%s)", jid, cron_expr)
    return jid


def add_once_job(sid: str, run_at: str, job_id: str | None = None) -> str:
    """添加一次性任务。run_at 为 ISO8601 字符串。"""
    from datetime import datetime
    sch = get_scheduler()
    dt = datetime.fromisoformat(run_at)
    jid = job_id or f"{sid}-once-{dt.strftime('%Y%m%d%H%M%S')}"
    sch.add_job(
        _trigger_claude,
        trigger="date",
        run_date=dt,
        args=[sid],
        id=jid,
        replace_existing=True,
    )
    logger.info("Once job added: %s at %s", jid, run_at)
    return jid


def list_jobs(sid: str | None = None) -> list[dict]:
    sch = get_scheduler()
    jobs = []
    for job in sch.get_jobs():
        if sid:
            # 匹配 sid 前缀（兼容 "sid-xxx" 和 "sid_xxx" 两种格式）
            # 同时匹配 job.kwargs/args 里存储的 sid
            job_args = job.args or []
            job_sid = job_args[0] if job_args else ""
            if job_sid != sid and not job.id.startswith(sid + "-") and not job.id.startswith(sid + "_"):
                continue
        next_run = job.next_run_time.isoformat() if job.next_run_time else None
        jobs.append({"id": job.id, "next_run": next_run, "trigger": str(job.trigger)})
    return jobs


def cancel_job(job_id: str) -> bool:
    sch = get_scheduler()
    try:
        sch.remove_job(job_id)
        return True
    except Exception:
        return False


def remove_jobs_for_sid(sid: str) -> int:
    """删除某策略的所有定时任务，返回删除数量。策略删除时调用。"""
    sch = get_scheduler()
    removed = 0
    for job in sch.get_jobs():
        if job.id.startswith(sid + "-") or job.id.startswith(sid + "_"):
            try:
                sch.remove_job(job.id)
                removed += 1
                logger.info("Removed orphaned job %s (strategy=%s)", job.id, sid)
            except Exception:
                pass
    return removed
