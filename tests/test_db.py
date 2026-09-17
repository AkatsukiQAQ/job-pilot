from __future__ import annotations

import json
import re
import sqlite3
from datetime import UTC, date, datetime, timedelta
from pathlib import Path

import pytest
from typer.testing import CliRunner

from jobpilot.cli import app
from jobpilot.domain import (
    AliasKind,
    ApplicationCreate,
    ApplicationStatus,
    CampaignCreate,
    CampaignKind,
    ClassifyMethod,
    CompanyCreate,
    EmailCategory,
    EmailClassificationCreate,
    EmailMessageCreate,
    EventCreate,
    EventSource,
    EventType,
    Origin,
    PiiKind,
    ReviewReason,
    SourceHealth,
    StatusSetBy,
    Track,
)
from jobpilot.store.db import (
    MigrationChecksumMismatch,
    connect,
    current_version,
    default_migrations_dir,
    has_fts5,
    latest_available_version,
    list_migrations,
    run_migrations,
    transaction,
)
from jobpilot.store.repo import (
    ApplicationRepo,
    AutoUpdate,
    CampaignRepo,
    ClassificationRepo,
    CompanyRepo,
    EmailAccountRepo,
    EmailRepo,
    EventRepo,
    PiiRepo,
    SourceStateRepo,
)

_TRIGGER_RE = re.compile(r"CREATE TRIGGER.*?END;", re.S)


def _init_sql() -> str:
    return next(s for v, _, s in list_migrations(default_migrations_dir()) if v == 1)


def _table_block(sql: str, table: str) -> str:
    m = re.search(rf"CREATE TABLE {table} \((.*?)\n\);", sql, re.S)
    assert m is not None, table
    return m.group(1)


def _check_values(sql: str, table: str, column: str) -> set[str]:
    block = _table_block(sql, table)
    m = re.search(rf"\b{column}\s+TEXT.*?\b{column} IN\s*\(([^)]*)\)", block, re.S)
    assert m is not None, f"{table}.{column}"
    return {v.strip().strip("'") for v in m.group(1).split(",")}


# ---------------------------------------------------------------------------- schema


def test_pragmas(conn: sqlite3.Connection) -> None:
    assert conn.execute("PRAGMA journal_mode").fetchone()[0] == "wal"
    assert conn.execute("PRAGMA foreign_keys").fetchone()[0] == 1
    assert has_fts5(conn)


def test_migrations_idempotent_and_unseeded(conn: sqlite3.Connection) -> None:
    assert current_version(conn) == latest_available_version() >= 1
    assert run_migrations(conn) == []
    for table in ("campaign", "audit_log", "company", "application", "email_message"):
        assert conn.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0] == 0, table  # D16


def test_checksum_guard(tmp_path: Path) -> None:
    mig = tmp_path / "mig"
    mig.mkdir()
    f = mig / "0001_init.sql"
    f.write_text("CREATE TABLE t (x INTEGER);\n", encoding="utf-8")
    c = connect(tmp_path / "x.db")
    assert run_migrations(c, mig) == ["0001_init"]
    f.write_text("CREATE TABLE t (x INTEGER, y INTEGER);\n", encoding="utf-8")
    with pytest.raises(MigrationChecksumMismatch):
        run_migrations(c, mig)
    c.close()


def test_migration_files_have_no_transaction_control_or_seed_rows() -> None:
    for _, name, sql in list_migrations(default_migrations_dir()):
        body = _TRIGGER_RE.sub("", sql)  # trigger bodies legitimately contain INSERT
        assert not re.search(r"^\s*(BEGIN|COMMIT)\b", body, re.I | re.M), name
        assert not re.search(r"^\s*INSERT\b", body, re.I | re.M), f"{name}: seed rows forbidden"


@pytest.mark.parametrize(
    ("table", "column", "enum"),
    [
        ("campaign", "kind", CampaignKind),
        ("company_alias", "kind", AliasKind),
        ("application", "track", Track),
        ("application", "auto_status", ApplicationStatus),
        ("application", "user_status", ApplicationStatus),
        ("application", "status_set_by", StatusSetBy),
        ("application", "origin", Origin),
        ("application_event", "event_type", EventType),
        ("application_event", "source", EventSource),
        ("email_classification", "category", EmailCategory),
        ("email_classification", "event_type", EventType),
        ("email_classification", "method", ClassifyMethod),
        ("email_classification", "review_reason", ReviewReason),
        ("pii_aliases", "kind", PiiKind),
        ("source_state", "status", SourceHealth),
    ],
)
def test_check_lists_match_enums(table: str, column: str, enum: type) -> None:
    values = _check_values(_init_sql(), table, column)
    assert values == {e.value for e in enum}  # type: ignore[attr-defined]


