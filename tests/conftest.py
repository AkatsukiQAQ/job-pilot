"""Shared fixtures: isolated environment, temp data dir, env secret backend."""

from __future__ import annotations

import os
import sqlite3
from collections.abc import Iterator
from pathlib import Path

import pytest
from typer.testing import CliRunner

from jobpilot.settings import Settings
from jobpilot.store.db import connect, run_migrations


@pytest.fixture(autouse=True)
def _isolate_env(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    for key in list(os.environ):
        if key.startswith("JOBPILOT_"):
            monkeypatch.delenv(key, raising=False)
    monkeypatch.chdir(tmp_path)  # no .env file in cwd
    monkeypatch.setenv("JOBPILOT_DATA_DIR", str(tmp_path / "data"))
    monkeypatch.setenv("JOBPILOT_SECRET_BACKEND", "env")


@pytest.fixture
def settings() -> Settings:
    return Settings()


@pytest.fixture
def runner() -> CliRunner:
    return CliRunner()


@pytest.fixture
def conn(settings: Settings) -> Iterator[sqlite3.Connection]:
    c = connect(settings.db_path)
    run_migrations(c)
    yield c
    c.close()


REPO_ROOT = Path(__file__).resolve().parents[1]
SRC_ROOT = REPO_ROOT / "src" / "jobpilot"
