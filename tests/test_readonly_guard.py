"""Read-only guard (CLAUDE.md constraint 1). Changing this file requires the user's consent.

Layer 3 of the read-only guarantee: no write-capable clients in the dependency tree, and the
connectors package exposes only fetch_* / list_* / get_* / import_* symbols.
"""

from __future__ import annotations

import importlib
import pkgutil
import re

from tests.conftest import REPO_ROOT, SRC_ROOT

FORBIDDEN_MODULES = ("smtplib", "imaplib", "poplib", "playwright", "selenium", "linkedin_api")
FORBIDDEN_DISTRIBUTIONS = ("playwright", "selenium", "linkedin-api", "linkedin_api", "unipile")
_IMPORT_RE = re.compile(
    r"^\s*(?:import|from)\s+(" + "|".join(FORBIDDEN_MODULES) + r")\b", re.MULTILINE
)
_PUBLIC_NAME_RE = re.compile(r"^(fetch|list|get|import)_")


def test_no_forbidden_imports_in_source() -> None:
    offenders = [
        str(py.relative_to(SRC_ROOT))
        for py in SRC_ROOT.rglob("*.py")
        if _IMPORT_RE.search(py.read_text(encoding="utf-8"))
    ]
    assert offenders == []


def test_no_forbidden_distributions_in_lockfile() -> None:
    lock = (REPO_ROOT / "uv.lock").read_text(encoding="utf-8")
    names = set(re.findall(r'^name = "([^"]+)"', lock, re.MULTILINE))
    assert not (names & set(FORBIDDEN_DISTRIBUTIONS))


def test_no_linkedin_voyager_strings() -> None:
    offenders = [
        str(py.relative_to(SRC_ROOT))
        for py in SRC_ROOT.rglob("*.py")
        if "linkedin.com/voyager" in py.read_text(encoding="utf-8")
    ]
    assert offenders == []


def test_connectors_expose_only_readonly_names() -> None:
    import jobpilot.connectors as connectors

    modules = [connectors]
    for info in pkgutil.walk_packages(connectors.__path__, prefix="jobpilot.connectors."):
        modules.append(importlib.import_module(info.name))
    for mod in modules:
        public = getattr(mod, "__all__", None)
        if public is None:
            public = [
                n
                for n, v in vars(mod).items()
                if not n.startswith("_")
                and callable(v)
                and getattr(v, "__module__", None) == mod.__name__
            ]
        bad = [n for n in public if not _PUBLIC_NAME_RE.match(n)]
        assert bad == [], f"{mod.__name__}: {bad}"
