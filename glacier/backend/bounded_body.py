"""Read a bounded request body before Starlette parses its multipart form."""

from fastapi import HTTPException, Request


async def read_bounded_body(request: Request, limit: int, message: str) -> None:
    try:
        declared = int(request.headers.get("content-length", "0"))
    except ValueError:
        declared = 0
    if declared > limit:
        raise HTTPException(413, message)

    chunks = []
    size = 0
    async for chunk in request.stream():
        size += len(chunk)
        if size > limit:
            raise HTTPException(413, message)
        chunks.append(chunk)
    request._body = b"".join(chunks)
