"""HTTP endpoints for A2A Agent Card discovery and JSON-RPC."""
from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse

import a2a

router = APIRouter()


@router.get("/.well-known/agent-card.json")
@router.get("/.well-known/agent.json")
def card(request: Request):
    scheme = "https" if request.url.scheme == "https" else "http"
    return a2a.agent_card(f"{scheme}://{request.headers.get('host', 'localhost')}")


@router.post("/a2a")
async def rpc(request: Request):
    try:
        body = await request.json()
    except Exception:
        body = None
    if not isinstance(body, dict):
        return JSONResponse({"jsonrpc": "2.0", "id": None,
                             "error": {"code": -32700, "message": "The request body must be JSON."}})
    return a2a.dispatch(body)
