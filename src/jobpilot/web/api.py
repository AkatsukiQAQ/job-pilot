"""JSON routes. Each handler only parses input, calls a repo / service, and shapes output."""

from __future__ import annotations

import sqlite3
from collections.abc import Iterator
from datetime import UTC, datetime, timedelta
from typing import Annotated, Any

from fastapi import APIRouter, Depends, HTTPException, Query, Request

from jobpilot.domain import (
    Application,
    ApplicationStatus,
    CampaignCreate,
    CampaignKind,
    EventType,
    Track,
)
from jobpilot.regions import get_region_pack, list_region_packs
from jobpilot.services import manual, status
from jobpilot.store.db import connect
from jobpilot.store.repo import ApplicationRepo, CampaignRepo, EventRepo
from jobpilot.web.schemas import (
    ApplicationDetail,
    ApplicationIn,
    ApplicationRow,
    CampaignIn,
    CampaignOut,
    DashboardOut,
    EventIn,
    EventOut,
    MetaOut,
    RecentEvent,
    StatusIn,
    UpcomingItem,
)

router = APIRouter(prefix="/api")


def get_conn(request: Request) -> Iterator[sqlite3.Connection]:
    """One connection per request: sqlite connections must stay on the thread that opened them."""
    conn = connect(request.app.state.settings.db_path)
    try:
        yield conn
    finally:
        conn.close()


Conn = Annotated[sqlite3.Connection, Depends(get_conn)]

