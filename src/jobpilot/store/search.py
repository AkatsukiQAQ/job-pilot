"""Email search: FTS5 (unicode61 / trigram) with a LIKE fallback for 1-2 character CJK queries.

Callers that expose results outside the process (MCP tools) must only read the *_public
columns returned here; body_text is never selected.
"""

from __future__ import annotations

import re
import sqlite3
import unicodedata

from jobpilot.textutil import has_cjk

_LIKE_ESCAPE_RE = re.compile(r"([\\%_])")

_SELECT_COLUMNS = (
    "m.msg_id, m.gmail_id, m.account_id, m.thread_id, m.internal_date_ms, m.from_domain,"
    " m.from_name_public, m.subject_public, m.snippet_public"
)


def _fts_query(tokens: list[str]) -> str:
    # Quote every token so FTS5 operators (AND/OR/NOT/NEAR, ':', '*') in user text cannot
    # change the query.
    return " ".join('"' + t.replace('"', '""') + '"' for t in tokens)


def _like_pattern(q: str) -> str:
    return "%" + _LIKE_ESCAPE_RE.sub(r"\\\1", q) + "%"


def search_emails(
    conn: sqlite3.Connection, query: str, *, account_id: int | None = None, limit: int = 20
) -> list[sqlite3.Row]:
    q = unicodedata.normalize("NFKC", query).strip()
    if not q:
        return []
    tokens = q.split()
    cjk = has_cjk(q)
    short_cjk = cjk and any(len(t) < 3 for t in tokens)  # trigram matches nothing under 3 chars
    acct_sql = " AND m.account_id = ?" if account_id is not None else ""
    acct_params: list[object] = [account_id] if account_id is not None else []
    if not short_cjk:
        table = "email_fts_tri" if cjk else "email_fts"
        sql = (
            f"SELECT {_SELECT_COLUMNS}, bm25({table}, 10.0, 4.0, 2.0, 1.0) AS rank"
            f" FROM {table} f JOIN email_message m ON m.msg_id = f.rowid"
            f" WHERE {table} MATCH ?{acct_sql}"
            " ORDER BY rank, m.internal_date_ms DESC LIMIT ?"
        )
        rows = conn.execute(sql, [_fts_query(tokens), *acct_params, limit]).fetchall()
        if rows:
            return rows
    like = _like_pattern(q)
    sql = (
        f"SELECT {_SELECT_COLUMNS}, 0.0 AS rank FROM email_message m"
        " WHERE (m.subject LIKE ? ESCAPE '\\' OR m.body_text LIKE ? ESCAPE '\\')"
        f"{acct_sql} ORDER BY m.internal_date_ms DESC LIMIT ?"
    )
    return conn.execute(sql, [like, like, *acct_params, limit]).fetchall()


__all__ = ["search_emails"]
