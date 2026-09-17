from __future__ import annotations

from pathlib import Path

from typer.testing import CliRunner

from jobpilot.cli import app


def test_help_lists_commands(runner: CliRunner) -> None:
    result = runner.invoke(app, ["--help"])
    assert result.exit_code == 0, result.output
    for cmd in ("campaign", "doctor", "init", "version"):
        assert cmd in result.output


def test_version_does_not_create_data_dir(runner: CliRunner, tmp_path: Path) -> None:
    result = runner.invoke(app, ["version"])
    assert result.exit_code == 0, result.output
    assert result.output.strip()
    assert not (tmp_path / "data").exists()

    result = runner.invoke(app, ["--version"])
    assert result.exit_code == 0, result.output
    assert not (tmp_path / "data").exists()


def test_doctor_before_init(runner: CliRunner, tmp_path: Path) -> None:
    result = runner.invoke(app, ["doctor"])
    assert result.exit_code == 0, result.output
    assert "not created" in result.output
    assert "env" in result.output  # secret backend warning is visible
    assert not (tmp_path / "data" / "jobpilot.db").exists()


def test_mcp_entry_point_is_a_placeholder() -> None:
    import pytest

    from jobpilot.mcp_server import main

    with pytest.raises(SystemExit) as exc:
        main()
    assert exc.value.code == 2
