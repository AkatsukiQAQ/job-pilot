from __future__ import annotations

from collections.abc import Iterator
from datetime import UTC, datetime, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo

import pytest
from fastapi.testclient import TestClient

from jobpilot.settings import Settings
from jobpilot.store.db import connect
from jobpilot.web.app import create_app


@pytest.fixture
def client(settings: Settings, tmp_path: Path) -> Iterator[TestClient]:
    app = create_app(settings, dist_dir=tmp_path / "no-dist")
    with TestClient(app, base_url="http://127.0.0.1") as c:
        yield c


def test_meta_lists_enums_and_default_tz(client: TestClient) -> None:
    body = client.get("/api/meta").json()
    assert "interviewing" in body["statuses"]
    assert "interview" in body["event_types"]
    assert body["region_packs"] == ["global_en", "japan"]
    assert body["tz"] == "UTC"


def test_root_without_built_frontend_is_404_not_500(client: TestClient) -> None:
    assert client.get("/").status_code == 404


def test_board_flow(client: TestClient) -> None:
    r = client.post(
        "/api/campaigns", json={"name": "2031 demo", "kind": "newgrad", "region_pack": "japan"}
    )
    assert r.status_code == 201
    campaign_id = r.json()["campaign_id"]
    assert r.json()["is_active"] is True
    assert client.get("/api/meta").json()["tz"] == "Asia/Tokyo"  # region-pack default

    dup = client.post(
        "/api/campaigns", json={"name": "2031 demo", "kind": "newgrad", "region_pack": "japan"}
    )
    assert dup.status_code == 409

    r = client.post(
        "/api/applications",
        json={
            "campaign_id": campaign_id,
            "company_name": "Acme Robotics",
            "role": "ML Engineer",
            "track": "newgrad",
        },
    )
    assert r.status_code == 201
    app_id = r.json()["application_id"]
    assert r.json()["status"] == "unrecorded"
    assert r.json()["company"] == "Acme Robotics"

    r = client.post(
        f"/api/applications/{app_id}/events",
        json={"event_type": "interview", "occurred_at": "2031-03-01T09:00:00Z", "summary": "1st"},
    )
    assert r.status_code == 201
    assert r.json()["auto_status"] == "interviewing"
    assert r.json()["status"] == "interviewing"
    assert r.json()["last_event_type"] == "interview"
    assert len(r.json()["events"]) == 1

    r = client.post(f"/api/applications/{app_id}/status", json={"user_status": "rejected"})
    assert r.json()["status"] == "rejected"
    assert r.json()["auto_status"] == "interviewing"

    bad = client.post(
        f"/api/applications/{app_id}/status",
        json={"user_status": "rejected", "excluded_reason": "x"},
    )
    assert bad.status_code == 422

    rows = client.get(f"/api/campaigns/{campaign_id}/applications").json()
    assert [row["application_id"] for row in rows] == [app_id]
    assert (
        client.get(
            f"/api/campaigns/{campaign_id}/applications", params={"status": "interviewing"}
        ).json()
        == []
    )

    dash = client.get(f"/api/campaigns/{campaign_id}/dashboard").json()
    assert dash["counts_by_status"] == {"rejected": 1}
    assert dash["recent_events"][0]["company"] == "Acme Robotics"
    assert dash["upcoming"] == []

    campaigns = client.get("/api/campaigns").json()
    assert campaigns[0]["application_count"] == 1


def test_activate_switches_the_active_campaign(client: TestClient) -> None:
    a = client.post(
        "/api/campaigns", json={"name": "a", "kind": "other", "region_pack": "global_en"}
    ).json()
    b = client.post(
        "/api/campaigns", json={"name": "b", "kind": "other", "region_pack": "global_en"}
    ).json()
    assert client.post(f"/api/campaigns/{a['campaign_id']}/activate").json()["is_active"] is True
    flags = {c["campaign_id"]: c["is_active"] for c in client.get("/api/campaigns").json()}
    assert flags == {a["campaign_id"]: True, b["campaign_id"]: False}
    assert client.post("/api/campaigns/999/activate").status_code == 404
    assert client.get("/api/applications/999").status_code == 404


