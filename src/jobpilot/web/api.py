"""JSON routes. Each handler only parses input, calls a repo / service, and shapes output."""

from __future__ import annotations

import sqlite3
from collections.abc import Iterable, Iterator
from datetime import UTC, datetime, timedelta
from typing import Annotated, Any
from zoneinfo import ZoneInfo

from fastapi import APIRouter, Depends, HTTPException, Query, Request

from jobpilot.domain import (
    Application,
    ApplicationStatus,
    Campaign,
    CampaignCreate,
    CampaignKind,
    EventType,
    Track,
)
from jobpilot.regions import get_region_pack, list_region_packs
from jobpilot.services import manual, status
from jobpilot.settings import Settings
from jobpilot.store.db import connect, to_iso
from jobpilot.store.repo import ApplicationRepo, CampaignRepo, EventRepo
from jobpilot.web.schemas import (
    ApplicationDetail,
    ApplicationIn,
    ApplicationPatch,
    ApplicationRow,
    CampaignDeleteOut,
    CampaignIn,
    CampaignOut,
    DashboardOut,
    DeleteOut,
    EventIn,
    EventOut,
    MetaOut,
    RecentEvent,
    StatusIn,
    UpcomingItem,
)

router = APIRouter(prefix="/api")


def get_conn(request: Request) -> Iterator[sqlite3.Connection]:
    """One connection per request, usable off its creating thread.

    FastAPI runs a sync generator dependency's setup code, the endpoint body, and the teardown
    code as separate submissions to its threadpool, so the connection can be opened on one worker
    thread and closed on another; ``check_same_thread=False`` allows that. Each request still gets
    its own connection.
    """
    conn = connect(request.app.state.settings.db_path, check_same_thread=False)
    try:
        yield conn
    finally:
        conn.close()


def _error(status_code: int, code: str, **extra: Any) -> HTTPException:
    return HTTPException(status_code, {"code": code, **extra})


Conn = Annotated[sqlite3.Connection, Depends(get_conn)]


def _sql_list(values: Iterable[str]) -> str:
    return "(" + ", ".join(f"'{v}'" for v in sorted(values)) + ")"


_SILENT_TYPES_SQL = _sql_list(t.value for t in status.SILENT_EVENT_TYPES)
_CLOSED_SQL = _sql_list(s.value for s in status.CLOSED_FOR_TODO)

_APPLICATION_SQL = (
    "SELECT a.*, c.name AS company,"
    " (SELECT e.event_type FROM application_event e WHERE e.application_id = a.application_id"
    f"  AND e.event_type NOT IN {_SILENT_TYPES_SQL}"
    "  ORDER BY e.occurred_at DESC, e.event_id DESC LIMIT 1) AS last_event_type"
    " FROM application a JOIN company c ON c.company_id = a.company_id"
)


def _row(r: sqlite3.Row, now: datetime) -> dict[str, Any]:
    app = Application.from_row(r)
    return {
        **app.model_dump(),
        "status": app.status,
        "company": r["company"],
        "last_event_type": r["last_event_type"],
        "is_ghosted": status.is_ghosted(app, now),
    }


def _campaign_or_404(conn: sqlite3.Connection, campaign_id: int) -> Campaign:
    campaign = CampaignRepo(conn).get(campaign_id)
    if campaign is None:
        raise _error(404, "not_found")
    return campaign


def _pack_tz(settings: Settings, region_pack: str | None) -> str:
    """Display tz for a region pack; a pack missing from the registry falls back like 'none'."""
    pack_tz = None
    if region_pack is not None and region_pack in list_region_packs():
        pack_tz = get_region_pack(region_pack).default_tz
    return settings.effective_tz(pack_tz)


def _settings(request: Request) -> Settings:
    return request.app.state.settings


# ---------------------------------------------------------------------------- meta


