from __future__ import annotations

from pathlib import Path
from zoneinfo import ZoneInfo

import pytest
from pydantic import ValidationError

from jobpilot.settings import Settings


def test_env_override_and_derived_paths(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    monkeypatch.setenv("JOBPILOT_DATA_DIR", str(tmp_path / "elsewhere"))
    s = Settings()
    assert s.data_dir == tmp_path / "elsewhere"
    assert s.db_path == tmp_path / "elsewhere" / "jobpilot.db"
    assert s.secrets_dir == tmp_path / "elsewhere" / "secrets"
    assert s.base_url == "http://127.0.0.1:8765"


def test_explicit_database_path_wins(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    monkeypatch.setenv("JOBPILOT_DATABASE_PATH", str(tmp_path / "custom.db"))
    assert Settings().db_path == tmp_path / "custom.db"


def test_no_personal_or_regional_defaults(settings: Settings) -> None:
    assert settings.tz is None
    assert settings.classifier_model is None
    assert settings.chat_model is None
    assert settings.campaign_name is None
    assert settings.campaign_kind is None
    assert settings.campaign_region_pack is None
    assert not settings.campaign_bootstrap_complete()


def test_effective_tz_falls_back_to_utc(settings: Settings) -> None:
    assert settings.effective_tz() == "UTC"
    assert settings.effective_tz("Etc/GMT-9") == "Etc/GMT-9"
    ZoneInfo(settings.effective_tz())  # resolvable (tzdata installed)


def test_tz_env_override(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("JOBPILOT_TZ", "Etc/UTC")
    assert Settings().effective_tz("Etc/GMT-9") == "Etc/UTC"


def test_invalid_auth_mode_rejected(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("JOBPILOT_AUTH_MODE", "open-bar")
    with pytest.raises(ValidationError):
        Settings()


def test_ensure_dirs_creates_layout(settings: Settings) -> None:
    settings.ensure_dirs()
    for p in (
        settings.secrets_dir,
        settings.rules_dir,
        settings.imports_dir,
        settings.backups_dir,
        settings.logs_dir,
    ):
        assert p.is_dir()