def test_update_campaign(client: TestClient) -> None:
    a = client.post(
        "/api/campaigns", json={"name": "a", "kind": "other", "region_pack": "global_en"}
    ).json()
    client.post("/api/campaigns", json={"name": "b", "kind": "other", "region_pack": "global_en"})
    r = client.patch(
        f"/api/campaigns/{a['campaign_id']}",
        json={"name": "a2", "kind": "midcareer", "region_pack": "japan", "starts_on": "2031-01-01"},
    )
    assert r.status_code == 200
    assert (r.json()["name"], r.json()["kind"], r.json()["starts_on"]) == (
        "a2",
        "midcareer",
        "2031-01-01",
    )
    # b was created after a, so a is no longer active; update() doesn't touch is_active either way.
    assert r.json()["is_active"] is False
    dup = client.patch(
        f"/api/campaigns/{a['campaign_id']}",
        json={"name": "b", "kind": "other", "region_pack": "global_en"},
    )
    assert dup.status_code == 409
    bad = client.patch(
        f"/api/campaigns/{a['campaign_id']}",
        json={
            "name": "a2",
            "kind": "other",
            "region_pack": "global_en",
            "starts_on": "2031-02-01",
            "ends_on": "2031-01-01",
        },
    )
    assert bad.status_code == 422
    assert (
        client.patch(
            "/api/campaigns/999", json={"name": "x", "kind": "other", "region_pack": "global_en"}
        ).status_code
        == 404
    )


def test_creating_second_campaign_leaves_one_active(client: TestClient) -> None:
    a = client.post(
        "/api/campaigns", json={"name": "one", "kind": "other", "region_pack": "global_en"}
    ).json()
    b = client.post(
        "/api/campaigns", json={"name": "two", "kind": "other", "region_pack": "global_en"}
    ).json()
    campaigns = client.get("/api/campaigns").json()
    assert sum(1 for c in campaigns if c["is_active"]) == 1
    assert next(c for c in campaigns if c["campaign_id"] == b["campaign_id"])["is_active"] is True
    assert next(c for c in campaigns if c["campaign_id"] == a["campaign_id"])["is_active"] is False


def test_patch_application(client: TestClient) -> None:
    campaign_id = client.post(
        "/api/campaigns", json={"name": "patch-camp", "kind": "other", "region_pack": "global_en"}
    ).json()["campaign_id"]
    a = client.post(
        "/api/applications",
        json={"campaign_id": campaign_id, "company_name": "Acme", "track": "other", "role": "SWE"},
    ).json()
    b = client.post(
        "/api/applications",
        json={"campaign_id": campaign_id, "company_name": "Beta", "track": "other", "role": "SWE"},
    ).json()

    r = client.patch(
        f"/api/applications/{a['application_id']}",
        json={
            "company_name": "Acme Renamed",
            "track": "midcareer",
            "role": "SWE",
            "deadline_at": "2031-05-01T00:00:00Z",
        },
    )
    assert r.status_code == 200
    assert r.json()["company"] == "Acme Renamed"
    assert r.json()["track"] == "midcareer"
    assert r.json()["deadline_at"].startswith("2031-05-01")

    got = client.get(f"/api/applications/{a['application_id']}").json()
    assert got["company"] == "Acme Renamed"
    rows = client.get(f"/api/campaigns/{campaign_id}/applications").json()
    assert any(row["company"] == "Acme Renamed" for row in rows)

    conflict = client.patch(
        f"/api/applications/{b['application_id']}",
        json={"company_name": "Acme Renamed", "track": "midcareer", "role": "SWE"},
    )
    assert conflict.status_code == 409
    assert conflict.json()["detail"]["code"] == "application_exists"

    missing = client.patch("/api/applications/999", json={"company_name": "X", "track": "other"})
    assert missing.status_code == 404
    assert missing.json()["detail"]["code"] == "not_found"


