"""`jobpilot auth google` end to end with the consent flow and Gmail API replaced by fakes."""

from __future__ import annotations

import json
import sqlite3
from pathlib import Path
from typing import Any

import pytest
from typer.testing import CliRunner

import jobpilot.cli as cli
from jobpilot.connectors.gmail import auth as gmail_auth
from jobpilot.connectors.gmail import readonly_http as gmail_http
from jobpilot.connectors.gmail.auth import get_token_ref
from tests.fakes.gmail import SCOPES, FakeGmailService, make_credentials


class MemStore:
    name = "mem"

    def __init__(self) -> None:
        self.data: dict[str, str] = {}

    def _k(self, slot: str, q: str | None) -> str:
        return f"{slot}__{q}" if q else slot

    def get(self, slot: str, *, qualifier: str | None = None) -> str | None:
        return self.data.get(self._k(slot, qualifier))

    def set(self, slot: str, value: str, *, qualifier: str | None = None) -> None:
        self.data[self._k(slot, qualifier)] = value

    def delete(self, slot: str, *, qualifier: str | None = None) -> bool:
        return self.data.pop(self._k(slot, qualifier), None) is not None


@pytest.fixture
def mem_store(monkeypatch: pytest.MonkeyPatch) -> MemStore:
    store = MemStore()
    monkeypatch.setattr(cli, "build_secret_store", lambda settings: store)
    return store


@pytest.fixture
def client_secret(tmp_path: Path) -> Path:
    p = tmp_path / "data" / "secrets" / "client_secret.json"
    p.parent.mkdir(parents=True)
    p.write_text(
        json.dumps(
            {
                "installed": {
                    "client_id": "client-id.apps.googleusercontent.test",
                    "client_secret": "client-secret",
                    "auth_uri": "https://accounts.google.com/o/oauth2/auth",
                    "token_uri": "https://oauth2.googleapis.com/token",
                    "redirect_uris": ["http://localhost"],
                }
            }
        ),
        encoding="utf-8",
    )
    return p


def _wire_fakes(
    monkeypatch: pytest.MonkeyPatch,
    *,
    mailbox: str,
    granted: list[str] | None = None,
    consent_kwargs: dict[str, Any] | None = None,
) -> None:
    def fake_consent(client_config: dict[str, Any], **kwargs: Any) -> Any:
        if consent_kwargs is not None:
            consent_kwargs.update(kwargs)
        creds = make_credentials(granted=granted)
        gmail_auth.get_checked_scopes(creds, require_all=True)
        return creds

    monkeypatch.setattr(gmail_auth, "fetch_consent", fake_consent)
    monkeypatch.setattr(
        gmail_auth, "fetch_tokeninfo", lambda http, creds: {"scope": " ".join(SCOPES)}
    )
    monkeypatch.setattr(
        gmail_http,
        "get_gmail_service",
        lambda http: FakeGmailService(profile={"emailAddress": mailbox, "historyId": "777"}),
    )


def test_auth_google_stores_token_and_account(
    runner: CliRunner,
    monkeypatch: pytest.MonkeyPatch,
    mem_store: MemStore,
    client_secret: Path,
    tmp_path: Path,
) -> None:
    kwargs: dict[str, Any] = {}
    _wire_fakes(monkeypatch, mailbox="Mailbox@Example.com", consent_kwargs=kwargs)
    result = runner.invoke(
        cli.app,
        ["auth", "google", "--login-hint", "mailbox@example.com", "--account-label", "main"],
    )
    assert result.exit_code == 0, result.output
    assert "authorized mailbox@example.com as account #1" in result.output
    assert kwargs["login_hint"] == "mailbox@example.com"
    assert kwargs["host"] == "127.0.0.1"

    ref = get_token_ref("mailbox@example.com")
    blob = mem_store.data[f"google_token__{ref}"]
    info = json.loads(blob)
    assert info["account"] == "mailbox@example.com"
    assert set(info["scopes"]) == set(SCOPES)
    assert "example" not in ref

    c = sqlite3.connect(tmp_path / "data" / "jobpilot.db")
    rows = c.execute("SELECT email, label, token_ref, enabled FROM email_account").fetchall()
    assert rows == [("mailbox@example.com", "main", ref, 1)]
    assert (
        c.execute("SELECT status FROM source_state WHERE source = 'gmail:1'").fetchone()[0]
        == "healthy"
    )
    assert (
        c.execute("SELECT COUNT(*) FROM audit_log WHERE action = 'email_account.add'").fetchone()[0]
        == 1
    )
    c.close()

    listing = runner.invoke(cli.app, ["auth", "list"])
    assert listing.exit_code == 0, listing.output
    assert "mailbox@example.com" in listing.output and "healthy" in listing.output


