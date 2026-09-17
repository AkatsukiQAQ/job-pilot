"""`jobpilot-mcp` console-script entry point. The MCP server itself arrives in Phase 1."""

from __future__ import annotations

import sys


def main() -> None:
    sys.stderr.write("jobpilot-mcp is not available yet (Phase 1). See docs/ROADMAP.md.\n")
    raise SystemExit(2)


__all__ = ["main"]