def test_delete_application(client: TestClient, settings: Settings) -> None:
    campaign_id = client.post(
        "/api/campaigns", json={"name": "del-camp", "kind": "other", "region_pack": "global_en"}
    ).json()["campaign_id"]
    app_id = client.post(
        "/api/applications",
        json={"campaign_id": campaign_id, "company_name": "Acme", "track": "other"},
    ).json()["application_id"]
    client.post(
        f"/api/applications/{app_id}/events",
        json={"event_type": "interview", "occurred_at": "2031-01-01T00:00:00Z"},
    )
    client.post(
        f"/api/applications/{app_id}/events",
        json={"event_type": "ack", "occurred_at": "2031-01-02T00:00:00Z"},
    )

    r = client.delete(f"/api/applications/{app_id}")
    assert r.status_code == 200
    assert r.json()["deleted_events"] == 2

    assert client.get(f"/api/applications/{app_id}").status_code == 404
    rows = client.get(f"/api/campaigns/{campaign_id}/applications").json()
    assert all(row["application_id"] != app_id for row in rows)

    conn = connect(settings.db_path)
    try:
        count = conn.execute(
            "SELECT COUNT(*) FROM audit_log WHERE action = 'application.delete' AND row_id = ?",
            (app_id,),
        ).fetchone()[0]
    finally:
        conn.close()
    assert count == 1

    assert client.delete(f"/api/applications/{app_id}").status_code == 404


def test_delete_event(client: TestClient) -> None:
    campaign_id = client.post(
        "/api/campaigns", json={"name": "ev-camp", "kind": "other", "region_pack": "global_en"}
    ).json()["campaign_id"]
    app_id = client.post(
        "/api/applications",
        json={"campaign_id": campaign_id, "company_name": "Acme", "track": "other"},
    ).json()["application_id"]
    other_id = client.post(
        "/api/applications",
        json={"campaign_id": campaign_id, "company_name": "Beta", "track": "other"},
    ).json()["application_id"]

    r = client.post(
        f"/api/applications/{app_id}/events",
        json={"event_type": "interview", "occurred_at": "2031-01-01T00:00:00Z"},
    )
    assert r.json()["auto_status"] == "interviewing"
    event_id = r.json()["events"][0]["event_id"]

    assert client.delete(f"/api/applications/{other_id}/events/{event_id}").status_code == 404

    r = client.delete(f"/api/applications/{app_id}/events/{event_id}")
    assert r.status_code == 200
    assert r.json()["auto_status"] == "unrecorded"
    assert r.json()["last_event_at"] is None
    assert r.json()["applied_at"] is None


def test_delete_campaign(client: TestClient) -> None:
    active = client.post(
        "/api/campaigns", json={"name": "del-c1", "kind": "other", "region_pack": "global_en"}
    ).json()
    other = client.post(
        "/api/campaigns", json={"name": "del-c2", "kind": "other", "region_pack": "global_en"}
    ).json()
    client.post(f"/api/campaigns/{active['campaign_id']}/activate")  # make 'active' active again

    app_id = client.post(
        "/api/applications",
        json={"campaign_id": active["campaign_id"], "company_name": "Acme", "track": "other"},
    ).json()["application_id"]
    client.post(
        f"/api/applications/{app_id}/events",
        json={"event_type": "interview", "occurred_at": "2031-01-01T00:00:00Z"},
    )
    client.post(
        "/api/applications",
        json={"campaign_id": active["campaign_id"], "company_name": "Beta", "track": "other"},
    )

    r = client.delete(f"/api/campaigns/{active['campaign_id']}")
    assert r.status_code == 200
    assert r.json() == {"deleted_applications": 2, "deleted_events": 1}

    campaigns = client.get("/api/campaigns").json()
    assert all(c["campaign_id"] != active["campaign_id"] for c in campaigns)
    remaining = next(c for c in campaigns if c["campaign_id"] == other["campaign_id"])
    assert remaining["is_active"] is True

    assert client.delete("/api/campaigns/999").status_code == 404


def test_duplicate_event_conflicts(client: TestClient) -> None:
    campaign_id = client.post(
        "/api/campaigns", json={"name": "dup-ev", "kind": "other", "region_pack": "global_en"}
    ).json()["campaign_id"]
    app_id = client.post(
        "/api/applications",
        json={"campaign_id": campaign_id, "company_name": "Acme", "track": "other"},
    ).json()["application_id"]
    body = {"event_type": "interview", "occurred_at": "2031-01-01T00:00:00Z"}
    assert client.post(f"/api/applications/{app_id}/events", json=body).status_code == 201
    second = client.post(f"/api/applications/{app_id}/events", json=body)
    assert second.status_code == 409
    assert second.json()["detail"]["code"] == "event_exists"


