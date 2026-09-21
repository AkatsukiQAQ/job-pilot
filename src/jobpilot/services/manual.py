"""User-initiated writes (web UI): straight to the database with audit rows (decision D29).

The operator is the user, so no proposal step is needed. Each function is one transaction.
"""

from __future__ import annotations

import sqlite3
from datetime import datetime

from jobpilot.domain import (
    STATUS_RANK,
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
from jobpilot.store.repo import ApplicationRepo, AutoUpdate, CampaignRepo, CompanyRepo, EventRepo
from jobpilot.textutil import nfkc, normalize_role

SOURCE = "web"


class ApplicationConflict(Exception):
    """An edit would collide with another application's natural key."""

    def __init__(self, existing_id: int) -> None:
        super().__init__(existing_id)
        self.existing_id = existing_id


def _resolve_company(conn: sqlite3.Connection, company_name: str, *, rename: bool) -> Company:
    name = company_name.strip()
    norm = nfkc(name).casefold()
    companies = CompanyRepo(conn)
    company = companies.get_by_norm(norm)
    if company is None:
        return companies.add(CompanyCreate(name=name, name_norm=norm), actor="user", source=SOURCE)
    if rename and company.name != name:
        return companies.rename(company.company_id, name, actor="user", source=SOURCE)
    return company


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
        company = _resolve_company(conn, company_name, rename=False)
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

    A company spelled differently is renamed (display name only). A natural-key collision with
    another application raises ApplicationConflict; an unknown id raises KeyError.
    """
    with transaction(conn):
        apps = ApplicationRepo(conn)
        current = apps.get(application_id)
        if current is None:
            raise KeyError(application_id)
        company = _resolve_company(conn, company_name, rename=True)
        role_norm = normalize_role(role)
        try:
            return apps.update_fields(
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
        except sqlite3.IntegrityError as e:
            other = apps.find_natural(
                current.campaign_id, company.company_id, track.value, role_norm
            )
            if other is None:
                raise
            raise ApplicationConflict(other.application_id) from e


def clear_next_action(conn: sqlite3.Connection, *, application_id: int) -> Application:
    """Mark the next action done. Raises KeyError if unknown."""
    return ApplicationRepo(conn).clear_next_action(application_id, actor="user", source=SOURCE)


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
        return status.recompute(conn, event.application_id, source=SOURCE)


def update_event(
    conn: sqlite3.Connection,
    *,
    event_id: int,
    event_type: EventType,
    occurred_at: datetime,
    summary: str | None = None,
) -> Application:
    """Edit one event and re-derive the owning application's status.

    Raises KeyError if unknown; a UNIQUE collision propagates as sqlite3.IntegrityError.
    """
    with transaction(conn):
        event = EventRepo(conn).update(
            event_id,
            event_type=event_type,
            occurred_at=occurred_at,
            summary=summary,
            actor="user",
            source=SOURCE,
        )
        return status.recompute(conn, event.application_id, source=SOURCE)


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
    existed, in which case nothing is recomputed or written. When the ledger now implies a
    higher status than before, the pending next action is considered done and cleared.
    """
    with transaction(conn):
        apps = ApplicationRepo(conn)
        before = apps.get(application_id)
        if before is None:
            raise KeyError(application_id)
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
        if not inserted:
            return before, False
        app = status.recompute(conn, application_id, source=SOURCE)
        if STATUS_RANK.get(app.auto_status, 0) > STATUS_RANK.get(before.auto_status, 0):
            app = apps.update_auto(
                application_id,
                AutoUpdate(clear_next_action=True),
                actor="system",
                source=SOURCE,
            )
        return app, True


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
    "ApplicationConflict",
    "add_application",
    "clear_next_action",
    "delete_application",
    "delete_campaign",
    "delete_event",
    "log_event",
    "set_status",
    "update_application",
    "update_event",
]
