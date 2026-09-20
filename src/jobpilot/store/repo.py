"""Repositories. Every write to a state table lands in the same transaction as its audit row.

Landing / cache tables (email_message, email_classification, pii_aliases, rule_stat,
llm_call_log) carry provenance in-row instead of one audit row per message.
"""

from __future__ import annotations

import json
import sqlite3
from collections.abc import Iterable, Iterator, Sequence
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from typing import Any

from jobpilot.domain import (
    STATUS_RANK,
    AliasKind,
    Application,
    ApplicationCreate,
    ApplicationEvent,
    ApplicationStatus,
    Campaign,
    CampaignCreate,
    Company,
    CompanyCreate,
    EmailAccount,
    EmailClassification,
    EmailClassificationCreate,
    EmailMessage,
    EmailMessageCreate,
    EventCreate,
    PiiKind,
    SourceHealth,
    SourceState,
    StatusSetBy,
    Track,
)
from jobpilot.store.db import to_iso, transaction, utc_now_iso

Actor = str  # 'user' | 'llm' | 'system' (enforced by the audit_log CHECK constraint)


def _row_json(row: sqlite3.Row | None) -> str | None:
    if row is None:
        return None
    d: dict[str, Any] = dict(row)
    return json.dumps(d, ensure_ascii=False, sort_keys=True)


def _iso(dt: datetime | None) -> str | None:
    return to_iso(dt) if dt is not None else None


def _now_iso(now: datetime | None) -> str:
    return to_iso(now) if now is not None else utc_now_iso()


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
        (actor, action, table_name, row_id, _row_json(before), _row_json(after), source),
    )


# ---------------------------------------------------------------------------- campaign


class CampaignRepo:
    def __init__(self, conn: sqlite3.Connection) -> None:
        self.conn = conn

    def add(self, new: CampaignCreate, *, actor: Actor = "user", source: str = "cli") -> Campaign:
        """Insert a campaign and its audit row in one transaction.

        A duplicate name raises sqlite3.IntegrityError (campaign.name is UNIQUE). When
        ``new.is_active`` is True, every other active campaign is deactivated first (one audit
        row each) so at most one campaign stays active.
        """
        with transaction(self.conn):
            if new.is_active:
                for other in self.conn.execute(
                    "SELECT * FROM campaign WHERE is_active = 1"
                ).fetchall():
                    deactivated = self.conn.execute(
                        "UPDATE campaign SET is_active = 0 WHERE campaign_id = ? RETURNING *",
                        (other["campaign_id"],),
                    ).fetchone()
                    assert deactivated is not None
                    write_audit(
                        self.conn,
                        actor=actor,
                        action="campaign.set_active",
                        table_name="campaign",
                        row_id=int(other["campaign_id"]),
                        before=other,
                        after=deactivated,
                        source=source,
                    )
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

    def get(self, campaign_id: int) -> Campaign | None:
        r = self.conn.execute(
            "SELECT * FROM campaign WHERE campaign_id = ?", (campaign_id,)
        ).fetchone()
        return Campaign.from_row(r) if r is not None else None

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

    def update(
        self, campaign_id: int, new: CampaignCreate, *, actor: Actor = "user", source: str = "web"
    ) -> Campaign:
        """Replace name / kind / region_pack / dates (is_active and flags untouched). Audited.

        A duplicate name raises sqlite3.IntegrityError; an unknown id raises KeyError.
        """
        with transaction(self.conn):
            before = self.conn.execute(
                "SELECT * FROM campaign WHERE campaign_id = ?", (campaign_id,)
            ).fetchone()
            if before is None:
                raise KeyError(campaign_id)
            row = self.conn.execute(
                "UPDATE campaign SET name = ?, kind = ?, region_pack = ?, starts_on = ?, ends_on = ?"
                " WHERE campaign_id = ? RETURNING *",
                (
                    new.name,
                    new.kind.value,
                    new.region_pack,
                    new.starts_on.isoformat() if new.starts_on else None,
                    new.ends_on.isoformat() if new.ends_on else None,
                    campaign_id,
                ),
            ).fetchone()
            assert row is not None
            write_audit(
                self.conn,
                actor=actor,
                action="campaign.update",
                table_name="campaign",
                row_id=campaign_id,
                before=before,
                after=row,
                source=source,
            )
        return Campaign.from_row(row)

    def set_active(
        self, campaign_id: int, *, actor: Actor = "user", source: str = "web"
    ) -> Campaign:
        """Make one campaign the active one (all others become inactive). Audited."""
        with transaction(self.conn):
            before = self.conn.execute(
                "SELECT * FROM campaign WHERE campaign_id = ?", (campaign_id,)
            ).fetchone()
            if before is None:
                raise KeyError(campaign_id)
            self.conn.execute(
                "UPDATE campaign SET is_active = 0 WHERE is_active = 1 AND campaign_id <> ?",
                (campaign_id,),
            )
            row = self.conn.execute(
                "UPDATE campaign SET is_active = 1 WHERE campaign_id = ? RETURNING *",
                (campaign_id,),
            ).fetchone()
            assert row is not None
            write_audit(
                self.conn,
                actor=actor,
                action="campaign.set_active",
                table_name="campaign",
                row_id=campaign_id,
                before=before,
                after=row,
                source=source,
            )
        return Campaign.from_row(row)

    def delete(
        self, campaign_id: int, *, actor: Actor = "user", source: str = "web"
    ) -> tuple[int, int]:
        """Delete a campaign, cascading its applications (and their events). Audited.

        Returns (deleted_applications, deleted_events). If the deleted campaign was active and
        others remain, the one with the smallest id becomes active. An unknown id raises KeyError.
        """
        with transaction(self.conn):
            before = self.conn.execute(
                "SELECT * FROM campaign WHERE campaign_id = ?", (campaign_id,)
            ).fetchone()
            if before is None:
                raise KeyError(campaign_id)
            app_ids = [
                int(r["application_id"])
                for r in self.conn.execute(
                    "SELECT application_id FROM application WHERE campaign_id = ?", (campaign_id,)
                ).fetchall()
            ]
            app_repo = ApplicationRepo(self.conn)
            n_events = sum(
                app_repo.delete(app_id, actor=actor, source=source) for app_id in app_ids
            )
            self.conn.execute("DELETE FROM campaign WHERE campaign_id = ?", (campaign_id,))
            write_audit(
                self.conn,
                actor=actor,
                action="campaign.delete",
                table_name="campaign",
                row_id=campaign_id,
                before=before,
                after=None,
                source=source,
            )
            if before["is_active"]:
                remaining = self.conn.execute(
                    "SELECT campaign_id FROM campaign ORDER BY campaign_id LIMIT 1"
                ).fetchone()
                if remaining is not None:
                    self.set_active(int(remaining["campaign_id"]), actor=actor, source=source)
        return len(app_ids), n_events

    def count(self) -> int:
        return int(self.conn.execute("SELECT COUNT(*) FROM campaign").fetchone()[0])


