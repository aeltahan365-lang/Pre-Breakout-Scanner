# HR Incident Tracker

An advanced HR / loss-prevention incident tracker: log a case, assign it to
someone by email, they get notified and update status/action taken through a
secure link (no account needed), and the system auto-reminds — then
auto-escalates to HR — if they don't close it by the due date.

This is a standalone FastAPI app living in its own directory. It does not
touch, import, or depend on anything else in this repository (the crypto
scanner in the parent directory).

## Features

- **Create incidents** — title, description, category (theft, fraud, policy
  violation, safety, harassment, property damage, shrinkage, vendor, other),
  severity (low/medium/high/critical), location, who reported it, who it's
  assigned to, and a due date (auto-suggested by severity if left blank:
  1/3/7/14 days).
- **Email on assignment** — the assignee gets an email immediately with a
  unique secure link (`/update/<token>`) to view the case and submit their
  status + action taken. No login required for them.
- **Status workflow** — Open → In Progress → Resolved → Closed, with HR able
  to reopen a closed case from the dashboard.
- **Full audit trail** — every creation, reassignment, status change,
  reminder, and escalation is logged with a timestamp and actor, shown as a
  timeline on the case detail page.
- **Auto reminders** — once a case passes its due date and is still open, a
  reminder email is sent to the assignee on a recurring interval (scaled by
  severity — critical cases get chased 4x as often as low-severity ones).
- **Auto escalation** — after N missed reminders (default 3), an escalation
  email goes out to HR and the original reporter.
- **HR dashboard** — filter by status/severity, search by title/reference/
  assignee, see overdue/escalated counts at a glance, protected by HTTP Basic
  Auth (multiple HR accounts supported).
- **Two ways to run reminders**: an in-process scheduler for when you run
  this as a long-lived server, or a standalone one-shot script
  (`send_reminders.py`) you can run from any cron system, including the
  included GitHub Actions workflow.

## Quick start (local)

```bash
cd hr_incident_tracker
pip install -r requirements.txt
cp .env.example ../.env      # fill in SMTP creds, or leave HR_SMTP_HOST unset for dry-run mode
cd ..
uvicorn hr_incident_tracker.main:app --reload
```

Visit `http://localhost:8000` — you'll be prompted for HR credentials
(default `admin` / `changeme`, set `HR_ADMIN_CREDENTIALS` before going live).

With no `HR_SMTP_HOST` set, emails are **not sent** — they're logged to the
console instead, so you can try the whole flow (create → email → update
link → status change) without any real mail server.

## How the reminder/escalation math works

- `HR_REMINDER_BASE_INTERVAL_HOURS` (default 24) is how often a nag email
  goes out once a case is overdue, for a medium-severity case. Multiplied
  per severity: critical ×0.25 (every 6h), high ×0.5 (every 12h), medium ×1
  (every 24h), low ×2 (every 48h).
- `HR_ESCALATION_THRESHOLD` (default 3): after this many reminders with no
  resolution, HR (`HR_ESCALATION_EMAIL`) and the original reporter get an
  escalation email. It fires once per case (until reassigned/reopened resets
  the counters).
- Reminders/escalation only apply to cases with status Open or In Progress —
  Resolved and Closed cases are left alone.

## Running reminders

**Option A — long-lived server.** If you deploy this as an always-on
process (e.g. `uvicorn` behind a process manager), it starts an in-process
scheduler on boot that sweeps for overdue cases every
`HR_REMINDER_CHECK_INTERVAL_MINUTES` (default 60).

**Option B — cron / GitHub Actions.** `.github/workflows/hr-reminders.yml`
runs `python -m hr_incident_tracker.send_reminders` hourly. Since GitHub
Actions checks out a fresh copy of the repo every run, this only does
anything useful if `HR_DATABASE_URL` points at a **persistent, shared**
database (e.g. hosted Postgres) that your deployed web app also uses —
configure it as a repository secret along with the SMTP secrets. If you're
using Option A already, you can disable this workflow.

## Data model

- **Incident** — the case record: title, description, category, severity,
  location, reporter, assignee, status, action taken, due date, reminder
  count, escalation flag, and a unique `update_token`.
- **IncidentEvent** — an append-only audit log entry (created, reassigned,
  status_updated, reminder_sent, escalated, reopened) tied to an incident.

Default storage is a local SQLite file at `hr_incident_tracker/data/`
(gitignored). Point `HR_DATABASE_URL` at Postgres/MySQL for production.

## Security notes

- The HR dashboard (`/`, `/incidents/new`, `/incidents/{id}`) is behind HTTP
  Basic Auth (`HR_ADMIN_CREDENTIALS`). Put this behind HTTPS in production —
  Basic Auth sends credentials on every request.
- The assignee's `/update/<token>` link is intentionally **not** behind
  login — it's secured by a 32-byte random token instead, so the assigned
  employee doesn't need an account. Treat that link as a bearer credential:
  it's only ever sent to the assignee's own email address.

## All environment variables

See `.env.example` for the full list with defaults and comments.
