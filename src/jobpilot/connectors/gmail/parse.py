"""Gmail API payload -> structured message record. Pure functions, no I/O, no market literals.

Language-specific word lists (generic anchor texts such as "click here" in other languages)
come from the region pack and are passed in by the caller.
"""

from __future__ import annotations

import base64
import contextlib
import html
import re
from collections.abc import Collection, Iterator
from email.header import decode_header, make_header
from email.utils import parseaddr
from html.parser import HTMLParser
from typing import Any

from jobpilot.domain import EmailMessageCreate, RawFormat
from jobpilot.textutil import detect_language, registrable_domain

METADATA_HEADERS: tuple[str, ...] = (
    "From",
    "To",
    "Cc",
    "Reply-To",
    "Sender",
    "Subject",
    "Date",
    "Message-ID",
    "In-Reply-To",
    "References",
    "List-Unsubscribe",
    "List-Id",
    "X-Google-Calendar-Notification",
)

_CHARSET_ALIASES = {
    "shift_jis": "cp932",
    "shift-jis": "cp932",
    "sjis": "cp932",
    "windows-31j": "cp932",
    "iso-2022-jp": "iso2022_jp",
    "euc-jp": "euc_jp",
    "gb2312": "gb18030",
    "gbk": "gb18030",
}
_CHARSET_RE = re.compile(r"charset=\"?([\w.-]+)", re.I)
_ICS_TYPES = frozenset({"text/calendar", "application/ics"})
_BLOCK_TAGS = frozenset(
    {
        "p",
        "div",
        "br",
        "tr",
        "li",
        "h1",
        "h2",
        "h3",
        "h4",
        "h5",
        "h6",
        "table",
        "blockquote",
        "pre",
        "hr",
    }
)
_SKIP_TAGS = frozenset({"script", "style", "head", "title"})
_URL_RE = re.compile(r"https?://[^\s<>\"')\]]+")
_DEFAULT_GENERIC_ANCHORS = frozenset(
    {"here", "click here", "join", "apply", "view", "open", "link"}
)
_PAIRED_SKIP_CLOSERS = frozenset({"div", "span", "table", "tr", "td", "section", "p"})


def get_headers(payload: dict[str, Any]) -> dict[str, str]:
    """Header name (casefolded) -> value; repeated References are concatenated."""
    out: dict[str, str] = {}
    for h in payload.get("headers", []) or []:
        name = str(h.get("name", "")).casefold()
        value = str(h.get("value", ""))
        if "=?" in value:  # defensive RFC 2047; Gmail normally returns decoded values
            with contextlib.suppress(Exception):
                value = str(make_header(decode_header(value)))
        if name == "references" and name in out:
            out[name] = f"{out[name]} {value}"
        elif name not in out:
            out[name] = value
    return out


def get_address(value: str | None) -> tuple[str | None, str | None, str | None]:
    """(display name, address, registrable domain); address and domain are casefolded."""
    if not value:
        return None, None, None
    name, addr = parseaddr(value)
    addr_cf = addr.casefold() if addr else ""
    if not addr_cf or "@" not in addr_cf:
        return (name or value.strip() or None), None, None
    return (name or None), addr_cf, registrable_domain(addr_cf.rpartition("@")[2])


def _walk(part: dict[str, Any]) -> Iterator[dict[str, Any]]:
    yield part
    for child in part.get("parts", []) or []:
        yield from _walk(child)  # multipart/* and nested message/rfc822 forwards


def _decode_part(part: dict[str, Any]) -> str:
    data = (part.get("body") or {}).get("data")
    if not data:
        return ""
    raw = base64.urlsafe_b64decode(data + "=" * (-len(data) % 4))
    ctype = next(
        (
            str(h["value"])
            for h in part.get("headers", []) or []
            if str(h.get("name", "")).casefold() == "content-type"
        ),
        "",
    )
    m = _CHARSET_RE.search(ctype)
    declared = _CHARSET_ALIASES.get(m.group(1).casefold(), m.group(1).casefold()) if m else None
    # ISO-2022-JP is 7-bit: it decodes "successfully" as UTF-8 into escape garbage, so detect
    # the escape sequences (or the declared charset) before trying UTF-8.
    if declared == "iso2022_jp" or b"\x1b$" in raw:
        with contextlib.suppress(UnicodeDecodeError, LookupError):
            return raw.decode("iso2022_jp")
    try:
        return raw.decode("utf-8")  # Gmail usually transcodes bodies to UTF-8 already
    except UnicodeDecodeError:
        if declared:
            with contextlib.suppress(LookupError):
                return raw.decode(declared, errors="replace")
        return raw.decode("utf-8", errors="replace")


class _HtmlToText(HTMLParser):
    def __init__(self, generic_anchors: Collection[str]) -> None:
        super().__init__(convert_charrefs=True)
        self.out: list[str] = []
        self.hrefs: list[str] = []
        self._generic = {a.casefold() for a in generic_anchors} | _DEFAULT_GENERIC_ANCHORS
        self._skip_stack: list[str] = []
        self._href: str | None = None
        self._anchor: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        a = dict(attrs)
        style = (a.get("style") or "").replace(" ", "").casefold()
        if tag in _SKIP_TAGS or "display:none" in style:
            self._skip_stack.append(tag)
            return
        if self._skip_stack:
            return
        if tag in _BLOCK_TAGS:
            self.out.append("\n")
        elif tag in {"td", "th"}:
            self.out.append("\t")
        elif tag == "a" and a.get("href"):
            self._href = a["href"]
            self._anchor = []
            self.hrefs.append(a["href"] or "")

    def handle_endtag(self, tag: str) -> None:
        if self._skip_stack:
            if tag == self._skip_stack[-1] or (
                tag in _PAIRED_SKIP_CLOSERS and tag == self._skip_stack[-1]
            ):
                self._skip_stack.pop()
            return
        if tag == "a" and self._href:
            text = "".join(self._anchor).strip()
            if not text or text.casefold() in self._generic:
                self.out.append(f"{text} ({self._href})".strip())
            else:
                self.out.append(text)
            self._href = None
            self._anchor = []
        elif tag in _BLOCK_TAGS:
            self.out.append("\n")

    def handle_data(self, data: str) -> None:
        if self._skip_stack:
            return
        (self._anchor if self._href is not None else self.out).append(data)