# ---------------------------------------------------------------------------- company


class CompanyRepo:
    def __init__(self, conn: sqlite3.Connection) -> None:
        self.conn = conn

    def get(self, company_id: int) -> Company | None:
        r = self.conn.execute(
            "SELECT * FROM company WHERE company_id = ?", (company_id,)
        ).fetchone()
        return Company.from_row(r) if r is not None else None

    def get_by_norm(self, name_norm: str) -> Company | None:
        r = self.conn.execute("SELECT * FROM company WHERE name_norm = ?", (name_norm,)).fetchone()
        return Company.from_row(r) if r is not None else None

    def find_alias(self, kind: AliasKind, alias_norm: str) -> Company | None:
        r = self.conn.execute(
            "SELECT c.* FROM company_alias a JOIN company c ON c.company_id = a.company_id"
            " WHERE a.kind = ? AND a.alias_norm = ?",
            (kind.value, alias_norm),
        ).fetchone()
        return Company.from_row(r) if r is not None else None

    def list_all(self) -> list[Company]:
        return [
            Company.from_row(r)
            for r in self.conn.execute("SELECT * FROM company ORDER BY company_id")
        ]

    def add(self, new: CompanyCreate, *, actor: Actor = "system", source: str = "sync") -> Company:
        with transaction(self.conn):
            row = self.conn.execute(
                "INSERT INTO company(name, name_norm, domain, industry, size_bucket, hq_country,"
                " is_current_employer, notes) VALUES (?, ?, ?, ?, ?, ?, ?, ?) RETURNING *",
                (
                    new.name,
                    new.name_norm,
                    new.domain,
                    new.industry,
                    new.size_bucket,
                    new.hq_country,
                    int(new.is_current_employer),
                    new.notes,
                ),
            ).fetchone()
            assert row is not None
            write_audit(
                self.conn,
                actor=actor,
                action="company.add",
                table_name="company",
                row_id=int(row["company_id"]),
                before=None,
                after=row,
                source=source,
            )
        return Company.from_row(row)

    def add_alias(
        self,
        kind: AliasKind,
        alias_norm: str,
        company_id: int,
        *,
        lang: str | None = None,
        source: str,
    ) -> bool:
        """INSERT OR IGNORE; returns True when a new alias row was written."""
        with transaction(self.conn):
            cur = self.conn.execute(
                "INSERT OR IGNORE INTO company_alias(kind, alias_norm, company_id, lang, source)"
                " VALUES (?, ?, ?, ?, ?)",
                (kind.value, alias_norm, company_id, lang, source),
            )
        return cur.rowcount == 1

    def set_current_employer(
        self, company_id: int, flag: bool, *, actor: Actor = "user", source: str = "cli"
    ) -> Company:
        with transaction(self.conn):
            before = self.conn.execute(
                "SELECT * FROM company WHERE company_id = ?", (company_id,)
            ).fetchone()
            if before is None:
                raise KeyError(company_id)
            row = self.conn.execute(
                "UPDATE company SET is_current_employer = ?, updated_at = ? WHERE company_id = ?"
                " RETURNING *",
                (int(flag), utc_now_iso(), company_id),
            ).fetchone()
            assert row is not None
            write_audit(
                self.conn,
                actor=actor,
                action="company.set_current_employer",
                table_name="company",
                row_id=company_id,
                before=before,
                after=row,
                source=source,
            )
        return Company.from_row(row)

    def current_employer_domains(self) -> set[str]:
        rows = self.conn.execute(
            "SELECT c.domain AS d FROM company c WHERE c.is_current_employer = 1 AND c.domain IS NOT NULL"
            " UNION SELECT a.alias_norm FROM company_alias a JOIN company c ON c.company_id = a.company_id"
            " WHERE c.is_current_employer = 1 AND a.kind = 'domain'"
        ).fetchall()
        return {str(r[0]) for r in rows}


# ---------------------------------------------------------------------------- application


@dataclass(frozen=True)
class AutoUpdate:
    """Fields the status engine may change; None = leave as is. user_status is never touched."""

    auto_status: ApplicationStatus | None = None
    status_set_by: StatusSetBy | None = None
    last_event_at: datetime | None = None
    applied_at: datetime | None = None
    next_action: str | None = None
    next_action_due: datetime | None = None
    deadline_at: datetime | None = None
    portal_url: str | None = None
    job_url: str | None = None
    clear_next_action: bool = False
    force_dates: bool = False