@router.get("/meta")
def meta(request: Request, conn: Conn) -> MetaOut:
    active = CampaignRepo(conn).get_active()
    return MetaOut(
        statuses=[s.value for s in ApplicationStatus],
        event_types=[e.value for e in EventType],
        tracks=[t.value for t in Track],
        kinds=[k.value for k in CampaignKind],
        region_packs=list_region_packs(),
        tz=_pack_tz(_settings(request), active.region_pack if active else None),
    )


# ---------------------------------------------------------------------------- campaigns


def _campaign_out(conn: sqlite3.Connection, settings: Settings) -> list[CampaignOut]:
    rows = conn.execute(
        "SELECT c.*, (SELECT COUNT(*) FROM application a WHERE a.campaign_id = c.campaign_id)"
        " AS application_count FROM campaign c ORDER BY c.campaign_id"
    ).fetchall()
    return [CampaignOut(**dict(r), tz=_pack_tz(settings, r["region_pack"])) for r in rows]


def _one_campaign(conn: sqlite3.Connection, request: Request, campaign_id: int) -> CampaignOut:
    return next(c for c in _campaign_out(conn, _settings(request)) if c.campaign_id == campaign_id)


@router.get("/campaigns")
def list_campaigns(request: Request, conn: Conn) -> list[CampaignOut]:
    return _campaign_out(conn, _settings(request))


@router.post("/campaigns", status_code=201)
def create_campaign(body: CampaignIn, request: Request, conn: Conn) -> CampaignOut:
    if body.region_pack not in list_region_packs():
        raise _error(422, "unknown_region_pack")
    try:
        created = CampaignRepo(conn).add(
            CampaignCreate(**body.model_dump()), actor="user", source=manual.SOURCE
        )
    except sqlite3.IntegrityError as e:
        raise _error(409, "campaign_name_exists") from e
    except ValueError as e:  # ends_on before starts_on
        raise _error(422, "campaign_dates_order", message=str(e)) from e
    return _one_campaign(conn, request, created.campaign_id)


@router.patch("/campaigns/{campaign_id}")
def update_campaign(
    campaign_id: int, body: CampaignIn, request: Request, conn: Conn
) -> CampaignOut:
    if body.region_pack not in list_region_packs():
        raise _error(422, "unknown_region_pack")
    try:
        CampaignRepo(conn).update(
            campaign_id, CampaignCreate(**body.model_dump()), source=manual.SOURCE
        )
    except KeyError as e:
        raise _error(404, "not_found") from e
    except sqlite3.IntegrityError as e:
        raise _error(409, "campaign_name_exists") from e
    except ValueError as e:
        raise _error(422, "campaign_dates_order", message=str(e)) from e
    return _one_campaign(conn, request, campaign_id)


@router.post("/campaigns/{campaign_id}/activate")
def activate_campaign(campaign_id: int, request: Request, conn: Conn) -> CampaignOut:
    try:
        CampaignRepo(conn).set_active(campaign_id, source=manual.SOURCE)
    except KeyError as e:
        raise _error(404, "not_found") from e
    return _one_campaign(conn, request, campaign_id)


@router.delete("/campaigns/{campaign_id}")
def delete_campaign(campaign_id: int, conn: Conn) -> CampaignDeleteOut:
    try:
        n_apps, n_events = manual.delete_campaign(conn, campaign_id=campaign_id)
    except KeyError as e:
        raise _error(404, "not_found") from e
    return CampaignDeleteOut(deleted_applications=n_apps, deleted_events=n_events)


@router.get("/campaigns/{campaign_id}/applications")
def list_applications(
    campaign_id: int,
    conn: Conn,
    status_filter: Annotated[str | None, Query(alias="status")] = None,
) -> list[ApplicationRow]:
    _campaign_or_404(conn, campaign_id)
    sql = _APPLICATION_SQL + " WHERE a.campaign_id = ?"
    params: list[Any] = [campaign_id]
    if status_filter:
        sql += " AND a.effective_status = ?"
        params.append(status_filter)
    sql += " ORDER BY a.updated_at DESC, a.application_id DESC"
    now = datetime.now(UTC)
    return [ApplicationRow(**_row(r, now)) for r in conn.execute(sql, params)]


