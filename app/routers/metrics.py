"""
Metrics API Router - Expose API cost and usage metrics.
"""
from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, Query

from app.cost_tracker import get_summary, get_recent_calls, get_cache_hit_rate


router = APIRouter(
    prefix="/metrics",
    tags=["Metrics"],
)


@router.get("/summary")
async def metrics_summary(
    hours: int = Query(default=24, ge=1, le=168, description="Lookback period in hours"),
):
    """
    Get API usage summary for the specified period.
    
    Returns aggregated metrics including:
    - Total calls and costs
    - Average latency
    - Per-endpoint breakdown
    """
    return get_summary(hours=hours)


@router.get("/recent")
async def recent_calls(
    limit: int = Query(default=100, ge=1, le=1000, description="Maximum records to return"),
    endpoint: Optional[str] = Query(default=None, description="Filter by endpoint URL"),
):
    """
    Get recent API call records.
    
    Returns individual call details for debugging and analysis.
    """
    records = get_recent_calls(limit=limit, endpoint_filter=endpoint)
    return {
        "count": len(records),
        "records": [r.to_dict() for r in records],
    }


@router.get("/cache-hit-rate")
async def cache_hit_rate(
    endpoint: Optional[str] = Query(default=None, description="Filter by endpoint URL"),
):
    """
    Get cache hit rate percentage.
    
    Shows effectiveness of caching for TTS and other cached APIs.
    """
    return {
        "cacheHitRate": get_cache_hit_rate(endpoint),
        "endpoint": endpoint or "all",
    }
