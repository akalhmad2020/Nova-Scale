from fastapi import Request
from fastapi.responses import JSONResponse


async def unhandled_exception_handler(
    request: Request,
    exc: Exception,
) -> JSONResponse:
    request_id = getattr(request.state, "request_id", None)

    headers: dict[str, str] = {}

    if request_id is not None:
        headers["X-Request-ID"] = request_id

    return JSONResponse(
        status_code=500,
        content={"detail": "Internal Server Error"},
        headers=headers,
    )