@router.get("/campaigns/{campaign_id}/dashboard")
def dashboard(campaign_id: int, conn: Conn, request: Request) -> DashboardOut:
    campaign = _campaign_or_404(conn, campaign_id)
    now = datetime.now(UTC)
    tz = ZoneInfo(_pack_tz(_settings(request), campaign.region_pack))
    local_now = now.astimezone(tz)
    today_start = local_now.replace(hour=0, minute=0, second=0, microsecond=0).astimezone(UTC)
    days_to_sunday = 6 - local_now.weekday()
    week_end = (
        (local_now + timedelta(days=days_to_sunday))
        .replace(hour=23, minute=59, second=59, microsecond=999000)
        .astimezone(UTC)
    )
    horizon = now + timedelta(days=7)
    lookback = today_start - timedelta(days=14)
    today_iso, horizon_iso, week_end_iso, lookback_iso = (
        to_iso(today_start),
        to_iso(horizon),
        to_iso(week_end),
        to_iso(lookback),
    )
    counts = {
        r[0]: r[1]
        for r in conn.execute(
            "SELECT effective_status, COUNT(*) FROM application WHERE campaign_id = ?"
            " GROUP BY effective_status",
            (campaign_id,),
        )
    }
    upcoming: list[UpcomingItem] = []
    rows = conn.execute(
        _APPLICATION_SQL + f" WHERE a.campaign_id = ? AND a.effective_status NOT IN {_CLOSED_SQL}"
        " AND (a.deadline_at BETWEEN ? AND ? OR a.next_action_due BETWEEN ? AND ?)",
        (campaign_id, lookback_iso, horizon_iso, lookback_iso, horizon_iso),
    ).fetchall()
    for r in rows:
        app = Application.from_row(r)
        for kind, due, label in (
            ("deadline", app.deadline_at, None),
            ("next_action", app.next_action_due, app.next_action),
        ):
            if due is not None and lookback <= due <= horizon:
                upcoming.append(
                    UpcomingItem(
                        application_id=app.application_id,
                        company=r["company"],
                        role=app.role,
                        kind=kind,
                        due=due,
                        label=label,
                        overdue=due < now,
                    )
                )
    upcoming.sort(key=lambda u: (not u.overdue, u.due))
    recent = conn.execute(
        "SELECT e.event_id, e.application_id, c.name AS company, e.event_type, e.occurred_at,"
        " e.summary FROM application_event e JOIN application a ON a.application_id = e.application_id"
        " JOIN company c ON c.company_id = a.company_id WHERE a.campaign_id = ?"
        " ORDER BY e.occurred_at DESC, e.event_id DESC LIMIT 20",
        (campaign_id,),
    ).fetchall()
    deadlines_this_week = conn.execute(
        "SELECT COUNT(*) FROM application WHERE campaign_id = ?"
        f" AND effective_status NOT IN {_CLOSED_SQL} AND deadline_at BETWEEN ? AND ?",
        (campaign_id, today_iso, week_end_iso),
    ).fetchone()[0]
    interviews_next_7d = conn.execute(
        "SELECT COUNT(*) FROM application_event e JOIN application a"
        " ON a.application_id = e.application_id WHERE a.campaign_id = ?"
        " AND e.event_type IN ('interview', 'final_interview', 'casual_interview')"
        f" AND a.effective_status NOT IN {_CLOSED_SQL}"
        " AND e.occurred_at BETWEEN ? AND ?",
        (campaign_id, today_iso, horizon_iso),
    ).fetchone()[0]
    return DashboardOut(
        counts_by_status=counts,
        upcoming=upcoming,
        recent_events=[RecentEvent(**dict(r)) for r in recent],
        deadlines_this_week=int(deadlines_this_week),
        interviews_next_7d=int(interviews_next_7d),
    )


# ---------------------------------------------------------------------------- applications


