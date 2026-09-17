"""SecretStore: slot allowlist, platform-native backends, routing.

Structural guarantees (ARCHITECTURE section 4 / 12):
- Only names in ALLOWED_SLOTS can be stored; there is no slot for a LinkedIn cookie,
  an SMTP password or an App Password.
- Large blobs (OAuth token JSON) never go to the OS credential manager (2560-byte limit);
  they are sealed to a file with DPAPI (Windows) or Fernet (elsewhere).
- Values are never logged and never written in plaintext by any backend.
"""

from __future__ import annotations

import os
import re
import sys
from pathlib import Path
from typing import TYPE_CHECKING, Protocol, runtime_checkable

from pydantic import SecretStr

if TYPE_CHECKING:
    from jobpilot.settings import Settings

ALLOWED_SLOTS: frozenset[str] = frozenset(
    {
        "google_token",
        "anthropic_api_key",
        "openai_api_key",
        "adzuna_app_id",
        "adzuna_app_key",
        "jsearch_api_key",
    }
)
LARGE_SLOTS: frozenset[str] = frozenset({"google_token"})
CRED_MAX_BLOB_BYTES = 5 * 512  # CRED_MAX_CREDENTIAL_BLOB_SIZE (wincred.h)
KEYRING_SERVICE = "jobpilot"
DPAPI_ENTROPY = b"jobpilot-secretstore-v1"  # isolation from other apps only, not a key
_QUALIFIER_RE = re.compile(r"^[A-Za-z0-9._-]{1,64}$")
FERNET_KEY_HINT = (
    "JOBPILOT_FERNET_KEY is not set. Generate one with: "
    'python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"'
)


class SecretError(Exception):
    """Base class for secret-store errors."""


class UnknownSlotError(SecretError, KeyError):
    """Slot name is not in ALLOWED_SLOTS."""


class SecretBackendUnavailable(SecretError):
    """The selected backend cannot run on this platform / configuration."""


class SecretTooLargeError(SecretError):
    """Value exceeds the OS credential manager blob limit."""


def secret_key(slot: str, qualifier: str | None = None) -> str:
    """Validate the slot and build the storage key.

    The optional qualifier scopes a slot per account (decision D20), e.g.
    ``google_token__acct1``.
    """
    if slot not in ALLOWED_SLOTS:
        raise UnknownSlotError(slot)
    if qualifier is None:
        return slot
    if not _QUALIFIER_RE.fullmatch(qualifier):
        raise SecretError(f"invalid qualifier for slot {slot!r}")
    return f"{slot}__{qualifier}"


@runtime_checkable
class SecretStore(Protocol):
    name: str

    def get(self, slot: str, *, qualifier: str | None = None) -> str | None: ...

    def set(self, slot: str, value: str, *, qualifier: str | None = None) -> None: ...

    def delete(self, slot: str, *, qualifier: str | None = None) -> bool: ...


class EnvStore:
    """Read-only backend for tests / CI: reads JOBPILOT_SECRET_<KEY>. Values are plaintext."""

    name = "env"
    prefix = "JOBPILOT_SECRET_"

    def _var(self, slot: str, qualifier: str | None) -> str:
        return self.prefix + secret_key(slot, qualifier).upper()

    def get(self, slot: str, *, qualifier: str | None = None) -> str | None:
        return os.environ.get(self._var(slot, qualifier))

    def set(self, slot: str, value: str, *, qualifier: str | None = None) -> None:
        secret_key(slot, qualifier)
        raise SecretBackendUnavailable("env backend is read-only")

    def delete(self, slot: str, *, qualifier: str | None = None) -> bool:
        secret_key(slot, qualifier)
        raise SecretBackendUnavailable("env backend is read-only")


class KeyringStore:
    """OS credential manager via keyring; short keys only."""

    name = "keyring"

    def get(self, slot: str, *, qualifier: str | None = None) -> str | None:
        key = secret_key(slot, qualifier)
        import keyring

        return keyring.get_password(KEYRING_SERVICE, key)

    def set(self, slot: str, value: str, *, qualifier: str | None = None) -> None:
        key = secret_key(slot, qualifier)
        if len(value.encode("utf-16-le")) > CRED_MAX_BLOB_BYTES:
            raise SecretTooLargeError(f"{slot}: value too large for keyring; use the file store")
        import keyring

        keyring.set_password(KEYRING_SERVICE, key, value)

    def delete(self, slot: str, *, qualifier: str | None = None) -> bool:
        key = secret_key(slot, qualifier)
        import keyring
        from keyring.errors import PasswordDeleteError

        try:
            keyring.delete_password(KEYRING_SERVICE, key)
        except PasswordDeleteError:
            return False
        return True


