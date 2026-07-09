import uuid

from starlette.middleware.base import BaseHTTPMiddleware


CORRELATION_ID_HEADER = "X-Correlation-Id"


class CorrelationIdMiddleware(
    BaseHTTPMiddleware
):

    async def dispatch(
        self,
        request,
        call_next
    ):

        incoming_correlation_id = request.headers.get(
            CORRELATION_ID_HEADER
        )

        request.state.correlation_id = (
            incoming_correlation_id
            if incoming_correlation_id
            else str(uuid.uuid4())
        )

        response = await call_next(
            request
        )

        response.headers[CORRELATION_ID_HEADER] = (
            request.state.correlation_id
        )

        return response