def test_connect_readonly_rejects_writes(conn: sqlite3.Connection, tmp_path: Path) -> None:
    ro = connect(tmp_path / "data" / "jobpilot.db", readonly=True)
    assert ro.execute("SELECT COUNT(*) FROM campaign").fetchone()[0] == 0
    with pytest.raises(sqlite3.OperationalError):
        ro.execute(
            "INSERT INTO campaign(name, kind, region_pack) VALUES ('x', 'other', 'global_en')"
        )
    ro.close()


def test_savepoint_nesting_rolls_back_only_inner(conn: sqlite3.Connection) -> None:
    with transaction(conn):
        conn.execute(
            "INSERT INTO campaign(name, kind, region_pack) VALUES ('outer', 'other', 'global_en')"
        )
        with pytest.raises(RuntimeError), transaction(conn):
            conn.execute(
                "INSERT INTO campaign(name, kind, region_pack) VALUES ('inner', 'other', 'global_en')"
            )
            raise RuntimeError("boom")
        assert conn.in_transaction
    names = [r[0] for r in conn.execute("SELECT name FROM campaign ORDER BY name")]
    assert names == ["outer"]


# ---------------------------------------------------------------------------- repos


def _campaign(conn: sqlite3.Connection) -> int:
    return (
        CampaignRepo(conn)
        .add(CampaignCreate(name="demo", kind=CampaignKind.OTHER, region_pack="global_en"))
        .campaign_id
    )


def _company(
    conn: sqlite3.Connection, name: str = "Acme Robotics", norm: str = "acmerobotics"
) -> int:
    return (
        CompanyRepo(conn)
        .add(CompanyCreate(name=name, name_norm=norm, domain="acme.example"))
        .company_id
    )


def test_repo_campaign_add_list_and_audit(conn: sqlite3.Connection) -> None:
    repo = CampaignRepo(conn)
    created = repo.add(
        CampaignCreate(
            name="demo",
            kind=CampaignKind.OTHER,
            region_pack="global_en",
            starts_on=date(2030, 1, 1),
            ends_on=date(2030, 12, 31),
            flags={"sample_flag": True},
        )
    )
    assert created.campaign_id == 1
    assert created.flags == {"sample_flag": True}
    assert created.created_at.tzinfo is not None
    assert [c.name for c in repo.list()] == ["demo"]
    assert repo.get_active() is not None
    assert repo.count() == 1

    audit = conn.execute(
        "SELECT actor, action, table_name, row_id, before_json, after_json, source FROM audit_log"
    ).fetchall()
    assert len(audit) == 1
    a = audit[0]
    assert (a["actor"], a["action"], a["table_name"], a["row_id"]) == (
        "user",
        "campaign.add",
        "campaign",
        1,
    )
    assert a["before_json"] is None
    assert json.loads(a["after_json"])["name"] == "demo"
    assert a["source"] == "cli"

    with pytest.raises(sqlite3.IntegrityError):
        repo.add(CampaignCreate(name="demo", kind=CampaignKind.OTHER, region_pack="global_en"))
    assert repo.count() == 1  # rolled back


def test_company_alias_and_current_employer(conn: sqlite3.Connection) -> None:
    repo = CompanyRepo(conn)
    cid = _company(conn)
    assert repo.add_alias(AliasKind.DOMAIN, "acme.example", cid, source="sender_domain") is True
    assert repo.add_alias(AliasKind.DOMAIN, "acme.example", cid, source="sender_domain") is False
    assert repo.find_alias(AliasKind.DOMAIN, "acme.example") is not None
    assert repo.find_alias(AliasKind.NAME, "nope") is None
    assert repo.current_employer_domains() == set()
    repo.set_current_employer(cid, True)
    assert repo.current_employer_domains() == {"acme.example"}
    actions = [r[0] for r in conn.execute("SELECT action FROM audit_log ORDER BY id")]
    assert actions == ["company.add", "company.set_current_employer"]


