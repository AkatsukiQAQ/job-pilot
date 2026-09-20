"""Status engine: derive an application's automatic status from its event ledger.

Shared by every writer of events (manual entry now, Gmail classification and chat later),
so the derivation lives in one place. ``user_status`` is never touched here.
"""

from __future__ import annotations

import sqlite3
from collections.abc import Sequence
from datetime import datetime, timedelta

from jobpilot.domain import (
    EVENT_STATUS,
    SILENCE_STATUSES,
    STATUS_RANK,
    Application,
    ApplicationEvent,
    ApplicationStatus,
    StatusSetBy,
)
from jobpilot.store.repo import ApplicationRepo, AutoUpdate, EventRepo

GHOSTED_DAYS = 30


def derive_auto_status(events: Sequence[ApplicationEvent]) -> ApplicationStatus:
    """Highest-ranked status implied by the events; ties go to the latest event.

    Events without an implied status (notes, portal checks, follow-ups) are ignored.
    """
    best: tuple[int, datetime, ApplicationStatus] | None = None
    for ev in events:
        status = EVENT_STATUS.get(ev.event_type)
        if status is None:
            continue
        key = (STATUS_RANK[status], ev.occurred_at, status)
        if best is None or key[:2] > best[:2]:
            best = key
    return best[2] if best else ApplicationStatus.UNRECORDED


def recompute(conn: sqlite3.Connection, application_id: int) -> Application:
    """Re-derive auto_status / last_event_at / applied_at from the ledger and persist them."""
    events = EventRepo(conn).list_for(application_id)
    dated = [ev.occurred_at for ev in events if EVENT_STATUS.get(ev.event_type) is not None]
    applied_rank = STATUS_RANK[ApplicationStatus.APPLIED]
    applied = [
        ev.occurred_at
        for ev in events
        if (s := EVENT_STATUS.get(ev.event_type)) is not None and STATUS_RANK[s] >= applied_rank
    ]
    return ApplicationRepo(conn).update_auto(
        application_id,
        AutoUpdate(
            auto_status=derive_auto_status(events),
            status_set_by=StatusSetBy.SYSTEM,
            last_event_at=max(dated) if dated else None,
            applied_at=min(applied) if applied else None,
            force_dates=True,
        ),
    )


def is_ghosted(app: Application, now: datetime, days: int = GHOSTED_DAYS) -> bool:
    """True when an in-progress application has heard nothing for ``days``. Not persisted."""
    return (
        app.status in SILENCE_STATUSES
        and app.last_event_at is not None
        and now - app.last_event_at >= timedelta(days=days)
    )


__all__ = ["GHOSTED_DAYS", "derive_auto_status", "is_ghosted", "recompute"]
