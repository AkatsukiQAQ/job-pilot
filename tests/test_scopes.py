from __future__ import annotations

import json

import pytest

from jobpilot.connectors.gmail.auth import (
    ALLOWED_SCOPES,
    REQUESTED_SCOPES,
    ScopeViolation,
    get_checked_scopes,
    get_credentials,
    get_token_ref,
)
from jobpilot.secrets import EnvStore
from tests.fakes.gmail import SCOPES, make_credentials


def test_scope_constants_snapshot() -> None:
    assert (
        frozenset(
            {
                "https://www.googleapis.com/auth/gmail.readonly",
                "https://www.googleapis.com/auth/calendar.events.readonly",
            }
        )
        == ALLOWED_SCOPES
    )
    assert set(REQUESTED_SCOPES) == ALLOWED_SCOPES
    assert all("readonly" in s for s in ALLOWED_SCOPES)


def test_exact_grant_passes() -> None:
    assert get_checked_scopes(make_credentials(), require_all=True) == ALLOWED_SCOPES


def test_extra_scope_is_rejected_even_when_not_requiring_all() -> None:
    creds = make_credentials(granted=[*SCOPES, "https://www.googleapis.com/auth/gmail.modify"])
    with pytest.raises(ScopeViolation, match="non-read-only"):
        get_checked_scopes(creds, require_all=False)


def test_partial_grant_rejected_at_consent_but_tolerated_on_reload() -> None:
    creds = make_credentials(granted=[SCOPES[0]])
    with pytest.raises(ScopeViolation, match="missing"):
        get_checked_scopes(creds, require_all=True)
    assert get_checked_scopes(creds, require_all=False) == frozenset({SCOPES[0]})


def test_token_ref_hides_the_address_and_is_stable() -> None:
    ref = get_token_ref("Mailbox@Example.com ")
    assert ref == get_token_ref("mailbox@example.com")
    assert ref.startswith("acct-") and len(ref) == len("acct-") + 16
    assert "example" not in ref


def test_stored_json_with_extra_scope_is_rejected(monkeypatch: pytest.MonkeyPatch) -> None:
    info = {
        "refresh_token": "1//r",
        "client_id": "cid",
        "client_secret": "cs",
        "scopes": [*SCOPES, "https://www.googleapis.com/auth/gmail.send"],
    }
    monkeypatch.setenv("JOBPILOT_SECRET_GOOGLE_TOKEN__ACCT-X", json.dumps(info))
    with pytest.raises(ScopeViolation):
        get_credentials(EnvStore(), "acct-x")