def test_application_status_precedence_and_audit(conn: sqlite3.Connection) -> None:
    camp = _campaign(conn)
    cid = _company(conn)
    apps = ApplicationRepo(conn)
    created = apps.add(
        ApplicationCreate(
            campaign_id=camp, company_id=cid, track=Track.OTHER, role="MLE", role_norm="mle"
        )
    )
    assert created.effective_status == ApplicationStatus.UNRECORDED  # generated column present
    assert created.origin == Origin.AUTO

    # same natural key -> UNIQUE violation
    with pytest.raises(sqlite3.IntegrityError):
        apps.add(
            ApplicationCreate(campaign_id=camp, company_id=cid, track=Track.OTHER, role_norm="mle")
        )
    assert apps.find_natural(camp, cid, "other", "mle") is not None

    now = datetime(2030, 3, 1, tzinfo=UTC)
    updated = apps.update_auto(
        created.application_id,
        AutoUpdate(
            auto_status=ApplicationStatus.INTERVIEWING,
            status_set_by=StatusSetBy.RULE,
            last_event_at=now,
        ),
    )
    assert updated.effective_status == ApplicationStatus.INTERVIEWING

    overridden = apps.set_user_status(created.application_id, ApplicationStatus.REJECTED)
    assert overridden.effective_status == ApplicationStatus.REJECTED
    assert overridden.status_set_by == StatusSetBy.USER

    # auto drift never touches the user's choice
    drifted = apps.update_auto(
        created.application_id, AutoUpdate(auto_status=ApplicationStatus.OFFER)
    )
    assert drifted.auto_status == ApplicationStatus.OFFER
    assert drifted.user_status == ApplicationStatus.REJECTED
    assert drifted.effective_status == ApplicationStatus.REJECTED

    rows = conn.execute(
        "SELECT action, before_json, after_json FROM audit_log WHERE table_name = 'application' ORDER BY id"
    ).fetchall()
    assert [r["action"] for r in rows] == [
        "application.add",
        "application.auto_update",
        "application.set_user_status",
        "application.auto_update",
    ]
    assert json.loads(rows[2]["before_json"])["user_status"] is None
    assert json.loads(rows[2]["after_json"])["user_status"] == "rejected"

    # excluded_reason only allowed when the effective status is unsuitable
    with pytest.raises(sqlite3.IntegrityError):
        apps.set_user_status(created.application_id, ApplicationStatus.APPLIED, excluded_reason="x")
    ok = apps.set_user_status(
        created.application_id, ApplicationStatus.UNSUITABLE, excluded_reason="requires internship"
    )
    assert ok.excluded_reason == "requires internship"


def test_event_repo_idempotent(conn: sqlite3.Connection) -> None:
    camp = _campaign(conn)
    cid = _company(conn)
    app_id = (
        ApplicationRepo(conn)
        .add(ApplicationCreate(campaign_id=camp, company_id=cid, track=Track.OTHER))
        .application_id
    )
    events = EventRepo(conn)
    new = EventCreate(
        application_id=app_id,
        event_type=EventType.ACK,
        occurred_at=datetime(2030, 3, 1, 9, 0, tzinfo=UTC),
        source=EventSource.GMAIL,
        source_ref="gmail:1:abc",
        confidence=0.9,
        summary="Application received",
    )
    ev1, inserted1 = events.add_idempotent(new)
    ev2, inserted2 = events.add_idempotent(new)
    assert inserted1 is True and inserted2 is False
    assert ev1.event_id == ev2.event_id
    assert len(events.list_for(app_id)) == 1
    assert (
        conn.execute(
            "SELECT COUNT(*) FROM audit_log WHERE table_name = 'application_event'"
        ).fetchone()[0]
        == 1
    )
    assert events.has_event_since(app_id, "ack", datetime(2030, 1, 1, tzinfo=UTC))
    assert not events.has_event_since(app_id, "ack", datetime(2030, 4, 1, tzinfo=UTC))


def _message(
    account_id: int, gmail_id: str, *, fmt: str = "metadata", body: str | None = None
) -> EmailMessageCreate:
    return EmailMessageCreate(
        account_id=account_id,
        gmail_id=gmail_id,
        thread_id="t-" + gmail_id,
        internal_date_ms=1_900_000_000_000,
        raw_format=fmt,  # type: ignore[arg-type]
        from_addr="recruit@acme.example",
        from_domain="acme.example",
        from_name="Acme Recruiting",
        from_name_public="Acme Recruiting",
        subject="Interview invitation",
        subject_public="Interview invitation",
        snippet="We would like to invite you",
        snippet_public="We would like to invite you",
        body_text=body,
        has_ics=None if body is None else False,
    )


