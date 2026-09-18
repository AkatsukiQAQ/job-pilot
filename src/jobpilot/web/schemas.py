"""Request / response models of the web API. The frontend's TypeScript types mirror these."""

from __future__ import annotations

from datetime import date, datetime

from pydantic import BaseModel, Field

from jobpilot.domain import (
    ApplicationStatus,
    CampaignKind,
    EventSource,
    EventType,
    Origin,
    Track,
)


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


class ApplicationIn(BaseModel):
    campaign_id: int
    company_name: str = Field(min_length=1, max_length=200)
    role: str | None = Field(default=None, max_length=200)
    track: Track
    job_url: str | None = None
    notes: str | None = None


class StatusIn(BaseModel):
    user_status: ApplicationStatus | None
    excluded_reason: str | None = None


class EventIn(BaseModel):
    event_type: EventType
    occurred_at: datetime
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