class ApplicationRepo:
    def __init__(self, conn: sqlite3.Connection) -> None:
        self.conn = conn

    def get(self, application_id: int) -> Application | None:
        r = self.conn.execute(
            "SELECT * FROM application WHERE application_id = ?", (application_id,)
        ).fetchone()
        return Application.from_row(r) if r is not None else None

    def find_natural(
        self, campaign_id: int, company_id: int, track: str, role_norm: str
    ) -> Application | None:
        r = self.conn.execute(
            "SELECT * FROM application WHERE campaign_id = ? AND company_id = ? AND track = ?"
            " AND role_norm = ?",
            (campaign_id, company_id, track, role_norm),
        ).fetchone()
        return Application.from_row(r) if r is not None else None

    def add(
        self, new: ApplicationCreate, *, actor: Actor = "system", source: str = "sync"
    ) -> Application:
        with transaction(self.conn):
            row = self.conn.execute(
                "INSERT INTO application(campaign_id, company_id, role, role_norm, track, channel,"
                " origin, job_url, portal_url, notes) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)"
                " RETURNING *",
                (
                    new.campaign_id,
                    new.company_id,
                    new.role,
                    new.role_norm,
                    new.track.value,
                    new.channel,
                    new.origin.value,
                    new.job_url,
                    new.portal_url,
                    new.notes,
                ),
            ).fetchone()
            assert row is not None
            write_audit(
                self.conn,
                actor=actor,
                action="application.add",
                table_name="application",
                row_id=int(row["application_id"]),
                before=None,
                after=row,
                source=source,
            )
        return Application.from_row(row)

    def update_auto(
        self,
        application_id: int,
        upd: AutoUpdate,
        *,
        actor: Actor = "system",
        source: str = "sync",
    ) -> Application:
        """Apply automatic changes; never touches user_status. Audited with before/after."""
        sets: list[str] = ["updated_at = ?"]
        params: list[Any] = [utc_now_iso()]
        if upd.auto_status is not None:
            sets.append("auto_status = ?")
            params.append(upd.auto_status.value)
        if upd.status_set_by is not None:
            sets.append("status_set_by = ?")
            params.append(upd.status_set_by.value)
        if upd.force_dates:
            sets.append("last_event_at = ?")
            params.append(_iso(upd.last_event_at))
            sets.append("applied_at = ?")
            params.append(_iso(upd.applied_at))
        else:
            if upd.last_event_at is not None:
                sets.append("last_event_at = ?")
                params.append(to_iso(upd.last_event_at))
            if upd.applied_at is not None:
                sets.append("applied_at = COALESCE(applied_at, ?)")
                params.append(to_iso(upd.applied_at))
        if upd.clear_next_action:
            sets.append("next_action = NULL")
            sets.append("next_action_due = NULL")
        else:
            if upd.next_action is not None:
                sets.append("next_action = ?")
                params.append(upd.next_action)
            if upd.next_action_due is not None:
                sets.append("next_action_due = ?")
                params.append(to_iso(upd.next_action_due))
        if upd.deadline_at is not None:
            sets.append(
                "deadline_at = CASE WHEN deadline_at IS NULL OR deadline_at > ? THEN ? ELSE deadline_at END"
            )
            params.extend([to_iso(upd.deadline_at), to_iso(upd.deadline_at)])
        if upd.portal_url is not None:
            sets.append("portal_url = COALESCE(portal_url, ?)")
            params.append(upd.portal_url)
        if upd.job_url is not None:
            sets.append("job_url = COALESCE(job_url, ?)")
            params.append(upd.job_url)
        params.append(application_id)
        with transaction(self.conn):
            before = self.conn.execute(
                "SELECT * FROM application WHERE application_id = ?", (application_id,)
            ).fetchone()
            if before is None:
                raise KeyError(application_id)
            row = self.conn.execute(
                f"UPDATE application SET {', '.join(sets)} WHERE application_id = ? RETURNING *",
                params,
            ).fetchone()
            assert row is not None
            if _row_json(before) != _row_json(row):
                write_audit(
                    self.conn,
                    actor=actor,
                    action="application.auto_update",
                    table_name="application",
                    row_id=application_id,
                    before=before,
                    after=row,
                    source=source,
                )
        return Application.from_row(row)

    def set_user_status(
        self,
        application_id: int,
        status: ApplicationStatus | None,
        *,
        excluded_reason: str | None = None,
        actor: Actor = "user",
        source: str = "cli",
    ) -> Application:
        """The user's override (None clears it). Always wins over auto_status."""
        with transaction(self.conn):
            before = self.conn.execute(
                "SELECT * FROM application WHERE application_id = ?", (application_id,)
            ).fetchone()
            if before is None:
                raise KeyError(application_id)
            row = self.conn.execute(
                "UPDATE application SET user_status = ?, status_set_by = ?, excluded_reason = ?,"
                " updated_at = ? WHERE application_id = ? RETURNING *",
                (
                    status.value if status else None,
                    StatusSetBy.USER.value if status else StatusSetBy.SYSTEM.value,
                    excluded_reason,
                    utc_now_iso(),
                    application_id,
                ),
            ).fetchone()
            assert row is not None
            write_audit(
                self.conn,
                actor=actor,
                action="application.set_user_status",
                table_name="application",
                row_id=application_id,
                before=before,
                after=row,
                source=source,
            )
        return Application.from_row(row)

    def update_fields(
        self,
        application_id: int,
        *,
        company_id: int,
        role: str | None,
        role_norm: str,
        track: Track,
        job_url: str | None,
        notes: str | None,
        portal_url: str | None,
        deadline_at: datetime | None,
        next_action: str | None,
        next_action_due: datetime | None,
        actor: Actor = "user",
        source: str = "web",
    ) -> Application:
        """User-initiated field edit (company / role / track / links / dates). Audited.

        An unknown id raises KeyError; a natural-key collision propagates as
        sqlite3.IntegrityError.
        """
        with transaction(self.conn):
            before = self.conn.execute(
                "SELECT * FROM application WHERE application_id = ?", (application_id,)
            ).fetchone()
            if before is None:
                raise KeyError(application_id)
            row = self.conn.execute(
                "UPDATE application SET company_id = ?, role = ?, role_norm = ?, track = ?,"
                " job_url = ?, notes = ?, portal_url = ?, deadline_at = ?, next_action = ?,"
                " next_action_due = ?, updated_at = ? WHERE application_id = ? RETURNING *",
                (
                    company_id,
                    role,
                    role_norm,
                    track.value,
                    job_url,
                    notes,
                    portal_url,
                    _iso(deadline_at),
                    next_action,
                    _iso(next_action_due),
                    utc_now_iso(),
                    application_id,
                ),
            ).fetchone()
            assert row is not None
            write_audit(
                self.conn,
                actor=actor,
                action="application.update",
                table_name="application",
                row_id=application_id,
                before=before,
                after=row,
                source=source,
            )
        return Application.from_row(row)

    def delete(self, application_id: int, *, actor: Actor = "user", source: str = "web") -> int:
        """Delete an application and its events (FK cascade). Returns the deleted event count.

        Every cascaded event gets its own audit row so the ledger keeps each event's content.
        """
        with transaction(self.conn):
            before = self.conn.execute(
                "SELECT * FROM application WHERE application_id = ?", (application_id,)
            ).fetchone()
            if before is None:
                raise KeyError(application_id)
            events = self.conn.execute(
                "SELECT * FROM application_event WHERE application_id = ? ORDER BY event_id",
                (application_id,),
            ).fetchall()
            for ev in events:
                write_audit(
                    self.conn,
                    actor=actor,
                    action="application_event.delete",
                    table_name="application_event",
                    row_id=int(ev["event_id"]),
                    before=ev,
                    after=None,
                    source=source,
                )
            count = len(events)
            self.conn.execute("DELETE FROM application WHERE application_id = ?", (application_id,))
            write_audit(
                self.conn,
                actor=actor,
                action="application.delete",
                table_name="application",
                row_id=application_id,
                before=before,
                after=None,
                source=source,
            )
        return count

    def list_for_campaign(
        self, campaign_id: int, *, statuses: Sequence[ApplicationStatus] | None = None
    ) -> list[Application]:
        sql = "SELECT * FROM application WHERE campaign_id = ?"
        params: list[Any] = [campaign_id]
        if statuses:
            sql += " AND effective_status IN (" + ",".join("?" * len(statuses)) + ")"
            params.extend(s.value for s in statuses)
        sql += " ORDER BY application_id"
        return [Application.from_row(r) for r in self.conn.execute(sql, params)]

    def count_for_campaign(self, campaign_id: int) -> int:
        return int(
            self.conn.execute(
                "SELECT COUNT(*) FROM application WHERE campaign_id = ?", (campaign_id,)
            ).fetchone()[0]
        )


