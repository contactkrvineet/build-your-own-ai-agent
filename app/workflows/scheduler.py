"""
APScheduler-based cron trigger system.

Workflow definitions are loaded from YAML files in ./workflows/.
Each job calls the agent with a pre-configured prompt and logs the result.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, List, Optional

import yaml
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger

from app.config.settings import get_settings
from app.utils.logger import logger

_scheduler: Optional[BackgroundScheduler] = None


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def start_scheduler() -> BackgroundScheduler:
    """Start the APScheduler background scheduler and register all jobs."""
    global _scheduler

    s = get_settings()
    if not s.scheduler_enabled:
        logger.info("Scheduler disabled in config.")
        return None  # type: ignore[return-value]

    _scheduler = BackgroundScheduler(timezone=s.scheduler_timezone)

    jobs_file = Path(s.scheduler_timezone).parent / "workflows" / "scheduled_jobs.yaml"
    # Try the configured jobs file or use the default location
    jobs_path = Path("./workflows/scheduled_jobs.yaml")
    if jobs_path.exists():
        _register_jobs_from_file(jobs_path)
    else:
        logger.info("No scheduled_jobs.yaml found — scheduler started with no jobs.")

    _scheduler.start()
    logger.info(f"Scheduler started ({s.scheduler_timezone} timezone).")
    return _scheduler


def stop_scheduler() -> None:
    global _scheduler
    if _scheduler and _scheduler.running:
        _scheduler.shutdown(wait=False)
        logger.info("Scheduler stopped.")


def add_cron_job(
    job_id: str,
    cron_expression: str,
    prompt: str,
    session_id: Optional[str] = None,
) -> None:
    """Dynamically add a cron job at runtime."""
    if not _scheduler:
        logger.warning("Scheduler not started. Call start_scheduler() first.")
        return

    parts = cron_expression.split()
    if len(parts) != 5:
        raise ValueError(
            f"Invalid cron expression '{cron_expression}'. "
            "Expected 5 fields: minute hour day month day_of_week"
        )
    minute, hour, day, month, day_of_week = parts

    _scheduler.add_job(
        func=_run_scheduled_job,
        trigger=CronTrigger(
            minute=minute,
            hour=hour,
            day=day,
            month=month,
            day_of_week=day_of_week,
        ),
        id=job_id,
        name=job_id,
        kwargs={"prompt": prompt, "session_id": session_id or f"scheduled_{job_id}"},
        replace_existing=True,
        misfire_grace_time=300,
    )
    logger.info(f"Cron job registered: {job_id} [{cron_expression}]")


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _register_jobs_from_file(path: Path) -> None:
    try:
        with path.open("r") as f:
            data: Dict[str, Any] = yaml.safe_load(f) or {}

        jobs: List[Dict] = data.get("jobs", [])
        for job in jobs:
            add_cron_job(
                job_id=job["id"],
                cron_expression=job["cron"],
                prompt=job["prompt"],
            )
        logger.info(f"Registered {len(jobs)} scheduled job(s) from {path}")
    except Exception as e:
        logger.error(f"Failed to load scheduled jobs from {path}: {e}")


def _run_scheduled_job(prompt: str, session_id: str) -> None:
    """Execute a scheduled agent query and log the result."""
    logger.info(f"Running scheduled job | session={session_id} | prompt='{prompt[:60]}'")
    try:
        from app.agent.core import get_agent

        agent = get_agent()
        response = agent.chat(prompt, session_id=session_id)
        logger.info(
            f"Scheduled job complete | session={session_id} | "
            f"route={response.route_used} | answer='{response.answer[:200]}'"
        )
    except Exception as e:
        logger.error(f"Scheduled job failed | session={session_id}: {e}")