def test_application_input_validation(client: TestClient) -> None:
    campaign_id = client.post(
        "/api/campaigns", json={"name": "val-camp", "kind": "other", "region_pack": "global_en"}
    ).json()["campaign_id"]

    blank = client.post(
        "/api/applications",
        json={"campaign_id": campaign_id, "company_name": "   ", "track": "other"},
    )
    assert blank.status_code == 422

    bad_url = client.post(
        "/api/applications",
        json={
            "campaign_id": campaign_id,
            "company_name": "Acme",
            "track": "other",
            "job_url": "ftp://x",
        },
    )
    assert bad_url.status_code == 422

    r = client.post(
        "/api/applications",
        json={
            "campaign_id": campaign_id,
            "company_name": "Gamma",
            "track": "other",
            "initial_status": "applied",
        },
    )
    assert r.status_code == 201
    assert r.json()["status"] == "applied"
    assert r.json()["user_status"] == "applied"
    assert r.json()["auto_status"] == "unrecorded"


def test_dashboard_windows(client: TestClient) -> None:
    campaign_id = client.post(
        "/api/campaigns", json={"name": "dash-camp", "kind": "other", "region_pack": "global_en"}
    ).json()["campaign_id"]
    now = datetime.now(UTC)

    in_week_id = client.post(
        "/api/applications",
        json={"campaign_id": campaign_id, "company_name": "Acme", "track": "other"},
    ).json()["application_id"]
    client.patch(
        f"/api/applications/{in_week_id}",
        json={
            "company_name": "Acme",
            "track": "other",
            "deadline_at": (now + timedelta(days=2)).isoformat(),
        },
    )

    overdue_id = client.post(
        "/api/applications",
        json={"campaign_id": campaign_id, "company_name": "Beta", "track": "other"},
    ).json()["application_id"]
    client.patch(
        f"/api/applications/{overdue_id}",
        json={
            "company_name": "Beta",
            "track": "other",
            "deadline_at": (now - timedelta(days=1)).isoformat(),
        },
    )

    interview_id = client.post(
        "/api/applications",
        json={"campaign_id": campaign_id, "company_name": "Gamma", "track": "other"},
    ).json()["application_id"]
    client.post(
        f"/api/applications/{interview_id}/events",
        json={"event_type": "interview", "occurred_at": (now + timedelta(days=3)).isoformat()},
    )

    stale_id = client.post(
        "/api/applications",
        json={"campaign_id": campaign_id, "company_name": "Delta", "track": "other"},
    ).json()["application_id"]
    client.patch(
        f"/api/applications/{stale_id}",
        json={
            "company_name": "Delta",
            "track": "other",
            "deadline_at": (now - timedelta(days=20)).isoformat(),
        },
    )

    dash = client.get(f"/api/campaigns/{campaign_id}/dashboard").json()
    by_id = {u["application_id"]: u for u in dash["upcoming"]}
    assert by_id[in_week_id]["overdue"] is False
    assert by_id[overdue_id]["overdue"] is True  # within the 14-day lookback
    assert stale_id not in by_id
    assert [u["application_id"] for u in dash["upcoming"]] == [overdue_id, in_week_id]
    assert dash["interviews_next_7d"] == 1

    tz = ZoneInfo("UTC")  # global_en's default_tz
    local_now = now.astimezone(tz)
    days_to_sunday = 6 - local_now.weekday()
    week_end = (local_now + timedelta(days=days_to_sunday)).replace(
        hour=23, minute=59, second=59, microsecond=999000
    )
    expected = 1 if now + timedelta(days=2) <= week_end else 0
    assert dash["deadlines_this_week"] == expected


def _campaign(client: TestClient, name: str, region_pack: str = "global_en") -> int:
    return client.post(
        "/api/campaigns", json={"name": name, "kind": "other", "region_pack": region_pack}
    ).json()["campaign_id"]