_APPLICATION_SQL = (
    "SELECT a.*, c.name AS company,"
    " (SELECT e.event_type FROM application_event e WHERE e.application_id = a.application_id"
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


def _campaign_or_404(conn: sqlite3.Connection, campaign_id: int) -> None:
    if CampaignRepo(conn).get(campaign_id) is None:
        raise HTTPException(404, "campaign not found")


# ---------------------------------------------------------------------------- meta


@router.get("/meta")
def meta(request: Request, conn: Conn) -> MetaOut:
    settings = request.app.state.settings
    active = CampaignRepo(conn).get_active()
    pack_tz = get_region_pack(active.region_pack).default_tz if active else None
    return MetaOut(
        statuses=[s.value for s in ApplicationStatus],
        event_types=[e.value for e in EventType],
        tracks=[t.value for t in Track],
        kinds=[k.value for k in CampaignKind],
        region_packs=list_region_packs(),
        tz=settings.effective_tz(pack_tz),
    )


# ---------------------------------------------------------------------------- campaigns


def _campaign_out(conn: sqlite3.Connection) -> list[CampaignOut]:
    rows = conn.execute(
        "SELECT c.*, (SELECT COUNT(*) FROM application a WHERE a.campaign_id = c.campaign_id)"
        " AS application_count FROM campaign c ORDER BY c.campaign_id"
    ).fetchall()
    return [CampaignOut(**{k: r[k] for k in CampaignOut.model_fields}) for r in rows]


@router.get("/campaigns")
def list_campaigns(conn: Conn) -> list[CampaignOut]:
    return _campaign_out(conn)


@router.post("/campaigns", status_code=201)
def create_campaign(body: CampaignIn, conn: Conn) -> CampaignOut:
    if body.region_pack not in list_region_packs():
        raise HTTPException(422, "unknown region pack")
    try:
        created = CampaignRepo(conn).add(
            CampaignCreate(**body.model_dump()), actor="user", source=manual.SOURCE
        )
    except sqlite3.IntegrityError as e:
        raise HTTPException(409, "a campaign with this name already exists") from e
    except ValueError as e:  # ends_on before starts_on
        raise HTTPException(422, str(e)) from e
    return next(c for c in _campaign_out(conn) if c.campaign_id == created.campaign_id)


@router.patch("/campaigns/{campaign_id}")
def update_campaign(campaign_id: int, body: CampaignIn, conn: Conn) -> CampaignOut:
    if body.region_pack not in list_region_packs():
        raise HTTPException(422, "unknown region pack")
    try:
        CampaignRepo(conn).update(
            campaign_id, CampaignCreate(**body.model_dump()), source=manual.SOURCE
        )
    except KeyError as e:
        raise HTTPException(404, "campaign not found") from e
    except sqlite3.IntegrityError as e:
        raise HTTPException(409, "a campaign with this name already exists") from e
    except ValueError as e:
        raise HTTPException(422, str(e)) from e
    return next(c for c in _campaign_out(conn) if c.campaign_id == campaign_id)


@router.post("/campaigns/{campaign_id}/activate")
def activate_campaign(campaign_id: int, conn: Conn) -> CampaignOut:
    try:
        CampaignRepo(conn).set_active(campaign_id, source=manual.SOURCE)
    except KeyError as e:
        raise HTTPException(404, "campaign not found") from e
    return next(c for c in _campaign_out(conn) if c.campaign_id == campaign_id)


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
def dashboard(campaign_id: int, conn: Conn) -> DashboardOut:
    _campaign_or_404(conn, campaign_id)
    now = datetime.now(UTC)
    counts = {
        r[0]: r[1]
        for r in conn.execute(
            "SELECT effective_status, COUNT(*) FROM application WHERE campaign_id = ?"
            " GROUP BY effective_status",
            (campaign_id,),
        )
    }
    upcoming: list[UpcomingItem] = []
    horizon = (now + timedelta(days=7)).isoformat()
    rows = conn.execute(
        _APPLICATION_SQL
        + " WHERE a.campaign_id = ? AND (a.deadline_at <= ? OR a.next_action_due <= ?)"
        " ORDER BY COALESCE(a.deadline_at, a.next_action_due)",
        (campaign_id, horizon, horizon),
    ).fetchall()
    for r in rows:
        app = Application.from_row(r)
        if app.deadline_at is not None:
            upcoming.append(
                UpcomingItem(
                    application_id=app.application_id,
                    company=r["company"],
                    role=app.role,
                    kind="deadline",
                    due=app.deadline_at,
                    label=None,
                )
            )
        if app.next_action_due is not None:
            upcoming.append(
                UpcomingItem(
                    application_id=app.application_id,
                    company=r["company"],
                    role=app.role,
                    kind="next_action",
                    due=app.next_action_due,
                    label=app.next_action,
                )
            )
    upcoming.sort(key=lambda u: u.due)
    recent = conn.execute(
        "SELECT e.event_id, e.application_id, c.name AS company, e.event_type, e.occurred_at,"
        " e.summary FROM application_event e JOIN application a ON a.application_id = e.application_id"
        " JOIN company c ON c.company_id = a.company_id WHERE a.campaign_id = ?"
        " ORDER BY e.occurred_at DESC, e.event_id DESC LIMIT 20",
        (campaign_id,),
    ).fetchall()
    return DashboardOut(
        counts_by_status=counts,
        upcoming=upcoming,
        recent_events=[RecentEvent(**dict(r)) for r in recent],
    )


# ---------------------------------------------------------------------------- applications


def _detail(conn: sqlite3.Connection, application_id: int) -> ApplicationDetail:
    r = conn.execute(_APPLICATION_SQL + " WHERE a.application_id = ?", (application_id,)).fetchone()
    if r is None:
        raise HTTPException(404, "application not found")
    events = [EventOut(**e.model_dump()) for e in EventRepo(conn).list_for(application_id)]
    return ApplicationDetail(**_row(r, datetime.now(UTC)), events=events)


@router.post("/applications", status_code=201)
def create_application(body: ApplicationIn, conn: Conn) -> ApplicationDetail:
    _campaign_or_404(conn, body.campaign_id)
    app, created = manual.add_application(conn, **body.model_dump())
    if not created:
        raise HTTPException(409, "this application already exists")
    return _detail(conn, app.application_id)


@router.get("/applications/{application_id}")
def get_application(application_id: int, conn: Conn) -> ApplicationDetail:
    return _detail(conn, application_id)


@router.post("/applications/{application_id}/status")
def set_application_status(application_id: int, body: StatusIn, conn: Conn) -> ApplicationDetail:
    if ApplicationRepo(conn).get(application_id) is None:
        raise HTTPException(404, "application not found")
    try:
        manual.set_status(conn, application_id=application_id, **body.model_dump())
    except sqlite3.IntegrityError as e:  # excluded_reason without 'unsuitable'
        raise HTTPException(422, "excluded_reason is only allowed with status 'unsuitable'") from e
    return _detail(conn, application_id)


@router.post("/applications/{application_id}/events", status_code=201)
def add_event(application_id: int, body: EventIn, conn: Conn) -> ApplicationDetail:
    if ApplicationRepo(conn).get(application_id) is None:
        raise HTTPException(404, "application not found")
    manual.log_event(conn, application_id=application_id, **body.model_dump())
    return _detail(conn, application_id)


__all__ = ["get_conn", "router"]
