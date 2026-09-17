"""Scan tracked repository files for personal / identifying information.

Usage:
    uv run python scripts/check_pii.py            # scan all git-tracked text files
    uv run python scripts/check_pii.py path ...   # scan given files (pre-commit style)

Two pattern sources:
1. Built-in generic patterns (phrasing that tends to leak the author's situation,
   machine-specific absolute paths, e-mail addresses outside a small allowlist).
2. An optional local denylist file `.pii-denylist.local` at the repo root, one
   regular expression per line, `#` comments allowed. This file is git-ignored so
   the author can list their own e-mail, handles, employer domain, etc. without
   committing them.

Exit code 1 if anything matches. Company names that appear only as hiring targets
are fine; the goal is to catch statements about the author.
"""

from __future__ import annotations

import re
import subprocess
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
DENYLIST_FILE = REPO / ".pii-denylist.local"

TEXT_SUFFIXES = {
    ".md",
    ".txt",
    ".py",
    ".toml",
    ".yaml",
    ".yml",
    ".json",
    ".ts",
    ".tsx",
    ".js",
    ".css",
    ".html",
    ".env",
    ".example",
    ".sql",
    ".cfg",
    ".ini",
}

# Generic patterns: phrasing that turns research/docs into statements about the author.
BUILTIN_PATTERNS: list[tuple[str, str]] = [
    (
        r"(?i)\bthe user's own (employer|address|domain|company)\b",
        "statement about the author's employer/address",
    ),
    (r"(?i)\bfor this user\b|\bthis user's\b|\bthis user is\b", "statement about 'this user'"),
    (r"(?i)\bcurrent[- ]affiliation\b", "author affiliation phrasing"),
    (r"(?i)[a-z]:\\\\?Users\\\\?[^\\\s]+", "Windows path containing a username"),
    (r"(?i)/(?:c|d)/Users/[^/\s]+", "POSIX-style path containing a username"),
    (r"(?i)/home/[a-z0-9_-]+/", "Linux home path containing a username"),
    (r"(?i)Personal_Projects", "author-specific local project path"),
]

# E-mail addresses are reported unless they belong to a known vendor / platform domain.
EMAIL_RE = re.compile(r"[A-Za-z0-9._%+-]+@([A-Za-z0-9.-]+\.[A-Za-z]{2,})")
EMAIL_ALLOW_SUFFIXES = (
    "anthropic.com",
    "google.com",
    "googleapis.com",
    "linkedin.com",
    "greenhouse.io",
    "greenhouse-mail.io",
    "lever.co",
    "ashbyhq.com",
    "workablemail.com",
    "smartrecruiters.com",
    "myworkday.com",
    "calendly.com",
    "indeed.com",
    "indeedemail.com",
    "zoom.us",
    "hirevue.com",
    "hackerrank.com",
    "arorua.net",
    "mynavi.jp",
    "rikunabi.com",
    "gaishishukatsu.com",
    "offerbox.jp",
    "career-tasu.jp",
    "career-tasu.co.jp",
    "wantedly.com",
    "labbase.jp",
    "onecareer.jp",
    "snar.jp",
    "hrmos.co",
    "herp.cloud",
    "talentio.com",
    "jobcan.ne.jp",
    "candidates.workablemail.com",
    "example.com",
    "example.co.jp",
    "acme.co.jp",
    "users.noreply.github.com",
    "gserviceaccount.com",
    "bizreach.jp",
    "tel.com",
    "facetoface.ne.jp",  # vendor / company senders cited in research
    "sakana.ai",  # appears as a hiring-target company contact address in research digests
)


def tracked_files() -> list[Path]:
    out = subprocess.run(
        ["git", "ls-files", "-z"], cwd=REPO, check=True, capture_output=True
    ).stdout
    return [REPO / p for p in out.decode("utf-8", "replace").split("\0") if p]


def load_local_denylist() -> list[tuple[re.Pattern[str], str]]:
    patterns: list[tuple[re.Pattern[str], str]] = []
    if not DENYLIST_FILE.exists():
        return patterns
    for raw in DENYLIST_FILE.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        patterns.append((re.compile(line), f"local denylist: {line}"))
    return patterns


def is_text(path: Path) -> bool:
    return path.suffix.lower() in TEXT_SUFFIXES or path.name in {
        "CLAUDE.md",
        "README.md",
        ".gitignore",
        ".gitattributes",
    }


def scan(paths: list[Path]) -> list[str]:
    builtin = [(re.compile(p), why) for p, why in BUILTIN_PATTERNS]
    local = load_local_denylist()
    problems: list[str] = []
    for path in paths:
        if not path.is_file() or not is_text(path):
            continue
        if path.name == "check_pii.py":
            continue
        try:
            text = path.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            continue
        rel = path.relative_to(REPO).as_posix()
        for lineno, line in enumerate(text.splitlines(), 1):
            for rx, why in builtin + local:
                if rx.search(line):
                    problems.append(f"{rel}:{lineno}: {why}: {line.strip()[:120]}")
            for m in EMAIL_RE.finditer(line):
                domain = m.group(1).lower()
                if not domain.endswith(EMAIL_ALLOW_SUFFIXES):
                    problems.append(
                        f"{rel}:{lineno}: e-mail address outside allowlist: {m.group(0)}"
                    )
    return problems


def main(argv: list[str]) -> int:
    paths = [Path(a).resolve() for a in argv[1:]] if len(argv) > 1 else tracked_files()
    problems = scan(paths)
    if problems:
        print("PII check failed:")
        for p in problems:
            print("  " + p)
        return 1
    print(f"PII check passed ({len(paths)} files).")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
