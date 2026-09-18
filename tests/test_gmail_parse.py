from __future__ import annotations

from jobpilot.connectors.gmail.parse import (
    get_address,
    get_body_text,
    get_body_urls,
    get_has_ics,
    get_headers,
    get_html_text,
    get_message_record,
)
from tests.fakes.gmail import b64, make_message


def test_headers_casefold_and_references_join() -> None:
    payload = {
        "headers": [
            {"name": "Subject", "value": "Hello"},
            {"name": "References", "value": "<a@x.example>"},
            {"name": "References", "value": "<b@x.example>"},
            {"name": "List-Unsubscribe", "value": "<mailto:u@x.example>"},
        ]
    }
    h = get_headers(payload)
    assert h["subject"] == "Hello"
    assert h["references"] == "<a@x.example> <b@x.example>"
    assert "list-unsubscribe" in h


def test_address_parsing() -> None:
    assert get_address("Acme Recruiting <Recruit@Mail.Acme.co.jp>") == (
        "Acme Recruiting",
        "recruit@mail.acme.co.jp",
        "acme.co.jp",
    )
    assert get_address("noreply@acme.example") == (None, "noreply@acme.example", "acme.example")
    assert get_address("Malformed Header") == ("Malformed Header", None, None)
    assert get_address(None) == (None, None, None)


def test_plain_preferred_but_short_plain_falls_back_to_html() -> None:
    msg = make_message(
        "m1",
        plain="see html",
        html="<p>Dear candidate,</p><p>Your interview is on <b>March 1</b>.</p>",
    )
    text = get_body_text(msg["payload"])
    assert text is not None
    assert "Dear candidate," in text and "March 1" in text and "<p>" not in text


def test_html_to_text_blocks_anchors_and_hidden_content() -> None:
    html = (
        "<html><head><title>x</title><style>p{}</style></head><body>"
        "<div style='display:none'>hidden tracking text</div>"
        "<p>Please <a href='https://portal.example/login'>click here</a> to continue.</p>"
        "<table><tr><td>Date</td><td>2030-03-01</td></tr></table>"
        "<a href='https://acme.example/jobs/1'>Applied Research Engineer</a>"
        "</body></html>"
    )
    text = get_html_text(html, generic_anchors=["click here"])
    assert "hidden tracking text" not in text
    assert "click here (https://portal.example/login)" in text
    assert "Date\t2030-03-01" in text
    assert "Applied Research Engineer" in text and "acme.example/jobs/1" not in text


def test_charset_fallback_for_japanese_bytes() -> None:
    text = "面接のご案内"  # interview invitation
    part = {
        "mimeType": "text/plain",
        "headers": [{"name": "Content-Type", "value": 'text/plain; charset="ISO-2022-JP"'}],
        "body": {"data": b64(text, "iso2022_jp")},
    }
    assert get_body_text({"mimeType": "multipart/alternative", "parts": [part]}) == text
    sjis = {
        "mimeType": "text/plain",
        "headers": [{"name": "Content-Type", "value": "text/plain; charset=Shift_JIS"}],
        "body": {"data": b64(text, "cp932")},
    }
    assert get_body_text({"parts": [sjis]}) == text


def test_ics_and_nested_forward_and_urls() -> None:
    inner = make_message("inner", plain="Original mail https://meet.example/abc?x=1")["payload"]
    inner["mimeType"] = "message/rfc822"
    msg = make_message("outer", plain="Forwarded: see below", ics=True)
    msg["payload"]["parts"].append(inner)
    assert get_has_ics(msg["payload"])
    body = get_body_text(msg["payload"])
    assert body is not None and "Forwarded" in body
    urls = get_body_urls(
        "text https://a.example/x and https://b.example/y.", "<a href='https://c.example/z'>c</a>"
    )
    assert [u["host"] for u in urls] == ["a.example", "b.example", "c.example"]


def test_get_message_record_metadata_and_full() -> None:
    raw = make_message(
        "g1",
        from_="Acme Recruiting <recruit@acme.example>",
        subject="Interview invitation &amp; details",
        snippet="We would like to invite you &#39;soon&#39;",
        extra_headers={
            "List-Unsubscribe": "<mailto:x@acme.example>",
            "Reply-To": "hr@acme.example",
        },
        labels=["INBOX", "CATEGORY_UPDATES"],
    )
    meta = get_message_record(7, raw, "metadata")
    assert meta.account_id == 7 and meta.gmail_id == "g1" and meta.thread_id == "t-g1"
    assert meta.from_addr == "recruit@acme.example" and meta.from_domain == "acme.example"
    assert meta.from_name == "Acme Recruiting" and meta.reply_to_addr == "hr@acme.example"
    assert meta.subject == "Interview invitation & details"
    assert meta.snippet == "We would like to invite you 'soon'"
    assert meta.has_list_unsubscribe is True
    assert meta.body_text is None and meta.has_ics is None and meta.body_urls is None
    assert meta.label_ids == ["INBOX", "CATEGORY_UPDATES"]
    assert meta.language == "en"

    full = get_message_record(7, raw, "full")
    assert full.raw_format == "full"
    assert full.body_text and "invite you" in full.body_text
    assert full.has_ics is False
    assert full.body_urls == []
    assert set(full.headers) <= {
        "from",
        "to",
        "subject",
        "date",
        "message-id",
        "reply-to",
        "list-unsubscribe",
    }
