-- 0001_init: Phase 0 (campaign, audit_log) + Phase 1 tracking domain, appended in place.
-- Rules: no seed rows (decision D16); no BEGIN/COMMIT at line start (the runner wraps the whole file
-- in one transaction; trigger bodies keep BEGIN on the CREATE TRIGGER line); timestamps are UTC
-- ISO-8601 text; dates are ISO YYYY-MM-DD text. Every CHECK list mirrors an enum in jobpilot.domain
-- (tests/test_db.py asserts equality). Edited in place until the Phase 1 exit criteria pass (only the
-- author's local DB exists; schema_migrations.checksum turns an edit into a loud error, so delete the
-- DB and re-run `jobpilot init` / `campaign add` / `auth google`). Frozen afterwards; 0002+ for changes.

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

-- Every change (automatic or manual) to a state table is mirrored here with before/after images.
-- Raw landing / derived-cache tables (email_message, email_classification, pii_aliases, rule_stat,
-- llm_call_log) carry their provenance in-row instead of one audit row per message.
CREATE TABLE audit_log (
    id          INTEGER PRIMARY KEY,
    ts          TEXT    NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ', 'now')),
    actor       TEXT    NOT NULL CHECK (actor IN ('user', 'llm', 'system')),
    action      TEXT    NOT NULL,                 -- e.g. 'campaign.add', 'application.auto_update'
    table_name  TEXT    NOT NULL,
    row_id      INTEGER,
    before_json TEXT,
    after_json  TEXT,
    source      TEXT    NOT NULL                  -- 'cli' | 'init' | 'sync' | 'mcp' | 'web' | ...
);
CREATE INDEX audit_log_table_row_idx ON audit_log (table_name, row_id);

-- ---------------------------------------------------------------- companies

CREATE TABLE company (
    company_id          INTEGER PRIMARY KEY,
    name                TEXT    NOT NULL,                -- display form as first seen
    name_norm           TEXT    NOT NULL UNIQUE,         -- services.resolve.normalize_company_name()
    domain              TEXT,                            -- registrable sender domain, lowercase; NULL when only seen via a relay/ATS
    industry            TEXT,
    size_bucket         TEXT,
    hq_country          TEXT,                            -- ISO 3166-1 alpha-2 or NULL
    is_current_employer INTEGER NOT NULL DEFAULT 0 CHECK (is_current_employer IN (0, 1)),
    notes               TEXT,
    created_at          TEXT    NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ', 'now')),
    updated_at          TEXT    NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ', 'now'))
);
CREATE INDEX company_domain_idx ON company (domain);

-- kind: name (normalised display name) | domain (registrable sender domain) | slug ('<platform>/<tenant>')
CREATE TABLE company_alias (
    kind        TEXT    NOT NULL CHECK (kind IN ('name', 'domain', 'slug')),
    alias_norm  TEXT    NOT NULL,
    company_id  INTEGER NOT NULL REFERENCES company (company_id) ON DELETE CASCADE,
    lang        TEXT    CHECK (lang IS NULL OR lang IN ('en', 'ja', 'zh')),
    source      TEXT    NOT NULL,                        -- 'user' | 'import' | 'sender_domain' | 'rule:<rule_id>' | 'llm'
    created_at  TEXT    NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ', 'now')),
    PRIMARY KEY (kind, alias_norm)
) WITHOUT ROWID;
CREATE INDEX company_alias_company_idx ON company_alias (company_id);

-- ---------------------------------------------------------------- applications

