-- 0001_init: campaign + audit_log.
-- Rules: no seed rows (decision D16); no BEGIN/COMMIT (the runner wraps each file in one
-- transaction); timestamps are UTC ISO-8601 text; dates are ISO YYYY-MM-DD text.
-- Evolution: this file is edited in place until the Phase 1 exit criteria pass (only the
-- author's local DB exists; schema_migrations.checksum turns an edit into a loud error, so
-- delete the DB and re-run `jobpilot campaign add`). After Phase 1 it is frozen and later
-- changes go to 0002_*.sql and onwards.

CREATE TABLE campaign (
    campaign_id INTEGER PRIMARY KEY,
    name        TEXT    NOT NULL UNIQUE,
    kind        TEXT    NOT NULL CHECK (kind IN ('newgrad', 'midcareer', 'intern', 'other')),
    region_pack TEXT    NOT NULL,                 -- key in the jobpilot.regions registry
    starts_on   TEXT,                             -- nullable ISO date
    ends_on     TEXT,                             -- nullable ISO date
    flags_json  TEXT    NOT NULL DEFAULT '{}',    -- e.g. {"international_student": true}
    is_active   INTEGER NOT NULL DEFAULT 1 CHECK (is_active IN (0, 1)),
    created_at  TEXT    NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ', 'now'))
);

CREATE INDEX campaign_is_active_idx ON campaign (is_active);

-- Every change (automatic or manual) is mirrored here with before/after images.
CREATE TABLE audit_log (
    id          INTEGER PRIMARY KEY,
    ts          TEXT    NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ', 'now')),
    actor       TEXT    NOT NULL CHECK (actor IN ('user', 'llm', 'system')),
    action      TEXT    NOT NULL,                 -- e.g. 'campaign.add'
    table_name  TEXT    NOT NULL,
    row_id      INTEGER,
    before_json TEXT,
    after_json  TEXT,
    source      TEXT    NOT NULL                  -- 'cli' | 'mcp' | 'web' | 'sync' | ...
);

CREATE INDEX audit_log_table_row_idx ON audit_log (table_name, row_id);
