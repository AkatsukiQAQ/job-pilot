"""`jobpilot` CLI.

Settings are built once per invocation in the root callback and injected via ctx.obj. The
database is opened lazily so `--help`, `version` and `doctor` never create files.
"""

from __future__ import annotations

import json
import os
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
from jobpilot.connectors.gmail import auth as gmail_auth
from jobpilot.connectors.gmail import readonly_http as gmail_http
from jobpilot.connectors.gmail import sync as gmail_api
from jobpilot.domain import Campaign, CampaignCreate, CampaignKind, SourceHealth
from jobpilot.regions import get_region_pack, list_region_packs
from jobpilot.secrets import (
    ALLOWED_SLOTS,
    SecretBackendUnavailable,
    SecretError,
    SecretStore,
    build_secret_store,
)
from jobpilot.settings import Settings
from jobpilot.store.db import (
    connect,
    current_version,
    has_fts5,
    latest_available_version,
    run_migrations,
    transaction,
)
from jobpilot.store.repo import CampaignRepo, EmailAccountRepo, SourceStateRepo

console = Console(highlight=False)
err = Console(stderr=True, highlight=False)


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
auth_app = typer.Typer(
    help="Google account authorization (read-only scopes only).", no_args_is_help=True
)
secrets_app = typer.Typer(
    help="API keys and tokens in the OS-protected secret store.", no_args_is_help=True
)
app.add_typer(campaign_app, name="campaign")
app.add_typer(auth_app, name="auth")
app.add_typer(secrets_app, name="secrets")


def _version_callback(value: bool) -> None:
    if value:
        typer.echo(get_version())
        raise typer.Exit()


def _ctx(ctx: typer.Context) -> AppContext:
    obj = ctx.obj
    assert isinstance(obj, AppContext)
    return obj


def _fail(message: str, code: int = 1) -> typer.Exit:
    err.print(f"[red]error:[/red] {message}")
    return typer.Exit(code=code)


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


# ---------------------------------------------------------------------------- campaign


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
        raise _fail(f"campaign {name!r} already exists ({e})") from e
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
    rows: list[Campaign] = []
    if app_ctx.settings.db_path.exists():
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


# ---------------------------------------------------------------------------- secrets


@secrets_app.command("set")
def secrets_set(
    ctx: typer.Context,
    slot: Annotated[str, typer.Argument(help="Slot name, e.g. anthropic_api_key.")],
    qualifier: Annotated[
        str | None, typer.Option("--qualifier", help="Per-account qualifier.")
    ] = None,
) -> None:
    """Store a secret (prompted, hidden input) in the OS-protected store."""
    if slot not in ALLOWED_SLOTS:
        raise typer.BadParameter(
            f"unknown slot {slot!r}; allowed: {', '.join(sorted(ALLOWED_SLOTS))}"
        )
    app_ctx = _ctx(ctx)
    value = typer.prompt(f"value for {slot}", hide_input=True)
    try:
        app_ctx.settings.ensure_dirs()
        app_ctx.secrets().set(slot, value.strip(), qualifier=qualifier)
    except SecretError as e:
        raise _fail(str(e)) from e
    console.print(f"stored {slot}")


# ---------------------------------------------------------------------------- auth


def _scope_short_names() -> str:
    return ", ".join(s.rsplit("/", 1)[-1] for s in gmail_auth.REQUESTED_SCOPES)