CREATE TABLE application (
    application_id   INTEGER PRIMARY KEY,
    campaign_id      INTEGER NOT NULL REFERENCES campaign (campaign_id),
    company_id       INTEGER NOT NULL REFERENCES company (company_id),
    canonical_id     INTEGER,                            -- Phase 4 job_canonical.id (FK arrives in 0006)
    role             TEXT,
    role_norm        TEXT    NOT NULL DEFAULT '',        -- '' when unknown; part of the natural key
    track            TEXT    NOT NULL CHECK (track IN ('intern', 'newgrad', 'midcareer', 'other')),
    channel          TEXT,                               -- 'gmail' | 'linkedin_easy_apply' | 'line' | 'portal' | 'manual'
    auto_status      TEXT    NOT NULL DEFAULT 'unrecorded'
                     CHECK (auto_status IN ('unrecorded','considering','preparing','applied','assessment','interviewing','offer','accepted','joined','rejected','withdrawn','unsuitable')),
    user_status      TEXT
                     CHECK (user_status IS NULL OR user_status IN ('unrecorded','considering','preparing','applied','assessment','interviewing','offer','accepted','joined','rejected','withdrawn','unsuitable')),
    effective_status TEXT    GENERATED ALWAYS AS (COALESCE(user_status, auto_status)) VIRTUAL,
    status_set_by    TEXT    NOT NULL DEFAULT 'system' CHECK (status_set_by IN ('user', 'rule', 'llm', 'import', 'system')),
    origin           TEXT    NOT NULL DEFAULT 'auto' CHECK (origin IN ('auto', 'manual', 'import')),  -- 'auto' = Phase 1 exception D23
    applied_at       TEXT,
    last_event_at    TEXT,                               -- max occurred_at of non-system, non-note events
    next_action      TEXT,                               -- 'follow_up' | 'portal_check' | 'await_link' | free text
    next_action_due  TEXT,
    deadline_at      TEXT,
    excluded_reason  TEXT,
    job_url          TEXT,
    portal_url       TEXT,
    notes            TEXT,
    created_at       TEXT    NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ', 'now')),
    updated_at       TEXT    NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ', 'now')),
    UNIQUE (campaign_id, company_id, track, role_norm),
    CHECK (excluded_reason IS NULL OR COALESCE(user_status, auto_status) = 'unsuitable')
);
CREATE INDEX application_campaign_status_idx ON application (campaign_id, effective_status);
CREATE INDEX application_company_idx        ON application (company_id);
CREATE INDEX application_last_event_idx     ON application (last_event_at);

-- append-only; source_ref NOT NULL DEFAULT '' so the UNIQUE key never contains a NULL
CREATE TABLE application_event (
    event_id       INTEGER PRIMARY KEY,
    application_id INTEGER NOT NULL REFERENCES application (application_id) ON DELETE CASCADE,
    event_type     TEXT    NOT NULL CHECK (event_type IN (
                     'entry','es_submitted','document_screening','ack','viewed','casual_interview','web_test','assessment',
                     'interview','final_interview','scheduling','pass','rejection','offer_informal','offer','offer_meeting',
                     'accepted','resignation_negotiation','joined','withdrawn','portal_check_required','followup_needed','note')),
    round_no       INTEGER CHECK (round_no IS NULL OR round_no >= 1),
    occurred_at    TEXT    NOT NULL,                     -- UTC ISO
    source         TEXT    NOT NULL CHECK (source IN ('gmail', 'gcal', 'linkedin_export', 'chat', 'manual', 'import', 'system')),
    source_ref     TEXT    NOT NULL DEFAULT '',          -- 'gmail:<account_id>:<gmail_id>' | 'followup:<application_id>:<last_event_at>'
    confidence     REAL    NOT NULL DEFAULT 1.0 CHECK (confidence >= 0 AND confidence <= 1),
    summary        TEXT,                                 -- scrubbed subject, <= 120 chars
    user_confirmed INTEGER NOT NULL DEFAULT 0 CHECK (user_confirmed IN (0, 1)),
    created_at     TEXT    NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ', 'now')),
    UNIQUE (application_id, event_type, occurred_at, source_ref)
);
CREATE INDEX application_event_app_idx ON application_event (application_id, occurred_at);

-- ---------------------------------------------------------------- mail (multiple accounts, D20)

CREATE TABLE email_account (
    account_id               INTEGER PRIMARY KEY,
    email                    TEXT    NOT NULL UNIQUE,   -- casefolded users.getProfile().emailAddress, confirmed after consent
    label                    TEXT,                      -- optional user label (--account-label)
    provider                 TEXT    NOT NULL DEFAULT 'google' CHECK (provider IN ('google')),
    token_ref                TEXT    NOT NULL UNIQUE,   -- SecretStore qualifier: 'acct-' || substr(sha256(casefold(email)), 1, 16); token JSON never lives here
    history_id               TEXT,                      -- incremental cursor = history.list response historyId; NULL until the first backfill completes
    backfill_from_history_id TEXT,                      -- profile.historyId captured BEFORE listing; becomes history_id when the backfill finishes
    backfill_done            INTEGER NOT NULL DEFAULT 0 CHECK (backfill_done IN (0, 1)),
    enabled                  INTEGER NOT NULL DEFAULT 1 CHECK (enabled IN (0, 1)),
    created_at               TEXT    NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ', 'now')),
    last_sync_at             TEXT
);

