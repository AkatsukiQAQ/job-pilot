"""Default region pack: generic ATS senders, English phrases, generic stages."""

from jobpilot.regions.base import YamlRegionPack


class GlobalEnPack(YamlRegionPack):
    name = "global_en"
    package = "jobpilot.regions.global_en"


__all__ = ["GlobalEnPack"]
