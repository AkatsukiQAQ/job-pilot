from __future__ import annotations

from typing import Any

import pytest

from jobpilot.connectors.gmail.sync import (
    UNITS_GET,
    UNITS_LIST,
    Budget,
    HistoryExpired,
    RateLimited,
    fetch_message,
    fetch_profile,
    list_history,
    list_message_ids,
)
from tests.fakes.gmail import FakeGmailService, make_message


class FakeClock:
    def __init__(self) -> None:
        self.t = 1000.0
        self.slept: list[float] = []

    def now(self) -> float:
        return self.t

    def sleep(self, seconds: float) -> None:
        self.slept.append(seconds)
        self.t += seconds


def _service(n: int = 5, **kw: Any) -> FakeGmailService:
    msgs = {f"m{i:02d}": make_message(f"m{i:02d}", date_ms=1_900_000_000_000 + i) for i in range(n)}
    return FakeGmailService(
        profile={"emailAddress": "mailbox@example.com", "historyId": "500"}, messages=msgs, **kw
    )  # type: ignore[arg-type]


def test_budget_sleeps_when_minute_allowance_is_exceeded() -> None:
    clock = FakeClock()
    budget = Budget(units_per_minute=60, clock=clock.now, sleep=clock.sleep)
    for _ in range(3):
        budget.spend(UNITS_GET)  # 60 units: fits exactly
    assert clock.slept == []
    budget.spend(UNITS_GET)  # 80 > 60 -> wait for the window to roll over
    assert clock.slept == [60.0]
    assert budget.total_units == 80
    budget.halve()
    assert budget.units_per_minute == 300  # floor


def test_list_pages_and_fetch_metadata() -> None:
    svc = _service(5)
    budget = Budget(units_per_minute=6000, clock=lambda: 0.0, sleep=lambda s: None)
    ids = list(list_message_ids(svc, q="newer_than:180d", budget=budget))
    assert [i for i, _ in ids] == [f"m{i:02d}" for i in range(5)]
    assert len(svc.list_calls) == 3  # page size 2
    assert budget.total_units == 3 * UNITS_LIST
    meta = fetch_message(svc, "m00", fmt="metadata", budget=budget)
    assert meta is not None and "parts" not in meta["payload"]
    assert all(
        h["name"] in {"From", "To", "Subject", "Date", "Message-ID"}
        for h in meta["payload"]["headers"]
    )
    full = fetch_message(svc, "m00", fmt="full", budget=budget)
    assert full is not None and full["payload"]["parts"]
    assert fetch_message(svc, "nope", fmt="metadata", budget=budget) is None  # 404 -> None
    profile = fetch_profile(svc, budget)
    assert profile["historyId"] == "500"


def test_rate_limit_surfaces_as_rate_limited() -> None:
    svc = _service(1, rate_limit_get={"m00"})
    budget = Budget(units_per_minute=6000, clock=lambda: 0.0, sleep=lambda s: None)
    with pytest.raises(RateLimited):
        fetch_message(svc, "m00", fmt="metadata", budget=budget)
    assert fetch_message(svc, "m00", fmt="metadata", budget=budget) is not None  # second try ok


def test_history_dedupes_filters_and_returns_mailbox_history_id() -> None:
    svc = _service(0)
    svc.history_records = [
        {
            "id": "101",
            "messagesAdded": [{"message": {"id": "h1", "threadId": "t", "labelIds": ["INBOX"]}}],
        },
        {
            "id": "102",
            "messagesAdded": [{"message": {"id": "h1", "threadId": "t", "labelIds": ["INBOX"]}}],
        },
        {
            "id": "103",
            "messagesAdded": [
                {"message": {"id": "h2", "threadId": "t", "labelIds": ["CATEGORY_PROMOTIONS"]}}
            ],
        },
        {
            "id": "104",
            "messagesAdded": [{"message": {"id": "h3", "threadId": "t", "labelIds": ["INBOX"]}}],
        },
    ]
    svc.history_id_now = "999"
    budget = Budget(units_per_minute=6000, clock=lambda: 0.0, sleep=lambda s: None)
    added, cursor = list_history(
        svc, start_history_id="100", budget=budget, skip_labels={"CATEGORY_PROMOTIONS"}
    )
    assert [m["id"] for m in added] == ["h1", "h3"]
    assert cursor == "999"  # the mailbox id from the response, not the max record id (104)


def test_history_404_raises_history_expired() -> None:
    svc = _service(0, history_404=True)
    budget = Budget(units_per_minute=6000, clock=lambda: 0.0, sleep=lambda s: None)
    with pytest.raises(HistoryExpired):
        list_history(svc, start_history_id="1", budget=budget)
