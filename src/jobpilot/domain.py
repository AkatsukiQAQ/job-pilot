"""Closed enums, derivation tables and row models shared by every layer.

SQL CHECK constraints, CLI choices and region-pack data all take these enums as the
single source of truth (tests/test_db.py asserts CHECK lists == enum values). No region-
or cycle-specific literal may appear here.
"""

from __future__ import annotations

import json
import sqlite3
from datetime import date, datetime
from enum import StrEnum
from typing import Any, Final, Literal, Self

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

# ---------------------------------------------------------------------------- enums


class CampaignKind(StrEnum):
    """Kind of job-search cycle (campaign.kind)."""

    NEWGRAD = "newgrad"
    MIDCAREER = "midcareer"
    INTERN = "intern"
    OTHER = "other"


class Track(StrEnum):
    """Which process a single application belongs to (application.track)."""

    INTERN = "intern"
    NEWGRAD = "newgrad"
    MIDCAREER = "midcareer"
    OTHER = "other"


class ApplicationStatus(StrEnum):
    """12-state closed enum for application.auto_status / user_status (decision D14)."""

    UNRECORDED = "unrecorded"
    CONSIDERING = "considering"
    PREPARING = "preparing"
    APPLIED = "applied"
    ASSESSMENT = "assessment"
    INTERVIEWING = "interviewing"
    OFFER = "offer"
    ACCEPTED = "accepted"
    JOINED = "joined"
    REJECTED = "rejected"
    WITHDRAWN = "withdrawn"
    UNSUITABLE = "unsuitable"


class EventType(StrEnum):
    """application_event.event_type (append-only ledger)."""

    ENTRY = "entry"
    ES_SUBMITTED = "es_submitted"
    DOCUMENT_SCREENING = "document_screening"
    ACK = "ack"
    VIEWED = "viewed"
    CASUAL_INTERVIEW = "casual_interview"
    WEB_TEST = "web_test"
    ASSESSMENT = "assessment"
    INTERVIEW = "interview"
    FINAL_INTERVIEW = "final_interview"
    SCHEDULING = "scheduling"
    PASS = "pass"
    REJECTION = "rejection"
    OFFER_INFORMAL = "offer_informal"
    OFFER = "offer"
    OFFER_MEETING = "offer_meeting"
    ACCEPTED = "accepted"
    RESIGNATION_NEGOTIATION = "resignation_negotiation"
    JOINED = "joined"
    WITHDRAWN = "withdrawn"
    PORTAL_CHECK_REQUIRED = "portal_check_required"
    FOLLOWUP_NEEDED = "followup_needed"
    NOTE = "note"


class EventSource(StrEnum):
    GMAIL = "gmail"
    GCAL = "gcal"
    LINKEDIN_EXPORT = "linkedin_export"
    CHAT = "chat"
    MANUAL = "manual"
    IMPORT = "import"
    SYSTEM = "system"


class EmailCategory(StrEnum):
    """email_classification.category (18 values)."""

    APPLICATION_ACK = "application_ack"
    VIEWED = "viewed"
    SCREENING_PASS = "screening_pass"
    ASSESSMENT_INVITE = "assessment_invite"
    SCHEDULING_REQUEST = "scheduling_request"
    INTERVIEW_CONFIRMED = "interview_confirmed"
    RESULT_NOTICE = "result_notice"  # "results are out" without pass/fail wording -> LLM or review
    OFFER = "offer"
    OFFER_DOCS = "offer_docs"
    REJECTION = "rejection"
    WITHDRAWAL_ACK = "withdrawal_ack"
    PORTAL_UPDATE = "portal_update"
    REMINDER = "reminder"
    EVENT = "event"
    OUTREACH = "outreach"
    NEWSLETTER = "newsletter"
    SYSTEM = "system"
    OTHER = "other"


class SourceHealth(StrEnum):
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    AUTH_REQUIRED = "auth_required"
    UNAVAILABLE = "unavailable"
    DISABLED = "disabled"


