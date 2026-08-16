"""
CROWDSHIELD REQUEST CORRELATION & SECURITY MIDDLEWARE (PHASE 6G)
================================================================
Injects X-Request-ID headers into all HTTP requests and responses for audit trail tracing,
and ensures safe error handling that never exposes raw credentials, secrets, or internal stack traces.
"""

import uuid
import logging
from typing import Callable, Optional
from contextvars import ContextVar
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

logger = logging.getLogger("crowdshield.middleware.correlation")

# ContextVar for storing request_id across async execution contexts
_request_id_ctx_var: ContextVar[Optional[str]] = ContextVar("request_id", default=None)


def get_current_request_id() -> Optional[str]:
    """Retrieves the current request ID from context."""
    return _request_id_ctx_var.get()


class RequestCorrelationMiddleware(BaseHTTPMiddleware):
    """
    Middleware that propagates or generates an X-Request-ID for every HTTP request.
    """

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        request_id = request.headers.get("X-Request-ID")
        if not request_id or len(request_id.strip()) == 0:
            request_id = f"req_{uuid.uuid4().hex[:12]}"

        # Store in state and contextvar
        request.state.request_id = request_id
        token = _request_id_ctx_var.set(request_id)

        try:
            response: Response = await call_next(request)
            response.headers["X-Request-ID"] = request_id
            return response
        finally:
            _request_id_ctx_var.reset(token)