def test_partial_grant_stores_nothing(
    runner: CliRunner,
    monkeypatch: pytest.MonkeyPatch,
    mem_store: MemStore,
    client_secret: Path,
    tmp_path: Path,
) -> None:
    _wire_fakes(monkeypatch, mailbox="mailbox@example.com", granted=[SCOPES[0]])
    result = runner.invoke(cli.app, ["auth", "google"])
    assert result.exit_code == 1
    assert "missing scopes" in result.output
    assert mem_store.data == {}
    assert not (tmp_path / "data" / "jobpilot.db").exists() or (
        sqlite3.connect(tmp_path / "data" / "jobpilot.db")
        .execute("SELECT COUNT(*) FROM email_account")
        .fetchone()[0]
        == 0
    )


def test_login_hint_mismatch_requires_confirmation(
    runner: CliRunner, monkeypatch: pytest.MonkeyPatch, mem_store: MemStore, client_secret: Path
) -> None:
    _wire_fakes(monkeypatch, mailbox="other@example.com")
    result = runner.invoke(
        cli.app, ["auth", "google", "--login-hint", "mailbox@example.com"], input="n\n"
    )
    assert result.exit_code == 1, result.output
    assert "not mailbox@example.com" in result.output
    assert mem_store.data == {}

    result = runner.invoke(
        cli.app, ["auth", "google", "--login-hint", "mailbox@example.com", "--yes"]
    )
    assert result.exit_code == 0, result.output
    assert f"google_token__{get_token_ref('other@example.com')}" in mem_store.data


def test_two_accounts_and_reauth_reuse_rows(
    runner: CliRunner,
    monkeypatch: pytest.MonkeyPatch,
    mem_store: MemStore,
    client_secret: Path,
    tmp_path: Path,
) -> None:
    _wire_fakes(monkeypatch, mailbox="a@example.com")
    assert runner.invoke(cli.app, ["auth", "google"]).exit_code == 0
    _wire_fakes(monkeypatch, mailbox="b@example.com")
    assert runner.invoke(cli.app, ["auth", "google"]).exit_code == 0
    _wire_fakes(monkeypatch, mailbox="a@example.com")
    assert runner.invoke(cli.app, ["auth", "google"]).exit_code == 0
    assert len(mem_store.data) == 2
    c = sqlite3.connect(tmp_path / "data" / "jobpilot.db")
    assert c.execute("SELECT COUNT(*) FROM email_account").fetchone()[0] == 2
    c.close()


def test_forget_disables_and_deletes_local_token(
    runner: CliRunner,
    monkeypatch: pytest.MonkeyPatch,
    mem_store: MemStore,
    client_secret: Path,
    tmp_path: Path,
) -> None:
    _wire_fakes(monkeypatch, mailbox="a@example.com")
    assert runner.invoke(cli.app, ["auth", "google"]).exit_code == 0
    result = runner.invoke(cli.app, ["auth", "forget", "A@example.com"])
    assert result.exit_code == 0, result.output
    assert "myaccount.google.com/permissions" in result.output
    assert mem_store.data == {}
    c = sqlite3.connect(tmp_path / "data" / "jobpilot.db")
    assert c.execute("SELECT enabled FROM email_account").fetchone()[0] == 0
    assert c.execute("SELECT status FROM source_state").fetchone()[0] == "disabled"
    c.close()
    assert runner.invoke(cli.app, ["auth", "forget", "nobody@example.com"]).exit_code == 1


def test_missing_client_secret_is_explained(runner: CliRunner, mem_store: MemStore) -> None:
    result = runner.invoke(cli.app, ["auth", "google"])
    assert result.exit_code == 1
    assert "OAuth client file not found" in result.output


def test_web_client_type_is_rejected(
    runner: CliRunner, mem_store: MemStore, tmp_path: Path
) -> None:
    p = tmp_path / "data" / "secrets" / "client_secret.json"
    p.parent.mkdir(parents=True)
    p.write_text(json.dumps({"web": {"client_id": "x"}}), encoding="utf-8")
    result = runner.invoke(cli.app, ["auth", "google"])
    assert result.exit_code == 1
    assert "Desktop app" in result.output


def test_doctor_reports_client_secret_and_accounts(
    runner: CliRunner, monkeypatch: pytest.MonkeyPatch, mem_store: MemStore, client_secret: Path
) -> None:
    before = runner.invoke(cli.app, ["doctor"])
    assert before.exit_code == 0, before.output
    assert "Desktop app client" in before.output
    _wire_fakes(monkeypatch, mailbox="a@example.com")
    assert runner.invoke(cli.app, ["auth", "google"]).exit_code == 0
    after = runner.invoke(cli.app, ["doctor"])
    assert after.exit_code == 0, after.output
    assert "1 enabled / 1 total" in after.output
    assert "gmail:1" in after.output


def test_secrets_set_command(runner: CliRunner, mem_store: MemStore) -> None:
    result = runner.invoke(cli.app, ["secrets", "set", "anthropic_api_key"], input="k-test\n")
    assert result.exit_code == 0, result.output
    assert mem_store.data["anthropic_api_key"] == "k-test"
    assert runner.invoke(cli.app, ["secrets", "set", "linkedin_cookie"], input="x\n").exit_code != 0
