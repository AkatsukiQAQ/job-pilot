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
    Company,
    CompanyCreate,
    EventCreate,
    EventSource,
    EventType,
    Origin,
    Track,
)
from jobpilot.services import status
from jobpilot.store.db import transaction
from jobpilot.store.repo import ApplicationRepo, CampaignRepo, CompanyRepo, EventRepo
from jobpilot.textutil import nfkc, normalize_role

SOURCE = "web"


def _resolve_company(conn: sqlite3.Connection, company_name: str) -> Company:
    name = company_name.strip()
    norm = nfkc(name).casefold()
    companies = CompanyRepo(conn)
    return companies.get_by_norm(norm) or companies.add(
        CompanyCreate(name=name, name_norm=norm), actor="user", source=SOURCE
    )


def add_application(
    conn: sqlite3.Connection,
    *,
    campaign_id: int,
    company_name: str,
    track: Track,
    role: str | None = None,
    job_url: str | None = None,
    notes: str | None = None,
    initial_status: ApplicationStatus | None = None,
) -> tuple[Application, bool]:
    """Create (or find) the company by exact normalised name, then the application.

    ``initial_status`` is a user assertion applied to a newly created application only (it never
    fabricates an event); it is ignored when the application already existed.
    Returns (application, created). Fuzzy company matching arrives with Gmail ingestion.
    """
    with transaction(conn):
        company = _resolve_company(conn, company_name)
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
        if initial_status is not None and initial_status != ApplicationStatus.UNRECORDED:
            created = set_status(
                conn, application_id=created.application_id, user_status=initial_status
            )
    return created, True


def update_application(
    conn: sqlite3.Connection,
    *,
    application_id: int,
    company_name: str,
    track: Track,
    role: str | None = None,
    job_url: str | None = None,
    notes: str | None = None,
    portal_url: str | None = None,
    deadline_at: datetime | None = None,
    next_action: str | None = None,
    next_action_due: datetime | None = None,
) -> Application:
    """User-initiated edit of an existing application's fields.

    A natural-key collision (same campaign/company/track/role as another application)
    propagates as sqlite3.IntegrityError.
    """
    with transaction(conn):
        company = _resolve_company(conn, company_name)
        role_norm = normalize_role(role)
        return ApplicationRepo(conn).update_fields(
            application_id,
            company_id=company.company_id,
            role=role,
            role_norm=role_norm,
            track=track,
            job_url=job_url,
            notes=notes,
            portal_url=portal_url,
            deadline_at=deadline_at,
            next_action=next_action,
            next_action_due=next_action_due,
            actor="user",
            source=SOURCE,
        )


def delete_application(conn: sqlite3.Connection, *, application_id: int) -> int:
    """Delete an application and its events. Returns the deleted event count."""
    return ApplicationRepo(conn).delete(application_id, actor="user", source=SOURCE)


def delete_campaign(conn: sqlite3.Connection, *, campaign_id: int) -> tuple[int, int]:
    """Delete a campaign and everything under it. Returns (applications, events) deleted."""
    return CampaignRepo(conn).delete(campaign_id, actor="user", source=SOURCE)


def delete_event(conn: sqlite3.Connection, *, event_id: int) -> Application:
    """Delete one event and re-derive the owning application's status. Raises KeyError if unknown."""
    with transaction(conn):
        event = EventRepo(conn).get(event_id)
        if event is None:
            raise KeyError(event_id)
        EventRepo(conn).delete(event_id, actor="user", source=SOURCE)
        return status.recompute(conn, event.application_id)


def log_event(
    conn: sqlite3.Connection,
    *,
    application_id: int,
    event_type: EventType,
    occurred_at: datetime,
    summary: str | None = None,
) -> tuple[Application, bool]:
    """Append a user-confirmed event and re-derive the automatic status.

    Returns (application, inserted); ``inserted`` is False when the identical event already
    existed (recompute still runs, though it is a no-op in that case).
    """
    with transaction(conn):
        _, inserted = EventRepo(conn).add_idempotent(
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
        return status.recompute(conn, application_id), inserted


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


__all__ = [
    "SOURCE",
    "add_application",
    "delete_application",
    "delete_campaign",
    "delete_event",
    "log_event",
    "set_status",
    "update_application",
]