@auth_app.command("google")
def auth_google(
    ctx: typer.Context,
    login_hint: Annotated[
        str | None, typer.Option("--login-hint", help="Mailbox to pre-select in the browser.")
    ] = None,
    account_label: Annotated[
        str | None, typer.Option("--account-label", help="Optional label.")
    ] = None,
    no_browser: Annotated[
        bool, typer.Option("--no-browser", help="Print the URL instead.")
    ] = False,
    timeout: Annotated[
        int | None, typer.Option("--timeout", help="Seconds to wait for consent.")
    ] = None,
    yes: Annotated[
        bool, typer.Option("--yes", help="Accept a mailbox that differs from --login-hint.")
    ] = False,
) -> None:
    """Authorize one mailbox with the two read-only scopes. Run once per account."""
    app_ctx = _ctx(ctx)
    s = app_ctx.settings
    s.ensure_dirs()
    try:
        client_config = gmail_auth.get_client_config(s.client_secret_path)
    except gmail_auth.ClientSecretError as e:
        raise _fail(str(e)) from e
    console.print(f"requesting scopes: {_scope_short_names()} (read-only)")
    try:
        creds = gmail_auth.fetch_consent(
            client_config,
            login_hint=login_hint,
            host=s.oauth_loopback_host,
            timeout_seconds=timeout or s.oauth_timeout_seconds,
            open_browser=not no_browser,
        )
    except gmail_auth.ScopeViolation as e:
        raise _fail(f"token not stored: {e}") from e
    except gmail_auth.ConsentTimeout as e:
        raise _fail(f"consent timed out: {e}") from e

    http = gmail_http.get_read_only_http(creds)
    service = gmail_http.get_gmail_service(http)
    budget = gmail_api.Budget(s.gmail_units_per_minute)
    profile = gmail_api.fetch_profile(service, budget)
    email = str(profile.get("emailAddress") or "").casefold()
    if not email:
        raise _fail("could not determine the authorized mailbox address")
    if login_hint and email != login_hint.casefold():
        console.print(f"[yellow]the browser authorized {email}, not {login_hint}[/yellow]")
        if not yes and not typer.confirm("keep this account?", default=False):
            raise _fail("aborted; token not stored")
    try:
        gmail_auth.fetch_tokeninfo(http, creds)
    except (gmail_auth.ScopeViolation, gmail_auth.AuthRequired) as e:
        raise _fail(f"token not stored: {e}") from e

    token_ref = gmail_auth.get_token_ref(email)
    info = json.loads(creds.to_json())
    info["account"] = email
    store = app_ctx.secrets()
    try:
        store.set(gmail_auth.TOKEN_SLOT, json.dumps(info), qualifier=token_ref)
    except SecretError as e:
        raise _fail(f"cannot store the token: {e}") from e
    conn = app_ctx.db()
    try:
        with transaction(conn):
            accounts = EmailAccountRepo(conn)
            existing = accounts.get_by_email(email)
            if existing is None:
                account = accounts.add(email, token_ref=token_ref, label=account_label)
            elif not existing.enabled:
                account = accounts.set_enabled(existing.account_id, True)
            else:
                account = existing
            SourceStateRepo(conn).mark_success(
                f"gmail:{account.account_id}", transport=gmail_http.TRANSPORT_NAME
            )
    except Exception:
        store.delete(gmail_auth.TOKEN_SLOT, qualifier=token_ref)
        raise
    console.print(
        f"authorized {email} as account #{account.account_id}; scopes: {_scope_short_names()}"
    )
    console.print("next: `jobpilot sync --backfill-days 180` (Phase 1 slice 4)")


@auth_app.command("list")
def auth_list(ctx: typer.Context) -> None:
    """List authorized mailboxes and their sync health."""
    app_ctx = _ctx(ctx)
    if not app_ctx.settings.db_path.exists():
        console.print("no accounts yet; run `jobpilot auth google`")
        return
    conn = app_ctx.db()
    accounts = EmailAccountRepo(conn).list()
    if not accounts:
        console.print("no accounts yet; run `jobpilot auth google`")
        return
    states = {st.source: st for st in SourceStateRepo(conn).list()}
    table = Table(title="google accounts")
    for col in ("id", "email", "label", "enabled", "cursor", "health", "last sync"):
        table.add_column(col)
    for a in accounts:
        st = states.get(f"gmail:{a.account_id}")
        table.add_row(
            str(a.account_id),
            a.email,
            a.label or "-",
            "yes" if a.enabled else "no",
            "set" if a.history_id else "none",
            st.status.value if st else "-",
            a.last_sync_at.isoformat() if a.last_sync_at else "-",
        )
    console.print(table)


