from __future__ import annotations

import sys
from pathlib import Path

import pytest
from pydantic import SecretStr

from jobpilot.secrets import (
    ALLOWED_SLOTS,
    LARGE_SLOTS,
    EnvStore,
    FernetFileStore,
    KeyringStore,
    RoutedStore,
    SecretBackendUnavailable,
    SecretError,
    SecretStore,
    SecretTooLargeError,
    UnknownSlotError,
    build_secret_store,
    secret_key,
)
from jobpilot.settings import Settings


def test_slot_allowlist_is_closed() -> None:
    assert "linkedin_cookie" not in ALLOWED_SLOTS
    assert "smtp_password" not in ALLOWED_SLOTS
    with pytest.raises(UnknownSlotError):
        secret_key("linkedin_cookie")
    assert LARGE_SLOTS <= ALLOWED_SLOTS


def test_qualifier() -> None:
    assert secret_key("google_token", "acct-1") == "google_token__acct-1"
    with pytest.raises(SecretError):
        secret_key("google_token", "bad qualifier!")


def test_env_store_is_read_only(monkeypatch: pytest.MonkeyPatch) -> None:
    store = EnvStore()
    assert isinstance(store, SecretStore)
    monkeypatch.setenv("JOBPILOT_SECRET_ANTHROPIC_API_KEY", "k-test")
    assert store.get("anthropic_api_key") == "k-test"
    assert store.get("openai_api_key") is None
    with pytest.raises(SecretBackendUnavailable):
        store.set("anthropic_api_key", "x")
    with pytest.raises(SecretBackendUnavailable):
        store.delete("anthropic_api_key")


def test_keyring_size_guard_before_touching_os() -> None:
    with pytest.raises(SecretTooLargeError):
        KeyringStore().set("google_token", "x" * 1300)


def test_fernet_roundtrip_and_isolation(tmp_path: Path) -> None:
    from cryptography.fernet import Fernet, InvalidToken

    key = SecretStr(Fernet.generate_key().decode())
    store = FernetFileStore(tmp_path / "secrets", key)
    assert isinstance(store, SecretStore)
    store.set("google_token", '{"refresh_token": "demo"}', qualifier="acct1")
    path = tmp_path / "secrets" / "google_token__acct1.fernet"
    assert path.exists()
    assert b"refresh_token" not in path.read_bytes()
    assert store.get("google_token", qualifier="acct1") == '{"refresh_token": "demo"}'
    assert store.get("google_token") is None
    assert store.delete("google_token", qualifier="acct1") is True
    assert store.delete("google_token", qualifier="acct1") is False

    other = FernetFileStore(tmp_path / "secrets", SecretStr(Fernet.generate_key().decode()))
    store.set("openai_api_key", "k")
    with pytest.raises(InvalidToken):
        other.get("openai_api_key")

    # a blob moved to another slot's file name is rejected
    (tmp_path / "secrets" / "openai_api_key.fernet").replace(
        tmp_path / "secrets" / "anthropic_api_key.fernet"
    )
    with pytest.raises(SecretError):
        store.get("anthropic_api_key")


def test_fernet_requires_key(tmp_path: Path) -> None:
    with pytest.raises(SecretBackendUnavailable):
        FernetFileStore(tmp_path, None)


class _Mem:
    name = "mem"

    def __init__(self) -> None:
        self.data: dict[str, str] = {}

    def get(self, slot: str, *, qualifier: str | None = None) -> str | None:
        return self.data.get(secret_key(slot, qualifier))

    def set(self, slot: str, value: str, *, qualifier: str | None = None) -> None:
        self.data[secret_key(slot, qualifier)] = value

    def delete(self, slot: str, *, qualifier: str | None = None) -> bool:
        return self.data.pop(secret_key(slot, qualifier), None) is not None


def test_routed_store_routes_large_slots() -> None:
    small, large = _Mem(), _Mem()
    routed = RoutedStore(small=small, large=large)
    routed.set("google_token", "big")
    routed.set("openai_api_key", "small")
    assert large.data == {"google_token": "big"}
    assert small.data == {"openai_api_key": "small"}
    assert routed.name == "mem+mem"


def test_factory_env_mode(settings: Settings) -> None:
    assert build_secret_store(settings).name == "env"


@pytest.mark.windows_only
@pytest.mark.skipif(sys.platform != "win32", reason="DPAPI is Windows-only")
def test_dpapi_roundtrip(tmp_path: Path) -> None:
    from jobpilot.secrets import DpapiFileStore

    store = DpapiFileStore(tmp_path / "secrets")
    store.set("google_token", '{"refresh_token": "demo"}')
    blob = (tmp_path / "secrets" / "google_token.dpapi").read_bytes()
    assert b"refresh_token" not in blob
    assert store.get("google_token") == '{"refresh_token": "demo"}'

    (tmp_path / "secrets" / "google_token.dpapi").replace(
        tmp_path / "secrets" / "openai_api_key.dpapi"
    )
    with pytest.raises(SecretError):
        store.get("openai_api_key")


@pytest.mark.skipif(sys.platform == "win32", reason="non-Windows auto mode selects Fernet")
def test_factory_auto_non_windows_requires_fernet_key(
    settings: Settings, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("JOBPILOT_SECRET_BACKEND", "auto")
    with pytest.raises(SecretBackendUnavailable):
        build_secret_store(Settings())
