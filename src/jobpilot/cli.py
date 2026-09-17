"""`jobpilot` CLI: campaign add/list, init, doctor, version.

Settings are built once per invocation in the root callback and injected via ctx.obj. The
database is opened lazily so `--help`, `version` and `doctor` never create files.
"""

from __future__ import annotations

import json
import platform
import sqlite3
import sys
from dataclasses import dataclass, field
from datetime import date
from typing import Annotated, Any
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

import typer
from rich.console import Console
from rich.table import Table

from jobpilot import get_version
from jobpilot.domain import Campaign, CampaignCreate, CampaignKind
from jobpilot.regions import get_region_pack, list_region_packs
from jobpilot.secrets import SecretBackendUnavailable, SecretStore, build_secret_store
from jobpilot.settings import Settings
from jobpilot.store.db import (
    connect,
    current_version,
    has_fts5,
    latest_available_version,
    run_migrations,
)
from jobpilot.store.repo import CampaignRepo

console = Console()
err = Console(stderr=True)


@dataclass
class AppContext:
    settings: Settings
    _conn: sqlite3.Connection | None = field(default=None, repr=False)

    def db(self) -> sqlite3.Connection:
        if self._conn is None:
            self._conn = connect(self.settings.db_path)
            run_migrations(self._conn)
        return self._conn

    def secrets(self) -> SecretStore:
        return build_secret_store(self.settings)

    def active_campaign(self) -> Campaign | None:
        if not self.settings.db_path.exists():
            return None
        return CampaignRepo(self.db()).get_active()

    def effective_tz(self) -> tuple[str, str]:
        """Return (tz name, source) where source is env | region pack name | default."""
        if self.settings.tz:
            return self.settings.tz, "JOBPILOT_TZ"
        campaign = self.active_campaign()
        if campaign is not None and campaign.region_pack in list_region_packs():
            pack = get_region_pack(campaign.region_pack)
            return pack.default_tz, f"region pack {pack.name}"
        return "UTC", "default"


app = typer.Typer(
    name="jobpilot",
    no_args_is_help=True,
    add_completion=False,
    help="Mita JobPilot: local-first, read-only job-hunting workbench.",
)
campaign_app = typer.Typer(help="Job-hunting campaigns (cycles).", no_args_is_help=True)
app.add_typer(campaign_app, name="campaign")


def _version_callback(value: bool) -> None:
    if value:
        typer.echo(get_version())
        raise typer.Exit()


def _ctx(ctx: typer.Context) -> AppContext:
    obj = ctx.obj
    assert isinstance(obj, AppContext)
    return obj


@app.callback()
def main(
    ctx: typer.Context,
    version: Annotated[
        bool,
        typer.Option(
            "--version",
            callback=_version_callback,
            is_eager=True,
            help="Show the version and exit.",
        ),
    ] = False,
) -> None:
    ctx.obj = AppContext(settings=Settings())


@app.command()
def version() -> None:
    """Print the installed version."""
    typer.echo(get_version())


def _parse_date(value: str | None, name: str) -> date | None:
    if value is None:
        return None
    try:
        return date.fromisoformat(value)
    except ValueError as e:
        raise typer.BadParameter(f"{name} must be an ISO date (YYYY-MM-DD)") from e


def _parse_flags(items: list[str] | None) -> dict[str, Any]:
    flags: dict[str, Any] = {}
    for item in items or []:
        key, sep, raw = item.partition("=")
        key = key.strip()
        if not key:
            raise typer.BadParameter(f"invalid --flag {item!r}")
        if not sep:
            flags[key] = True
            continue
        try:
            flags[key] = json.loads(raw)
        except json.JSONDecodeError:
            flags[key] = raw
    return flags


def _campaign_dict(c: Campaign) -> dict[str, Any]:
    return json.loads(c.model_dump_json())


