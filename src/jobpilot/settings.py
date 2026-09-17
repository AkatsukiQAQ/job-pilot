"""Single pydantic-settings model (JOBPILOT_ prefix).

Rules: every field has a default so `Settings()` always constructs; derived values are
filled in an after-validator; nothing here encodes a person, a region or a model id.
Never instantiate at import time; the CLI builds one Settings per invocation.
"""

from __future__ import annotations

from datetime import date
from pathlib import Path
from typing import Literal, Self

from platformdirs import user_data_dir
from pydantic import Field, SecretStr, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

from jobpilot.domain import CampaignKind

APP_DIR_NAME = "JobPilot"  # %LOCALAPPDATA%\JobPilot | ~/.local/share/JobPilot

AuthMode = Literal["none", "password", "proxy"]
SecretBackend = Literal["auto", "keyring", "dpapi", "fernet", "env"]
LogLevel = Literal["DEBUG", "INFO", "WARNING", "ERROR"]


def default_data_dir() -> Path:
    # roaming=False on purpose: DPAPI blobs must not roam to another machine.
    return Path(user_data_dir(APP_DIR_NAME, appauthor=False))


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_prefix="JOBPILOT_",
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        env_ignore_empty=True,
    )

    # storage
    data_dir: Path = Field(default_factory=default_data_dir)
    database_path: Path | None = None  # derived: data_dir / "jobpilot.db"

    # display; None -> active campaign's region pack default_tz -> "UTC"
    tz: str | None = None

    # web (Phase 2+; declared now so deployment stays env-only)
    host: str = "127.0.0.1"
    port: int = Field(default=8765, ge=1, le=65535)
    base_url: str | None = None  # derived: http://{host}:{port}
    auth_mode: AuthMode = "none"

    # sync (Phase 1)
    poll_seconds: int = Field(default=90, ge=15)

    # LLM (decision D8: model ids only from config, "provider:model-id")
    classifier_model: str | None = None
    chat_model: str | None = None

    # secrets
    secret_backend: SecretBackend = "auto"
    fernet_key: SecretStr | None = None  # JOBPILOT_FERNET_KEY, non-Windows / containers

    # bootstrap of the first campaign (decision D16: never seeded by migrations)
    campaign_name: str | None = None
    campaign_kind: CampaignKind | None = None
    campaign_region_pack: str | None = None
    campaign_starts: date | None = None
    campaign_ends: date | None = None

    log_level: LogLevel = "INFO"

    @model_validator(mode="after")
    def _derive(self) -> Self:
        if self.database_path is None:
            self.database_path = self.data_dir / "jobpilot.db"
        if self.base_url is None:
            self.base_url = f"http://{self.host}:{self.port}"
        return self

    @property
    def db_path(self) -> Path:
        assert self.database_path is not None  # filled by _derive
        return self.database_path

    @property
    def secrets_dir(self) -> Path:
        return self.data_dir / "secrets"

    @property
    def rules_dir(self) -> Path:
        return self.data_dir / "rules"  # user_senders.yaml lives here, never in the repo

    @property
    def imports_dir(self) -> Path:
        return self.data_dir / "imports"

    @property
    def backups_dir(self) -> Path:
        return self.data_dir / "backups"

    @property
    def logs_dir(self) -> Path:
        return self.data_dir / "logs"

    def effective_tz(self, fallback: str | None = None) -> str:
        return self.tz or fallback or "UTC"

    def campaign_bootstrap_complete(self) -> bool:
        return bool(self.campaign_name and self.campaign_kind and self.campaign_region_pack)

    def ensure_dirs(self) -> None:
        for p in (
            self.data_dir,
            self.secrets_dir,
            self.rules_dir,
            self.imports_dir,
            self.backups_dir,
            self.logs_dir,
        ):
            p.mkdir(parents=True, exist_ok=True)


__all__ = ["APP_DIR_NAME", "AuthMode", "LogLevel", "SecretBackend", "Settings", "default_data_dir"]