def _application(client: TestClient, campaign_id: int, company: str, **extra: object) -> int:
    return client.post(
        "/api/applications",
        json={"campaign_id": campaign_id, "company_name": company, "track": "other", **extra},
    ).json()["application_id"]


def _audit_count(settings: Settings, action: str, row_id: int | None = None) -> int:
    conn = connect(settings.db_path)
    try:
        sql = "SELECT COUNT(*) FROM audit_log WHERE action = ?"
        params: tuple[object, ...] = (action,)
        if row_id is not None:
            sql += " AND row_id = ?"
            params += (row_id,)
        return int(conn.execute(sql, params).fetchone()[0])
    finally:
        conn.close()


def test_upcoming_emits_one_item_per_in_window_field(client: TestClient) -> None:
    campaign_id = _campaign(client, "per-field")
    now = datetime.now(UTC)
    app_id = _application(client, campaign_id, "Acme")
    client.patch(
        f"/api/applications/{app_id}",
        json={
            "company_name": "Acme",
            "track": "other",
            "deadline_at": (now + timedelta(days=40)).isoformat(),
            "next_action": "call back",
            "next_action_due": (now + timedelta(days=1)).isoformat(),
        },
    )
    upcoming = client.get(f"/api/campaigns/{campaign_id}/dashboard").json()["upcoming"]
    assert [(u["kind"], u["label"]) for u in upcoming] == [("next_action", "call back")]


def test_closed_applications_leave_the_todo_lists(client: TestClient) -> None:
    campaign_id = _campaign(client, "closed")
    now = datetime.now(UTC)
    app_id = _application(client, campaign_id, "Acme")
    client.patch(
        f"/api/applications/{app_id}",
        json={
            "company_name": "Acme",
            "track": "other",
            "deadline_at": (now + timedelta(hours=1)).isoformat(),
            "next_action": "reply",
            "next_action_due": (now + timedelta(hours=2)).isoformat(),
        },
    )
    dash = client.get(f"/api/campaigns/{campaign_id}/dashboard").json()
    assert len(dash["upcoming"]) == 2
    assert dash["deadlines_this_week"] == 1

    client.post(f"/api/applications/{app_id}/status", json={"user_status": "rejected"})
    dash = client.get(f"/api/campaigns/{campaign_id}/dashboard").json()
    assert dash["upcoming"] == []
    assert dash["deadlines_this_week"] == 0


def test_patch_event_rederives_status(client: TestClient) -> None:
    campaign_id = _campaign(client, "patch-ev")
    app_id = _application(client, campaign_id, "Acme")
    other_id = _application(client, campaign_id, "Beta")
    r = client.post(
        f"/api/applications/{app_id}/events",
        json={"event_type": "interview", "occurred_at": "2031-01-01T00:00:00Z"},
    )
    event_id = r.json()["events"][0]["event_id"]
    client.post(
        f"/api/applications/{app_id}/events",
        json={"event_type": "ack", "occurred_at": "2031-01-05T00:00:00Z"},
    )

    r = client.patch(
        f"/api/applications/{app_id}/events/{event_id}",
        json={"event_type": "rejection", "occurred_at": "2031-02-01T00:00:00Z", "summary": "no"},
    )
    assert r.status_code == 200
    assert r.json()["auto_status"] == "rejected"
    assert r.json()["last_event_at"].startswith("2031-02-01")
    assert r.json()["last_event_type"] == "rejection"
    edited = next(e for e in r.json()["events"] if e["event_id"] == event_id)
    assert (edited["event_type"], edited["summary"]) == ("rejection", "no")

    collision = client.patch(
        f"/api/applications/{app_id}/events/{event_id}",
        json={"event_type": "ack", "occurred_at": "2031-01-05T00:00:00Z"},
    )
    assert collision.status_code == 409
    assert collision.json()["detail"]["code"] == "event_exists"

    wrong_owner = client.patch(
        f"/api/applications/{other_id}/events/{event_id}",
        json={"event_type": "ack", "occurred_at": "2031-03-01T00:00:00Z"},
    )
    assert wrong_owner.status_code == 404

    naive = client.patch(
        f"/api/applications/{app_id}/events/{event_id}",
        json={"event_type": "ack", "occurred_at": "2031-03-01T00:00:00"},
    )
    assert naive.status_code == 422


