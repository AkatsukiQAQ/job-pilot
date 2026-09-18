"""Offline stand-ins for the Gmail API and google-auth credentials. Fictional data only."""

from __future__ import annotations

import base64
import json
from collections.abc import Callable, Iterable
from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta
from typing import Any

import httplib2
from google.oauth2.credentials import Credentials
from googleapiclient.errors import HttpError

SCOPES = [
    "https://www.googleapis.com/auth/gmail.readonly",
    "https://www.googleapis.com/auth/calendar.events.readonly",
]


def b64(text: str, encoding: str = "utf-8") -> str:
    return base64.urlsafe_b64encode(text.encode(encoding)).decode("ascii").rstrip("=")


def make_credentials(
    *,
    scopes: Iterable[str] | None = None,
    granted: Iterable[str] | None = None,
    valid: bool = True,
    token: str = "ya29.test-token",
    client_id: str = "client-id.apps.googleusercontent.test",
) -> Credentials:
    scopes = list(scopes) if scopes is not None else list(SCOPES)
    expiry = datetime.now(UTC).replace(tzinfo=None) + (
        timedelta(hours=1) if valid else -timedelta(hours=1)
    )
    return Credentials(
        token=token,
        refresh_token="1//refresh-token",
        token_uri="https://oauth2.googleapis.com/token",
        client_id=client_id,
        client_secret="client-secret",
        scopes=scopes,
        granted_scopes=list(granted) if granted is not None else list(scopes),
        expiry=expiry,
    )


def make_message(
    gmail_id: str,
    *,
    thread_id: str | None = None,
    from_: str = "Acme Recruiting <recruit@acme.example>",
    to: str = "candidate@example.com",
    subject: str = "Interview invitation",
    date_ms: int = 1_900_000_000_000,
    snippet: str | None = None,
    plain: str | None = "Dear candidate, we would like to invite you to an interview.",
    html: str | None = None,
    labels: Iterable[str] = ("INBOX",),
    history_id: str = "100",
    extra_headers: dict[str, str] | None = None,
    ics: bool = False,
) -> dict[str, Any]:
    headers = [
        {"name": "From", "value": from_},
        {"name": "To", "value": to},
        {"name": "Subject", "value": subject},
        {"name": "Date", "value": "Mon, 1 Mar 2030 09:00:00 +0900"},
        {"name": "Message-ID", "value": f"<{gmail_id}@acme.example>"},
    ]
    for k, v in (extra_headers or {}).items():
        headers.append({"name": k, "value": v})
    parts: list[dict[str, Any]] = []
    if plain is not None:
        parts.append({"mimeType": "text/plain", "body": {"data": b64(plain)}, "headers": []})
    if html is not None:
        parts.append({"mimeType": "text/html", "body": {"data": b64(html)}, "headers": []})
    if ics:
        parts.append(
            {
                "mimeType": "text/calendar",
                "filename": "invite.ics",
                "body": {"data": b64("BEGIN:VCALENDAR")},
            }
        )
    payload: dict[str, Any] = {
        "mimeType": "multipart/alternative",
        "headers": headers,
        "parts": parts,
    }
    return {
        "id": gmail_id,
        "threadId": thread_id or f"t-{gmail_id}",
        "historyId": history_id,
        "internalDate": str(date_ms),
        "labelIds": list(labels),
        "snippet": snippet if snippet is not None else (plain or "")[:80],
        "payload": payload,
    }


def _http_error(status: int, reason: str = "") -> HttpError:
    resp = httplib2.Response({"status": status})
    content = json.dumps(
        {"error": {"code": status, "message": reason, "errors": [{"reason": reason}]}}
    ).encode()
    return HttpError(resp, content, uri="https://gmail.googleapis.com/fake")


class _Request:
    def __init__(self, fn: Callable[[], Any]) -> None:
        self._fn = fn

    def execute(self, num_retries: int = 0) -> Any:
        return self._fn()


@dataclass
class FakeGmailService:
    """Replays Gmail API shapes: users().getProfile/messages().list|get|list_next/history()."""

    profile: dict[str, Any]
    messages: dict[str, dict[str, Any]] = field(default_factory=dict)
    history_records: list[dict[str, Any]] = field(default_factory=list)
    history_id_now: str = "200"
    page_size: int = 2
    history_404: bool = False
    fail_get: set[str] = field(default_factory=set)
    rate_limit_get: set[str] = field(default_factory=set)
    list_calls: list[dict[str, Any]] = field(default_factory=list)
    get_calls: list[tuple[str, str]] = field(default_factory=list)
    fail_list_page: int | None = None

    def users(self) -> _Users:
        return _Users(self)