def status_sort_key(status: ApplicationStatus) -> int:
    """Board ordering: active processes first, then terminal ones."""
    return STATUS_RANK.get(status, 0)


# ---------------------------------------------------------------------------- events


class EventRepo:
    def __init__(self, conn: sqlite3.Connection) -> None:
        self.conn = conn

    def add_idempotent(
        self, new: EventCreate, *, actor: Actor = "system", source: str = "sync"
    ) -> tuple[ApplicationEvent, bool]:
        """Insert unless (application_id, event_type, occurred_at, source_ref) exists.

        Returns (row, inserted). Audit is written only when a row was inserted.
        """
        occurred = to_iso(new.occurred_at)
        with transaction(self.conn):
            row = self.conn.execute(
                "INSERT INTO application_event(application_id, event_type, round_no, occurred_at,"
                " source, source_ref, confidence, summary, user_confirmed)"
                " VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)"
                " ON CONFLICT(application_id, event_type, occurred_at, source_ref) DO NOTHING"
                " RETURNING *",
                (
                    new.application_id,
                    new.event_type.value,
                    new.round_no,
                    occurred,
                    new.source.value,
                    new.source_ref,
                    new.confidence,
                    new.summary,
                    int(new.user_confirmed),
                ),
            ).fetchone()
            if row is not None:
                write_audit(
                    self.conn,
                    actor=actor,
                    action="application_event.add",
                    table_name="application_event",
                    row_id=int(row["event_id"]),
                    before=None,
                    after=row,
                    source=source,
                )
                return ApplicationEvent.from_row(row), True
            existing = self.conn.execute(
                "SELECT * FROM application_event WHERE application_id = ? AND event_type = ?"
                " AND occurred_at = ? AND source_ref = ?",
                (new.application_id, new.event_type.value, occurred, new.source_ref),
            ).fetchone()
            assert existing is not None
            return ApplicationEvent.from_row(existing), False

    def get(self, event_id: int) -> ApplicationEvent | None:
        r = self.conn.execute(
            "SELECT * FROM application_event WHERE event_id = ?", (event_id,)
        ).fetchone()
        return ApplicationEvent.from_row(r) if r is not None else None

    def delete(
        self, event_id: int, *, actor: Actor = "user", source: str = "web"
    ) -> ApplicationEvent:
        """Delete one event. Audited. An unknown id raises KeyError."""
        with transaction(self.conn):
            before = self.conn.execute(
                "SELECT * FROM application_event WHERE event_id = ?", (event_id,)
            ).fetchone()
            if before is None:
                raise KeyError(event_id)
            self.conn.execute("DELETE FROM application_event WHERE event_id = ?", (event_id,))
            write_audit(
                self.conn,
                actor=actor,
                action="application_event.delete",
                table_name="application_event",
                row_id=event_id,
                before=before,
                after=None,
                source=source,
            )
        return ApplicationEvent.from_row(before)

    def list_for(self, application_id: int) -> list[ApplicationEvent]:
        rows = self.conn.execute(
            "SELECT * FROM application_event WHERE application_id = ? ORDER BY occurred_at, event_id",
            (application_id,),
        )
        return [ApplicationEvent.from_row(r) for r in rows]

    def has_event_since(self, application_id: int, event_type: str, since: datetime) -> bool:
        r = self.conn.execute(
            "SELECT 1 FROM application_event WHERE application_id = ? AND event_type = ?"
            " AND occurred_at >= ? LIMIT 1",
            (application_id, event_type, to_iso(since)),
        ).fetchone()
        return r is not None


# ---------------------------------------------------------------------------- email accounts


class EmailAccountRepo:
    def __init__(self, conn: sqlite3.Connection) -> None:
        self.conn = conn

    def add(
        self,
        email: str,
        *,
        token_ref: str,
        label: str | None = None,
        actor: Actor = "user",
        source: str = "cli",
    ) -> EmailAccount:
        with transaction(self.conn):
            row = self.conn.execute(
                "INSERT INTO email_account(email, label, token_ref) VALUES (?, ?, ?) RETURNING *",
                (email.casefold(), label, token_ref),
            ).fetchone()
            assert row is not None
            write_audit(
                self.conn,
                actor=actor,
                action="email_account.add",
                table_name="email_account",
                row_id=int(row["account_id"]),
                before=None,
                after=row,
                source=source,
            )
        return EmailAccount.from_row(row)

    def get(self, account_id: int) -> EmailAccount | None:
        r = self.conn.execute(
            "SELECT * FROM email_account WHERE account_id = ?", (account_id,)
        ).fetchone()
        return EmailAccount.from_row(r) if r is not None else None

    def get_by_email(self, email: str) -> EmailAccount | None:
        r = self.conn.execute(
            "SELECT * FROM email_account WHERE email = ?", (email.casefold(),)
        ).fetchone()
        return EmailAccount.from_row(r) if r is not None else None

    def list(self, *, enabled_only: bool = False) -> list[EmailAccount]:
        sql = "SELECT * FROM email_account"
        if enabled_only:
            sql += " WHERE enabled = 1"
        sql += " ORDER BY account_id"
        return [EmailAccount.from_row(r) for r in self.conn.execute(sql)]

    def set_history_id(
        self, account_id: int, history_id: str, *, last_sync_at: datetime | None = None
    ) -> None:
        with transaction(self.conn):
            self.conn.execute(
                "UPDATE email_account SET history_id = ?, last_sync_at = ? WHERE account_id = ?",
                (history_id, _now_iso(last_sync_at), account_id),
            )

    def set_backfill_state(
        self,
        account_id: int,
        *,
        from_history_id: str | None,
        done: bool,
        history_id: str | None = None,
    ) -> None:
        with transaction(self.conn):
            if history_id is not None:
                self.conn.execute(
                    "UPDATE email_account SET backfill_from_history_id = ?, backfill_done = ?,"
                    " history_id = ?, last_sync_at = ? WHERE account_id = ?",
                    (from_history_id, int(done), history_id, utc_now_iso(), account_id),
                )
            else:
                self.conn.execute(
                    "UPDATE email_account SET backfill_from_history_id = ?, backfill_done = ?"
                    " WHERE account_id = ?",
                    (from_history_id, int(done), account_id),
                )

    def set_enabled(
        self, account_id: int, enabled: bool, *, actor: Actor = "user", source: str = "cli"
    ) -> EmailAccount:
        with transaction(self.conn):
            before = self.conn.execute(
                "SELECT * FROM email_account WHERE account_id = ?", (account_id,)
            ).fetchone()
            if before is None:
                raise KeyError(account_id)
            row = self.conn.execute(
                "UPDATE email_account SET enabled = ? WHERE account_id = ? RETURNING *",
                (int(enabled), account_id),
            ).fetchone()
            assert row is not None
            write_audit(
                self.conn,
                actor=actor,
                action="email_account.set_enabled",
                table_name="email_account",
                row_id=account_id,
                before=before,
                after=row,
                source=source,
            )
        return EmailAccount.from_row(row)


