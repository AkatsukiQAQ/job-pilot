"""Text helpers with no market-specific literals: normalisation, domains, language detection."""

from __future__ import annotations

import re
import unicodedata

from jobpilot.domain import Lang

# Public-suffix-like second-level labels where the registrable domain has three labels.
# Internet infrastructure facts, not regional rules.
_SECOND_LEVEL: frozenset[str] = frozenset(
    {
        "co.jp",
        "ne.jp",
        "or.jp",
        "ac.jp",
        "go.jp",
        "ad.jp",
        "ed.jp",
        "gr.jp",
        "lg.jp",
        "co.uk",
        "org.uk",
        "ac.uk",
        "gov.uk",
        "com.au",
        "net.au",
        "org.au",
        "edu.au",
        "co.kr",
        "or.kr",
        "ac.kr",
        "com.cn",
        "net.cn",
        "org.cn",
        "edu.cn",
        "com.tw",
        "org.tw",
        "com.hk",
        "com.sg",
        "com.br",
        "co.in",
        "co.nz",
        "co.za",
        "com.mx",
    }
)

_WS_RE = re.compile(r"\s+")
# Kana: hiragana U+3040-U+309F, katakana U+30A0-U+30FF, half-width katakana U+FF66-U+FF9F.
# Written as escapes so core code carries no CJK literals (tests/test_regions.py guards this).
_KANA_RE = re.compile("[\u3040-\u30ff\uff66-\uff9f]")
# CJK unified ideographs (main block + extension A + compatibility).
_HAN_RE = re.compile("[\u3400-\u4dbf\u4e00-\u9fff\uf900-\ufaff]")
_LATIN_RE = re.compile(r"[A-Za-z]")


def nfkc(text: str) -> str:
    """NFKC normalisation + whitespace collapse (full-width digits/letters become ASCII)."""
    return _WS_RE.sub(" ", unicodedata.normalize("NFKC", text)).strip()


def registrable_domain(host: str) -> str:
    """Lowercase registrable domain: last two labels, or three under known second-level suffixes."""
    h = host.strip().strip(".").casefold()
    if "@" in h:
        h = h.rsplit("@", 1)[1]
    labels = [x for x in h.split(".") if x]
    if len(labels) <= 2:
        return ".".join(labels)
    tail2 = ".".join(labels[-2:])
    if tail2 in _SECOND_LEVEL and len(labels) >= 3:
        return ".".join(labels[-3:])
    return tail2


def domain_label(domain: str) -> str:
    """'acme.co.jp' -> 'acme'; the organisation label of a registrable domain."""
    d = registrable_domain(domain)
    labels = d.split(".")
    if len(labels) >= 3 and ".".join(labels[-2:]) in _SECOND_LEVEL:
        return labels[-3]
    return labels[0] if labels else d


def has_cjk(text: str) -> bool:
    return bool(_KANA_RE.search(text) or _HAN_RE.search(text))


def detect_language(text: str) -> Lang | None:
    """Rough script-based detection: kana -> ja, ideographs without kana -> zh, latin -> en."""
    if not text:
        return None
    if _KANA_RE.search(text):
        return "ja"
    if _HAN_RE.search(text):
        return "zh"
    if _LATIN_RE.search(text):
        return "en"
    return None


def normalize_role(role: str | None) -> str:
    """Natural-key form of a role title: NFKC, casefold, single spaces; '' when unknown."""
    if not role:
        return ""
    return nfkc(role).casefold()


__all__ = [
    "detect_language",
    "domain_label",
    "has_cjk",
    "nfkc",
    "normalize_role",
    "registrable_domain",
]
