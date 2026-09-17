"""Read-only connectors (Gmail, Calendar, LinkedIn archive, job boards, web search).

Policy (ARCHITECTURE section 4, layer 3): every public symbol of this package and its
subpackages must be named fetch_* / list_* / get_* / import_*; nothing here may import
smtplib, imaplib, playwright, selenium or linkedin_api. Enforced by tests/test_readonly_guard.py.
"""

__all__: list[str] = []
