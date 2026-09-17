from __future__ import annotations

import json
import re
import sqlite3
from datetime import date
from pathlib import Path

import pytest
from typer.testing import CliRunner

from jobpilot.cli import app
from jobpilot.domain import CampaignCreate, CampaignKind
from jobpilot.store.db import (
    MigrationChecksumMismatch,
    connect,
    current_version,
    default_migrations_dir,
    has_fts5,
    latest_available_version,
    list_migrations,
    run_migrations,
)
from jobpilot.store.repo import CampaignRepo


def test_pragmas(conn: sqlite3.Connection) -> None:
    assert conn.execute("PRAGMA journal_mode").fetchone()[0] == "wal"
    assert conn.execute("PRAGMA foreign_keys").fetchone()[0] == 1
    assert has_fts5(conn)


def test_migrations_idempotent_and_unseeded(conn: sqlite3.Connection) -> None:
    assert current_version(conn) == latest_available_version() >= 1
    assert run_migrations(conn) == []
    assert conn.execute("SELECT COUNT(*) FROM campaign").fetchone()[0] == 0  # D16
    assert conn.execute("SELECT COUNT(*) FROM audit_log").fetchone()[0] == 0


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


def test_migration_files_have_no_transaction_control() -> None:
    for _, name, sql in list_migrations(default_migrations_dir()):
        assert not re.search(r"^\s*(BEGIN|COMMIT)\b", sql, re.I | re.M), name
        assert not re.search(r"^\s*INSERT\b", sql, re.I | re.M), f"{name}: seed rows forbidden"


def test_kind_check_matches_enum() -> None:
    sql = next(s for v, _, s in list_migrations(default_migrations_dir()) if v == 1)
    m = re.search(r"kind\s+TEXT\s+NOT NULL\s+CHECK\s*\(kind IN \(([^)]*)\)\)", sql)
    assert m is not None
    values = {v.strip().strip("'") for v in m.group(1).split(",")}
    assert values == {k.value for k in CampaignKind}


def test_repo_add_list_and_audit(conn: sqlite3.Connection) -> None:
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

    rows = repo.list()
    assert [c.name for c in rows] == ["demo"]
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
    # idempotent
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
