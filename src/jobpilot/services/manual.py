"""User-initiated writes (web UI): straight to the database with audit rows (decision D29).

The operator is the user, so no proposal step is needed. Each function is one transaction.
"""

from __future__ import annotations

import sqlite3
from datetime import datetime

from jobpilot.domain import (
    Application,
    ApplicationCreate,
    ApplicationStatus,
    CompanyCreate,
    EventCreate,
    EventSource,
    EventType,
    Origin,
    Track,
)
from jobpilot.services import status
from jobpilot.store.db import transaction
from jobpilot.store.repo import ApplicationRepo, CompanyRepo, EventRepo
from jobpilot.textutil import nfkc, normalize_role

SOURCE = "web"


def add_application(
    conn: sqlite3.Connection,
    *,
    campaign_id: int,
    company_name: str,
    track: Track,
    role: str | None = None,
    job_url: str | None = None,
    notes: str | None = None,
) -> tuple[Application, bool]:
    """Create (or find) the company by exact normalised name, then the application.

    Returns (application, created). Fuzzy company matching arrives with Gmail ingestion.
    """
    name = company_name.strip()
    norm = nfkc(name).casefold()
    with transaction(conn):
        companies = CompanyRepo(conn)
        company = companies.get_by_norm(norm) or companies.add(
            CompanyCreate(name=name, name_norm=norm), actor="user", source=SOURCE
        )
        apps = ApplicationRepo(conn)
        role_norm = normalize_role(role)
        existing = apps.find_natural(campaign_id, company.company_id, track.value, role_norm)
        if existing is not None:
            return existing, False
        created = apps.add(
            ApplicationCreate(
                campaign_id=campaign_id,
                company_id=company.company_id,
                track=track,
                role=role,
                role_norm=role_norm,
                channel="manual",
                origin=Origin.MANUAL,
                job_url=job_url,
                notes=notes,
            ),
            actor="user",
            source=SOURCE,
        )
    return created, True


def log_event(
    conn: sqlite3.Connection,
    *,
    application_id: int,
    event_type: EventType,
    occurred_at: datetime,
    summary: str | None = None,
) -> Application:
    """Append a user-confirmed event and re-derive the automatic status."""
    with transaction(conn):
        EventRepo(conn).add_idempotent(
            EventCreate(
                application_id=application_id,
                event_type=event_type,
                occurred_at=occurred_at,
                source=EventSource.MANUAL,
                summary=summary,
                user_confirmed=True,
            ),
            actor="user",
            source=SOURCE,
        )
        return status.recompute(conn, application_id)


def set_status(
    conn: sqlite3.Connection,
    *,
    application_id: int,
    user_status: ApplicationStatus | None,
    excluded_reason: str | None = None,
) -> Application:
    """Set (or clear with None) the user's override; it always wins over auto_status."""
    return ApplicationRepo(conn).set_user_status(
        application_id, user_status, excluded_reason=excluded_reason, actor="user", source=SOURCE
    )


__all__ = ["SOURCE", "add_application", "log_event", "set_status"]