def test_naive_datetimes_are_rejected(client: TestClient) -> None:
    campaign_id = _campaign(client, "naive")
    app_id = _application(client, campaign_id, "Acme")
    r = client.post(
        f"/api/applications/{app_id}/events",
        json={"event_type": "ack", "occurred_at": "2031-01-01T00:00:00"},
    )
    assert r.status_code == 422
    r = client.patch(
        f"/api/applications/{app_id}",
        json={"company_name": "Acme", "track": "other", "deadline_at": "2031-01-01T00:00:00"},
    )
    assert r.status_code == 422


def test_clear_next_action(client: TestClient, settings: Settings) -> None:
    campaign_id = _campaign(client, "next")
    app_id = _application(client, campaign_id, "Acme")
    client.patch(
        f"/api/applications/{app_id}",
        json={
            "company_name": "Acme",
            "track": "other",
            "next_action": "call",
            "next_action_due": "2031-01-01T00:00:00Z",
        },
    )
    r = client.delete(f"/api/applications/{app_id}/next-action")
    assert r.status_code == 200
    assert (r.json()["next_action"], r.json()["next_action_due"]) == (None, None)
    assert _audit_count(settings, "application.update", app_id) == 2  # patch + clear
    assert client.delete("/api/applications/999/next-action").status_code == 404


def test_progress_event_clears_next_action(client: TestClient) -> None:
    campaign_id = _campaign(client, "progress")
    app_id = _application(client, campaign_id, "Acme")
    client.patch(
        f"/api/applications/{app_id}",
        json={
            "company_name": "Acme",
            "track": "other",
            "next_action": "wait",
            "next_action_due": "2031-01-01T00:00:00Z",
        },
    )
    r = client.post(
        f"/api/applications/{app_id}/events",
        json={"event_type": "note", "occurred_at": "2031-01-02T00:00:00Z"},
    )
    assert r.json()["next_action"] == "wait"  # no status change, nothing cleared
    r = client.post(
        f"/api/applications/{app_id}/events",
        json={"event_type": "interview", "occurred_at": "2031-01-03T00:00:00Z"},
    )
    assert r.json()["auto_status"] == "interviewing"
    assert (r.json()["next_action"], r.json()["next_action_due"]) == (None, None)


def test_patch_renames_company_display_name(client: TestClient, settings: Settings) -> None:
    campaign_id = _campaign(client, "rename")
    app_id = _application(client, campaign_id, "acme robotics")
    r = client.patch(
        f"/api/applications/{app_id}",
        json={"company_name": "ACME Robotics", "track": "other"},
    )
    assert r.json()["company"] == "ACME Robotics"
    assert client.get(f"/api/applications/{app_id}").json()["company"] == "ACME Robotics"
    assert _audit_count(settings, "company.rename") == 1
    conn = connect(settings.db_path)
    try:
        assert conn.execute("SELECT COUNT(*) FROM company").fetchone()[0] == 1
    finally:
        conn.close()


def test_patch_conflict_reports_existing_id(client: TestClient) -> None:
    campaign_id = _campaign(client, "conflict")
    a = _application(client, campaign_id, "Acme", role="SWE")
    b = _application(client, campaign_id, "Beta", role="SWE")
    r = client.patch(
        f"/api/applications/{b}", json={"company_name": "Acme", "track": "other", "role": "SWE"}
    )
    assert r.status_code == 409
    assert r.json()["detail"] == {"code": "application_exists", "existing_application_id": a}


