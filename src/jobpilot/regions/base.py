"""RegionPack protocol, sourced data models, and the YAML-backed default implementation.

Every data item carries provenance (`verified`, `source_url`). Unverified items may only
propose, never auto-apply (ARCHITECTURE section 10). All fields added after Phase 0 have
defaults so older data files keep loading.
"""

from __future__ import annotations

from collections.abc import Callable
from datetime import date
from importlib.resources import files
from typing import Any, ClassVar, Literal, Protocol, runtime_checkable

import yaml
from pydantic import BaseModel, Field

from jobpilot.domain import ApplicationStatus, Campaign, CampaignKind, Lang, Track

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


CompanyFrom = Literal["none", "local_part", "subdomain", "display_name", "subject", "group"]
HeaderName = Literal["from", "reply_to", "sender", "any"]


class SenderRule(Sourced):
    rule_id: str
    from_pattern: str | None = None  # regex on the address; platform/vendor level only
    subject_pattern: str | None = None
    platform: str
    category: str  # EmailCategory value or 'unknown' (platform only; body decides)
    gate: bool = False  # True -> fetch the full body
    relay: bool = False  # multi-company relay: never derive the company from the sender domain
    company_from: CompanyFrom = "none"
    company_group: str | None = None  # named regex group when company_from == 'group'
    header: HeaderName = "any"
    llm_allowed: bool = True  # False when the platform's terms forbid feeding content to AI
    weight: float = 1.0


class UrlRule(Sourced):
    rule_id: str
    host_pattern: str  # regex on the URL host
    path_pattern: str | None = None  # regex on the path; named group 'company' yields a slug
    platform: str
    category: str | None = None  # e.g. 'assessment_invite' for test vendors
    gate: bool = True


PhraseScope = Literal["subject", "body", "any"]


class PhraseEntry(Sourced):
    phrase: str
    category: str  # EmailCategory value, or a helper category (pii_*, quote_marker, ...)
    weight: float = 1.0
    regex: bool = False  # phrase is a regex (applied after NFKC)
    core: bool = False  # rejection needs at least one core hit
    scope: PhraseScope = "any"
    event_type: str | None = None  # overrides CATEGORY_DEFAULT_EVENT
    track_hint: str | None = None  # 'intern' when the phrase implies an internship process


class CompanySuffix(Sourced):
    token: str  # legal-form token, matched after NFKC + casefold
    position: Literal["prefix", "suffix", "any"] = "any"
    lang: str | None = None


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

    def phrase_lists(self, lang: Lang) -> list[PhraseEntry]: ...

    def company_suffixes(self) -> list[CompanySuffix]: ...

    def salary_parsers(self) -> list[SalaryParser]: ...

    def onboarding_questions(self, kind: CampaignKind) -> list[Question]: ...


class YamlRegionPack:
    """Reads ``data/pack.yaml`` (default_lang, default_tz) and ``data/*.yaml`` item files.

    Item files: stages.yaml, milestones.yaml, senders.yaml, urls.yaml, phrases.<lang>.yaml,
    company_suffixes.yaml, questions.yaml. Schema v1: ``{version: 1, items: [...]}``.
    A missing file yields [].
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

    def phrase_lists(self, lang: Lang) -> list[PhraseEntry]:
        return [PhraseEntry.model_validate(i) for i in self._items(f"phrases.{lang}.yaml")]

    def company_suffixes(self) -> list[CompanySuffix]:
        return [CompanySuffix.model_validate(i) for i in self._items("company_suffixes.yaml")]

    def salary_parsers(self) -> list[SalaryParser]:
        return []

    def onboarding_questions(self, kind: CampaignKind) -> list[Question]:
        qs = [Question.model_validate(i) for i in self._items("questions.yaml")]
        return [q for q in qs if not q.kinds or kind in q.kinds]


__all__ = [
    "SCHEMA_VERSION",
    "CompanyFrom",
    "CompanySuffix",
    "HeaderName",
    "Lang",
    "Milestone",
    "PhraseEntry",
    "PhraseScope",
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
