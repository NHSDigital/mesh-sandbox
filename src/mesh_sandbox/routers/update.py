from fastapi import APIRouter, Depends, Response, status

from ..dependencies import authorised_mailbox
from .request_logging import RequestLoggingRoute

router = APIRouter(
    dependencies=[Depends(authorised_mailbox)],
    route_class=RequestLoggingRoute,
)


@router.post(
    "",
    include_in_schema=False,
    status_code=status.HTTP_200_OK,
)
async def update():
    return Response(status_code=200)