@campaign_app.command("add")
def campaign_add(
    ctx: typer.Context,
    name: Annotated[str, typer.Option("--name", help="Campaign name, e.g. a cycle label.")],
    kind: Annotated[CampaignKind, typer.Option("--kind", help="Kind of cycle.")],
    region_pack: Annotated[str, typer.Option("--region-pack", help="Registered region pack name.")],
    starts: Annotated[str | None, typer.Option("--starts", help="ISO start date.")] = None,
    ends: Annotated[str | None, typer.Option("--ends", help="ISO end date.")] = None,
    flag: Annotated[
        list[str] | None,
        typer.Option("--flag", help="Flag as key or key=value (JSON value); repeatable."),
    ] = None,
    inactive: Annotated[bool, typer.Option("--inactive", help="Create as inactive.")] = False,
    as_json: Annotated[bool, typer.Option("--json", help="Print the row as JSON.")] = False,
) -> None:
    """Create a campaign (job-search cycle)."""
    if region_pack not in list_region_packs():
        raise typer.BadParameter(
            f"unknown region pack {region_pack!r}; available: {', '.join(list_region_packs())}"
        )
    try:
        new = CampaignCreate(
            name=name,
            kind=kind,
            region_pack=region_pack,
            starts_on=_parse_date(starts, "--starts"),
            ends_on=_parse_date(ends, "--ends"),
            flags=_parse_flags(flag),
            is_active=not inactive,
        )
    except ValueError as e:
        raise typer.BadParameter(str(e)) from e
    app_ctx = _ctx(ctx)
    app_ctx.settings.ensure_dirs()
    try:
        created = CampaignRepo(app_ctx.db()).add(new)
    except sqlite3.IntegrityError as e:
        err.print(f"[red]error:[/red] campaign {name!r} already exists ({e})")
        raise typer.Exit(code=1) from e
    if as_json:
        typer.echo(json.dumps(_campaign_dict(created), ensure_ascii=False))
    else:
        console.print(f"created campaign #{created.campaign_id} {created.name!r}")


@campaign_app.command("list")
def campaign_list(
    ctx: typer.Context,
    as_json: Annotated[bool, typer.Option("--json", help="Print rows as JSON.")] = False,
    all_rows: Annotated[bool, typer.Option("--all", help="Include inactive campaigns.")] = True,
) -> None:
    """List campaigns."""
    app_ctx = _ctx(ctx)
    if not app_ctx.settings.db_path.exists():
        rows: list[Campaign] = []
    else:
        rows = CampaignRepo(app_ctx.db()).list(include_inactive=all_rows)
    if as_json:
        typer.echo(json.dumps([_campaign_dict(c) for c in rows], ensure_ascii=False))
        return
    if not rows:
        console.print(
            "no campaigns yet; run `jobpilot campaign add --name ... --kind ... --region-pack ...`"
        )
        return
    table = Table(title="campaigns")
    for col in ("id", "name", "kind", "region pack", "starts", "ends", "active"):
        table.add_column(col)
    for c in rows:
        table.add_row(
            str(c.campaign_id),
            c.name,
            c.kind.value,
            c.region_pack,
            c.starts_on.isoformat() if c.starts_on else "-",
            c.ends_on.isoformat() if c.ends_on else "-",
            "yes" if c.is_active else "no",
        )
    console.print(table)


@dataclass
class _Check:
    name: str
    value: str
    level: str = "ok"  # ok | warn | fail


