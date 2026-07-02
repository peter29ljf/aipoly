from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from backend import scheduler, strategies as strat

router = APIRouter(prefix="/api/strategies/{sid}/schedules", tags=["schedules"])

# 预设频率选项 → cron 表达式（UTC）
PRESET_CRONS: dict[str, str] = {
    "15min":  "*/15 * * * *",
    "30min":  "*/30 * * * *",
    "1h":     "0 * * * *",
    "2h":     "0 */2 * * *",
    "4h":     "0 */4 * * *",
    "8h":     "0 */8 * * *",
    "12h":    "0 */12 * * *",
    "daily":  "0 9 * * *",
}

SCHEDULE_JOB_SUFFIX = "-auto"


def _job_id(sid: str) -> str:
    return f"{sid}{SCHEDULE_JOB_SUFFIX}"


class ScheduleConfigRequest(BaseModel):
    enabled: bool
    preset: str  # key of PRESET_CRONS


@router.get("")
def list_schedules(sid: str):
    if not strat.get_strategy(sid):
        raise HTTPException(404, "Strategy not found")
    return scheduler.list_jobs(sid)


@router.get("/config")
def get_schedule_config(sid: str):
    if not strat.get_strategy(sid):
        raise HTTPException(404, "Strategy not found")
    job_id = _job_id(sid)
    jobs = scheduler.list_jobs(sid)
    active_job = next((j for j in jobs if j["id"] == job_id), None)
    # 反查当前 preset
    current_preset = None
    if active_job:
        cron_str = active_job.get("trigger", "")
        for preset, cron in PRESET_CRONS.items():
            parts = cron.split()
            # 简单匹配 hour/minute 字段
            if all(f in cron_str for f in [f"hour='{parts[1]}'", f"minute='{parts[0]}'"]):
                current_preset = preset
                break
    return {
        "enabled": active_job is not None,
        "preset": current_preset,
        "presets": list(PRESET_CRONS.keys()),
        "job": active_job,
    }


@router.put("/config")
def set_schedule_config(sid: str, req: ScheduleConfigRequest):
    if not strat.get_strategy(sid):
        raise HTTPException(404, "Strategy not found")
    job_id = _job_id(sid)
    # 先删除旧任务
    scheduler.cancel_job(job_id)
    if not req.enabled:
        return {"enabled": False}
    cron = PRESET_CRONS.get(req.preset)
    if not cron:
        raise HTTPException(400, f"未知 preset: {req.preset}，可选: {list(PRESET_CRONS.keys())}")
    jid = scheduler.add_cron_job(sid, cron, job_id=job_id)
    return {"enabled": True, "preset": req.preset, "job_id": jid}


@router.delete("/{job_id}")
def cancel_schedule(sid: str, job_id: str):
    ok = scheduler.cancel_job(job_id)
    if not ok:
        raise HTTPException(404, "Job not found")
    return {"ok": True}
