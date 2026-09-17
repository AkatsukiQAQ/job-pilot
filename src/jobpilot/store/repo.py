"""Repositories. Every write lands in the same transaction as its audit_log row."""

from __future__ import annotations

import json
import sqlite3
from typing import Any

from jobpilot.domain import Campaign, CampaignCreate
from jobpilot.store.db import transaction

Actor = str  # 'user' | 'llm' | 'system' (enforced by the audit_log CHECK constraint)


def _row_json(row: sqlite3.Row) -> str:
    d: dict[str, Any] = dict(row)
    return json.dumps(d, ensure_ascii=False, sort_keys=True)


def write_audit(
    conn: sqlite3.Connection,
    *,
    actor: Actor,
    action: str,
    table_name: str,
    row_id: int | None,
    before: sqlite3.Row | None,
    after: sqlite3.Row | None,
    source: str,
) -> None:
    conn.execute(
        "INSERT INTO audit_log(actor, action, table_name, row_id, before_json, after_json, source)"
        " VALUES (?, ?, ?, ?, ?, ?, ?)",
        (
            actor,
            action,
            table_name,
            row_id,
            _row_json(before) if before is not None else None,
            _row_json(after) if after is not None else None,
            source,
        ),
    )


class CampaignRepo:
    def __init__(self, conn: sqlite3.Connection) -> None:
        self.conn = conn

    def add(self, new: CampaignCreate, *, actor: Actor = "user", source: str = "cli") -> Campaign:
        """Insert a campaign and its audit row in one transaction.

        A duplicate name raises sqlite3.IntegrityError (campaign.name is UNIQUE).
        """
        with transaction(self.conn):
            row = self.conn.execute(
                "INSERT INTO campaign(name, kind, region_pack, starts_on, ends_on, flags_json,"
                " is_active) VALUES (?, ?, ?, ?, ?, ?, ?) RETURNING *",
                (
                    new.name,
                    new.kind.value,
                    new.region_pack,
                    new.starts_on.isoformat() if new.starts_on else None,
                    new.ends_on.isoformat() if new.ends_on else None,
                    json.dumps(new.flags, ensure_ascii=False, sort_keys=True),
                    int(new.is_active),
                ),
            ).fetchone()
            assert row is not None
            write_audit(
                self.conn,
                actor=actor,
                action="campaign.add",
                table_name="campaign",
                row_id=int(row["campaign_id"]),
                before=None,
                after=row,
                source=source,
            )
        return Campaign.from_row(row)

    def list(self, *, include_inactive: bool = True) -> list[Campaign]:
        sql = "SELECT * FROM campaign"
        if not include_inactive:
            sql += " WHERE is_active = 1"
        sql += " ORDER BY campaign_id"
        return [Campaign.from_row(r) for r in self.conn.execute(sql)]

    def get_active(self) -> Campaign | None:
        r = self.conn.execute(
            "SELECT * FROM campaign WHERE is_active = 1 ORDER BY campaign_id LIMIT 1"
        ).fetchone()
        return Campaign.from_row(r) if r is not None else None

    def count(self) -> int:
        return int(self.conn.execute("SELECT COUNT(*) FROM campaign").fetchone()[0])


__all__ = ["Actor", "CampaignRepo", "write_audit"]
