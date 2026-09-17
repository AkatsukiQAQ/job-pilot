"""Japan region pack. All market-specific literals live in data/*.yaml, not in Python."""

from jobpilot.regions.base import YamlRegionPack


class JapanPack(YamlRegionPack):
    name = "japan"
    package = "jobpilot.regions.japan"
    # Phase 4: override salary_parsers() with salary_basis parsers (REQUIREMENTS 5.3).


__all__ = ["JapanPack"]