# ---------------------------------------------------------------------------- email messages


@dataclass(frozen=True)
class SenderCount:
    key: str
    count: int
    latest_ms: int


@dataclass(frozen=True)
class SendersReport:
    by_domain: list[SenderCount]
    by_address: list[SenderCount]
    by_subject_template: list[SenderCount]
    skipped_label_counts: dict[str, int]
    total: int


class EmailRepo:
    def __init__(self, conn: sqlite3.Connection) -> None:
        self.conn = conn

    def upsert(self, new: EmailMessageCreate) -> tuple[int, bool]:
        """Insert a message; on conflict only upgrade metadata -> full body columns.

        Returns (msg_id, is_new).
        """
        with transaction(self.conn):
            is_new = not self.exists(new.account_id, new.gmail_id)
            row = self.conn.execute(
                "INSERT INTO email_message(account_id, gmail_id, thread_id, history_id,"
                " internal_date_ms, label_ids_json, from_addr, from_domain, from_name,"
                " from_name_public, reply_to_addr, sender_addr, to_addr, message_id_hdr,"
                " in_reply_to, references_hdr, has_list_unsubscribe, headers_json, subject,"
                " subject_public, snippet, snippet_public, body_text, body_urls_json, has_ics,"
                " raw_format, language)"
                " VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)"
                " ON CONFLICT(account_id, gmail_id) DO UPDATE SET"
                "  body_text = CASE WHEN excluded.raw_format = 'full' THEN excluded.body_text ELSE email_message.body_text END,"
                "  body_urls_json = CASE WHEN excluded.raw_format = 'full' THEN excluded.body_urls_json ELSE email_message.body_urls_json END,"
                "  has_ics = CASE WHEN excluded.raw_format = 'full' THEN excluded.has_ics ELSE email_message.has_ics END,"
                "  raw_format = CASE WHEN excluded.raw_format = 'full' THEN 'full' ELSE email_message.raw_format END,"
                "  language = COALESCE(excluded.language, email_message.language),"
                "  history_id = COALESCE(excluded.history_id, email_message.history_id)"
                " RETURNING msg_id",
                (
                    new.account_id,
                    new.gmail_id,
                    new.thread_id,
                    new.history_id,
                    new.internal_date_ms,
                    json.dumps(new.label_ids),
                    new.from_addr,
                    new.from_domain,
                    new.from_name,
                    new.from_name_public,
                    new.reply_to_addr,
                    new.sender_addr,
                    new.to_addr,
                    new.message_id_hdr,
                    new.in_reply_to,
                    new.references_hdr,
                    int(new.has_list_unsubscribe),
                    json.dumps(new.headers, ensure_ascii=False),
                    new.subject,
                    new.subject_public,
                    new.snippet,
                    new.snippet_public,
                    new.body_text,
                    json.dumps(new.body_urls, ensure_ascii=False)
                    if new.body_urls is not None
                    else None,
                    None if new.has_ics is None else int(new.has_ics),
                    new.raw_format,
                    new.language,
                ),
            ).fetchone()
            assert row is not None
            msg_id = int(row["msg_id"])
        return msg_id, is_new

    def exists(self, account_id: int, gmail_id: str) -> bool:
        r = self.conn.execute(
            "SELECT 1 FROM email_message WHERE account_id = ? AND gmail_id = ?",
            (account_id, gmail_id),
        ).fetchone()
        return r is not None

    def known_gmail_ids(self, account_id: int, ids: Sequence[str]) -> set[str]:
        out: set[str] = set()
        for i in range(0, len(ids), 500):
            chunk = ids[i : i + 500]
            rows = self.conn.execute(
                "SELECT gmail_id FROM email_message WHERE account_id = ? AND gmail_id IN ("
                + ",".join("?" * len(chunk))
                + ")",
                (account_id, *chunk),
            ).fetchall()
            out.update(str(r[0]) for r in rows)
        return out

    def get(self, msg_id: int) -> EmailMessage | None:
        r = self.conn.execute("SELECT * FROM email_message WHERE msg_id = ?", (msg_id,)).fetchone()
        return EmailMessage.from_row(r) if r is not None else None

    def get_by_gmail_id(self, account_id: int, gmail_id: str) -> EmailMessage | None:
        r = self.conn.execute(
            "SELECT * FROM email_message WHERE account_id = ? AND gmail_id = ?",
            (account_id, gmail_id),
        ).fetchone()
        return EmailMessage.from_row(r) if r is not None else None

    def count(self, account_id: int | None = None) -> int:
        if account_id is None:
            return int(self.conn.execute("SELECT COUNT(*) FROM email_message").fetchone()[0])
        return int(
            self.conn.execute(
                "SELECT COUNT(*) FROM email_message WHERE account_id = ?", (account_id,)
            ).fetchone()[0]
        )

    def newest_internal_date_ms(self, account_id: int) -> int | None:
        r = self.conn.execute(
            "SELECT MAX(internal_date_ms) FROM email_message WHERE account_id = ?", (account_id,)
        ).fetchone()
        return int(r[0]) if r is not None and r[0] is not None else None

    def iter_unclassified(self, *, prompt_version: str | None = None) -> Iterator[EmailMessage]:
        """Messages without a classification (or with a stale LLM prompt version)."""
        if prompt_version is None:
            sql = (
                "SELECT m.* FROM email_message m LEFT JOIN email_classification c ON c.msg_id = m.msg_id"
                " WHERE c.msg_id IS NULL ORDER BY m.internal_date_ms, m.msg_id"
            )
            params: tuple[Any, ...] = ()
        else:
            sql = (
                "SELECT m.* FROM email_message m LEFT JOIN email_classification c ON c.msg_id = m.msg_id"
                " WHERE c.msg_id IS NULL OR (c.method = 'llm' AND c.prompt_version <> ?)"
                " ORDER BY m.internal_date_ms, m.msg_id"
            )
            params = (prompt_version,)
        for r in self.conn.execute(sql, params).fetchall():
            yield EmailMessage.from_row(r)

    def thread_application(self, account_id: int, thread_id: str) -> int | None:
        r = self.conn.execute(
            "SELECT c.application_id FROM email_classification c JOIN email_message m ON m.msg_id = c.msg_id"
            " WHERE m.account_id = ? AND m.thread_id = ? AND c.application_id IS NOT NULL"
            " ORDER BY m.internal_date_ms DESC LIMIT 1",
            (account_id, thread_id),
        ).fetchone()
        return int(r[0]) if r is not None else None

    def list_for_application(self, application_id: int) -> list[EmailMessage]:
        rows = self.conn.execute(
            "SELECT m.* FROM email_message m JOIN email_classification c ON c.msg_id = m.msg_id"
            " WHERE c.application_id = ? ORDER BY m.internal_date_ms",
            (application_id,),
        ).fetchall()
        return [EmailMessage.from_row(r) for r in rows]

    def senders_report(
        self, *, account_id: int | None = None, top: int = 50, skipped_labels: Sequence[str] = ()
    ) -> SendersReport:
        where = " WHERE account_id = ?" if account_id is not None else ""
        params: tuple[Any, ...] = (account_id,) if account_id is not None else ()

        def q(expr: str) -> list[SenderCount]:
            rows = self.conn.execute(
                f"SELECT {expr} AS k, COUNT(*) AS n, MAX(internal_date_ms) AS latest FROM email_message"
                f"{where} GROUP BY k ORDER BY n DESC, latest DESC LIMIT ?",
                (*params, top),
            ).fetchall()
            return [SenderCount(str(r["k"] or ""), int(r["n"]), int(r["latest"])) for r in rows]

        subject_template = (
            "TRIM(REPLACE(REPLACE(REPLACE(REPLACE(REPLACE(REPLACE(REPLACE(REPLACE(REPLACE(REPLACE("
            "subject_public, '0', '#'), '1', '#'), '2', '#'), '3', '#'), '4', '#'), '5', '#'),"
            " '6', '#'), '7', '#'), '8', '#'), '9', '#'))"
        )
        skipped: dict[str, int] = {}
        for label in skipped_labels:
            r = self.conn.execute(
                f"SELECT COUNT(*) FROM email_message{where}{' AND' if where else ' WHERE'}"
                " label_ids_json LIKE ?",
                (*params, f'%"{label}"%'),
            ).fetchone()
            skipped[label] = int(r[0])
        total = self.conn.execute(f"SELECT COUNT(*) FROM email_message{where}", params).fetchone()[
            0
        ]
        return SendersReport(
            by_domain=q("from_domain"),
            by_address=q("from_addr"),
            by_subject_template=q(subject_template),
            skipped_label_counts=skipped,
            total=int(total),
        )