@auth_app.command("forget")
def auth_forget(
    ctx: typer.Context,
    email: Annotated[str, typer.Argument(help="Mailbox address to forget.")],
) -> None:
    """Delete the local token and disable the account (revoke on Google's side yourself)."""
    app_ctx = _ctx(ctx)
    conn = app_ctx.db()
    accounts = EmailAccountRepo(conn)
    account = accounts.get_by_email(email)
    if account is None:
        raise _fail(f"no account {email.casefold()!r}")
    app_ctx.secrets().delete(gmail_auth.TOKEN_SLOT, qualifier=account.token_ref)
    with transaction(conn):
        accounts.set_enabled(account.account_id, False)
        SourceStateRepo(conn).mark_disabled(f"gmail:{account.account_id}")
    console.print(
        f"forgot local token for account #{account.account_id}. To revoke on Google's side open"
        " https://myaccount.google.com/permissions (we never send a revoke request ourselves)."
    )


# ---------------------------------------------------------------------------- doctor / init


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
    db_exists = s.db_path.exists()
    if db_exists:
        conn = connect(s.db_path)
        applied = current_version(conn)
        level = "ok" if applied == available else "warn"
        checks.append(
            _Check("database", f"{s.db_path} (schema v{applied}, available v{available})", level)
        )
        fts = has_fts5(conn)
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

    cs = s.client_secret_path
    if cs.exists():
        try:
            gmail_auth.get_client_config(cs)
            checks.append(_Check("google_client_secret", f"{cs} (Desktop app client)"))
        except gmail_auth.ClientSecretError as e:
            checks.append(_Check("google_client_secret", str(e), "fail"))
    else:
        checks.append(
            _Check(
                "google_client_secret", f"{cs} (missing; needed for `jobpilot auth google`)", "warn"
            )
        )

    if db_exists:
        conn = connect(s.db_path)
        accounts = EmailAccountRepo(conn).list()
        enabled = [a for a in accounts if a.enabled]
        checks.append(
            _Check(
                "email_accounts",
                f"{len(enabled)} enabled / {len(accounts)} total",
                "ok" if enabled else "warn",
            )
        )
        for st in SourceStateRepo(conn).list():
            level = {
                SourceHealth.HEALTHY: "ok",
                SourceHealth.DEGRADED: "warn",
                SourceHealth.DISABLED: "ok",
                SourceHealth.AUTH_REQUIRED: "fail",
                SourceHealth.UNAVAILABLE: "fail",
            }[st.status]
            detail = st.status.value
            if st.last_success_at:
                detail += f", last success {st.last_success_at.isoformat()}"
            if st.last_error:
                detail += f", last error {st.last_error}"
            checks.append(_Check(f"source {st.source}", detail, level))
        conn.close()
    else:
        checks.append(_Check("email_accounts", "0 (database not created)", "warn"))

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
    """Report environment, storage, timezone, secrets, accounts and region-pack status."""
    failures = _print_doctor(_run_doctor(_ctx(ctx)), quiet)
    if failures:
        raise typer.Exit(code=1)


@app.command()
def serve(
    ctx: typer.Context,
    host: Annotated[str | None, typer.Option(help="Bind address (default JOBPILOT_HOST).")] = None,
    port: Annotated[int | None, typer.Option(help="Port (default JOBPILOT_PORT).")] = None,
    reload: Annotated[bool, typer.Option("--reload", help="Restart on code changes.")] = False,
) -> None:
    """Run the local web board: JSON API plus the built frontend."""
    import uvicorn

    from jobpilot.web.app import create_app

    s = _ctx(ctx).settings
    bind_host, bind_port = host or s.host, port or s.port
    if reload:
        # The reload worker rebuilds Settings() from the environment; pass the effective bind host
        # through so create_app's loopback guard sees what uvicorn actually binds.
        os.environ["JOBPILOT_HOST"] = bind_host
        uvicorn.run(
            "jobpilot.web.app:app_from_env",
            factory=True,
            reload=True,
            host=bind_host,
            port=bind_port,
        )
    else:
        uvicorn.run(create_app(s, bind_host=bind_host), host=bind_host, port=bind_port)


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
            raise _fail(f"unknown region pack {s.campaign_region_pack!r}")
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
            "no campaign yet: run `jobpilot campaign add ...` or set"
            " JOBPILOT_CAMPAIGN_NAME/_KIND/_REGION_PACK"
        )
    failures = _print_doctor(_run_doctor(app_ctx), quiet=False)
    if failures:
        raise typer.Exit(code=1)


def run() -> None:  # pragma: no cover - convenience for `python -m jobpilot.cli`
    app()


if __name__ == "__main__":  # pragma: no cover
    sys.exit(app())
