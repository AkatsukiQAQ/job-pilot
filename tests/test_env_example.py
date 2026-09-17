from __future__ import annotations

import re

from tests.conftest import REPO_ROOT

from jobpilot.settings import Settings

_KEY_RE = re.compile(r"^#?\s*JOBPILOT_([A-Z0-9_]+)=", re.MULTILINE)
# secret injection variables handled by jobpilot.secrets, not Settings fields
_EXEMPT_PREFIXES = ("SECRET_",)


def test_env_example_keys_are_settings_fields() -> None:
    text = (REPO_ROOT / "env.example").read_text(encoding="utf-8")
    keys = {k for k in _KEY_RE.findall(text) if not k.startswith(_EXEMPT_PREFIXES)}
    fields = {name.upper() for name in Settings.model_fields}
    assert keys, "no keys found in env.example"
    assert keys <= fields, keys - fields


def test_env_example_covers_every_setting() -> None:
    text = (REPO_ROOT / "env.example").read_text(encoding="utf-8")
    keys = set(_KEY_RE.findall(text))
    missing = {name.upper() for name in Settings.model_fields} - keys
    assert missing == set(), missing


def test_env_example_has_no_machine_paths_or_emails() -> None:
    text = (REPO_ROOT / "env.example").read_text(encoding="utf-8")
    assert not re.search(r"[A-Za-z]:\\Users\\", text)
    assert "@" not in text.replace("@theme", "")
