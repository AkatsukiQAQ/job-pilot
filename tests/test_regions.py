from __future__ import annotations

import re
from datetime import UTC, datetime
from zoneinfo import ZoneInfo

import pytest
from tests.conftest import SRC_ROOT

from jobpilot.domain import Campaign, CampaignKind, Track
from jobpilot.regions import (
    RegionPack,
    UnknownRegionPackError,
    get_region_pack,
    list_region_packs,
)


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
    # placeholders load as empty lists without error
    assert pack.stage_taxonomy(Track.OTHER) == []
    assert pack.milestones(campaign) == []
    assert pack.sender_rules() == []
    assert pack.url_rules() == []
    assert pack.salary_parsers() == []
    assert pack.phrase_lists("en") == []
    assert pack.onboarding_questions(CampaignKind.OTHER) == []


def test_core_code_has_no_region_or_cycle_literals() -> None:
    """CLAUDE.md constraint 6: market literals live only in regions/*/data files."""
    pattern = re.compile(r"新卒|2027|日本|Asia/Tokyo")
    offenders: list[str] = []
    for py in SRC_ROOT.rglob("*.py"):
        if pattern.search(py.read_text(encoding="utf-8")):
            offenders.append(str(py.relative_to(SRC_ROOT)))
    assert offenders == []


def test_yaml_placeholders_are_schema_v1() -> None:
    import yaml

    for data_file in SRC_ROOT.glob("regions/*/data/*.yaml"):
        doc = yaml.safe_load(data_file.read_text(encoding="utf-8"))
        assert doc["version"] == 1, data_file
        for item in doc.get("items") or []:
            assert "verified" in item and "source_url" in item, data_file
