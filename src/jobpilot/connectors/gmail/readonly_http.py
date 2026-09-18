"""Read-only guarantee, layer 2: a Google transport that cannot issue writes.

Two layers, each sufficient on its own:

* ``ReadOnlyHttp`` (outer, what googleapiclient calls) rejects every non-GET, every request to
  a host outside ``ALLOWED_HOSTS``, the ``/batch`` endpoint (its body may wrap write
  sub-requests) and any GET carrying a body, before any I/O happens.
* ``GetOnlyHttp`` (inner ``httplib2.Http``) lets through only HTTPS GETs to ``ALLOWED_HOSTS``
  plus the single POST that OAuth token refresh needs (``TOKEN_ENDPOINT``). google-auth's
  ``AuthorizedHttp`` performs refresh through ``self._request`` which wraps this inner object,
  so refresh keeps working while the outer layer never sees a POST.
"""

from __future__ import annotations

from collections.abc import Callable
from typing import Any
from urllib.parse import urlsplit

import httplib2
from google.oauth2.credentials import Credentials
from google_auth_httplib2 import AuthorizedHttp
from googleapiclient.discovery import build

ALLOWED_HOSTS: frozenset[str] = frozenset({"gmail.googleapis.com", "oauth2.googleapis.com"})
TOKEN_ENDPOINT = "https://oauth2.googleapis.com/token"
TRANSPORT_NAME = "google-readonly-http"

EgressHook = Callable[[str, str, str, int], None]  # method, host, path, status


class WriteAttempted(RuntimeError):
    """A non-GET (or off-allowlist) Google request was attempted; raised before any I/O."""


def _check_host(uri: str) -> tuple[str, str]:
    parts = urlsplit(uri)
    host = (parts.hostname or "").lower()
    if parts.scheme != "https" or host not in ALLOWED_HOSTS:
        raise WriteAttempted(f"host not allowed: {parts.scheme}://{parts.netloc}")
    return host, parts.path


class GetOnlyHttp(httplib2.Http):
    """Inner transport: HTTPS GET to allow-listed hosts, plus POST to the token endpoint only."""

    def request(  # type: ignore[override]
        self,
        uri: str,
        method: str = "GET",
        body: Any = None,
        headers: dict[str, str] | None = None,
        redirections: int = httplib2.DEFAULT_MAX_REDIRECTS,
        connection_type: Any = None,
    ) -> tuple[Any, bytes]:
        verb = (method or "GET").upper()
        _check_host(uri)
        is_token_refresh = verb == "POST" and uri.split("?", 1)[0] == TOKEN_ENDPOINT
        if verb != "GET" and not is_token_refresh:
            raise WriteAttempted(f"{verb} {uri.split('?', 1)[0]}")
        return super().request(  # type: ignore[no-any-return]
            uri,
            verb,
            body=body,
            headers=headers,
            redirections=redirections,
            connection_type=connection_type,
        )


class ReadOnlyHttp(AuthorizedHttp):
    """Outer transport handed to googleapiclient: GET-only, allow-listed hosts, no /batch."""

    def __init__(
        self,
        credentials: Credentials,
        http: Any | None = None,
        *,
        egress_hook: EgressHook | None = None,
        timeout: float = 60.0,
    ) -> None:
        super().__init__(credentials, http or GetOnlyHttp(timeout=timeout))
        self._egress_hook = egress_hook

    def request(  # type: ignore[override]
        self,
        uri: str,
        method: str = "GET",
        body: Any = None,
        headers: dict[str, str] | None = None,
        redirections: int = httplib2.DEFAULT_MAX_REDIRECTS,
        connection_type: Any = None,
        **kwargs: Any,
    ) -> tuple[Any, bytes]:
        verb = (method or "GET").upper()
        if verb != "GET":
            raise WriteAttempted(f"{verb} {uri.split('?', 1)[0]}")
        host, path = _check_host(uri)
        if "/batch" in path:
            raise WriteAttempted("batch endpoint is not allowed")
        if body not in (None, b"", ""):
            raise WriteAttempted("GET with a request body")
        resp, content = super().request(
            uri,
            "GET",
            body=None,
            headers=headers,
            redirections=redirections,
            connection_type=connection_type,
            **kwargs,
        )
        if self._egress_hook is not None:
            self._egress_hook("GET", host, path, int(getattr(resp, "status", 0)))
        return resp, content


def get_read_only_http(
    credentials: Credentials, *, egress_hook: EgressHook | None = None, timeout: float = 60.0
) -> ReadOnlyHttp:
    return ReadOnlyHttp(credentials, egress_hook=egress_hook, timeout=timeout)


def get_gmail_service(http: Any) -> Any:
    """Gmail v1 resource over the read-only transport.

    No discoveryServiceUrl -> googleapiclient uses its bundled static discovery document, so
    building the service performs zero network requests.
    """
    return build("gmail", "v1", http=http, cache_discovery=False)


__all__ = ["get_gmail_service", "get_read_only_http"]
