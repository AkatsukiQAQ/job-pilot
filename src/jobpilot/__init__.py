"""Mita JobPilot: local-first, read-only-integrated job-hunting workbench."""

from importlib.metadata import PackageNotFoundError, version


def get_version() -> str:
    try:
        return version("jobpilot")
    except PackageNotFoundError:  # running from a source tree without install
        return "0.0.0+unknown"


__all__ = ["get_version"]
