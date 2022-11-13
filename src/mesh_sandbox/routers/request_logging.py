from typing import Callable

from fastapi import Request, Response
from fastapi.routing import APIRoute


class RequestLoggingRoute(APIRoute):
    """A FastAPI route that will add request info to logs from this level down.
    It has access to the path params that aren't available in the middleware pre-request handling."""

    def get_route_handler(self) -> Callable:
        original_route_handler = super().get_route_handler()
        router_name = self.name

        async def _request_logging_route_handler(request: Request) -> Response:
            request.state.router_name = router_name
            return await original_route_handler(request)

        return _request_logging_route_handler