# ---------------------------------------------------------------------------- classification


class ClassificationRepo:
    def __init__(self, conn: sqlite3.Connection) -> None:
        self.conn = conn

    def upsert(self, new: EmailClassificationCreate) -> EmailClassification:
        cols = {
            "msg_id": new.msg_id,
            "is_job_related": int(new.is_job_related),
            "category": new.category.value,
            "company": new.company,
            "company_slug": new.company_slug,
            "role": new.role,
            "ats": new.ats,
            "stage": new.stage,
            "event_type": new.event_type.value if new.event_type else None,
            "action_required": int(new.action_required),
            "deadline_iso": new.deadline_iso,
            "event_start_iso": new.event_start_iso,
            "event_end_iso": new.event_end_iso,
            "meeting_url": new.meeting_url,
            "meeting_link_pending": int(new.meeting_link_pending),
            "portal_url": new.portal_url,
            "language": new.language,
            "confidence": new.confidence,
            "injection_suspected": int(new.injection_suspected),
            "method": new.method.value,
            "rule_id": new.rule_id,
            "model": new.model,
            "prompt_version": new.prompt_version,
            "input_hash": new.input_hash,
            "scores_json": json.dumps(new.scores, ensure_ascii=False)
            if new.scores is not None
            else None,
            "needs_review": int(new.needs_review),
            "review_reason": new.review_reason.value if new.review_reason else None,
            "candidates_json": (
                json.dumps(new.candidates, ensure_ascii=False)
                if new.candidates is not None
                else None
            ),
            "application_id": new.application_id,
            "event_id": new.event_id,
            "user_verdict": new.user_verdict,
            "classified_at": utc_now_iso(),
        }
        names = list(cols)
        updates = ", ".join(f"{c} = excluded.{c}" for c in names if c != "msg_id")
        with transaction(self.conn):
            row = self.conn.execute(
                f"INSERT INTO email_classification({', '.join(names)}) VALUES ({', '.join('?' * len(names))})"
                f" ON CONFLICT(msg_id) DO UPDATE SET {updates} RETURNING *",
                [cols[c] for c in names],
            ).fetchone()
            assert row is not None
        return EmailClassification.from_row(row)

    def get(self, msg_id: int) -> EmailClassification | None:
        r = self.conn.execute(
            "SELECT * FROM email_classification WHERE msg_id = ?", (msg_id,)
        ).fetchone()
        return EmailClassification.from_row(r) if r is not None else None

    def cache_lookup(
        self, msg_id: int, *, prompt_version: str, input_hash: str
    ) -> EmailClassification | None:
        r = self.conn.execute(
            "SELECT * FROM email_classification WHERE msg_id = ? AND method = 'llm'"
            " AND prompt_version = ? AND input_hash = ?",
            (msg_id, prompt_version, input_hash),
        ).fetchone()
        return EmailClassification.from_row(r) if r is not None else None

    def list_needs_review(self, *, limit: int = 100) -> list[EmailClassification]:
        rows = self.conn.execute(
            "SELECT c.* FROM email_classification c JOIN email_message m ON m.msg_id = c.msg_id"
            " WHERE c.needs_review = 1 AND c.user_verdict IS NULL"
            " ORDER BY m.internal_date_ms DESC LIMIT ?",
            (limit,),
        ).fetchall()
        return [EmailClassification.from_row(r) for r in rows]

    def count_needs_review(self, application_id: int | None = None) -> int:
        if application_id is None:
            r = self.conn.execute(
                "SELECT COUNT(*) FROM email_classification WHERE needs_review = 1 AND user_verdict IS NULL"
            ).fetchone()
        else:
            r = self.conn.execute(
                "SELECT COUNT(*) FROM email_classification WHERE needs_review = 1"
                " AND user_verdict IS NULL AND application_id = ?",
                (application_id,),
            ).fetchone()
        return int(r[0])

    def link(self, msg_id: int, *, application_id: int | None, event_id: int | None) -> None:
        with transaction(self.conn):
            self.conn.execute(
                "UPDATE email_classification SET application_id = ?, event_id = ? WHERE msg_id = ?",
                (application_id, event_id, msg_id),
            )