class ClassifyMethod(StrEnum):
    RULE = "rule"
    LLM = "llm"


class ReviewReason(StrEnum):
    LOW_CONFIDENCE = "low_confidence"
    AMBIGUOUS_COMPANY = "ambiguous_company"
    THREAD_COMPANY_CONFLICT = "thread_company_conflict"
    UNKNOWN_COMPANY = "unknown_company"
    CURRENT_EMPLOYER = "current_employer"
    UNVERIFIED_RULE = "unverified_rule"
    LLM_ERROR = "llm_error"
    INJECTION_SUSPECTED = "injection_suspected"


class StatusSetBy(StrEnum):
    USER = "user"
    RULE = "rule"
    LLM = "llm"
    IMPORT = "import"
    SYSTEM = "system"


class Origin(StrEnum):
    AUTO = "auto"
    MANUAL = "manual"
    IMPORT = "import"


class AliasKind(StrEnum):
    NAME = "name"
    DOMAIN = "domain"
    SLUG = "slug"


class PiiKind(StrEnum):
    EMAIL = "email"
    PHONE = "phone"
    URL = "url"
    PERSON = "person"


Lang = Literal["en", "ja", "zh"]
RawFormat = Literal["metadata", "full"]

# ---------------------------------------------------------------------------- derivation tables

# ARCHITECTURE 5.1: which status an event implies. None = the event carries no status.
EVENT_STATUS: Final[dict[EventType, ApplicationStatus | None]] = {
    EventType.ENTRY: ApplicationStatus.PREPARING,
    EventType.ES_SUBMITTED: ApplicationStatus.APPLIED,
    EventType.DOCUMENT_SCREENING: ApplicationStatus.APPLIED,
    EventType.ACK: ApplicationStatus.APPLIED,
    EventType.VIEWED: ApplicationStatus.APPLIED,
    EventType.CASUAL_INTERVIEW: ApplicationStatus.CONSIDERING,
    EventType.WEB_TEST: ApplicationStatus.ASSESSMENT,
    EventType.ASSESSMENT: ApplicationStatus.ASSESSMENT,
    EventType.INTERVIEW: ApplicationStatus.INTERVIEWING,
    EventType.FINAL_INTERVIEW: ApplicationStatus.INTERVIEWING,
    EventType.SCHEDULING: ApplicationStatus.INTERVIEWING,
    EventType.PASS: None,
    EventType.REJECTION: ApplicationStatus.REJECTED,
    EventType.OFFER_INFORMAL: ApplicationStatus.OFFER,
    EventType.OFFER: ApplicationStatus.OFFER,
    EventType.OFFER_MEETING: ApplicationStatus.OFFER,
    EventType.ACCEPTED: ApplicationStatus.ACCEPTED,
    EventType.RESIGNATION_NEGOTIATION: ApplicationStatus.ACCEPTED,
    EventType.JOINED: ApplicationStatus.JOINED,
    EventType.WITHDRAWN: ApplicationStatus.WITHDRAWN,
    EventType.PORTAL_CHECK_REQUIRED: None,
    EventType.FOLLOWUP_NEEDED: None,
    EventType.NOTE: None,
}

# Highest rank wins; ties -> latest occurred_at. Terminal outcomes outrank progress so a late
# "ack" reminder never regresses a status. UNRECORDED / UNSUITABLE are never derived.
STATUS_RANK: Final[dict[ApplicationStatus, int]] = {
    ApplicationStatus.CONSIDERING: 1,
    ApplicationStatus.PREPARING: 2,
    ApplicationStatus.APPLIED: 3,
    ApplicationStatus.ASSESSMENT: 4,
    ApplicationStatus.INTERVIEWING: 5,
    ApplicationStatus.OFFER: 6,
    ApplicationStatus.ACCEPTED: 7,
    ApplicationStatus.JOINED: 8,
    ApplicationStatus.WITHDRAWN: 9,
    ApplicationStatus.REJECTED: 10,
}

