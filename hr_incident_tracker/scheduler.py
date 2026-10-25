import atexit
import logging

from apscheduler.schedulers.background import BackgroundScheduler

from . import config
from .reminders import run_reminder_sweep

logger = logging.getLogger("hr_incident_tracker.scheduler")

_scheduler = None


def start_scheduler():
    """Starts the in-process reminder sweep loop for long-lived server
    deployments (uvicorn). Safe to call more than once; only starts once."""
    global _scheduler
    if _scheduler is not None:
        return _scheduler
    _scheduler = BackgroundScheduler(timezone="UTC")
    _scheduler.add_job(
        run_reminder_sweep,
        "interval",
        minutes=config.REMINDER_CHECK_INTERVAL_MINUTES,
        id="reminder_sweep",
    )
    _scheduler.start()
    atexit.register(lambda: _scheduler.shutdown(wait=False))
    logger.info("Reminder scheduler started (checking every %s minutes)", config.REMINDER_CHECK_INTERVAL_MINUTES)
    return _scheduler
