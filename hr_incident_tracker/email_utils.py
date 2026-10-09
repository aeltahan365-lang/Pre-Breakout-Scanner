import logging
import smtplib
from email.message import EmailMessage

from . import config

logger = logging.getLogger("hr_incident_tracker.email")


def send_email(to_addrs, subject, body_text):
    if isinstance(to_addrs, str):
        to_addrs = [to_addrs]
    to_addrs = [a for a in to_addrs if a]
    if not to_addrs:
        return

    if config.DRY_RUN_EMAIL:
        logger.info("[DRY RUN] Email to %s | Subject: %s\n%s", to_addrs, subject, body_text)
        return

    msg = EmailMessage()
    msg["Subject"] = subject
    msg["From"] = config.SMTP_FROM
    msg["To"] = ", ".join(to_addrs)
    msg.set_content(body_text)

    with smtplib.SMTP(config.SMTP_HOST, config.SMTP_PORT, timeout=20) as server:
        if config.SMTP_USE_TLS:
            server.starttls()
        if config.SMTP_USERNAME and config.SMTP_PASSWORD:
            server.login(config.SMTP_USERNAME, config.SMTP_PASSWORD)
        server.send_message(msg)


def incident_assigned_email(incident):
    link = f"{config.APP_BASE_URL}/update/{incident.update_token}"
    subject = f"[HR Loss Prevention] New case assigned to you — {incident.reference}: {incident.title}"
    body = f"""Hello {incident.assigned_to_name},

A loss prevention / HR case has been assigned to you.

Reference:    {incident.reference}
Title:        {incident.title}
Category:     {incident.category}
Severity:     {incident.severity.upper()}
Location:     {incident.location or "N/A"}
Due date:     {incident.due_date:%Y-%m-%d}
Reported by:  {incident.reported_by_name or "N/A"}

Description:
{incident.description}

Please review the case and record your status and action taken using the
secure link below (no login required):

{link}

This case must be updated before the due date above. Reminder emails will
be sent automatically if it is not closed on time, and it will be escalated
to HR if it stays open too long.

— HR Incident Tracker
"""
    send_email(incident.assigned_to_email, subject, body)


def incident_reminder_email(incident):
    link = f"{config.APP_BASE_URL}/update/{incident.update_token}"
    subject = f"[REMINDER] Overdue HR case {incident.reference} — action required"
    body = f"""Hello {incident.assigned_to_name},

This is reminder #{incident.reminder_count}: the following case is PAST its
due date and still not closed.

Reference:  {incident.reference}
Title:      {incident.title}
Severity:   {incident.severity.upper()}
Due date:   {incident.due_date:%Y-%m-%d} (overdue)
Status:     {incident.status.replace('_', ' ').title()}

Please update the status and action taken as soon as possible:

{link}

— HR Incident Tracker (automatic reminder)
"""
    send_email(incident.assigned_to_email, subject, body)


def incident_escalation_email(incident):
    to = [e for e in [config.HR_ESCALATION_EMAIL, incident.reported_by_email] if e]
    if not to:
        return
    subject = f"[ESCALATION] HR case {incident.reference} is overdue and unresolved"
    body = f"""This case has missed {incident.reminder_count} reminder(s) and is still not closed:

Reference:    {incident.reference}
Title:        {incident.title}
Severity:     {incident.severity.upper()}
Assigned to:  {incident.assigned_to_name} <{incident.assigned_to_email}>
Due date:     {incident.due_date:%Y-%m-%d}
Status:       {incident.status.replace('_', ' ').title()}

Dashboard: {config.APP_BASE_URL}/incidents/{incident.id}

— HR Incident Tracker (automatic escalation)
"""
    send_email(to, subject, body)


def incident_status_changed_email(incident, changed_by):
    to = [e for e in [incident.reported_by_email, config.HR_ESCALATION_EMAIL] if e]
    if not to:
        return
    subject = f"[HR Case Update] {incident.reference} — status: {incident.status.replace('_', ' ').title()}"
    body = f"""The following case was updated by {changed_by or incident.assigned_to_name}:

Reference:  {incident.reference}
Title:      {incident.title}
New status: {incident.status.replace('_', ' ').title()}

Action taken:
{incident.action_taken or "(none recorded)"}

Dashboard: {config.APP_BASE_URL}/incidents/{incident.id}
"""
    send_email(to, subject, body)
