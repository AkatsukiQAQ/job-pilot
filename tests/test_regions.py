from __future__ import annotations

import re
from datetime import UTC, datetime
from zoneinfo import ZoneInfo

import pytest

from jobpilot.domain import Campaign, CampaignKind, Track
from jobpilot.regions import (
    RegionPack,
    SenderRule,
    UnknownRegionPackError,
    get_region_pack,
    list_region_packs,
)
from tests.conftest import SRC_ROOT

# Hiragana/katakana + CJK ideographs, written as escapes so this file documents the rule.
_CJK_RE = re.compile("[぀-ヿ㐀-䶿一-鿿豈-﫿]")


def test_registry() -> None:
    assert list_region_packs() == ["global_en", "japan"]
    with pytest.raises(UnknownRegionPackError):
        get_region_pack("mars")


@pytest.mark.parametrize("name", ["global_en", "japan"])
def test_packs_satisfy_protocol_and_load(name: str) -> None:
    pack = get_region_pack(name)
    assert isinstance(pack, RegionPack)
    assert pack.name == name
    ZoneInfo(pack.default_tz)  # resolvable
    assert pack.default_lang in {"en", "ja", "zh"}

    campaign = Campaign(
        campaign_id=1,
        name="demo",
        kind=CampaignKind.OTHER,
        region_pack=name,
        created_at=datetime.now(UTC),
    )
    # every data file loads (placeholders are empty lists)
    assert isinstance(pack.stage_taxonomy(Track.OTHER), list)
    assert isinstance(pack.milestones(campaign), list)
    assert isinstance(pack.sender_rules(), list)
    assert isinstance(pack.url_rules(), list)
    assert isinstance(pack.company_suffixes(), list)
    assert pack.salary_parsers() == []
    assert isinstance(pack.phrase_lists("en"), list)
    assert isinstance(pack.onboarding_questions(CampaignKind.OTHER), list)


def test_sender_rule_defaults_keep_old_files_loading() -> None:
    rule = SenderRule.model_validate({"rule_id": "x", "platform": "p", "category": "unknown"})
    assert rule.relay is False
    assert rule.company_from == "none"
    assert rule.header == "any"
    assert rule.llm_allowed is True
    assert rule.verified is False


def test_core_code_has_no_region_or_cycle_literals() -> None:
    """CLAUDE.md constraint 6: market literals live only in regions/*/data files."""
    pattern = re.compile(r"新卒|2027|日本|Asia/Tokyo")  # newgrad / year / Japan
    offenders = [
        str(py.relative_to(SRC_ROOT))
        for py in SRC_ROOT.rglob("*.py")
        if pattern.search(py.read_text(encoding="utf-8"))
    ]
    assert offenders == []


def test_core_code_has_no_cjk_literals() -> None:
    """Language word lists belong in region-pack YAML, not in Python source."""
    offenders: list[str] = []
    for py in SRC_ROOT.rglob("*.py"):
        if "data" in py.parts:
            continue
        text = py.read_text(encoding="utf-8")
        if _CJK_RE.search(text):
            offenders.append(str(py.relative_to(SRC_ROOT)))
    assert offenders == []


def test_yaml_files_are_schema_v1_with_provenance() -> None:
    import yaml

    for data_file in SRC_ROOT.glob("regions/*/data/*.yaml"):
        doc = yaml.safe_load(data_file.read_text(encoding="utf-8"))
        assert doc["version"] == 1, data_file
        for item in doc.get("items") or []:
            assert "verified" in item and "source_url" in item, data_file