# Default event for a category when a phrase entry does not override it. None = no event.
CATEGORY_DEFAULT_EVENT: Final[dict[EmailCategory, EventType | None]] = {
    EmailCategory.APPLICATION_ACK: EventType.ACK,
    EmailCategory.VIEWED: EventType.VIEWED,
    EmailCategory.SCREENING_PASS: EventType.PASS,
    EmailCategory.ASSESSMENT_INVITE: EventType.ASSESSMENT,
    EmailCategory.SCHEDULING_REQUEST: EventType.SCHEDULING,
    EmailCategory.INTERVIEW_CONFIRMED: EventType.INTERVIEW,
    EmailCategory.RESULT_NOTICE: None,
    EmailCategory.OFFER: EventType.OFFER,
    EmailCategory.OFFER_DOCS: EventType.OFFER,
    EmailCategory.REJECTION: EventType.REJECTION,
    EmailCategory.WITHDRAWAL_ACK: EventType.WITHDRAWN,
    EmailCategory.PORTAL_UPDATE: EventType.PORTAL_CHECK_REQUIRED,
    EmailCategory.REMINDER: None,
    EmailCategory.EVENT: EventType.NOTE,
    EmailCategory.OUTREACH: EventType.NOTE,
    EmailCategory.NEWSLETTER: None,
    EmailCategory.SYSTEM: None,
    EmailCategory.OTHER: None,
}

# Categories that never create applications or events (stored for search only).
NON_PROCESS_CATEGORIES: Final[frozenset[EmailCategory]] = frozenset(
    {EmailCategory.NEWSLETTER, EmailCategory.SYSTEM, EmailCategory.OTHER, EmailCategory.REMINDER}
)

# Statuses in which silence from the company is meaningful (follow-up / ghosted checks).
SILENCE_STATUSES: Final[frozenset[ApplicationStatus]] = frozenset(
    {ApplicationStatus.APPLIED, ApplicationStatus.ASSESSMENT, ApplicationStatus.INTERVIEWING}
)

# ---------------------------------------------------------------------------- row models


def _json_or_default(v: Any, default: Any) -> Any:
    if v is None:
        return default
    return json.loads(v) if isinstance(v, str) else v