def test_email_repo_upsert_upgrades_metadata_to_full(conn: sqlite3.Connection) -> None:
    acct = EmailAccountRepo(conn).add("mailbox@example.com", token_ref="acct-0123456789abcdef")
    repo = EmailRepo(conn)
    msg_id, is_new = repo.upsert(_message(acct.account_id, "g1"))
    assert is_new is True
    again, is_new2 = repo.upsert(
        _message(acct.account_id, "g1", fmt="full", body="Dear candidate, ...")
    )
    assert again == msg_id and is_new2 is False
    stored = repo.get(msg_id)
    assert stored is not None
    assert stored.raw_format == "full" and stored.body_text == "Dear candidate, ..."
    # a later metadata-only upsert must not erase the body
    repo.upsert(_message(acct.account_id, "g1"))
    stored2 = repo.get(msg_id)
    assert stored2 is not None and stored2.body_text == "Dear candidate, ..."
    assert repo.count(acct.account_id) == 1
    assert repo.known_gmail_ids(acct.account_id, ["g1", "g2"]) == {"g1"}
    assert repo.newest_internal_date_ms(acct.account_id) == 1_900_000_000_000
    report = repo.senders_report(top=5, skipped_labels=["CATEGORY_PROMOTIONS"])
    assert report.total == 1
    assert report.by_domain[0].key == "acme.example"
    assert report.skipped_label_counts == {"CATEGORY_PROMOTIONS": 0}


def test_classification_repo_upsert_and_cache(conn: sqlite3.Connection) -> None:
    acct = EmailAccountRepo(conn).add("mailbox@example.com", token_ref="acct-0123456789abcdef")
    msg_id, _ = EmailRepo(conn).upsert(_message(acct.account_id, "g1"))
    repo = ClassificationRepo(conn)
    first = repo.upsert(
        EmailClassificationCreate(
            msg_id=msg_id,
            is_job_related=True,
            category=EmailCategory.INTERVIEW_CONFIRMED,
            confidence=0.8,
            method=ClassifyMethod.LLM,
            prompt_version="v1",
            input_hash="h1",
            scores={"interview_confirmed": 2.0},
            needs_review=True,
            review_reason=ReviewReason.UNKNOWN_COMPANY,
            candidates=[{"company_id": 1, "name": "Acme", "score": 0.85}],
        )
    )
    assert first.scores == {"interview_confirmed": 2.0}
    assert first.candidates and first.candidates[0]["name"] == "Acme"
    assert repo.cache_lookup(msg_id, prompt_version="v1", input_hash="h1") is not None
    assert repo.cache_lookup(msg_id, prompt_version="v2", input_hash="h1") is None
    assert repo.count_needs_review() == 1
    second = repo.upsert(
        EmailClassificationCreate(
            msg_id=msg_id,
            is_job_related=False,
            category=EmailCategory.OTHER,
            confidence=1.0,
            method=ClassifyMethod.RULE,
        )
    )
    assert second.category == EmailCategory.OTHER
    assert conn.execute("SELECT COUNT(*) FROM email_classification").fetchone()[0] == 1
    assert list(EmailRepo(conn).iter_unclassified()) == []


def test_pii_repo_aliases_are_stable(conn: sqlite3.Connection) -> None:
    repo = PiiRepo(conn)
    a = repo.alias_for(PiiKind.EMAIL, "hash-1")
    b = repo.alias_for(PiiKind.EMAIL, "hash-2")
    assert a == "[email:1]" and b == "[email:2]"
    assert repo.alias_for(PiiKind.EMAIL, "hash-1") == a
    assert repo.alias_for(PiiKind.PHONE, "hash-3") == "[phone:1]"
    assert repo.count() == 3


