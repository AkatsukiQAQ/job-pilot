from __future__ import annotations

from collections.abc import Iterator
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from jobpilot.settings import Settings
from jobpilot.web.app import create_app


@pytest.fixture
def client(settings: Settings, tmp_path: Path) -> Iterator[TestClient]:
    with TestClient(create_app(settings, dist_dir=tmp_path / "no-dist")) as c:
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
    assert r.json()["is_active"] is True  # untouched
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