class _Row(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    @classmethod
    def from_row(cls, row: sqlite3.Row) -> Self:
        return cls.model_validate(dict(row))


class CampaignCreate(BaseModel):
    """Input for creating a campaign. Never seeded by migrations (decision D16)."""

    name: str = Field(min_length=1, max_length=120)
    kind: CampaignKind
    region_pack: str = Field(pattern=r"^[a-z][a-z0-9_]*$")
    starts_on: date | None = None
    ends_on: date | None = None
    flags: dict[str, Any] = Field(default_factory=dict)
    is_active: bool = True

    @model_validator(mode="after")
    def _check_dates(self) -> Self:
        if self.starts_on and self.ends_on and self.ends_on < self.starts_on:
            raise ValueError("ends_on must not be before starts_on")
        return self


class Campaign(CampaignCreate):
    """A stored campaign row."""

    model_config = ConfigDict(from_attributes=True)

    campaign_id: int
    created_at: datetime

    @field_validator("flags", mode="before")
    @classmethod
    def _parse_flags(cls, v: Any) -> Any:
        return _json_or_default(v, {})

    @classmethod
    def from_row(cls, row: sqlite3.Row) -> Campaign:
        d: dict[str, Any] = dict(row)
        d["flags"] = d.pop("flags_json")
        return cls.model_validate(d)


class CompanyCreate(BaseModel):
    name: str = Field(min_length=1)
    name_norm: str = Field(min_length=1)
    domain: str | None = None
    industry: str | None = None
    size_bucket: str | None = None
    hq_country: str | None = None
    is_current_employer: bool = False
    notes: str | None = None


class Company(_Row):
    company_id: int
    name: str
    name_norm: str
    domain: str | None = None
    industry: str | None = None
    size_bucket: str | None = None
    hq_country: str | None = None
    is_current_employer: bool = False
    notes: str | None = None
    created_at: datetime
    updated_at: datetime


class CompanyAlias(_Row):
    kind: AliasKind
    alias_norm: str
    company_id: int
    lang: str | None = None
    source: str
    created_at: datetime


class ApplicationCreate(BaseModel):
    campaign_id: int
    company_id: int
    track: Track
    role: str | None = None
    role_norm: str = ""
    channel: str | None = None
    origin: Origin = Origin.AUTO
    job_url: str | None = None
    portal_url: str | None = None
    notes: str | None = None


class Application(_Row):
    application_id: int
    campaign_id: int
    company_id: int
    canonical_id: int | None = None
    role: str | None = None
    role_norm: str = ""
    track: Track
    channel: str | None = None
    auto_status: ApplicationStatus
    user_status: ApplicationStatus | None = None
    effective_status: ApplicationStatus | None = None
    status_set_by: StatusSetBy
    origin: Origin
    applied_at: datetime | None = None
    last_event_at: datetime | None = None
    next_action: str | None = None
    next_action_due: datetime | None = None
    deadline_at: datetime | None = None
    excluded_reason: str | None = None
    job_url: str | None = None
    portal_url: str | None = None
    notes: str | None = None
    created_at: datetime
    updated_at: datetime

    @model_validator(mode="after")
    def _fill_effective(self) -> Self:
        if self.effective_status is None:
            self.effective_status = self.user_status or self.auto_status
        return self

    @property
    def status(self) -> ApplicationStatus:
        return self.effective_status or self.user_status or self.auto_status


class EventCreate(BaseModel):
    application_id: int
    event_type: EventType
    occurred_at: datetime
    source: EventSource
    source_ref: str = ""
    round_no: int | None = Field(default=None, ge=1)
    confidence: float = Field(default=1.0, ge=0.0, le=1.0)
    summary: str | None = Field(default=None, max_length=120)
    user_confirmed: bool = False


class ApplicationEvent(_Row):
    event_id: int
    application_id: int
    event_type: EventType
    round_no: int | None = None
    occurred_at: datetime
    source: EventSource
    source_ref: str = ""
    confidence: float
    summary: str | None = None
    user_confirmed: bool = False
    created_at: datetime


class EmailAccount(_Row):
    account_id: int
    email: str
    label: str | None = None
    provider: Literal["google"] = "google"
    token_ref: str
    history_id: str | None = None
    backfill_from_history_id: str | None = None
    backfill_done: bool = False
    enabled: bool = True
    created_at: datetime
    last_sync_at: datetime | None = None


class EmailMessageCreate(BaseModel):
    account_id: int
    gmail_id: str
    thread_id: str
    internal_date_ms: int
    raw_format: RawFormat
    history_id: str | None = None
    label_ids: list[str] = Field(default_factory=list)
    from_addr: str | None = None
    from_domain: str | None = None
    from_name: str | None = None
    from_name_public: str | None = None
    reply_to_addr: str | None = None
    sender_addr: str | None = None
    to_addr: str | None = None
    message_id_hdr: str | None = None
    in_reply_to: str | None = None
    references_hdr: str | None = None
    has_list_unsubscribe: bool = False
    headers: dict[str, str] = Field(default_factory=dict)
    subject: str = ""
    subject_public: str = ""
    snippet: str = ""
    snippet_public: str = ""
    body_text: str | None = None
    body_urls: list[dict[str, str]] | None = None
    has_ics: bool | None = None
    language: Lang | None = None


class EmailMessage(_Row):
    msg_id: int
    account_id: int
    gmail_id: str
    thread_id: str
    history_id: str | None = None
    internal_date_ms: int
    label_ids: list[str] = Field(default_factory=list)
    from_addr: str | None = None
    from_domain: str | None = None
    from_name: str | None = None
    from_name_public: str | None = None
    reply_to_addr: str | None = None
    sender_addr: str | None = None
    to_addr: str | None = None
    message_id_hdr: str | None = None
    in_reply_to: str | None = None
    references_hdr: str | None = None
    has_list_unsubscribe: bool = False
    headers: dict[str, str] = Field(default_factory=dict)
    subject: str = ""
    subject_public: str = ""
    snippet: str = ""
    snippet_public: str = ""
    body_text: str | None = None
    body_urls: list[dict[str, str]] | None = None
    has_ics: bool | None = None
    raw_format: RawFormat
    language: Lang | None = None
    fetched_at: datetime
    body_purged_at: datetime | None = None

    @classmethod
    def from_row(cls, row: sqlite3.Row) -> EmailMessage:
        d: dict[str, Any] = dict(row)
        d["label_ids"] = _json_or_default(d.pop("label_ids_json", None), [])
        d["headers"] = _json_or_default(d.pop("headers_json", None), {})
        d["body_urls"] = _json_or_default(d.pop("body_urls_json", None), None)
        return cls.model_validate(d)


class EmailClassificationCreate(BaseModel):
    msg_id: int
    is_job_related: bool
    category: EmailCategory
    confidence: float = Field(ge=0.0, le=1.0)
    method: ClassifyMethod
    company: str | None = None
    company_slug: str | None = None
    role: str | None = None
    ats: str | None = None
    stage: str | None = None
    event_type: EventType | None = None
    action_required: bool = False
    deadline_iso: str | None = None
    event_start_iso: str | None = None
    event_end_iso: str | None = None
    meeting_url: str | None = None
    meeting_link_pending: bool = False
    portal_url: str | None = None
    language: Lang | None = None
    injection_suspected: bool = False
    rule_id: str | None = None
    model: str | None = None
    prompt_version: str | None = None
    input_hash: str | None = None
    scores: dict[str, float] | None = None
    needs_review: bool = False
    review_reason: ReviewReason | None = None
    candidates: list[dict[str, Any]] | None = None
    application_id: int | None = None
    event_id: int | None = None
    user_verdict: Literal["accepted", "rejected", "corrected"] | None = None


class EmailClassification(EmailClassificationCreate):
    model_config = ConfigDict(from_attributes=True)

    classified_at: datetime

    @classmethod
    def from_row(cls, row: sqlite3.Row) -> EmailClassification:
        d: dict[str, Any] = dict(row)
        d["scores"] = _json_or_default(d.pop("scores_json", None), None)
        d["candidates"] = _json_or_default(d.pop("candidates_json", None), None)
        return cls.model_validate(d)


class SourceState(_Row):
    source: str
    transport: str
    status: SourceHealth
    cursor: str | None = None
    last_success_at: datetime | None = None
    last_error: str | None = None
    failure_streak: int = 0
    next_retry_at: datetime | None = None
    data_as_of: datetime | None = None
    updated_at: datetime


__all__ = [
    "CATEGORY_DEFAULT_EVENT",
    "EVENT_STATUS",
    "NON_PROCESS_CATEGORIES",
    "SILENCE_STATUSES",
    "STATUS_RANK",
    "AliasKind",
    "Application",
    "ApplicationCreate",
    "ApplicationEvent",
    "ApplicationStatus",
    "Campaign",
    "CampaignCreate",
    "CampaignKind",
    "ClassifyMethod",
    "Company",
    "CompanyAlias",
    "CompanyCreate",
    "EmailAccount",
    "EmailCategory",
    "EmailClassification",
    "EmailClassificationCreate",
    "EmailMessage",
    "EmailMessageCreate",
    "EventCreate",
    "EventSource",
    "EventType",
    "Lang",
    "Origin",
    "PiiKind",
    "RawFormat",
    "ReviewReason",
    "SourceHealth",
    "SourceState",
    "StatusSetBy",
    "Track",
]
