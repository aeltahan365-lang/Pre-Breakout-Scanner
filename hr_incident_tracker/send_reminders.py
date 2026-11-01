"""Standalone entrypoint: run one reminder/escalation sweep and exit.

Use this when you don't want a long-lived server process handling reminders
(e.g. from a system cron job, or the GitHub Actions workflow in
.github/workflows/hr-reminders.yml). It talks to the same database as the
web app (HR_DATABASE_URL), so for this to do anything meaningful in CI, that
must point at a persistent, shared database rather than the default local
SQLite file.

Usage: python -m hr_incident_tracker.send_reminders
"""
import logging

from .database import Base, engine
from .reminders import run_reminder_sweep

logging.basicConfig(level=logging.INFO)

if __name__ == "__main__":
    Base.metadata.create_all(bind=engine)
    result = run_reminder_sweep()
    print(result)