# ---------------------------------------------------------------------------- rules


@dataclass(frozen=True)
class RuleRow:
    rule_id: str
    kind: str  # sender | url | phrase
    region_pack: str
    definition_hash: str
    from_pattern: str | None = None
    subject_pattern: str | None = None
    body_url_pattern: str | None = None
    platform: str | None = None
    category: str | None = None
    gate: bool = False
    verified: bool = False
    source_url: str | None = None


class RuleRepo:
    def __init__(self, conn: sqlite3.Connection) -> None:
        self.conn = conn

    def sync(self, rules: Iterable[RuleRow]) -> int:
        """Mirror the loaded rule set; a changed definition resets its rule_stat. Returns changes."""
        changed = 0
        with transaction(self.conn):
            for r in rules:
                prev = self.conn.execute(
                    "SELECT definition_hash FROM classification_rule WHERE rule_id = ?",
                    (r.rule_id,),
                ).fetchone()
                if prev is not None and str(prev[0]) == r.definition_hash:
                    continue
                changed += 1
                self.conn.execute(
                    "INSERT INTO classification_rule(rule_id, kind, region_pack, from_pattern,"
                    " subject_pattern, body_url_pattern, platform, category, gate, verified,"
                    " source_url, definition_hash, loaded_at)"
                    " VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)"
                    " ON CONFLICT(rule_id) DO UPDATE SET kind = excluded.kind,"
                    " region_pack = excluded.region_pack, from_pattern = excluded.from_pattern,"
                    " subject_pattern = excluded.subject_pattern, body_url_pattern = excluded.body_url_pattern,"
                    " platform = excluded.platform, category = excluded.category, gate = excluded.gate,"
                    " verified = excluded.verified, source_url = excluded.source_url,"
                    " definition_hash = excluded.definition_hash, loaded_at = excluded.loaded_at",
                    (
                        r.rule_id,
                        r.kind,
                        r.region_pack,
                        r.from_pattern,
                        r.subject_pattern,
                        r.body_url_pattern,
                        r.platform,
                        r.category,
                        int(r.gate),
                        int(r.verified),
                        r.source_url,
                        r.definition_hash,
                        utc_now_iso(),
                    ),
                )
                if prev is not None:
                    self.conn.execute("DELETE FROM rule_stat WHERE rule_id = ?", (r.rule_id,))
        return changed

    def bump_fired(self, rule_id: str, *, at: datetime | None = None) -> None:
        with transaction(self.conn):
            self.conn.execute(
                "INSERT INTO rule_stat(rule_id, n_fired, last_fired_at) VALUES (?, 1, ?)"
                " ON CONFLICT(rule_id) DO UPDATE SET n_fired = n_fired + 1, last_fired_at = excluded.last_fired_at",
                (rule_id, _now_iso(at)),
            )

    def bump_verdict(self, rule_id: str, *, confirmed: bool) -> None:
        col = "n_confirmed" if confirmed else "n_rejected"
        with transaction(self.conn):
            self.conn.execute(
                f"INSERT INTO rule_stat(rule_id, {col}) VALUES (?, 1)"
                f" ON CONFLICT(rule_id) DO UPDATE SET {col} = {col} + 1",
                (rule_id,),
            )

    def stats(self) -> list[sqlite3.Row]:
        return self.conn.execute(
            "SELECT r.rule_id, r.kind, r.region_pack, r.verified, s.n_fired, s.n_confirmed, s.n_rejected,"
            " s.last_fired_at FROM classification_rule r LEFT JOIN rule_stat s ON s.rule_id = r.rule_id"
            " ORDER BY COALESCE(s.n_fired, 0) DESC, r.rule_id"
        ).fetchall()


# ---------------------------------------------------------------------------- pii aliases


class PiiRepo:
    def __init__(self, conn: sqlite3.Connection) -> None:
        self.conn = conn

    def alias_for(self, kind: PiiKind, value_hash: str) -> str:
        """Return the stable alias for a hashed value, allocating '[kind:n]' when unseen."""
        r = self.conn.execute(
            "SELECT alias FROM pii_aliases WHERE value_hash = ?", (value_hash,)
        ).fetchone()
        if r is not None:
            return str(r[0])
        with transaction(self.conn):
            n = int(
                self.conn.execute(
                    "SELECT COUNT(*) FROM pii_aliases WHERE kind = ?", (kind.value,)
                ).fetchone()[0]
            )
            alias = f"[{kind.value}:{n + 1}]"
            self.conn.execute(
                "INSERT INTO pii_aliases(alias, kind, value_hash) VALUES (?, ?, ?)",
                (alias, kind.value, value_hash),
            )
        return alias

    def count(self) -> int:
        return int(self.conn.execute("SELECT COUNT(*) FROM pii_aliases").fetchone()[0])


# ---------------------------------------------------------------------------- llm call log


