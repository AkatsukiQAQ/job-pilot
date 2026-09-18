"""Call-path guard: the sync layer only ever touches read methods of the Gmail resource."""

from __future__ import annotations

import importlib
import pkgutil
import re

import jobpilot.connectors.gmail as gmail_pkg
from jobpilot.connectors.gmail.sync import (
    Budget,
    fetch_message,
    fetch_profile,
    list_history,
    list_message_ids,
)
from tests.fakes.gmail import FakeGmailService, RecordingProxy, make_message

ALLOWED_RESOURCE_ATTRS = {
    "users",
    "getProfile",
    "messages",
    "history",
    "list",
    "list_next",
    "get",
    "execute",
}
_PUBLIC_NAME_RE = re.compile(r"^(fetch|list|get|import)_")


def test_sync_layer_touches_only_read_methods() -> None:
    svc = FakeGmailService(
        profile={"emailAddress": "mailbox@example.com", "historyId": "1"},
        messages={"m1": make_message("m1")},
        history_records=[
            {
                "id": "2",
                "messagesAdded": [{"message": {"id": "m1", "threadId": "t", "labelIds": []}}],
            }
        ],
    )
    proxy = RecordingProxy(svc)
    budget = Budget(units_per_minute=6000, clock=lambda: 0.0, sleep=lambda s: None)
    fetch_profile(proxy, budget)
    list(list_message_ids(proxy, q="x", budget=budget))
    fetch_message(proxy, "m1", fmt="metadata", budget=budget)
    fetch_message(proxy, "m1", fmt="full", budget=budget)
    list_history(proxy, start_history_id="1", budget=budget)
    assert set(proxy.names) <= ALLOWED_RESOURCE_ATTRS, set(proxy.names) - ALLOWED_RESOURCE_ATTRS


def test_gmail_modules_export_only_readonly_names() -> None:
    for info in pkgutil.walk_packages(gmail_pkg.__path__, prefix="jobpilot.connectors.gmail."):
        mod = importlib.import_module(info.name)
        public = getattr(mod, "__all__", [])
        bad = [n for n in public if not _PUBLIC_NAME_RE.match(n)]
        assert bad == [], f"{info.name}: {bad}"
