"""Custom exception handler producing a consistent error envelope.

"""

from typing import Any, Optional

from rest_framework.response import Response
from rest_framework.views import exception_handler


def custom_exception_handler(exc: Exception, context: dict) -> Optional[Response]:
    """Wrap DRF's default error response in the Imara error envelope."""
    response = exception_handler(exc, context)
    if response is None:
        return None

    original_data: Any = response.data
    message = _extract_message(original_data)

    response.data = {
        'error': {
            'code': exc.__class__.__name__,
            'message': message,
            'details': original_data if isinstance(original_data, dict) else None,
        }
    }
    return response


def _extract_message(data: Any) -> str:
    """Pull a single human-readable message out of DRF's varied error shapes."""
    if isinstance(data, dict):
        for value in data.values():
            if isinstance(value, list) and value:
                return str(value[0])
            if isinstance(value, str):
                return value
        return 'Request failed validation.'
    if isinstance(data, list) and data:
        return str(data[0])
    return str(data)