"""Core reminder/escalation sweep — shared by the in-process scheduler
(scheduler.py, used when running as a long-lived server) and the standalone
cron entrypoint (send_reminders.py, used e.g. from GitHub Actions)."""
import logging
from datetime import timedelta

from . import config, email_utils
from .database import SessionLocal
from .models import Incident, IncidentEvent, utcnow

logger = logging.getLogger("hr_incident_tracker.reminders")


def run_reminder_sweep():
    db = SessionLocal()
    sent, escalated = 0, 0
    try:
        overdue = [i for i in db.query(Incident).all() if i.is_overdue]
        for incident in overdue:
            interval_hours = config.REMINDER_BASE_INTERVAL_HOURS * config.SEVERITY_REMINDER_MULTIPLIER.get(
                incident.severity, 1.0
            )
            due_for_reminder = (
                incident.last_reminder_sent_at is None
                or utcnow() - incident.last_reminder_sent_at >= timedelta(hours=interval_hours)
            )
            if not due_for_reminder:
                continue

            incident.reminder_count += 1
            incident.last_reminder_sent_at = utcnow()
            email_utils.incident_reminder_email(incident)
            db.add(IncidentEvent(
                incident_id=incident.id,
                event_type="reminder_sent",
                actor="system",
                note=f"Reminder #{incident.reminder_count} sent to {incident.assigned_to_email}",
            ))
            sent += 1

            if not incident.escalated and incident.reminder_count >= config.ESCALATION_THRESHOLD:
                incident.escalated = True
                email_utils.incident_escalation_email(incident)
                db.add(IncidentEvent(
                    incident_id=incident.id,
                    event_type="escalated",
                    actor="system",
                    note=f"Escalated to HR after {incident.reminder_count} missed reminders",
                ))
                escalated += 1

            db.commit()
    finally:
        db.close()
    logger.info("Reminder sweep complete: %s reminder(s) sent, %s escalation(s)", sent, escalated)
    return {"reminders_sent": sent, "escalations": escalated}