def _detail(conn: sqlite3.Connection, application_id: int) -> ApplicationDetail:
    r = conn.execute(_APPLICATION_SQL + " WHERE a.application_id = ?", (application_id,)).fetchone()
    if r is None:
        raise _error(404, "not_found")
    events = [EventOut(**e.model_dump()) for e in EventRepo(conn).list_for(application_id)]
    return ApplicationDetail(**_row(r, datetime.now(UTC)), events=events)


@router.post("/applications", status_code=201)
def create_application(body: ApplicationIn, conn: Conn) -> ApplicationDetail:
    _campaign_or_404(conn, body.campaign_id)
    app, created = manual.add_application(conn, **body.model_dump())
    if not created:
        raise _error(409, "application_exists", existing_application_id=app.application_id)
    return _detail(conn, app.application_id)


@router.get("/applications/{application_id}")
def get_application(application_id: int, conn: Conn) -> ApplicationDetail:
    return _detail(conn, application_id)


@router.patch("/applications/{application_id}")
def update_application(
    application_id: int, body: ApplicationPatch, conn: Conn
) -> ApplicationDetail:
    try:
        manual.update_application(conn, application_id=application_id, **body.model_dump())
    except KeyError as e:
        raise _error(404, "not_found") from e
    except manual.ApplicationConflict as e:
        raise _error(409, "application_exists", existing_application_id=e.existing_id) from e
    except sqlite3.IntegrityError as e:
        raise _error(409, "application_exists") from e
    return _detail(conn, application_id)


@router.delete("/applications/{application_id}/next-action")
def clear_next_action(application_id: int, conn: Conn) -> ApplicationDetail:
    try:
        manual.clear_next_action(conn, application_id=application_id)
    except KeyError as e:
        raise _error(404, "not_found") from e
    return _detail(conn, application_id)


@router.delete("/applications/{application_id}")
def delete_application(application_id: int, conn: Conn) -> DeleteOut:
    try:
        n_events = manual.delete_application(conn, application_id=application_id)
    except KeyError as e:
        raise _error(404, "not_found") from e
    return DeleteOut(deleted_events=n_events)


@router.post("/applications/{application_id}/status")
def set_application_status(application_id: int, body: StatusIn, conn: Conn) -> ApplicationDetail:
    if ApplicationRepo(conn).get(application_id) is None:
        raise _error(404, "not_found")
    try:
        manual.set_status(conn, application_id=application_id, **body.model_dump())
    except sqlite3.IntegrityError as e:  # excluded_reason without 'unsuitable'
        raise _error(422, "excluded_reason_requires_unsuitable") from e
    return _detail(conn, application_id)


@router.post("/applications/{application_id}/events", status_code=201)
def add_event(application_id: int, body: EventIn, conn: Conn) -> ApplicationDetail:
    if ApplicationRepo(conn).get(application_id) is None:
        raise _error(404, "not_found")
    _, inserted = manual.log_event(conn, application_id=application_id, **body.model_dump())
    if not inserted:
        raise _error(409, "event_exists")
    return _detail(conn, application_id)


def _event_or_404(conn: sqlite3.Connection, application_id: int, event_id: int) -> None:
    event = EventRepo(conn).get(event_id)
    if event is None or event.application_id != application_id:
        raise _error(404, "not_found")


@router.patch("/applications/{application_id}/events/{event_id}")
def update_event(
    application_id: int, event_id: int, body: EventIn, conn: Conn
) -> ApplicationDetail:
    _event_or_404(conn, application_id, event_id)
    try:
        manual.update_event(conn, event_id=event_id, **body.model_dump())
    except sqlite3.IntegrityError as e:
        raise _error(409, "event_exists") from e
    return _detail(conn, application_id)


@router.delete("/applications/{application_id}/events/{event_id}")
def delete_event(application_id: int, event_id: int, conn: Conn) -> ApplicationDetail:
    _event_or_404(conn, application_id, event_id)
    manual.delete_event(conn, event_id=event_id)
    return _detail(conn, application_id)


__all__ = ["get_conn", "router"]
