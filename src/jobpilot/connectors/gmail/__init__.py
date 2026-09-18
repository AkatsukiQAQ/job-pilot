"""Gmail read-only connector.

Modules: readonly_http (transport that cannot write), auth (consent + token lifecycle),
parse (API payload -> EmailMessageCreate), sync (paged list/get/history with a quota budget).
Public names in this package follow the read-only naming policy (fetch_/list_/get_/import_).
"""

__all__: list[str] = []
