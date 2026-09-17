from __future__ import annotations

import sqlite3

from jobpilot.domain import EmailMessageCreate
from jobpilot.store.repo import EmailAccountRepo, EmailRepo
from jobpilot.store.search import search_emails


def _seed(conn: sqlite3.Connection) -> tuple[int, int]:
    acct = EmailAccountRepo(conn).add("mailbox@example.com", token_ref="acct-0123456789abcdef")
    repo = EmailRepo(conn)
    ja, _ = repo.upsert(
        EmailMessageCreate(
            account_id=acct.account_id,
            gmail_id="ja1",
            thread_id="t1",
            internal_date_ms=1_900_000_000_000,
            raw_format="full",
            from_domain="acme.example",
            from_name="Acme",
            from_name_public="Acme",
            subject="面接のご案内",  # interview invitation (ja)
            subject_public="面接のご案内",
            snippet="",
            snippet_public="",
            body_text="日時 2030年3月1日 14:00",  # date/time line (ja)
        )
    )
    en, _ = repo.upsert(
        EmailMessageCreate(
            account_id=acct.account_id,
            gmail_id="en1",
            thread_id="t2",
            internal_date_ms=1_900_000_100_000,
            raw_format="metadata",
            from_domain="acme.example",
            from_name="ACME Recruiting",
            from_name_public="ACME Recruiting",
            subject="Your application to ACME",
            subject_public="Your application to ACME",
            snippet="Thanks for applying",
            snippet_public="Thanks for applying",
        )
    )
    return ja, en


def test_trigram_needs_three_chars_and_like_fallback(conn: sqlite3.Connection) -> None:
    ja, _ = _seed(conn)
    two = "面接"  # 2 chars -> trigram matches nothing
    three = "面接の"
    assert (
        conn.execute(
            "SELECT COUNT(*) FROM email_fts_tri WHERE email_fts_tri MATCH ?", (f'"{two}"',)
        ).fetchone()[0]
        == 0
    )
    assert (
        conn.execute(
            "SELECT COUNT(*) FROM email_fts_tri WHERE email_fts_tri MATCH ?", (f'"{three}"',)
        ).fetchone()[0]
        == 1
    )
    rows = search_emails(conn, two)
    assert [r["msg_id"] for r in rows] == [ja]  # LIKE fallback
    rows = search_emails(conn, three)
    assert [r["msg_id"] for r in rows] == [ja]  # trigram path


def test_unicode61_case_insensitive_and_public_columns_only(conn: sqlite3.Connection) -> None:
    _, en = _seed(conn)
    rows = search_emails(conn, "acme")
    assert en in [r["msg_id"] for r in rows]
    cols = list(rows[0].keys())
    assert set(cols) >= {
        "msg_id",
        "gmail_id",
        "subject_public",
        "snippet_public",
        "from_name_public",
    }
    assert "body_text" not in cols
    assert "subject" not in cols


def test_fts_follows_updates_and_integrity(conn: sqlite3.Connection) -> None:
    ja, _ = _seed(conn)
    date_word = "日時"  # appears only in the body
    assert (
        conn.execute(
            "SELECT COUNT(*) FROM email_fts_tri WHERE email_fts_tri MATCH ?",
            (f'"{date_word} 2030"',),
        ).fetchone()[0]
        == 1
    )
    conn.execute("UPDATE email_message SET body_text = NULL WHERE msg_id = ?", (ja,))
    assert (
        conn.execute(
            "SELECT COUNT(*) FROM email_fts_tri WHERE email_fts_tri MATCH ?",
            (f'"{date_word} 2030"',),
        ).fetchone()[0]
        == 0
    )
    conn.execute("INSERT INTO email_fts(email_fts) VALUES ('integrity-check')")
    conn.execute("INSERT INTO email_fts_tri(email_fts_tri) VALUES ('integrity-check')")


def test_account_filter_and_empty_query(conn: sqlite3.Connection) -> None:
    _seed(conn)
    assert search_emails(conn, "   ") == []
    assert search_emails(conn, "acme", account_id=999) == []
    assert search_emails(conn, "acme", account_id=1)
