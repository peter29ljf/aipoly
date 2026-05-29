from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from backend import scheduler, strategies as strat

router = APIRouter(prefix="/api/strategies/{sid}/schedules", tags=["schedules"])


class CronJobRequest(BaseModel):
    cron: str  # "分 时 日 月 周"
    job_id: str | None = None


class OnceJobRequest(BaseModel):
    run_at: str  # ISO8601
    job_id: str | None = None


@router.get("")
def list_schedules(sid: str):
    if not strat.get_strategy(sid):
        raise HTTPException(404, "Strategy not found")
    return scheduler.list_jobs(sid)


@router.post("/cron")
def add_cron(sid: str, req: CronJobRequest):
    if not strat.get_strategy(sid):
        raise HTTPException(404, "Strategy not found")
    try:
        jid = scheduler.add_cron_job(sid, req.cron, req.job_id)
    except ValueError as e:
        raise HTTPException(400, str(e))
    return {"job_id": jid}


@router.post("/once")
def add_once(sid: str, req: OnceJobRequest):
    if not strat.get_strategy(sid):
        raise HTTPException(404, "Strategy not found")
    try:
        jid = scheduler.add_once_job(sid, req.run_at, req.job_id)
    except Exception as e:
        raise HTTPException(400, str(e))
    return {"job_id": jid}


@router.delete("/{job_id}")
def cancel_schedule(sid: str, job_id: str):
    ok = scheduler.cancel_job(job_id)
    if not ok:
        raise HTTPException(404, "Job not found")
    return {"ok": True}