class LlmCallRepo:
    def __init__(self, conn: sqlite3.Connection) -> None:
        self.conn = conn

    def add(
        self,
        *,
        purpose: str,
        msg_id: int | None,
        model: str,
        provider: str | None,
        prompt_version: str,
        input_tokens: int,
        output_tokens: int,
        cache_read_tokens: int = 0,
        cache_write_tokens: int = 0,
        requests: int = 1,
        cost_usd: str | None,
        price_source: str,
        status: str,
    ) -> int:
        with transaction(self.conn):
            row = self.conn.execute(
                "INSERT INTO llm_call_log(purpose, msg_id, model, provider, prompt_version, input_tokens,"
                " output_tokens, cache_read_tokens, cache_write_tokens, requests, cost_usd, price_source,"
                " status) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?) RETURNING id",
                (
                    purpose,
                    msg_id,
                    model,
                    provider,
                    prompt_version,
                    input_tokens,
                    output_tokens,
                    cache_read_tokens,
                    cache_write_tokens,
                    requests,
                    cost_usd,
                    price_source,
                    status,
                ),
            ).fetchone()
            assert row is not None
        return int(row[0])

    def summary(self) -> tuple[int, float, int]:
        """(calls, total_cost_usd, calls_with_unknown_price)."""
        r = self.conn.execute(
            "SELECT COUNT(*), COALESCE(SUM(CAST(cost_usd AS REAL)), 0.0),"
            " SUM(CASE WHEN cost_usd IS NULL THEN 1 ELSE 0 END) FROM llm_call_log"
        ).fetchone()
        return int(r[0]), float(r[1]), int(r[2] or 0)


# ---------------------------------------------------------------------------- source state


_MAX_BACKOFF_SECONDS = 3600
_BASE_BACKOFF_SECONDS = 90


class SourceStateRepo:
    def __init__(self, conn: sqlite3.Connection) -> None:
        self.conn = conn

    def get(self, source: str) -> SourceState | None:
        r = self.conn.execute("SELECT * FROM source_state WHERE source = ?", (source,)).fetchone()
        return SourceState.from_row(r) if r is not None else None

    def list(self) -> list[SourceState]:
        return [
            SourceState.from_row(r)
            for r in self.conn.execute("SELECT * FROM source_state ORDER BY source")
        ]

    def _audit_transition(
        self, before: sqlite3.Row | None, after: sqlite3.Row, *, source_tag: str
    ) -> None:
        if before is None or str(before["status"]) != str(after["status"]):
            write_audit(
                self.conn,
                actor="system",
                action="source_state.status",
                table_name="source_state",
                row_id=None,
                before=before,
                after=after,
                source=source_tag,
            )

    def mark_success(
        self,
        source: str,
        *,
        transport: str,
        cursor: str | None = None,
        data_as_of: datetime | None = None,
        now: datetime | None = None,
    ) -> SourceState:
        ts = _now_iso(now)
        with transaction(self.conn):
            before = self.conn.execute(
                "SELECT * FROM source_state WHERE source = ?", (source,)
            ).fetchone()
            row = self.conn.execute(
                "INSERT INTO source_state(source, transport, status, cursor, last_success_at, last_error,"
                " failure_streak, next_retry_at, data_as_of, updated_at)"
                " VALUES (?, ?, 'healthy', ?, ?, NULL, 0, NULL, ?, ?)"
                " ON CONFLICT(source) DO UPDATE SET transport = excluded.transport, status = 'healthy',"
                " cursor = COALESCE(excluded.cursor, source_state.cursor), last_success_at = excluded.last_success_at,"
                " last_error = NULL, failure_streak = 0, next_retry_at = NULL,"
                " data_as_of = COALESCE(excluded.data_as_of, source_state.data_as_of), updated_at = excluded.updated_at"
                " RETURNING *",
                (source, transport, cursor, ts, _iso(data_as_of), ts),
            ).fetchone()
            assert row is not None
            self._audit_transition(before, row, source_tag="sync")
        return SourceState.from_row(row)

    def mark_failure(
        self,
        source: str,
        *,
        transport: str,
        error_label: str,
        auth_required: bool = False,
        now: datetime | None = None,
    ) -> SourceState:
        """Record a failure: streak+1, exponential backoff, status degraded/unavailable/auth_required."""
        now_dt = now or datetime.now(UTC)
        with transaction(self.conn):
            before = self.conn.execute(
                "SELECT * FROM source_state WHERE source = ?", (source,)
            ).fetchone()
            streak = int(before["failure_streak"]) + 1 if before is not None else 1
            if auth_required:
                status = SourceHealth.AUTH_REQUIRED
            elif streak >= 3:
                status = SourceHealth.UNAVAILABLE
            else:
                status = SourceHealth.DEGRADED
            backoff = min(_BASE_BACKOFF_SECONDS * (2 ** (streak - 1)), _MAX_BACKOFF_SECONDS)
            next_retry = now_dt + timedelta(seconds=backoff)
            row = self.conn.execute(
                "INSERT INTO source_state(source, transport, status, last_error, failure_streak,"
                " next_retry_at, updated_at) VALUES (?, ?, ?, ?, ?, ?, ?)"
                " ON CONFLICT(source) DO UPDATE SET transport = excluded.transport, status = excluded.status,"
                " last_error = excluded.last_error, failure_streak = excluded.failure_streak,"
                " next_retry_at = excluded.next_retry_at, updated_at = excluded.updated_at RETURNING *",
                (
                    source,
                    transport,
                    status.value,
                    error_label[:200],
                    streak,
                    to_iso(next_retry),
                    to_iso(now_dt),
                ),
            ).fetchone()
            assert row is not None
            self._audit_transition(before, row, source_tag="sync")
        return SourceState.from_row(row)

    def mark_disabled(self, source: str, *, transport: str = "google-readonly-http") -> SourceState:
        with transaction(self.conn):
            before = self.conn.execute(
                "SELECT * FROM source_state WHERE source = ?", (source,)
            ).fetchone()
            row = self.conn.execute(
                "INSERT INTO source_state(source, transport, status, updated_at) VALUES (?, ?, 'disabled', ?)"
                " ON CONFLICT(source) DO UPDATE SET status = 'disabled', updated_at = excluded.updated_at"
                " RETURNING *",
                (source, transport, utc_now_iso()),
            ).fetchone()
            assert row is not None
            self._audit_transition(before, row, source_tag="cli")
        return SourceState.from_row(row)


__all__ = [
    "Actor",
    "ApplicationRepo",
    "AutoUpdate",
    "CampaignRepo",
    "ClassificationRepo",
    "CompanyRepo",
    "EmailAccountRepo",
    "EmailRepo",
    "EventRepo",
    "LlmCallRepo",
    "PiiRepo",
    "RuleRepo",
    "RuleRow",
    "SenderCount",
    "SendersReport",
    "SourceStateRepo",
    "status_sort_key",
    "write_audit",
]