def test_source_state_backoff_and_transitions(conn: sqlite3.Connection) -> None:
    repo = SourceStateRepo(conn)
    t0 = datetime(2030, 1, 1, tzinfo=UTC)
    s1 = repo.mark_failure("gmail:1", transport="t", error_label="HttpError 500", now=t0)
    s2 = repo.mark_failure("gmail:1", transport="t", error_label="HttpError 500", now=t0)
    s3 = repo.mark_failure("gmail:1", transport="t", error_label="HttpError 500", now=t0)
    assert (s1.status, s2.status, s3.status) == (
        SourceHealth.DEGRADED,
        SourceHealth.DEGRADED,
        SourceHealth.UNAVAILABLE,
    )
    assert s1.next_retry_at is not None and s3.next_retry_at is not None
    assert s3.next_retry_at > s1.next_retry_at
    assert s3.failure_streak == 3
    ok = repo.mark_success(
        "gmail:1", transport="t", cursor="12345", data_as_of=t0 + timedelta(days=1)
    )
    assert ok.status == SourceHealth.HEALTHY and ok.failure_streak == 0 and ok.cursor == "12345"
    auth = repo.mark_failure(
        "gmail:1", transport="t", error_label="invalid_grant", auth_required=True, now=t0
    )
    assert auth.status == SourceHealth.AUTH_REQUIRED
    transitions = [
        (
            json.loads(r["before_json"])["status"] if r["before_json"] else None,
            json.loads(r["after_json"])["status"],
        )
        for r in conn.execute(
            "SELECT before_json, after_json FROM audit_log WHERE table_name = 'source_state' ORDER BY id"
        )
    ]
    assert transitions == [
        (None, "degraded"),
        ("degraded", "unavailable"),
        ("unavailable", "healthy"),
        ("healthy", "auth_required"),
    ]


# ---------------------------------------------------------------------------- CLI


def test_cli_campaign_add_and_list_json(runner: CliRunner) -> None:
    result = runner.invoke(
        app,
        [
            "campaign",
            "add",
            "--name",
            "demo",
            "--kind",
            "other",
            "--region-pack",
            "global_en",
            "--starts",
            "2030-01-01",
            "--flag",
            "sample_flag",
            "--flag",
            "budget=3",
        ],
    )
    assert result.exit_code == 0, result.output

    result = runner.invoke(app, ["campaign", "list", "--json"])
    assert result.exit_code == 0, result.output
    rows = json.loads(result.output)
    assert len(rows) == 1
    assert rows[0]["name"] == "demo"
    assert rows[0]["kind"] == "other"
    assert rows[0]["flags"] == {"sample_flag": True, "budget": 3}

    result = runner.invoke(app, ["campaign", "list"])
    assert result.exit_code == 0, result.output
    assert "demo" in result.output


def test_cli_rejects_unknown_region_pack_and_bad_date(runner: CliRunner) -> None:
    result = runner.invoke(
        app, ["campaign", "add", "--name", "x", "--kind", "other", "--region-pack", "mars"]
    )
    assert result.exit_code != 0
    assert "unknown region pack" in result.output

    result = runner.invoke(
        app,
        [
            "campaign",
            "add",
            "--name",
            "x",
            "--kind",
            "other",
            "--region-pack",
            "global_en",
            "--starts",
            "soon",
        ],
    )
    assert result.exit_code != 0
    assert "ISO date" in result.output


def test_cli_duplicate_name_exits_1(runner: CliRunner) -> None:
    args = ["campaign", "add", "--name", "dup", "--kind", "other", "--region-pack", "global_en"]
    assert runner.invoke(app, args).exit_code == 0
    result = runner.invoke(app, args)
    assert result.exit_code == 1
    assert "already exists" in result.output


def test_init_bootstraps_campaign_from_env(
    runner: CliRunner, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    monkeypatch.setenv("JOBPILOT_CAMPAIGN_NAME", "demo")
    monkeypatch.setenv("JOBPILOT_CAMPAIGN_KIND", "other")
    monkeypatch.setenv("JOBPILOT_CAMPAIGN_REGION_PACK", "global_en")
    result = runner.invoke(app, ["init"])
    assert result.exit_code == 0, result.output
    assert "created campaign #1" in result.output
    c = sqlite3.connect(tmp_path / "data" / "jobpilot.db")
    assert c.execute("SELECT COUNT(*) FROM campaign").fetchone()[0] == 1
    assert c.execute("SELECT source FROM audit_log").fetchone()[0] == "init"
    c.close()
    result = runner.invoke(app, ["init"])
    assert result.exit_code == 0, result.output
    assert "created campaign" not in result.output


def test_doctor_after_init_reports_region_tz(runner: CliRunner) -> None:
    assert (
        runner.invoke(
            app, ["campaign", "add", "--name", "demo", "--kind", "other", "--region-pack", "japan"]
        ).exit_code
        == 0
    )
    result = runner.invoke(app, ["doctor"])
    assert result.exit_code == 0, result.output
    assert "region pack japan" in result.output
