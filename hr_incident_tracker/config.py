"""Configuration for the HR Incident Tracker, sourced entirely from environment
variables so the same code runs unchanged in dev, GitHub Actions, and prod."""
import os

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

# Public URL the app is served at (used to build links inside emails).
APP_BASE_URL = os.getenv("HR_APP_BASE_URL", "http://localhost:8000").rstrip("/")

# --- Database -----------------------------------------------------------
# Defaults to a local SQLite file for easy dev use. For production, point
# this at a persistent database (e.g. Postgres) — required if you also want
# the standalone reminder cron (send_reminders.py / GitHub Actions) to see
# the same data as the running web app.
_DEFAULT_SQLITE_PATH = os.path.join(os.path.dirname(__file__), "data", "hr_incidents.db")
DATABASE_URL = os.getenv("HR_DATABASE_URL", f"sqlite:///{_DEFAULT_SQLITE_PATH}")

# --- Email (SMTP) ---------------------------------------------------------
SMTP_HOST = os.getenv("HR_SMTP_HOST")
SMTP_PORT = int(os.getenv("HR_SMTP_PORT", "587"))
SMTP_USERNAME = os.getenv("HR_SMTP_USERNAME")
SMTP_PASSWORD = os.getenv("HR_SMTP_PASSWORD")
SMTP_FROM = os.getenv("HR_SMTP_FROM", SMTP_USERNAME or "hr-incidents@example.com")
SMTP_USE_TLS = os.getenv("HR_SMTP_USE_TLS", "true").lower() != "false"

# If no SMTP host is configured, emails are logged instead of sent so the
# app is fully usable without real credentials during setup/testing.
DRY_RUN_EMAIL = os.getenv("HR_EMAIL_DRY_RUN", "").lower() == "true" or not SMTP_HOST

# Extra recipient(s) that get looped in on escalations (e.g. HR manager inbox).
HR_ESCALATION_EMAIL = os.getenv("HR_ESCALATION_EMAIL")

# --- HR dashboard auth ------------------------------------------------
# Comma-separated "user:password" pairs, e.g. "hr1:secret1,hr2:secret2".
# Anyone hitting the dashboard/creation/detail pages is HTTP Basic Auth
# challenged against this list. The assignee-facing /update/<token> link
# is intentionally NOT behind this auth — it's secured by the unguessable
# per-incident token instead, so the assigned employee never needs an account.
ADMIN_CREDENTIALS_RAW = os.getenv("HR_ADMIN_CREDENTIALS", "admin:changeme")


def _parse_admin_credentials(raw):
    creds = {}
    for pair in raw.split(","):
        pair = pair.strip()
        if not pair or ":" not in pair:
            continue
        user, _, pw = pair.partition(":")
        creds[user.strip()] = pw.strip()
    return creds


ADMIN_CREDENTIALS = _parse_admin_credentials(ADMIN_CREDENTIALS_RAW)

# --- Case taxonomy ---------------------------------------------------------
CATEGORIES = [
    "Theft",
    "Fraud",
    "Policy Violation",
    "Safety Incident",
    "Harassment / Conduct",
    "Property Damage",
    "Inventory Shrinkage",
    "Vendor / Third-Party",
    "Other",
]

SEVERITIES = ["low", "medium", "high", "critical"]

# Default number of days until due, per severity, used when the creator
# doesn't pick an explicit due date.
SEVERITY_DEFAULT_DUE_DAYS = {"critical": 1, "high": 3, "medium": 7, "low": 14}

# --- Reminders & escalation -------------------------------------------
# How often (hours) a nag email is re-sent to the assignee once a case is
# overdue, scaled by severity (critical cases get chased far more often).
REMINDER_BASE_INTERVAL_HOURS = float(os.getenv("HR_REMINDER_BASE_INTERVAL_HOURS", "24"))
SEVERITY_REMINDER_MULTIPLIER = {"critical": 0.25, "high": 0.5, "medium": 1.0, "low": 2.0}

# Number of missed reminders after which HR/the reporter is auto-escalated to.
ESCALATION_THRESHOLD = int(os.getenv("HR_ESCALATION_THRESHOLD", "3"))

# How often the in-process scheduler checks for overdue cases, when the app
# is run as a long-lived server (uvicorn). Irrelevant to the standalone
# send_reminders.py cron entrypoint, which runs one sweep and exits.
REMINDER_CHECK_INTERVAL_MINUTES = int(os.getenv("HR_REMINDER_CHECK_INTERVAL_MINUTES", "60"))
