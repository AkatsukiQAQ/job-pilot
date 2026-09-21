"""Request / response models of the web API. The frontend's TypeScript types mirror these."""

from __future__ import annotations

from datetime import date, datetime

from pydantic import AwareDatetime, BaseModel, Field, field_validator

from jobpilot.domain import (
    ApplicationStatus,
    CampaignKind,
    EventSource,
    EventType,
    Origin,
    Track,
)

_URL_SCHEMES = ("http://", "https://")


def _validate_url(v: str | None) -> str | None:
    """Shared job_url / portal_url rule: strip, empty -> None, else http(s):// and <= 2048 chars."""
    if v is None:
        return None
    v = v.strip()
    if not v:
        return None
    if not v.startswith(_URL_SCHEMES):
        raise ValueError("must start with http:// or https://")
    if len(v) > 2048:
        raise ValueError("must be at most 2048 characters")
    return v


class MetaOut(BaseModel):
    statuses: list[str]
    event_types: list[str]
    tracks: list[str]
    kinds: list[str]
    region_packs: list[str]
    tz: str


class CampaignIn(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    kind: CampaignKind
    region_pack: str
    starts_on: date | None = None
    ends_on: date | None = None


class CampaignOut(BaseModel):
    campaign_id: int
    name: str
    kind: CampaignKind
    region_pack: str
    starts_on: date | None
    ends_on: date | None
    is_active: bool
    application_count: int
    tz: str  # region-pack default, overridden by JOBPILOT_TZ


class ApplicationIn(BaseModel):
    campaign_id: int
    company_name: str = Field(min_length=1, max_length=200)
    role: str | None = Field(default=None, max_length=200)
    track: Track
    job_url: str | None = None
    notes: str | None = None
    initial_status: ApplicationStatus | None = None

    @field_validator("company_name")
    @classmethod
    def _strip_company_name(cls, v: str) -> str:
        v = v.strip()
        if not v:
            raise ValueError("company_name must not be blank")
        return v

    @field_validator("job_url")
    @classmethod
    def _check_job_url(cls, v: str | None) -> str | None:
        return _validate_url(v)


class ApplicationPatch(BaseModel):
    company_name: str = Field(min_length=1, max_length=200)
    role: str | None = Field(default=None, max_length=200)
    track: Track
    job_url: str | None = None
    notes: str | None = None
    portal_url: str | None = None
    deadline_at: AwareDatetime | None = None
    next_action: str | None = Field(default=None, max_length=120)
    next_action_due: AwareDatetime | None = None

    @field_validator("company_name")
    @classmethod
    def _strip_company_name(cls, v: str) -> str:
        v = v.strip()
        if not v:
            raise ValueError("company_name must not be blank")
        return v

    @field_validator("job_url", "portal_url")
    @classmethod
    def _check_url(cls, v: str | None) -> str | None:
        return _validate_url(v)


class StatusIn(BaseModel):
    user_status: ApplicationStatus | None
    excluded_reason: str | None = None


class EventIn(BaseModel):
    event_type: EventType
    occurred_at: AwareDatetime
    summary: str | None = Field(default=None, max_length=120)


class EventOut(BaseModel):
    event_id: int
    event_type: EventType
    occurred_at: datetime
    source: EventSource
    summary: str | None
    confidence: float
    user_confirmed: bool


class ApplicationRow(BaseModel):
    application_id: int
    campaign_id: int
    company: str
    role: str | None
    track: Track
    auto_status: ApplicationStatus
    user_status: ApplicationStatus | None
    status: ApplicationStatus  # effective: user_status or auto_status
    origin: Origin
    last_event_at: datetime | None
    last_event_type: EventType | None
    next_action: str | None
    next_action_due: datetime | None
    deadline_at: datetime | None
    job_url: str | None
    is_ghosted: bool


class ApplicationDetail(ApplicationRow):
    notes: str | None
    portal_url: str | None
    applied_at: datetime | None
    excluded_reason: str | None
    created_at: datetime
    events: list[EventOut]


class UpcomingItem(BaseModel):
    application_id: int
    company: str
    role: str | None
    kind: str  # 'deadline' | 'next_action'
    due: datetime
    label: str | None  # next_action text when kind == 'next_action'
    overdue: bool


class RecentEvent(BaseModel):
    event_id: int
    application_id: int
    company: str
    event_type: EventType
    occurred_at: datetime
    summary: str | None


class DashboardOut(BaseModel):
    counts_by_status: dict[str, int]
    upcoming: list[UpcomingItem]
    recent_events: list[RecentEvent]
    deadlines_this_week: int
    interviews_next_7d: int


class DeleteOut(BaseModel):
    deleted_events: int


class CampaignDeleteOut(BaseModel):
    deleted_applications: int
    deleted_events: int
