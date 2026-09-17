import logging
import os
from datetime import datetime, time, timedelta

from fastapi import Depends, FastAPI, Form, HTTPException, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session

from . import config, email_utils
from .auth import require_hr_auth
from .database import Base, SessionLocal, engine, get_db
from .models import Incident, IncidentEvent, Status, utcnow
from .reminders import run_reminder_sweep
from .scheduler import start_scheduler

BASE_DIR = os.path.dirname(__file__)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("hr_incident_tracker")

app = FastAPI(title="HR Incident Tracker")
app.mount("/static", StaticFiles(directory=os.path.join(BASE_DIR, "static")), name="static")
templates = Jinja2Templates(directory=os.path.join(BASE_DIR, "templates"))
templates.env.filters["status_label"] = lambda v: v.replace("_", " ").title()


@app.on_event("startup")
def on_startup():
    Base.metadata.create_all(bind=engine)
    start_scheduler()
    run_reminder_sweep()


def _parse_due_date(due_date_str: str):
    # Naive datetime, implicitly UTC — see models.utcnow() for why.
    d = datetime.strptime(due_date_str, "%Y-%m-%d").date()
    return datetime.combine(d, time(23, 59, 59))


# ---------------------------------------------------------------------------
# HR dashboard (HTTP Basic Auth protected)
# ---------------------------------------------------------------------------

@app.get("/", response_class=HTMLResponse)
def dashboard(
    request: Request,
    status: str = "",
    severity: str = "",
    q: str = "",
    db: Session = Depends(get_db),
    user: str = Depends(require_hr_auth),
):
    query = db.query(Incident)
    if status:
        query = query.filter(Incident.status == status)
    if severity:
        query = query.filter(Incident.severity == severity)
    if q:
        like = f"%{q}%"
        query = query.filter(
            (Incident.title.ilike(like))
            | (Incident.reference.ilike(like))
            | (Incident.assigned_to_email.ilike(like))
            | (Incident.assigned_to_name.ilike(like))
        )
    incidents = query.order_by(Incident.created_at.desc()).all()

    all_incidents = db.query(Incident).all()
    total_open = sum(1 for i in all_incidents if i.is_open)
    total_overdue = sum(1 for i in all_incidents if i.is_overdue)
    total_escalated = sum(1 for i in all_incidents if i.escalated)

    return templates.TemplateResponse(request, "dashboard.html", {
        "incidents": incidents,
        "filters": {"status": status, "severity": severity, "q": q},
        "statuses": [s.value for s in Status],
        "severities": config.SEVERITIES,
        "total_open": total_open,
        "total_overdue": total_overdue,
        "total_escalated": total_escalated,
        "total_all": len(all_incidents),
        "user": user,
    })


@app.get("/incidents/new", response_class=HTMLResponse)
def new_incident_form(request: Request, user: str = Depends(require_hr_auth)):
    return templates.TemplateResponse(request, "incident_form.html", {
        "categories": config.CATEGORIES,
        "severities": config.SEVERITIES,
        "user": user,
    })


@app.post("/incidents/new")
def create_incident(
    title: str = Form(...),
    description: str = Form(...),
    category: str = Form(...),
    severity: str = Form(...),
    location: str = Form(""),
    reported_by_name: str = Form(""),
    reported_by_email: str = Form(""),
    assigned_to_name: str = Form(...),
    assigned_to_email: str = Form(...),
    due_date: str = Form(""),
    db: Session = Depends(get_db),
    user: str = Depends(require_hr_auth),
):
    if due_date:
        due = _parse_due_date(due_date)
    else:
        days = config.SEVERITY_DEFAULT_DUE_DAYS.get(severity, 7)
        due = utcnow() + timedelta(days=days)

    incident = Incident(
        title=title.strip(),
        description=description.strip(),
        category=category,
        severity=severity,
        location=location.strip(),
        reported_by_name=reported_by_name.strip(),
        reported_by_email=reported_by_email.strip(),
        assigned_to_name=assigned_to_name.strip(),
        assigned_to_email=assigned_to_email.strip(),
        due_date=due,
        created_by=user,
    )
    db.add(incident)
    db.commit()
    db.refresh(incident)

    incident.reference = f"INC-{incident.created_at:%Y}-{incident.id:05d}"
    db.add(IncidentEvent(
        incident_id=incident.id,
        event_type="created",
        actor=user,
        note=f"Case created and assigned to {incident.assigned_to_name} <{incident.assigned_to_email}>",
    ))
    db.commit()

    try:
        email_utils.incident_assigned_email(incident)
    except Exception:
        logger.exception("Failed to send assignment email for incident %s", incident.id)

    return RedirectResponse(url=f"/incidents/{incident.id}", status_code=303)


