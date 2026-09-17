"""Closed enums and the campaign row model shared by every layer.

SQL CHECK constraints, CLI choices and region-pack data all take these enums as the
single source of truth. No region- or cycle-specific literal may appear here.
"""

from __future__ import annotations

import json
import sqlite3
from datetime import date, datetime
from enum import StrEnum
from typing import Any, Self

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


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
        return json.loads(v) if isinstance(v, str) else v

    @classmethod
    def from_row(cls, row: sqlite3.Row) -> Campaign:
        d: dict[str, Any] = dict(row)
        d["flags"] = d.pop("flags_json")
        return cls.model_validate(d)


__all__ = ["ApplicationStatus", "Campaign", "CampaignCreate", "CampaignKind", "Track"]
