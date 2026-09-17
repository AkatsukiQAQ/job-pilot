"""Region packs: per-market stage taxonomies, milestones, sender/URL rules, phrases, questions.

Core code never assumes a market; everything market-specific lives in a pack's data/*.yaml.
"""

from jobpilot.regions.base import (
    CompanySuffix,
    Lang,
    Milestone,
    PhraseEntry,
    Question,
    RegionPack,
    SenderRule,
    Stage,
    UrlRule,
    YamlRegionPack,
)
from jobpilot.regions.global_en import GlobalEnPack
from jobpilot.regions.japan import JapanPack
from jobpilot.regions.registry import (
    UnknownRegionPackError,
    get_region_pack,
    list_region_packs,
    register,
)

register(GlobalEnPack.name, GlobalEnPack)
register(JapanPack.name, JapanPack)

__all__ = [
    "CompanySuffix",
    "GlobalEnPack",
    "JapanPack",
    "Lang",
    "Milestone",
    "PhraseEntry",
    "Question",
    "RegionPack",
    "SenderRule",
    "Stage",
    "UnknownRegionPackError",
    "UrlRule",
    "YamlRegionPack",
    "get_region_pack",
    "list_region_packs",
    "register",
]