@app.get("/incidents/{incident_id}", response_class=HTMLResponse)
def incident_detail(
    incident_id: int,
    request: Request,
    db: Session = Depends(get_db),
    user: str = Depends(require_hr_auth),
):
    incident = db.get(Incident, incident_id)
    if not incident:
        raise HTTPException(404, "Incident not found")
    update_link = f"{config.APP_BASE_URL}/update/{incident.update_token}"
    return templates.TemplateResponse(request, "incident_detail.html", {
        "incident": incident,
        "update_link": update_link,
        "user": user,
    })


@app.post("/incidents/{incident_id}/reassign")
def reassign_incident(
    incident_id: int,
    assigned_to_name: str = Form(...),
    assigned_to_email: str = Form(...),
    due_date: str = Form(""),
    db: Session = Depends(get_db),
    user: str = Depends(require_hr_auth),
):
    incident = db.get(Incident, incident_id)
    if not incident:
        raise HTTPException(404, "Incident not found")

    old_assignee = f"{incident.assigned_to_name} <{incident.assigned_to_email}>"
    incident.assigned_to_name = assigned_to_name.strip()
    incident.assigned_to_email = assigned_to_email.strip()
    if due_date:
        incident.due_date = _parse_due_date(due_date)
    incident.reminder_count = 0
    incident.last_reminder_sent_at = None
    incident.escalated = False

    db.add(IncidentEvent(
        incident_id=incident.id,
        event_type="reassigned",
        actor=user,
        old_value=old_assignee,
        new_value=f"{incident.assigned_to_name} <{incident.assigned_to_email}>",
    ))
    db.commit()

    try:
        email_utils.incident_assigned_email(incident)
    except Exception:
        logger.exception("Failed to send reassignment email for incident %s", incident.id)

    return RedirectResponse(url=f"/incidents/{incident.id}", status_code=303)


@app.post("/incidents/{incident_id}/reopen")
def reopen_incident(
    incident_id: int,
    db: Session = Depends(get_db),
    user: str = Depends(require_hr_auth),
):
    incident = db.get(Incident, incident_id)
    if not incident:
        raise HTTPException(404, "Incident not found")
    old_status = incident.status
    incident.status = Status.OPEN.value
    incident.closed_at = None
    incident.reminder_count = 0
    incident.last_reminder_sent_at = None
    incident.escalated = False
    db.add(IncidentEvent(
        incident_id=incident.id,
        event_type="reopened",
        actor=user,
        old_value=old_status,
        new_value=incident.status,
    ))
    db.commit()
    return RedirectResponse(url=f"/incidents/{incident.id}", status_code=303)


@app.post("/reminders/run")
def trigger_reminder_sweep(user: str = Depends(require_hr_auth)):
    """Manual "run reminders now" button, useful for testing without waiting
    for the scheduled interval."""
    return run_reminder_sweep()


# ---------------------------------------------------------------------------
# Assignee-facing page — secured by the unguessable token, no login required.
# ---------------------------------------------------------------------------

@app.get("/update/{token}", response_class=HTMLResponse)
def assignee_update_form(token: str, request: Request, db: Session = Depends(get_db)):
    incident = db.query(Incident).filter(Incident.update_token == token).first()
    if not incident:
        raise HTTPException(404, "This link is invalid or has expired.")
    return templates.TemplateResponse(request, "update_form.html", {"incident": incident})


@app.post("/update/{token}", response_class=HTMLResponse)
def assignee_submit_update(
    token: str,
    request: Request,
    status_value: str = Form(..., alias="status"),
    action_taken: str = Form(...),
    db: Session = Depends(get_db),
):
    incident = db.query(Incident).filter(Incident.update_token == token).first()
    if not incident:
        raise HTTPException(404, "This link is invalid or has expired.")

    allowed = {Status.IN_PROGRESS.value, Status.RESOLVED.value, Status.CLOSED.value}
    if status_value not in allowed:
        raise HTTPException(400, "Invalid status")

    old_status = incident.status
    incident.status = status_value
    incident.action_taken = action_taken.strip()
    if status_value == Status.CLOSED.value:
        incident.closed_at = utcnow()

    db.add(IncidentEvent(
        incident_id=incident.id,
        event_type="status_updated",
        actor=incident.assigned_to_email,
        old_value=old_status,
        new_value=status_value,
        note=action_taken.strip(),
    ))
    db.commit()

    try:
        email_utils.incident_status_changed_email(incident, incident.assigned_to_name)
    except Exception:
        logger.exception("Failed to send status-change email for incident %s", incident.id)

    return templates.TemplateResponse(request, "update_success.html", {"incident": incident})
