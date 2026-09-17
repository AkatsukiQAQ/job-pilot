"""Connection factory (WAL / foreign keys / busy timeout / Row) and idempotent migrations.

Migrations are numbered ``NNNN_name.sql`` files packaged next to this module. Each file is
applied inside one explicit transaction and recorded in ``schema_migrations`` with a sha256
checksum; a file that changes after being applied fails loudly.
"""

from __future__ import annotations

import hashlib
import re
import sqlite3
from collections.abc import Iterator
from contextlib import contextmanager
from datetime import UTC, datetime
from importlib.resources import files
from importlib.resources.abc import Traversable
from pathlib import Path

_MIGRATION_RE = re.compile(r"^(\d{4})_([a-z0-9_]+)\.sql$")


class MigrationError(RuntimeError):
    """Migration runner failure."""


class MigrationChecksumMismatch(MigrationError):
    """An already-applied migration file was edited."""


def utc_now_iso() -> str:
    return datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%S.%f")[:-3] + "Z"


def connect(path: Path | str) -> sqlite3.Connection:
    """Open (and create if needed) the database with the project's PRAGMA set."""
    p = Path(path)
    if str(p) != ":memory:":
        p.parent.mkdir(parents=True, exist_ok=True)
    # autocommit=True: the driver never opens implicit transactions; transaction() is explicit.
    conn = sqlite3.connect(p, timeout=5.0, autocommit=True)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")
    conn.execute("PRAGMA busy_timeout=5000")
    conn.execute("PRAGMA synchronous=NORMAL")
    return conn


@contextmanager
def transaction(conn: sqlite3.Connection) -> Iterator[sqlite3.Connection]:
    conn.execute("BEGIN")
    try:
        yield conn
    except BaseException:
        conn.execute("ROLLBACK")
        raise
    conn.execute("COMMIT")


def default_migrations_dir() -> Traversable:
    return files("jobpilot.store") / "migrations"


def _ensure_schema_table(conn: sqlite3.Connection) -> None:
    conn.execute(
        "CREATE TABLE IF NOT EXISTS schema_migrations("
        " version INTEGER PRIMARY KEY, name TEXT NOT NULL,"
        " applied_at TEXT NOT NULL, checksum TEXT NOT NULL)"
    )


def list_migrations(migrations: Traversable | Path | None = None) -> list[tuple[int, str, str]]:
    """Return (version, name, sql) sorted by version. Line endings are normalised to LF."""
    root = migrations or default_migrations_dir()
    out: list[tuple[int, str, str]] = []
    for entry in root.iterdir():
        m = _MIGRATION_RE.match(entry.name)
        if m:
            sql = entry.read_text(encoding="utf-8").replace("\r\n", "\n")
            out.append((int(m.group(1)), m.group(2), sql))
    out.sort()
    return out


def latest_available_version(migrations: Traversable | Path | None = None) -> int:
    versions = [v for v, _, _ in list_migrations(migrations)]
    return max(versions, default=0)


def current_version(conn: sqlite3.Connection) -> int:
    _ensure_schema_table(conn)
    row = conn.execute("SELECT COALESCE(MAX(version), 0) FROM schema_migrations").fetchone()
    return int(row[0])


def run_migrations(
    conn: sqlite3.Connection, migrations: Traversable | Path | None = None
) -> list[str]:
    """Apply pending migrations; idempotent; refuses if an applied file changed."""
    _ensure_schema_table(conn)
    applied: dict[int, str] = {
        int(r["version"]): str(r["checksum"])
        for r in conn.execute("SELECT version, checksum FROM schema_migrations")
    }
    done: list[str] = []
    for version, name, sql in list_migrations(migrations):
        checksum = hashlib.sha256(sql.encode("utf-8")).hexdigest()
        if version in applied:
            if applied[version] != checksum:
                raise MigrationChecksumMismatch(
                    f"{version:04d}_{name}.sql changed after being applied"
                )
            continue
        with transaction(conn):
            # autocommit=True: executescript performs no implicit COMMIT, so the file runs inside
            # our transaction. Migration files must not contain BEGIN/COMMIT.
            conn.executescript(sql)
            conn.execute(
                "INSERT INTO schema_migrations(version, name, applied_at, checksum)"
                " VALUES (?, ?, ?, ?)",
                (version, name, utc_now_iso(), checksum),
            )
        done.append(f"{version:04d}_{name}")
    return done


def has_fts5(conn: sqlite3.Connection) -> bool:
    row = conn.execute(
        "SELECT 1 FROM pragma_compile_options WHERE compile_options = 'ENABLE_FTS5'"
    ).fetchone()
    return row is not None


__all__ = [
    "MigrationChecksumMismatch",
    "MigrationError",
    "connect",
    "current_version",
    "default_migrations_dir",
    "has_fts5",
    "latest_available_version",
    "list_migrations",
    "run_migrations",
    "transaction",
    "utc_now_iso",
]
