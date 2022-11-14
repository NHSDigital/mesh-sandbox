from time import time
from typing import Callable

from fastapi import HTTPException, Request, Response
from fastapi.routing import APIRoute

from ..common import logger


class RequestLoggingRoute(APIRoute):
    """A FastAPI route that will add request info to logs from this level down.
    It has access to the path params that aren't available in the middleware pre-request handling."""

    def get_route_handler(self) -> Callable:
        original_route_handler = super().get_route_handler()
        router_name = self.name

        async def _request_logging_route_handler(request: Request) -> Response:
            request.state.router_name = router_name
            # pylint: disable=logging-fstring-interpolation
            logger.info(f"begin {router_name} {request.url}")

            start = time()
            try:
                result = await original_route_handler(request)
                logger.info(f"end {router_name} {request.url} {result.status_code} {round(time()-start, 5)}")
                return result
            except HTTPException as http_err:
                logger.warning(f"end {router_name} {request.url} {http_err.status_code} {round(time()-start, 5)}")
                raise
            except Exception as err:
                logger.exception(f"end {router_name} {request.url} {time()-start} {round(time()-start, 5)} - {err}")
                raise

        return _request_logging_route_handler