def test_duplicate_event_writes_nothing(client: TestClient, settings: Settings) -> None:
    campaign_id = _campaign(client, "dup-noop")
    app_id = _application(client, campaign_id, "Acme")
    body = {"event_type": "interview", "occurred_at": "2031-01-01T00:00:00Z"}
    first = client.post(f"/api/applications/{app_id}/events", json=body).json()
    conn = connect(settings.db_path)
    try:
        audits_before = conn.execute("SELECT COUNT(*) FROM audit_log").fetchone()[0]
        updated_before = conn.execute(
            "SELECT updated_at FROM application WHERE application_id = ?", (app_id,)
        ).fetchone()[0]
        assert client.post(f"/api/applications/{app_id}/events", json=body).status_code == 409
        assert conn.execute("SELECT COUNT(*) FROM audit_log").fetchone()[0] == audits_before
        updated_after = conn.execute(
            "SELECT updated_at FROM application WHERE application_id = ?", (app_id,)
        ).fetchone()[0]
    finally:
        conn.close()
    assert updated_after == updated_before
    assert first["auto_status"] == "interviewing"


def test_pipeline_latest_event_ignores_silent_types(client: TestClient) -> None:
    campaign_id = _campaign(client, "silent")
    app_id = _application(client, campaign_id, "Acme")
    client.post(
        f"/api/applications/{app_id}/events",
        json={"event_type": "ack", "occurred_at": "2031-01-01T00:00:00Z"},
    )
    r = client.post(
        f"/api/applications/{app_id}/events",
        json={"event_type": "pass", "occurred_at": "2031-01-05T00:00:00Z"},
    )
    assert r.json()["last_event_at"].startswith("2031-01-05")
    r = client.post(
        f"/api/applications/{app_id}/events",
        json={"event_type": "note", "occurred_at": "2031-01-09T00:00:00Z"},
    )
    assert r.json()["last_event_type"] == "pass"
    assert r.json()["last_event_at"].startswith("2031-01-05")
    rows = client.get(f"/api/campaigns/{campaign_id}/applications").json()
    assert rows[0]["last_event_type"] == "pass"


def test_campaign_tz_follows_its_own_pack(client: TestClient) -> None:
    jp = _campaign(client, "jp", region_pack="japan")
    en = _campaign(client, "en")  # newest campaign becomes active
    campaigns = {c["campaign_id"]: c for c in client.get("/api/campaigns").json()}
    assert campaigns[jp]["tz"] == "Asia/Tokyo"
    assert campaigns[en]["tz"] == "UTC"
    assert campaigns[en]["is_active"] is True
    assert client.get("/api/meta").json()["tz"] == "UTC"

    now = datetime.now(UTC)
    app_id = _application(client, jp, "Acme")
    client.post(
        f"/api/applications/{app_id}/events",
        json={"event_type": "interview", "occurred_at": (now + timedelta(days=1)).isoformat()},
    )
    dash = client.get(f"/api/campaigns/{jp}/dashboard")
    assert dash.status_code == 200
    assert dash.json()["interviews_next_7d"] == 1


def test_unknown_region_pack_in_db_does_not_break_reads(
    client: TestClient, settings: Settings
) -> None:
    conn = connect(settings.db_path)
    try:
        conn.execute(
            "INSERT INTO campaign(name, kind, region_pack, flags_json, is_active)"
            " VALUES ('gone', 'other', 'gone', '{}', 1)"
        )
        campaign_id = conn.execute("SELECT campaign_id FROM campaign").fetchone()[0]
    finally:
        conn.close()
    assert client.get("/api/meta").json()["tz"] == "UTC"
    assert client.get("/api/campaigns").json()[0]["tz"] == "UTC"
    assert client.get(f"/api/campaigns/{campaign_id}/dashboard").status_code == 200


def test_untrusted_host_is_rejected(settings: Settings, tmp_path: Path) -> None:
    app = create_app(settings, dist_dir=tmp_path / "no-dist")
    with TestClient(app, base_url="http://evil.example") as c:
        assert c.get("/api/meta").status_code == 400
    with TestClient(app, base_url="http://localhost") as c:
        assert c.get("/api/meta").status_code == 200


def test_non_loopback_bind_without_auth_is_refused(tmp_path: Path) -> None:
    with pytest.raises(RuntimeError, match=r"127\.0\.0\.1"):
        create_app(Settings(host="0.0.0.0"), dist_dir=tmp_path / "no-dist")
    with pytest.raises(RuntimeError):
        create_app(Settings(), dist_dir=tmp_path / "no-dist", bind_host="0.0.0.0")
