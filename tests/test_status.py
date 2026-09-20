from __future__ import annotations

import sqlite3
from datetime import UTC, datetime, timedelta

import pytest

from jobpilot.domain import (
    ApplicationCreate,
    ApplicationEvent,
    ApplicationStatus,
    CampaignCreate,
    CampaignKind,
    CompanyCreate,
    EventCreate,
    EventSource,
    EventType,
    Track,
)
from jobpilot.services import manual, status
from jobpilot.store.repo import ApplicationRepo, CampaignRepo, CompanyRepo, EventRepo

T0 = datetime(2030, 3, 1, tzinfo=UTC)


def _ev(event_type: EventType, days: int) -> ApplicationEvent:
    return ApplicationEvent(
        event_id=days,
        application_id=1,
        event_type=event_type,
        occurred_at=T0 + timedelta(days=days),
        source=EventSource.MANUAL,
        confidence=1.0,
        created_at=T0,
    )


def test_derive_takes_highest_rank_and_never_regresses() -> None:
    events = [_ev(EventType.ACK, 0), _ev(EventType.INTERVIEW, 5), _ev(EventType.ACK, 9)]
    assert status.derive_auto_status(events) is ApplicationStatus.INTERVIEWING


def test_derive_terminal_outranks_progress() -> None:
    events = [_ev(EventType.OFFER, 0), _ev(EventType.REJECTION, 1)]
    assert status.derive_auto_status(events) is ApplicationStatus.REJECTED


def test_derive_ignores_events_without_status() -> None:
    assert status.derive_auto_status([]) is ApplicationStatus.UNRECORDED
    assert status.derive_auto_status([_ev(EventType.NOTE, 0)]) is ApplicationStatus.UNRECORDED


@pytest.fixture
def application(conn: sqlite3.Connection) -> int:
    campaign = CampaignRepo(conn).add(
        CampaignCreate(name="demo", kind=CampaignKind.OTHER, region_pack="global_en")
    )
    company = CompanyRepo(conn).add(CompanyCreate(name="Acme", name_norm="acme"))
    app = ApplicationRepo(conn).add(
        ApplicationCreate(
            campaign_id=campaign.campaign_id, company_id=company.company_id, track=Track.OTHER
        )
    )
    return app.application_id


def test_recompute_writes_auto_fields(conn: sqlite3.Connection, application: int) -> None:
    repo = EventRepo(conn)
    for et, days in ((EventType.ACK, 0), (EventType.INTERVIEW, 5), (EventType.NOTE, 9)):
        repo.add_idempotent(
            EventCreate(
                application_id=application,
                event_type=et,
                occurred_at=T0 + timedelta(days=days),
                source=EventSource.MANUAL,
            )
        )
    app = status.recompute(conn, application)
    assert app.auto_status is ApplicationStatus.INTERVIEWING
    assert app.applied_at == T0
    assert app.last_event_at == T0 + timedelta(days=5)  # the note does not count
    assert status.is_ghosted(app, T0 + timedelta(days=36))
    assert not status.is_ghosted(app, T0 + timedelta(days=20))


def test_user_status_wins_and_is_audited(conn: sqlite3.Connection, application: int) -> None:
    manual.log_event(
        conn, application_id=application, event_type=EventType.INTERVIEW, occurred_at=T0
    )
    app = manual.set_status(
        conn, application_id=application, user_status=ApplicationStatus.REJECTED
    )
    assert app.auto_status is ApplicationStatus.INTERVIEWING
    assert app.status is ApplicationStatus.REJECTED
    # a later automatic event does not change what the user sees
    app, inserted = manual.log_event(
        conn, application_id=application, event_type=EventType.OFFER, occurred_at=T0
    )
    assert inserted
    assert app.auto_status is ApplicationStatus.OFFER
    assert app.status is ApplicationStatus.REJECTED
    audit = conn.execute(
        "SELECT before_json, after_json FROM audit_log WHERE action = 'application.set_user_status'"
    ).fetchone()
    assert '"user_status": null' in audit["before_json"]
    assert '"user_status": "rejected"' in audit["after_json"]


def test_delete_event_clears_derived_fields(conn: sqlite3.Connection, application: int) -> None:
    app, inserted = manual.log_event(
        conn, application_id=application, event_type=EventType.INTERVIEW, occurred_at=T0
    )
    assert inserted
    assert app.auto_status is ApplicationStatus.INTERVIEWING
    event_id = EventRepo(conn).list_for(application)[0].event_id

    app = manual.delete_event(conn, event_id=event_id)
    assert app.auto_status is ApplicationStatus.UNRECORDED
    assert app.last_event_at is None
    assert app.applied_at is None

    with pytest.raises(KeyError):
        manual.delete_event(conn, event_id=event_id)


def test_add_application_dedupes_company_and_natural_key(conn: sqlite3.Connection) -> None:
    campaign = CampaignRepo(conn).add(
        CampaignCreate(name="demo", kind=CampaignKind.OTHER, region_pack="global_en")
    )
    a, created = manual.add_application(
        conn, campaign_id=campaign.campaign_id, company_name="Acme", track=Track.OTHER, role="SWE"
    )
    b, created_again = manual.add_application(
        conn, campaign_id=campaign.campaign_id, company_name=" ACME ", track=Track.OTHER, role="swe"
    )
    assert created and not created_again
    assert a.application_id == b.application_id
    assert conn.execute("SELECT COUNT(*) FROM company").fetchone()[0] == 1