-- Surrogate INTEGER PK is mandatory: FTS5 external-content tables key on rowid and VACUUM may renumber
-- implicit rowids (sqlite.org/lang_vacuum.html). Gmail ids are unique per mailbox only.
CREATE TABLE email_message (
    msg_id               INTEGER PRIMARY KEY,
    account_id           INTEGER NOT NULL REFERENCES email_account (account_id) ON DELETE CASCADE,
    gmail_id             TEXT    NOT NULL,
    thread_id            TEXT    NOT NULL,
    history_id           TEXT,
    internal_date_ms     INTEGER NOT NULL,              -- Message.internalDate (epoch ms, Google acceptance time)
    label_ids_json       TEXT    NOT NULL DEFAULT '[]',
    from_addr            TEXT,
    from_domain          TEXT,                          -- registrable domain of from_addr
    from_name            TEXT,
    from_name_public     TEXT,                          -- alias-scrubbed at ingest; the only name column tools may read
    reply_to_addr        TEXT,
    sender_addr          TEXT,                          -- Sender: header (calendar-notification detection)
    to_addr              TEXT,
    message_id_hdr       TEXT,
    in_reply_to          TEXT,
    references_hdr       TEXT,
    has_list_unsubscribe INTEGER NOT NULL DEFAULT 0 CHECK (has_list_unsubscribe IN (0, 1)),
    headers_json         TEXT    NOT NULL DEFAULT '{}', -- only the requested metadataHeaders
    subject              TEXT    NOT NULL DEFAULT '',
    subject_public       TEXT    NOT NULL DEFAULT '',   -- alias-scrubbed at ingest
    snippet              TEXT    NOT NULL DEFAULT '',
    snippet_public       TEXT    NOT NULL DEFAULT '',   -- alias-scrubbed at ingest
    body_text            TEXT,                          -- only when raw_format = 'full'; purged after body_retention_days
    body_urls_json       TEXT,                          -- [{"host": ..., "url": ...}] from text and <a href>; never resolved
    has_ics              INTEGER CHECK (has_ics IS NULL OR has_ics IN (0, 1)),   -- NULL = unknown (metadata only)
    raw_format           TEXT    NOT NULL CHECK (raw_format IN ('metadata', 'full')),
    language             TEXT    CHECK (language IS NULL OR language IN ('en', 'ja', 'zh')),
    fetched_at           TEXT    NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ', 'now')),
    body_purged_at       TEXT,
    UNIQUE (account_id, gmail_id)
);
CREATE INDEX email_message_thread_idx      ON email_message (account_id, thread_id);
CREATE INDEX email_message_date_idx        ON email_message (internal_date_ms);
CREATE INDEX email_message_from_domain_idx ON email_message (from_domain);

-- Twin FTS5 external-content tables (ARCHITECTURE 3): unicode61 for Latin words, trigram for CJK.
-- Trigram queries shorter than 3 characters match nothing -> store/search.py falls back to LIKE.
-- Options kept to the SQLite >= 3.34 baseline so the Docker image's SQLite also accepts them.
CREATE VIRTUAL TABLE email_fts USING fts5(
    subject, from_name, snippet, body_text,
    content='email_message', content_rowid='msg_id', tokenize='unicode61 remove_diacritics 2'
);
CREATE VIRTUAL TABLE email_fts_tri USING fts5(
    subject, from_name, snippet, body_text,
    content='email_message', content_rowid='msg_id', tokenize='trigram'
);
CREATE TRIGGER email_message_ai AFTER INSERT ON email_message BEGIN
    INSERT INTO email_fts(rowid, subject, from_name, snippet, body_text)
        VALUES (new.msg_id, new.subject, new.from_name, new.snippet, new.body_text);
    INSERT INTO email_fts_tri(rowid, subject, from_name, snippet, body_text)
        VALUES (new.msg_id, new.subject, new.from_name, new.snippet, new.body_text);
END;
CREATE TRIGGER email_message_ad AFTER DELETE ON email_message BEGIN
    INSERT INTO email_fts(email_fts, rowid, subject, from_name, snippet, body_text)
        VALUES ('delete', old.msg_id, old.subject, old.from_name, old.snippet, old.body_text);
    INSERT INTO email_fts_tri(email_fts_tri, rowid, subject, from_name, snippet, body_text)
        VALUES ('delete', old.msg_id, old.subject, old.from_name, old.snippet, old.body_text);
