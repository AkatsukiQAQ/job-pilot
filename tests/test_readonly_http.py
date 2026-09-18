"""Transport-layer guard (read-only guarantee, layer 2). New file: test_readonly_guard.py is untouched."""

from __future__ import annotations

import json
from typing import Any

import httplib2
import pytest

from jobpilot.connectors.gmail.readonly_http import (
    ALLOWED_HOSTS,
    TOKEN_ENDPOINT,
    GetOnlyHttp,
    ReadOnlyHttp,
    WriteAttempted,
    get_gmail_service,
    get_read_only_http,
)
from tests.fakes.gmail import make_credentials


class RecordingHttp:
    """Inner http stand-in: records calls; returns a canned 200 JSON body."""

    def __init__(self, body: dict[str, Any] | None = None) -> None:
        self.calls: list[tuple[str, str, Any, dict[str, str] | None]] = []
        self.body = json.dumps(body or {"ok": True}).encode()

    def request(
        self,
        uri: str,
        method: str = "GET",
        body: Any = None,
        headers: dict[str, str] | None = None,
        **_: Any,
    ) -> tuple[Any, bytes]:
        self.calls.append((method, uri, body, headers))
        return httplib2.Response({"status": 200, "content-type": "application/json"}), self.body


def test_allowlists_are_minimal() -> None:
    assert frozenset({"gmail.googleapis.com", "oauth2.googleapis.com"}) == ALLOWED_HOSTS
    assert TOKEN_ENDPOINT == "https://oauth2.googleapis.com/token"


@pytest.mark.parametrize("verb", ["POST", "PUT", "PATCH", "DELETE", "HEAD"])
def test_outer_rejects_non_get_before_io(verb: str) -> None:
    inner = RecordingHttp()
    http = ReadOnlyHttp(make_credentials(), inner)
    with pytest.raises(WriteAttempted):
        http.request(
            "https://gmail.googleapis.com/gmail/v1/users/me/messages/x/modify", verb, body=b"{}"
        )
    assert inner.calls == []


def test_outer_rejects_bad_hosts_batch_and_get_with_body() -> None:
    inner = RecordingHttp()
    http = ReadOnlyHttp(make_credentials(), inner)
    with pytest.raises(WriteAttempted):
        http.request("https://www.example.com/anything", "GET")
    with pytest.raises(WriteAttempted):
        http.request("http://gmail.googleapis.com/gmail/v1/users/me/profile", "GET")
    with pytest.raises(WriteAttempted):
        http.request("https://gmail.googleapis.com/batch/gmail/v1", "GET")
    with pytest.raises(WriteAttempted):
        http.request("https://gmail.googleapis.com/gmail/v1/users/me/profile", "GET", body=b"x")
    assert inner.calls == []


def test_outer_get_passes_bearer_header_and_calls_hook() -> None:
    inner = RecordingHttp({"emailAddress": "mailbox@example.com"})
    seen: list[tuple[str, str, str, int]] = []
    http = ReadOnlyHttp(
        make_credentials(token="ya29.abc"), inner, egress_hook=lambda *a: seen.append(a)
    )
    resp, content = http.request("https://gmail.googleapis.com/gmail/v1/users/me/profile", "GET")
    assert resp.status == 200
    assert json.loads(content)["emailAddress"] == "mailbox@example.com"
    method, _uri, body, headers = inner.calls[0]
    assert method == "GET" and body is None
    assert headers is not None and headers.get("authorization") == "Bearer ya29.abc"
    assert seen == [("GET", "gmail.googleapis.com", "/gmail/v1/users/me/profile", 200)]


def test_googleapiclient_write_methods_are_unreachable() -> None:
    inner = RecordingHttp()
    service = get_gmail_service(
        ReadOnlyHttp(make_credentials(), inner)
    )  # static discovery: no network
    with pytest.raises(WriteAttempted):
        service.users().messages().modify(
            userId="me", id="x", body={"addLabelIds": ["STARRED"]}
        ).execute()
    with pytest.raises(WriteAttempted):
        service.users().messages().trash(userId="me", id="x").execute()
    with pytest.raises(WriteAttempted):
        batch = service.new_batch_http_request()
        batch.add(service.users().messages().get(userId="me", id="x"))
        batch.execute()
    assert inner.calls == []


def test_googleapiclient_get_goes_through() -> None:
    inner = RecordingHttp({"emailAddress": "mailbox@example.com", "historyId": "42"})
    service = get_gmail_service(
        get_read_only_http(make_credentials()).__class__(make_credentials(), inner)
    )
    profile = service.users().getProfile(userId="me").execute()
    assert profile["historyId"] == "42"
    assert inner.calls[0][0] == "GET"


def test_inner_layer_allows_only_token_refresh_post(monkeypatch: pytest.MonkeyPatch) -> None:
    calls: list[tuple[str, str]] = []

    def fake_request(
        self: httplib2.Http, uri: str, method: str = "GET", **_: Any
    ) -> tuple[Any, bytes]:
        calls.append((method, uri))
        return httplib2.Response({"status": 200}), b"{}"

    monkeypatch.setattr(httplib2.Http, "request", fake_request)
    inner = GetOnlyHttp()
    inner.request(TOKEN_ENDPOINT, "POST", body="grant_type=refresh_token")
    inner.request("https://gmail.googleapis.com/gmail/v1/users/me/profile", "GET")
    with pytest.raises(WriteAttempted):
        inner.request(
            "https://gmail.googleapis.com/gmail/v1/users/me/messages/x/modify", "POST", body="{}"
        )
    with pytest.raises(WriteAttempted):
        inner.request("https://oauth2.googleapis.com/revoke", "POST", body="token=x")
    with pytest.raises(WriteAttempted):
        inner.request("https://www.googleapis.com/oauth2/v4/token", "POST", body="x")
    assert [c[0] for c in calls] == ["POST", "GET"]


def test_refresh_uses_inner_layer_not_outer(monkeypatch: pytest.MonkeyPatch) -> None:
    """An expired token triggers a refresh POST on the inner http; the outer layer sees only GET."""
    outer_calls: list[str] = []
    inner_calls: list[tuple[str, str]] = []

    def fake_request(
        self: httplib2.Http, uri: str, method: str = "GET", **_: Any
    ) -> tuple[Any, bytes]:
        inner_calls.append((method, uri))
        if uri.startswith(TOKEN_ENDPOINT):
            body = {
                "access_token": "ya29.new",
                "expires_in": 3600,
                "scope": " ".join(make_credentials().scopes or []),
            }
            return httplib2.Response(
                {"status": 200, "content-type": "application/json"}
            ), json.dumps(body).encode()
        return httplib2.Response(
            {"status": 200, "content-type": "application/json"}
        ), b'{"ok": true}'

    monkeypatch.setattr(httplib2.Http, "request", fake_request)
    creds = make_credentials(valid=False)
    http = ReadOnlyHttp(creds)
    original = http.request

    def spy(uri: str, method: str = "GET", *a: Any, **k: Any) -> Any:
        outer_calls.append(method)
        return original(uri, method, *a, **k)

    monkeypatch.setattr(http, "request", spy)
    http.request("https://gmail.googleapis.com/gmail/v1/users/me/profile", "GET")
    assert outer_calls == ["GET"]
    assert ("POST", TOKEN_ENDPOINT) in inner_calls
    assert creds.token == "ya29.new"
    assert set(creds.granted_scopes or []) == set(make_credentials().scopes or [])
