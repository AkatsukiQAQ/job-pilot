"""Region-pack registry. Adding a country = adding a package + one register() call."""

from __future__ import annotations

from collections.abc import Callable

from jobpilot.regions.base import RegionPack


class UnknownRegionPackError(KeyError):
    """No region pack registered under this name."""


_REGISTRY: dict[str, Callable[[], RegionPack]] = {}


def register(name: str, factory: Callable[[], RegionPack]) -> None:
    _REGISTRY[name] = factory


def list_region_packs() -> list[str]:
    return sorted(_REGISTRY)


def get_region_pack(name: str) -> RegionPack:
    try:
        factory = _REGISTRY[name]
    except KeyError as e:
        raise UnknownRegionPackError(name) from e
    return factory()


__all__ = ["UnknownRegionPackError", "get_region_pack", "list_region_packs", "register"]