END;
CREATE TRIGGER email_message_au AFTER UPDATE OF subject, from_name, snippet, body_text ON email_message BEGIN
    INSERT INTO email_fts(email_fts, rowid, subject, from_name, snippet, body_text)
        VALUES ('delete', old.msg_id, old.subject, old.from_name, old.snippet, old.body_text);
    INSERT INTO email_fts(rowid, subject, from_name, snippet, body_text)
        VALUES (new.msg_id, new.subject, new.from_name, new.snippet, new.body_text);
    INSERT INTO email_fts_tri(email_fts_tri, rowid, subject, from_name, snippet, body_text)
        VALUES ('delete', old.msg_id, old.subject, old.from_name, old.snippet, old.body_text);
    INSERT INTO email_fts_tri(rowid, subject, from_name, snippet, body_text)
        VALUES (new.msg_id, new.subject, new.from_name, new.snippet, new.body_text);
END;

-- One row per message = the latest classification. LLM cache hit iff
-- method = 'llm' AND prompt_version = ? AND input_hash = ? (input_hash = sha256(prompt_version || payload_json)).
CREATE TABLE email_classification (
    msg_id               INTEGER PRIMARY KEY REFERENCES email_message (msg_id) ON DELETE CASCADE,
    is_job_related       INTEGER NOT NULL CHECK (is_job_related IN (0, 1)),
    category             TEXT    NOT NULL CHECK (category IN (
                           'application_ack','viewed','screening_pass','assessment_invite','scheduling_request','interview_confirmed',
                           'result_notice','offer','offer_docs','rejection','withdrawal_ack','portal_update','reminder','event',
                           'outreach','newsletter','system','other')),
    company              TEXT,                           -- as written in the mail; never derived from a relay/ATS domain
    company_slug         TEXT,                           -- '<platform>/<tenant>' when the sender/URL encodes the tenant
    role                 TEXT,
    ats                  TEXT,                           -- platform id from rules (greenhouse, sonar, ...)
    stage                TEXT,                           -- region-pack stage code (stages.yaml) or NULL
    event_type           TEXT    CHECK (event_type IS NULL OR event_type IN (
                           'entry','es_submitted','document_screening','ack','viewed','casual_interview','web_test','assessment',
                           'interview','final_interview','scheduling','pass','rejection','offer_informal','offer','offer_meeting',
                           'accepted','resignation_negotiation','joined','withdrawn','portal_check_required','followup_needed','note')),
    action_required      INTEGER NOT NULL DEFAULT 0 CHECK (action_required IN (0, 1)),
    deadline_iso         TEXT,
    event_start_iso      TEXT,
    event_end_iso        TEXT,
    meeting_url          TEXT,                           -- real URL, local only (de-aliased after the LLM call)
    meeting_link_pending INTEGER NOT NULL DEFAULT 0 CHECK (meeting_link_pending IN (0, 1)),
    portal_url           TEXT,
    language             TEXT    CHECK (language IS NULL OR language IN ('en', 'ja', 'zh')),
    confidence           REAL    NOT NULL CHECK (confidence >= 0 AND confidence <= 1),
    injection_suspected  INTEGER NOT NULL DEFAULT 0 CHECK (injection_suspected IN (0, 1)),
    method               TEXT    NOT NULL CHECK (method IN ('rule', 'llm')),
    rule_id              TEXT,
    model                TEXT,                           -- 'provider:model-id' as configured (D8)
    prompt_version       TEXT,
    input_hash           TEXT,
    scores_json          TEXT,                           -- {category: score} from the phrase tier, for review/debugging
    needs_review         INTEGER NOT NULL DEFAULT 0 CHECK (needs_review IN (0, 1)),
    review_reason        TEXT    CHECK (review_reason IS NULL OR review_reason IN
                           ('low_confidence','ambiguous_company','thread_company_conflict','unknown_company','current_employer',
                            'unverified_rule','llm_error','injection_suspected')),
    candidates_json      TEXT,                           -- [{company_id, name, score}] when ambiguous
    application_id       INTEGER REFERENCES application (application_id) ON DELETE SET NULL,
    event_id             INTEGER REFERENCES application_event (event_id) ON DELETE SET NULL,
    user_verdict         TEXT    CHECK (user_verdict IS NULL OR user_verdict IN ('accepted', 'rejected', 'corrected')),
    classified_at        TEXT    NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ', 'now'))
);
CREATE INDEX email_classification_review_idx ON email_classification (needs_review) WHERE needs_review = 1;
CREATE INDEX email_classification_app_idx    ON email_classification (application_id);

