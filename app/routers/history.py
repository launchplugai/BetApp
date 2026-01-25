# app/routers/history.py
"""
Canonical history endpoints (Ticket 6B).

These endpoints provide the public API contract for history.
They use the same HistoryStore singleton as /app/history endpoints.
"""

from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse

from app.correlation import get_request_id

router = APIRouter(tags=["history"])


@router.get("/history")
async def get_history(raw_request: Request, limit: int = 50):
    """
    Get evaluation history.

    Returns items in reverse chronological order (newest first).
    No authentication required - uses in-memory store.

    Response:
        {
            "items": [...],
            "count": N
        }
    """
    from app.history_store import get_history_store

    request_id = get_request_id(raw_request) or "unknown"
    store = get_history_store()

    items = store.list(limit=limit)
    return {
        "request_id": request_id,
        "items": [item.to_dict() for item in items],
        "count": len(items),
    }


@router.get("/history/{item_id}")
async def get_history_item(item_id: str, raw_request: Request):
    """
    Get a specific history item by ID.

    Returns the item with raw evaluation data for re-evaluate/edit.

    Response:
        {
            "item": { ...historyItem, "raw": {...} }
        }
    """
    from app.history_store import get_history_store

    request_id = get_request_id(raw_request) or "unknown"
    store = get_history_store()

    item = store.get(item_id)
    if not item:
        return JSONResponse(
            status_code=404,
            content={
                "request_id": request_id,
                "error": "not_found",
                "detail": f"History item {item_id} not found",
            },
        )

    return {
        "request_id": request_id,
        "item": item.to_dict_with_raw(),
    }