class _FileStore:
    """Shared plumbing: one sealed file per key, atomic replace, 0600 on POSIX."""

    name = "file"
    suffix = ".bin"

    def __init__(self, secrets_dir: Path) -> None:
        self.dir = secrets_dir

    def _path(self, key: str) -> Path:
        return self.dir / f"{key}{self.suffix}"

    def _seal(self, data: bytes, key: str) -> bytes:
        raise NotImplementedError

    def _open(self, blob: bytes, key: str) -> bytes:
        raise NotImplementedError

    def get(self, slot: str, *, qualifier: str | None = None) -> str | None:
        key = secret_key(slot, qualifier)
        p = self._path(key)
        if not p.exists():
            return None
        return self._open(p.read_bytes(), key).decode("utf-8")

    def set(self, slot: str, value: str, *, qualifier: str | None = None) -> None:
        key = secret_key(slot, qualifier)
        self.dir.mkdir(parents=True, exist_ok=True)
        p = self._path(key)
        tmp = p.with_name(p.name + ".tmp")
        tmp.write_bytes(self._seal(value.encode("utf-8"), key))
        if os.name == "posix":
            tmp.chmod(0o600)
        tmp.replace(p)

    def delete(self, slot: str, *, qualifier: str | None = None) -> bool:
        p = self._path(secret_key(slot, qualifier))
        if p.exists():
            p.unlink()
            return True
        return False


class DpapiFileStore(_FileStore):
    """Windows DPAPI (current-user scope). Any process running as this user can decrypt."""

    name = "dpapi-file"
    suffix = ".dpapi"

    def __init__(self, secrets_dir: Path) -> None:
        if sys.platform != "win32":
            raise SecretBackendUnavailable("DPAPI is only available on Windows")
        super().__init__(secrets_dir)

    @staticmethod
    def _descr(key: str) -> str:
        return f"jobpilot:{key}"

    def _seal(self, data: bytes, key: str) -> bytes:
        import win32crypt
        import win32cryptcon

        # Never CRYPTPROTECT_LOCAL_MACHINE: that would let every user on the machine decrypt.
        return win32crypt.CryptProtectData(
            data,
            self._descr(key),
            DPAPI_ENTROPY,
            None,
            None,
            win32cryptcon.CRYPTPROTECT_UI_FORBIDDEN,
        )

    def _open(self, blob: bytes, key: str) -> bytes:
        import win32crypt
        import win32cryptcon

        descr, data = win32crypt.CryptUnprotectData(
            blob, DPAPI_ENTROPY, None, None, win32cryptcon.CRYPTPROTECT_UI_FORBIDDEN
        )
        if descr != self._descr(key):
            raise SecretError(f"sealed blob does not belong to slot {key!r}")
        return data


class FernetFileStore(_FileStore):
    """Fernet-sealed files for non-Windows hosts and containers. Key comes from settings."""

    name = "fernet-file"
    suffix = ".fernet"

    def __init__(self, secrets_dir: Path, key: SecretStr | None) -> None:
        super().__init__(secrets_dir)
        if key is None:
            raise SecretBackendUnavailable(FERNET_KEY_HINT)
        from cryptography.fernet import Fernet

        self._fernet = Fernet(key.get_secret_value().encode("ascii"))

    def _seal(self, data: bytes, key: str) -> bytes:
        return self._fernet.encrypt(key.encode("utf-8") + b"\n" + data)

    def _open(self, blob: bytes, key: str) -> bytes:
        plain = self._fernet.decrypt(blob)  # InvalidToken propagates
        head, _, body = plain.partition(b"\n")
        if head.decode("utf-8") != key:
            raise SecretError(f"sealed blob does not belong to slot {key!r}")
        return body


class RoutedStore:
    """Short values to `small`, LARGE_SLOTS to `large`."""

    def __init__(self, small: SecretStore, large: SecretStore) -> None:
        self.small = small
        self.large = large
        self.name = f"{small.name}+{large.name}"

    def _pick(self, slot: str) -> SecretStore:
        return self.large if slot in LARGE_SLOTS else self.small

    def get(self, slot: str, *, qualifier: str | None = None) -> str | None:
        return self._pick(slot).get(slot, qualifier=qualifier)

    def set(self, slot: str, value: str, *, qualifier: str | None = None) -> None:
        self._pick(slot).set(slot, value, qualifier=qualifier)

    def delete(self, slot: str, *, qualifier: str | None = None) -> bool:
        return self._pick(slot).delete(slot, qualifier=qualifier)


def keyring_available() -> bool:
    try:
        import keyring
        from keyring.backends import fail

        return not isinstance(keyring.get_keyring(), fail.Keyring)
    except Exception:
        return False


def build_secret_store(settings: Settings) -> SecretStore:
    """Choose backends from settings.secret_backend; raise SecretBackendUnavailable if impossible."""
    mode = settings.secret_backend
    if mode == "env":
        return EnvStore()
    if mode == "keyring":
        return KeyringStore()
    if mode == "auto":
        mode = "dpapi" if sys.platform == "win32" else "fernet"
    large: SecretStore = (
        DpapiFileStore(settings.secrets_dir)
        if mode == "dpapi"
        else FernetFileStore(settings.secrets_dir, settings.fernet_key)
    )
    small: SecretStore = KeyringStore() if keyring_available() else large
    return RoutedStore(small=small, large=large)


__all__ = [
    "ALLOWED_SLOTS",
    "CRED_MAX_BLOB_BYTES",
    "LARGE_SLOTS",
    "DpapiFileStore",
    "EnvStore",
    "FernetFileStore",
    "KeyringStore",
    "RoutedStore",
    "SecretBackendUnavailable",
    "SecretError",
    "SecretStore",
    "SecretTooLargeError",
    "UnknownSlotError",
    "build_secret_store",
    "keyring_available",
    "secret_key",
]
