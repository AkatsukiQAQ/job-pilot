"""Gmail API access (no database): quota budget, paged listing, message fetch, history.

Quota units (official Gmail API usage limits): getProfile 1, messages.list 5, messages.get 20
(any format), history.list 2. The per-user ceiling is 6,000 units per minute.
"""

from __future__ import annotations

import time
from collections.abc import Callable, Collection, Iterator
from dataclasses import dataclass, field
from typing import Any

from googleapiclient.errors import HttpError

from jobpilot.connectors.gmail.parse import METADATA_HEADERS
from jobpilot.domain import RawFormat

UNITS_PROFILE = 1
UNITS_LIST = 5
UNITS_GET = 20
UNITS_HISTORY = 2
NUM_RETRIES = 5  # googleapiclient retries 429 / 403 rate errors / 5xx with exponential backoff
_RATE_LIMIT_MARKERS = ("rateLimitExceeded", "userRateLimitExceeded")


class HistoryExpired(RuntimeError):
    """history.list returned 404: startHistoryId is too old; the caller must resync."""


class RateLimited(RuntimeError):
    """Rate limit error escaped the library's retries; the caller should slow down."""


@dataclass
class Budget:
    """Per-account quota budget: sleeps when a minute's allowance would be exceeded."""

    units_per_minute: int
    clock: Callable[[], float] = time.monotonic
    sleep: Callable[[float], None] = time.sleep
    total_units: int = field(default=0, init=False)
    _window_start: float = field(default=-1.0, init=False)
    _spent: int = field(default=0, init=False)

    def spend(self, units: int) -> None:
        now = self.clock()
        if self._window_start < 0 or now - self._window_start >= 60.0:
            self._window_start, self._spent = now, 0
        if self._spent + units > self.units_per_minute:
            wait = 60.0 - (now - self._window_start)
            if wait > 0:
                self.sleep(wait)
            self._window_start, self._spent = self.clock(), 0
        self._spent += units
        self.total_units += units

    def halve(self) -> None:
        self.units_per_minute = max(300, self.units_per_minute // 2)


def _status(e: HttpError) -> int:
    return int(getattr(e.resp, "status", 0) or 0)


def _is_rate_limit(e: HttpError) -> bool:
    status = _status(e)
    text = str(e)
    return status == 429 or (status == 403 and any(m in text for m in _RATE_LIMIT_MARKERS))


def _execute(request: Any) -> Any:
    try:
        return request.execute(num_retries=NUM_RETRIES)
    except HttpError as e:
        if _is_rate_limit(e):
            raise RateLimited(str(e)) from e
        raise


def fetch_profile(service: Any, budget: Budget) -> dict[str, Any]:
    """users.getProfile: emailAddress, messagesTotal, threadsTotal, historyId."""
    budget.spend(UNITS_PROFILE)
    return _execute(service.users().getProfile(userId="me"))


def list_message_ids(
    service: Any, *, q: str, budget: Budget, page_size: int = 500
) -> Iterator[tuple[str, str]]:
    """Yield (gmail_id, thread_id) for every message matching the Gmail search query."""
    messages = service.users().messages()
    req = messages.list(userId="me", q=q, maxResults=page_size)
    while req is not None:
        budget.spend(UNITS_LIST)
        resp = _execute(req)
        for m in resp.get("messages", []) or []:
            yield str(m["id"]), str(m.get("threadId") or m["id"])
        req = messages.list_next(req, resp)


def fetch_message(
    service: Any, gmail_id: str, *, fmt: RawFormat, budget: Budget
) -> dict[str, Any] | None:
    """users.messages.get; None when the message vanished between listing and fetching."""
    budget.spend(UNITS_GET)
    kwargs: dict[str, Any] = {"format": fmt}
    if fmt == "metadata":
        kwargs["metadataHeaders"] = list(METADATA_HEADERS)
    try:
        return _execute(service.users().messages().get(userId="me", id=gmail_id, **kwargs))
    except HttpError as e:
        if _status(e) == 404:
            return None
        raise


def list_history(
    service: Any,
    *,
    start_history_id: str,
    budget: Budget,
    skip_labels: Collection[str] = (),
) -> tuple[list[dict[str, Any]], str]:
    """Messages added since start_history_id, deduplicated, plus the mailbox historyId to store.

    The cursor to persist is the response's ``historyId`` (the mailbox's current id), not the
    largest history record id. A 404 means the id is too old -> HistoryExpired.
    """
    seen: dict[str, dict[str, Any]] = {}
    latest = start_history_id
    history = service.users().history()
    req = history.list(
        userId="me", startHistoryId=start_history_id, historyTypes=["messageAdded"], maxResults=500
    )
    skip = set(skip_labels)
    while req is not None:
        budget.spend(UNITS_HISTORY)
        try:
            resp = _execute(req)
        except HttpError as e:
            if _status(e) == 404:
                raise HistoryExpired(start_history_id) from e
            raise
        latest = str(resp.get("historyId") or latest)
        for rec in resp.get("history", []) or []:
            for added in rec.get("messagesAdded", []) or []:
                msg = added.get("message") or {}
                if not msg.get("id"):
                    continue
                if skip and skip.intersection(msg.get("labelIds", []) or []):
                    continue
                seen.setdefault(str(msg["id"]), msg)
        req = history.list_next(req, resp)
    return list(seen.values()), latest


__all__ = [
    "fetch_message",
    "fetch_profile",
    "list_history",
    "list_message_ids",
]
