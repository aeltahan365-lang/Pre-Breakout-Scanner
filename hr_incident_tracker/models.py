import enum
import secrets
from datetime import datetime, timezone

from sqlalchemy import (
    Boolean, Column, DateTime, ForeignKey, Integer, String, Text,
)
from sqlalchemy.orm import relationship

from .database import Base


def utcnow():
    # Naive datetime representing UTC — SQLite silently drops tzinfo on
    # round-trip, so every DateTime column and comparison in this app uses
    # naive-but-implicitly-UTC values to stay consistent across backends.
    return datetime.now(timezone.utc).replace(tzinfo=None)


class Status(str, enum.Enum):
    OPEN = "open"
    IN_PROGRESS = "in_progress"
    RESOLVED = "resolved"
    CLOSED = "closed"


class Severity(str, enum.Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


OPEN_STATUSES = (Status.OPEN.value, Status.IN_PROGRESS.value)


class Incident(Base):
    __tablename__ = "incidents"

    id = Column(Integer, primary_key=True)
    reference = Column(String(32), unique=True, index=True)

    title = Column(String(255), nullable=False)
    description = Column(Text, nullable=False)
    category = Column(String(64), nullable=False)
    severity = Column(String(16), nullable=False, default=Severity.MEDIUM.value)
    location = Column(String(255))

    reported_by_name = Column(String(255))
    reported_by_email = Column(String(255))

    assigned_to_name = Column(String(255), nullable=False)
    assigned_to_email = Column(String(255), nullable=False, index=True)

    status = Column(String(16), nullable=False, default=Status.OPEN.value, index=True)
    action_taken = Column(Text, default="")

    created_at = Column(DateTime(), default=utcnow)
    updated_at = Column(DateTime(), default=utcnow, onupdate=utcnow)
    due_date = Column(DateTime(), nullable=False, index=True)
    closed_at = Column(DateTime(), nullable=True)

    update_token = Column(String(64), unique=True, index=True, default=lambda: secrets.token_urlsafe(32))

    reminder_count = Column(Integer, default=0)
    last_reminder_sent_at = Column(DateTime(), nullable=True)
    escalated = Column(Boolean, default=False)

    created_by = Column(String(255))

    events = relationship(
        "IncidentEvent",
        back_populates="incident",
        cascade="all, delete-orphan",
        order_by="IncidentEvent.created_at",
    )

    @property
    def is_open(self):
        return self.status in OPEN_STATUSES

    @property
    def is_overdue(self):
        return self.is_open and self.due_date is not None and utcnow() > self.due_date


class IncidentEvent(Base):
    __tablename__ = "incident_events"

    id = Column(Integer, primary_key=True)
    incident_id = Column(Integer, ForeignKey("incidents.id"), nullable=False)
    event_type = Column(String(32), nullable=False)
    actor = Column(String(255))
    note = Column(Text)
    old_value = Column(String(255))
    new_value = Column(String(255))
    created_at = Column(DateTime(), default=utcnow)

    incident = relationship("Incident", back_populates="events")
