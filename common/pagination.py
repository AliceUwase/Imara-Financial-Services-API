"""Cursor pagination defaults for the Imara API.

A single class is exposed so that any view needing cursor pagination
applies a consistent payload size and ordering. Defaults are chosen for
low-bandwidth mobile consumers: small page size, predictable shape.
"""

from rest_framework.pagination import CursorPagination


class FinancingRequestCursorPagination(CursorPagination):
    """Cursor pagination tuned for the lender financing request feed.
    
    Orders by descending created_at so the newest requests appear first.
    The default page size of 10 keeps each response under ~5 KB on
    typical financing request payloads, which is comfortable for users
    on unstable mobile data.
    """

    page_size = 10
    page_size_query_param = 'page_size'
    max_page_size = 50
    ordering = '-created_at'
    cursor_query_param = 'cursor'