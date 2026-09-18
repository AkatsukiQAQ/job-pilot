"""Google OAuth for one or more mailboxes: consent, scope assertions, token lifecycle.

Read-only guarantee, layer 1: the token is minted with exactly the two read-only scopes and is
never persisted unless Google granted exactly those. Tokens are sealed in the SecretStore under
the ``google_token`` slot, qualified per account (``acct-<sha256(email)[:16]>``), so the file
name never reveals the address.
"""

from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
from typing import Any

import google_auth_httplib2
from google.auth.exceptions import RefreshError
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow

from jobpilot.connectors.gmail.readonly_http import GetOnlyHttp
from jobpilot.secrets import SecretStore

GMAIL_READONLY = "https://www.googleapis.com/auth/gmail.readonly"
CALENDAR_EVENTS_READONLY = "https://www.googleapis.com/auth/calendar.events.readonly"
REQUESTED_SCOPES: tuple[str, ...] = (GMAIL_READONLY, CALENDAR_EVENTS_READONLY)
ALLOWED_SCOPES: frozenset[str] = frozenset(REQUESTED_SCOPES)
TOKENINFO_URL = "https://oauth2.googleapis.com/tokeninfo"
TOKEN_SLOT = "google_token"
_RELAX_ENV = "OAUTHLIB_RELAX_TOKEN_SCOPE"


class ScopeViolation(RuntimeError):
    """The token carries scopes other than the two read-only ones (or lacks one of them)."""


class ClientSecretError(RuntimeError):
    """client_secret.json missing or not a Desktop-app client."""


class AuthRequired(RuntimeError):
    """No usable token: consent never happened, or the refresh token was revoked/expired."""


class ConsentTimeout(RuntimeError):
    """The loopback server timed out waiting for the browser redirect."""


def get_token_ref(email: str) -> str:
    """SecretStore qualifier for an account; hides the address in file names."""
    digest = hashlib.sha256(email.strip().casefold().encode("utf-8")).hexdigest()
    return f"acct-{digest[:16]}"


def get_client_config(path: Path) -> dict[str, Any]:
    if not path.exists():
        raise ClientSecretError(
            f"OAuth client file not found: {path}. Download the Desktop-app client JSON from"
            " Google Cloud Console and save it there."
        )
    try:
        cfg = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as e:
        raise ClientSecretError(f"cannot read OAuth client file: {e.__class__.__name__}") from e
    if not isinstance(cfg, dict) or "installed" not in cfg:
        raise ClientSecretError(
            "expected a 'Desktop app' OAuth client (top-level key 'installed'); 'web' clients"
            " cannot use the loopback flow"
        )
    return cfg


def get_checked_scopes(creds: Credentials, *, require_all: bool) -> frozenset[str]:
    """Assert the token's scopes against the allowlist.

    ``require_all=True`` (right after consent, when granted_scopes is authoritative) demands
    exactly the two scopes; ``False`` (after reload/refresh) only forbids extra scopes.
    """
    granted = frozenset(creds.granted_scopes or ())
    if not granted:
        granted = frozenset(creds.scopes or ())
    extra = granted - ALLOWED_SCOPES
    if extra:
        raise ScopeViolation(
            f"token carries non-read-only scopes {sorted(extra)}; revoke it at"
            " https://myaccount.google.com/permissions and run `jobpilot auth google` again"
        )
    missing = ALLOWED_SCOPES - granted
    if require_all and missing:
        raise ScopeViolation(
            f"missing scopes {sorted(missing)}; run `jobpilot auth google` again and tick both"
            " permissions on the consent screen"
        )
    return granted


def fetch_consent(
    client_config: dict[str, Any],
    *,
    login_hint: str | None,
    host: str = "127.0.0.1",
    timeout_seconds: int = 300,
    open_browser: bool = True,
) -> Credentials:
    """Run the loopback + PKCE consent flow and return credentials with exactly the two scopes."""
    from google_auth_oauthlib.flow import WSGITimeoutError

    flow = InstalledAppFlow.from_client_config(client_config, scopes=list(REQUESTED_SCOPES))
    kwargs: dict[str, Any] = {
        "prompt": "consent" if login_hint else "select_account consent",
        "include_granted_scopes": "false",  # installed apps cannot do incremental auth anyway
    }
    if login_hint:
        kwargs["login_hint"] = login_hint
    previous = os.environ.get(_RELAX_ENV)
    # A partial grant would otherwise surface as an oauthlib Warning; we want our own check.
    os.environ[_RELAX_ENV] = "1"
    try:
        creds = flow.run_local_server(
            host=host,
            bind_addr=host,
            port=0,
            open_browser=open_browser,
            timeout_seconds=timeout_seconds,
            **kwargs,
        )
    except WSGITimeoutError as e:
        raise ConsentTimeout(str(e)) from e
    finally:
        if previous is None:
            os.environ.pop(_RELAX_ENV, None)
        else:
            os.environ[_RELAX_ENV] = previous
    if not isinstance(creds, Credentials):  # external-account credentials are not user tokens
        raise ScopeViolation(f"unexpected credential type {type(creds).__name__}")
    get_checked_scopes(creds, require_all=True)
    return creds


def get_refresh_request() -> google_auth_httplib2.Request:
    """Transport for token refresh: the only POST the inner layer permits."""
    return google_auth_httplib2.Request(GetOnlyHttp(timeout=60))


def fetch_tokeninfo(http: Any, creds: Credentials) -> dict[str, Any]:
    """Online cross-check of the issued scopes (GET; host is allow-listed)."""
    if not creds.valid:
        creds.refresh(get_refresh_request())
    resp, content = http.request(f"{TOKENINFO_URL}?access_token={creds.token}", "GET")
    status = int(getattr(resp, "status", 0))
    if status != 200:
        raise AuthRequired(f"tokeninfo returned HTTP {status}")
    info: dict[str, Any] = json.loads(content)
    scopes = frozenset(str(info.get("scope", "")).split())
    if not scopes <= ALLOWED_SCOPES:
        raise ScopeViolation(
            f"tokeninfo reports unexpected scopes {sorted(scopes - ALLOWED_SCOPES)}"
        )
    if creds.client_id and info.get("aud") not in (None, creds.client_id):
        raise ScopeViolation("tokeninfo audience does not match this OAuth client")
    return info


def get_credentials(store: SecretStore, token_ref: str) -> Credentials | None:
    blob = store.get(TOKEN_SLOT, qualifier=token_ref)
    if blob is None:
        return None
    info = json.loads(blob)
    creds = Credentials.from_authorized_user_info(info)  # scopes come from the stored JSON
    get_checked_scopes(creds, require_all=False)
    return creds


def fetch_fresh_credentials(store: SecretStore, token_ref: str) -> Credentials:
    """Load, refresh if needed (the one permitted POST), re-check scopes, persist."""
    creds = get_credentials(store, token_ref)
    if creds is None:
        raise AuthRequired("no token stored for this account; run `jobpilot auth google`")
    if not creds.valid:
        try:
            creds.refresh(get_refresh_request())
        except RefreshError as e:
            if "invalid_grant" in str(e):
                raise AuthRequired(
                    "refresh token revoked or expired; run `jobpilot auth google` again"
                ) from e
            raise
        get_checked_scopes(creds, require_all=False)
        store.set(TOKEN_SLOT, creds.to_json(), qualifier=token_ref)
    return creds


__all__ = [
    "fetch_consent",
    "fetch_fresh_credentials",
    "fetch_tokeninfo",
    "get_checked_scopes",
    "get_client_config",
    "get_credentials",
    "get_refresh_request",
    "get_token_ref",
]