class _Users:
    def __init__(self, svc: FakeGmailService) -> None:
        self._svc = svc

    def getProfile(self, userId: str) -> _Request:
        return _Request(lambda: dict(self._svc.profile))

    def messages(self) -> _Messages:
        return _Messages(self._svc)

    def history(self) -> _History:
        return _History(self._svc)


class _Messages:
    def __init__(self, svc: FakeGmailService) -> None:
        self._svc = svc

    def list(
        self, userId: str, q: str = "", maxResults: int = 500, pageToken: str | None = None
    ) -> _Request:
        svc = self._svc
        svc.list_calls.append({"q": q, "maxResults": maxResults, "pageToken": pageToken})
        ids = sorted(svc.messages)
        start = int(pageToken or 0)
        page_no = start // svc.page_size

        def run() -> dict[str, Any]:
            if svc.fail_list_page is not None and page_no == svc.fail_list_page:
                svc.fail_list_page = None  # fail once
                raise _http_error(500, "backendError")
            chunk = ids[start : start + svc.page_size]
            resp: dict[str, Any] = {
                "messages": [{"id": i, "threadId": svc.messages[i]["threadId"]} for i in chunk],
                "resultSizeEstimate": len(ids),
            }
            if start + svc.page_size < len(ids):
                resp["nextPageToken"] = str(start + svc.page_size)
            return resp

        req = _Request(run)
        setattr(req, "_q", q)  # noqa: B010
        return req

    def list_next(
        self, previous_request: Any, previous_response: dict[str, Any]
    ) -> _Request | None:
        token = previous_response.get("nextPageToken")
        if not token:
            return None
        return self.list(userId="me", q=getattr(previous_request, "_q", ""), pageToken=token)

    def get(
        self, userId: str, id: str, format: str = "full", metadataHeaders: list[str] | None = None
    ) -> _Request:
        svc = self._svc
        svc.get_calls.append((id, format))

        def run() -> dict[str, Any]:
            if id in svc.rate_limit_get:
                svc.rate_limit_get.discard(id)
                raise _http_error(429, "rateLimitExceeded")
            if id in svc.fail_get or id not in svc.messages:
                raise _http_error(404, "notFound")
            msg = json.loads(json.dumps(svc.messages[id]))
            if format == "metadata":
                wanted = {h.casefold() for h in (metadataHeaders or [])}
                payload = msg["payload"]
                payload["headers"] = [
                    h for h in payload.get("headers", []) if h["name"].casefold() in wanted
                ]
                payload.pop("parts", None)
                payload["body"] = {"size": 0}
            return msg

        return _Request(run)


class _History:
    def __init__(self, svc: FakeGmailService) -> None:
        self._svc = svc

    def list(
        self,
        userId: str,
        startHistoryId: str,
        historyTypes: list[str],
        maxResults: int = 500,
        pageToken: str | None = None,
    ) -> _Request:
        svc = self._svc

        def run() -> dict[str, Any]:
            if svc.history_404:
                raise _http_error(404, "notFound")
            return {"history": list(svc.history_records), "historyId": svc.history_id_now}

        return _Request(run)

    def list_next(self, previous_request: Any, previous_response: dict[str, Any]) -> None:
        return None


class RecordingProxy:
    """Wraps an object and records every attribute name touched (for read-only path assertions)."""

    def __init__(self, target: Any, names: list[str] | None = None) -> None:
        object.__setattr__(self, "_target", target)
        object.__setattr__(self, "names", names if names is not None else [])

    def __getattr__(self, name: str) -> Any:
        self.names.append(name)
        value = getattr(self._target, name)
        if callable(value):

            def call(*args: Any, **kwargs: Any) -> Any:
                result = value(*args, **kwargs)
                if isinstance(result, dict | list | str | int | float | bool | type(None)):
                    return result
                return RecordingProxy(result, self.names)

            return call
        return RecordingProxy(value, self.names)

    def __setattr__(self, name: str, value: Any) -> None:
        setattr(self._target, name, value)