def get_html_text(html_text: str, *, generic_anchors: Collection[str] = ()) -> str:
    p = _HtmlToText(generic_anchors)
    p.feed(html_text)
    p.close()
    text = "".join(p.out)
    text = re.sub(r"[ \t]+\n", "\n", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def get_body_parts(payload: dict[str, Any]) -> tuple[str | None, str | None]:
    """(text/plain, text/html) bodies, first occurrence of each, attachments skipped."""
    plain: str | None = None
    html_body: str | None = None
    for p in _walk(payload):
        if p.get("filename"):
            continue
        mt = str(p.get("mimeType") or "").casefold()
        if mt == "text/plain" and plain is None:
            plain = _decode_part(p)
        elif mt == "text/html" and html_body is None:
            html_body = _decode_part(p)
    return plain, html_body


def get_body_text(payload: dict[str, Any], *, generic_anchors: Collection[str] = ()) -> str | None:
    """Prefer text/plain; fall back to HTML->text when plain is missing or near-empty."""
    plain, html_body = get_body_parts(payload)
    if plain and (len(plain.strip()) >= 40 or not html_body):
        return plain
    if html_body:
        return get_html_text(html_body, generic_anchors=generic_anchors)
    return plain or None


def get_has_ics(payload: dict[str, Any]) -> bool:
    return any(
        str(p.get("mimeType") or "").casefold() in _ICS_TYPES
        or str(p.get("filename") or "").casefold().endswith(".ics")
        for p in _walk(payload)
    )


def get_body_urls(text: str | None, html_body: str | None = None) -> list[dict[str, str]]:
    """URLs seen in text and <a href>; never resolved (click trackers would register an open)."""
    urls: set[str] = set(_URL_RE.findall(text or ""))
    if html_body:
        p = _HtmlToText(())
        p.feed(html_body)
        p.close()
        urls.update(u for u in p.hrefs if u.startswith(("http://", "https://")))
    out: list[dict[str, str]] = []
    for u in sorted(urls):
        host = u.split("/", 3)[2].lower() if u.count("/") >= 2 else ""
        out.append({"host": host, "url": u})
    return out


def get_message_record(
    account_id: int,
    raw: dict[str, Any],
    fmt: RawFormat,
    *,
    generic_anchors: Collection[str] = (),
) -> EmailMessageCreate:
    """Turn a users.messages.get response into an EmailMessageCreate (public columns unscrubbed).

    The caller (sync service) fills the *_public columns through the PII scrubber; here they
    default to the raw values so a record is always complete.
    """
    payload = raw.get("payload") or {}
    headers = get_headers(payload)
    from_name, from_addr, from_domain = get_address(headers.get("from"))
    _, reply_to, _ = get_address(headers.get("reply-to"))
    _, sender, _ = get_address(headers.get("sender"))
    subject = html.unescape(headers.get("subject", "")).strip()
    snippet = html.unescape(str(raw.get("snippet") or "")).strip()
    body_text: str | None = None
    body_urls: list[dict[str, str]] | None = None
    has_ics: bool | None = None
    if fmt == "full":
        plain, html_body = get_body_parts(payload)
        body_text = get_body_text(payload, generic_anchors=generic_anchors)
        body_urls = get_body_urls(plain or body_text, html_body)
        has_ics = get_has_ics(payload)
    kept = {k: v for k, v in headers.items() if k in {h.casefold() for h in METADATA_HEADERS}}
    return EmailMessageCreate(
        account_id=account_id,
        gmail_id=str(raw["id"]),
        thread_id=str(raw.get("threadId") or raw["id"]),
        internal_date_ms=int(raw.get("internalDate") or 0),
        raw_format=fmt,
        history_id=str(raw["historyId"]) if raw.get("historyId") else None,
        label_ids=[str(x) for x in raw.get("labelIds", []) or []],
        from_addr=from_addr,
        from_domain=from_domain,
        from_name=from_name,
        from_name_public=from_name,
        reply_to_addr=reply_to,
        sender_addr=sender,
        to_addr=headers.get("to"),
        message_id_hdr=headers.get("message-id"),
        in_reply_to=headers.get("in-reply-to"),
        references_hdr=headers.get("references"),
        has_list_unsubscribe="list-unsubscribe" in headers,
        headers=kept,
        subject=subject,
        subject_public=subject,
        snippet=snippet,
        snippet_public=snippet,
        body_text=body_text,
        body_urls=body_urls,
        has_ics=has_ics,
        language=detect_language(" ".join(x for x in (subject, snippet, body_text or "") if x)),
    )


__all__ = [
    "get_address",
    "get_body_parts",
    "get_body_text",
    "get_body_urls",
    "get_has_ics",
    "get_headers",
    "get_html_text",
    "get_message_record",
]