-- Runtime mirror of region-pack + local user_senders.yaml rules; filled by classify.rules.sync_rules(), never by migrations.
CREATE TABLE classification_rule (
    rule_id          TEXT    PRIMARY KEY,                -- '<pack>:<rule_id>' e.g. 'japan:sonar_from', 'user:<id>'
    kind             TEXT    NOT NULL CHECK (kind IN ('sender', 'url', 'phrase')),
    region_pack      TEXT    NOT NULL,                   -- 'global_en' | 'japan' | 'user'
    from_pattern     TEXT,
    subject_pattern  TEXT,
    body_url_pattern TEXT,
    platform         TEXT,
    category         TEXT,
    gate             INTEGER NOT NULL DEFAULT 0 CHECK (gate IN (0, 1)),
    verified         INTEGER NOT NULL DEFAULT 0 CHECK (verified IN (0, 1)),
    source_url       TEXT,
    definition_hash  TEXT    NOT NULL,                   -- sha256 of the YAML item; a change resets rule_stat
    loaded_at        TEXT    NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ', 'now'))
);
CREATE TABLE rule_stat (
    rule_id       TEXT    PRIMARY KEY REFERENCES classification_rule (rule_id) ON DELETE CASCADE,
    n_fired       INTEGER NOT NULL DEFAULT 0,
    n_confirmed   INTEGER NOT NULL DEFAULT 0,
    n_rejected    INTEGER NOT NULL DEFAULT 0,
    last_fired_at TEXT
);

-- Stable aliases shared by LLM input and tool output. Plaintext never persists; the reverse map lives
-- only in memory during one classification call. Allocated by the sync process only (single writer).
CREATE TABLE pii_aliases (
    alias         TEXT PRIMARY KEY,                      -- '[email:12]' | '[phone:3]' | '[url:7]' | '[person:5]'
    kind          TEXT NOT NULL CHECK (kind IN ('email', 'phone', 'url', 'person')),
    value_hash    TEXT NOT NULL UNIQUE,                  -- sha256(kind || 0x00 || NFKC-casefolded value)
    first_seen_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ', 'now'))
);
CREATE INDEX pii_aliases_kind_idx ON pii_aliases (kind);

-- Every LLM call (Phase 1 exit criterion: backfill cost recorded). cost_usd is Decimal-as-text.
CREATE TABLE llm_call_log (
    id                 INTEGER PRIMARY KEY,
    ts                 TEXT    NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ', 'now')),
    purpose            TEXT    NOT NULL,                 -- 'email_classify'
    msg_id             INTEGER REFERENCES email_message (msg_id) ON DELETE SET NULL,
    model              TEXT    NOT NULL,                 -- configured 'provider:model-id'
    provider           TEXT,
    prompt_version     TEXT    NOT NULL,
    input_tokens       INTEGER NOT NULL DEFAULT 0,
    output_tokens      INTEGER NOT NULL DEFAULT 0,
    cache_read_tokens  INTEGER NOT NULL DEFAULT 0,
    cache_write_tokens INTEGER NOT NULL DEFAULT 0,
    requests           INTEGER NOT NULL DEFAULT 1,
    cost_usd           TEXT,
    price_source       TEXT    NOT NULL CHECK (price_source IN ('pydantic_ai', 'genai_prices', 'unknown')),
    status             TEXT    NOT NULL                  -- 'ok' | exception class name
);
CREATE INDEX llm_call_log_ts_idx ON llm_call_log (ts);

-- Board header / UI status bar. last_error is sanitised (class name + status code), never bodies/addresses/tokens.
CREATE TABLE source_state (
    source          TEXT    PRIMARY KEY,                 -- 'gmail:<account_id>' (Phase 3: 'gcal:<account_id>', Phase 2: 'linkedin_export')
    transport       TEXT    NOT NULL,                    -- 'google-readonly-http' | 'file'
    status          TEXT    NOT NULL CHECK (status IN ('healthy', 'degraded', 'auth_required', 'unavailable', 'disabled')),
    cursor          TEXT,                                -- display copy of email_account.history_id
    last_success_at TEXT,
    last_error      TEXT,
    failure_streak  INTEGER NOT NULL DEFAULT 0,
    next_retry_at   TEXT,
    data_as_of      TEXT,                                -- newest internal_date seen
    updated_at      TEXT    NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ', 'now'))
);