def _run_doctor(app_ctx: AppContext) -> list[_Check]:
    s = app_ctx.settings
    checks: list[_Check] = [
        _Check("python", platform.python_version()),
        _Check("sqlite", sqlite3.sqlite_version),
        _Check("data_dir", f"{s.data_dir} ({'exists' if s.data_dir.exists() else 'not created'})"),
    ]

    available = latest_available_version()
    if s.db_path.exists():
        conn = connect(s.db_path)
        applied = current_version(conn)
        level = "ok" if applied == available else "warn"
        checks.append(
            _Check("database", f"{s.db_path} (schema v{applied}, available v{available})", level)
        )
        checks.append(
            _Check("fts5", "yes" if has_fts5(conn) else "no", "ok" if has_fts5(conn) else "fail")
        )
        conn.close()
    else:
        checks.append(_Check("database", f"{s.db_path} (not created; run `jobpilot init`)", "warn"))
        probe = sqlite3.connect(":memory:")
        fts = has_fts5(probe)
        probe.close()
        checks.append(_Check("fts5", "yes" if fts else "no", "ok" if fts else "fail"))

    tz_name, tz_source = app_ctx.effective_tz()
    try:
        ZoneInfo(tz_name)
        checks.append(_Check("timezone", f"{tz_name} ({tz_source})"))
    except ZoneInfoNotFoundError:
        checks.append(
            _Check("timezone", f"{tz_name} ({tz_source}) is not a valid IANA zone", "fail")
        )

    checks.append(_Check("web", f"{s.base_url} auth_mode={s.auth_mode} (Phase 2+)"))

    try:
        store = app_ctx.secrets()
        level = "warn" if store.name == "env" else "ok"
        note = " (env backend is plaintext; tests/CI only)" if store.name == "env" else ""
        checks.append(_Check("secret_backend", f"{store.name}{note}", level))
    except SecretBackendUnavailable as e:
        checks.append(_Check("secret_backend", f"unavailable: {e}", "fail"))

    checks.append(_Check("region_packs", ", ".join(list_region_packs())))
    campaign = app_ctx.active_campaign()
    checks.append(
        _Check(
            "active_campaign",
            f"#{campaign.campaign_id} {campaign.name} ({campaign.kind.value}, {campaign.region_pack})"
            if campaign
            else "none",
            "ok" if campaign else "warn",
        )
    )
    checks.append(
        _Check(
            "models",
            f"classifier={s.classifier_model or 'unset'} chat={s.chat_model or 'unset'}",
            "ok" if (s.classifier_model and s.chat_model) else "warn",
        )
    )
    return checks


def _print_doctor(checks: list[_Check], quiet: bool) -> int:
    failures = 0
    table = Table(title="jobpilot doctor", show_lines=False)
    table.add_column("check")
    table.add_column("status")
    table.add_column("detail")
    for c in checks:
        if c.level == "fail":
            failures += 1
        if quiet and c.level == "ok":
            continue
        colour = {"ok": "green", "warn": "yellow", "fail": "red"}[c.level]
        table.add_row(c.name, f"[{colour}]{c.level}[/{colour}]", c.value)
    if not quiet or table.row_count:
        console.print(table)
    return failures


@app.command()
def doctor(
    ctx: typer.Context,
    quiet: Annotated[
        bool, typer.Option("--quiet", help="Only show warnings and failures.")
    ] = False,
) -> None:
    """Report environment, storage, timezone, secrets and region-pack status."""
    failures = _print_doctor(_run_doctor(_ctx(ctx)), quiet)
    if failures:
        raise typer.Exit(code=1)


@app.command()
def init(ctx: typer.Context) -> None:
    """Create the data directory, apply migrations, bootstrap the first campaign from env."""
    app_ctx = _ctx(ctx)
    s = app_ctx.settings
    s.ensure_dirs()
    conn = app_ctx.db()
    repo = CampaignRepo(conn)
    if repo.count() == 0 and s.campaign_bootstrap_complete():
        assert s.campaign_name is not None and s.campaign_kind is not None
        assert s.campaign_region_pack is not None
        if s.campaign_region_pack not in list_region_packs():
            err.print(f"[red]error:[/red] unknown region pack {s.campaign_region_pack!r}")
            raise typer.Exit(code=1)
        created = repo.add(
            CampaignCreate(
                name=s.campaign_name,
                kind=s.campaign_kind,
                region_pack=s.campaign_region_pack,
                starts_on=s.campaign_starts,
                ends_on=s.campaign_ends,
            ),
            source="init",
        )
        console.print(f"created campaign #{created.campaign_id} {created.name!r} from environment")
    elif repo.count() == 0:
        console.print(
            "no campaign yet: run `jobpilot campaign add ...` or set JOBPILOT_CAMPAIGN_NAME/_KIND/_REGION_PACK"
        )
    failures = _print_doctor(_run_doctor(app_ctx), quiet=False)
    if failures:
        raise typer.Exit(code=1)


def run() -> None:  # pragma: no cover - convenience for `python -m jobpilot.cli`
    app()


if __name__ == "__main__":  # pragma: no cover
    sys.exit(app())
