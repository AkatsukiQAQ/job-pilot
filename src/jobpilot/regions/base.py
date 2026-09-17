"""RegionPack protocol, sourced data models, and the YAML-backed default implementation.

Every data item carries provenance (`verified`, `source_url`). Unverified items may only
propose, never auto-apply (ARCHITECTURE section 10).
"""

from __future__ import annotations

from collections.abc import Callable
from datetime import date
from importlib.resources import files
from typing import Any, ClassVar, Literal, Protocol, runtime_checkable

import yaml
from pydantic import BaseModel, Field

from jobpilot.domain import ApplicationStatus, Campaign, CampaignKind, Track

Lang = Literal["en", "ja", "zh"]
SCHEMA_VERSION = 1


class Sourced(BaseModel):
    verified: bool = False
    source_url: str | None = None


class Stage(Sourced):
    code: str
    label: dict[str, str]  # lang -> label
    maps_to: ApplicationStatus
    tracks: list[Track]


class Milestone(Sourced):
    key: str
    label: dict[str, str]
    on: date | None = None
    until: date | None = None
    requires_flag: str | None = None  # only shown if campaign.flags[requires_flag] is truthy
    kinds: list[CampaignKind] = Field(default_factory=list)  # empty = all kinds


class SenderRule(Sourced):
    rule_id: str
    from_pattern: str | None = None  # regex on From/Sender address; platform/vendor level only
    subject_pattern: str | None = None
    platform: str
    category: str
    gate: bool = False  # True -> fetch the full body


class UrlRule(Sourced):
    rule_id: str
    host_pattern: str
    platform: str


class PhraseEntry(Sourced):
    phrase: str
    category: str
    weight: float = 1.0


class Question(Sourced):
    key: str
    text: dict[str, str]
    category: str  # profile_facts.category (Phase 3)
    kinds: list[CampaignKind] = Field(default_factory=list)  # empty = all kinds


class SalaryParse(BaseModel):
    basis: str
    amount_min: int | None = None
    amount_max: int | None = None
    currency: str | None = None


SalaryParser = Callable[[str], SalaryParse | None]


@runtime_checkable
class RegionPack(Protocol):
    name: str
    default_lang: str
    default_tz: str

    def stage_taxonomy(self, track: Track) -> list[Stage]: ...

    def milestones(self, campaign: Campaign) -> list[Milestone]: ...

    def sender_rules(self) -> list[SenderRule]: ...

    def url_rules(self) -> list[UrlRule]: ...

    def salary_parsers(self) -> list[SalaryParser]: ...

    def phrase_lists(self, lang: Lang) -> list[PhraseEntry]: ...

    def onboarding_questions(self, kind: CampaignKind) -> list[Question]: ...


class YamlRegionPack:
    """Reads ``data/pack.yaml`` (default_lang, default_tz) and ``data/*.yaml`` item files.

    Item files: stages.yaml, milestones.yaml, senders.yaml, urls.yaml, phrases.<lang>.yaml,
    questions.yaml. Schema v1: ``{version: 1, items: [...]}``. A missing file yields [].
    """

    name: ClassVar[str]
    package: ClassVar[str]

    def __init__(self) -> None:
        meta = self._load_doc("pack.yaml")
        self.default_lang: str = str(meta.get("default_lang", "en"))
        self.default_tz: str = str(meta.get("default_tz", "UTC"))

    def _load_doc(self, filename: str) -> dict[str, Any]:
        res = files(self.package) / "data" / filename
        if not res.is_file():
            return {}
        doc = yaml.safe_load(res.read_text(encoding="utf-8")) or {}
        if not isinstance(doc, dict):
            raise ValueError(f"{self.package}/data/{filename}: expected a mapping")
        if doc.get("version") != SCHEMA_VERSION:
            raise ValueError(f"{self.package}/data/{filename}: unsupported schema version")
        return doc

    def _items(self, filename: str) -> list[dict[str, Any]]:
        return list(self._load_doc(filename).get("items") or [])

    def stage_taxonomy(self, track: Track) -> list[Stage]:
        stages = [Stage.model_validate(i) for i in self._items("stages.yaml")]
        return [s for s in stages if track in s.tracks]

    def milestones(self, campaign: Campaign) -> list[Milestone]:
        out: list[Milestone] = []
        for m in (Milestone.model_validate(i) for i in self._items("milestones.yaml")):
            if m.kinds and campaign.kind not in m.kinds:
                continue
            if m.requires_flag and not campaign.flags.get(m.requires_flag):
                continue
            out.append(m)
        return out

    def sender_rules(self) -> list[SenderRule]:
        return [SenderRule.model_validate(i) for i in self._items("senders.yaml")]

    def url_rules(self) -> list[UrlRule]:
        return [UrlRule.model_validate(i) for i in self._items("urls.yaml")]

    def salary_parsers(self) -> list[SalaryParser]:
        return []

    def phrase_lists(self, lang: Lang) -> list[PhraseEntry]:
        return [PhraseEntry.model_validate(i) for i in self._items(f"phrases.{lang}.yaml")]

    def onboarding_questions(self, kind: CampaignKind) -> list[Question]:
        qs = [Question.model_validate(i) for i in self._items("questions.yaml")]
        return [q for q in qs if not q.kinds or kind in q.kinds]


__all__ = [
    "SCHEMA_VERSION",
    "Lang",
    "Milestone",
    "PhraseEntry",
    "Question",
    "RegionPack",
    "SalaryParse",
    "SalaryParser",
    "SenderRule",
    "Sourced",
    "Stage",
    "UrlRule",
    "YamlRegionPack",
]
