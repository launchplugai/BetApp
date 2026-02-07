"""
API Cost Tracker - In-memory tracking for external API calls.

Tracks cost, latency, and usage patterns for data-driven optimization.
Follows the same pattern as history_store.py for consistency.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Dict, List, Optional, Any
from collections import defaultdict
import time


# =============================================================================
# Cost Configuration
# =============================================================================

# Per-1K token pricing (approximate, update as needed)
OPENAI_PRICING = {
    # TTS models
    "gpt-4o-mini-tts": {"input": 0.0, "output": 0.0, "per_1k_chars": 0.015},  # per 1K characters
    "tts-1": {"input": 0.0, "output": 0.0, "per_1k_chars": 0.015},
    "tts-1-hd": {"input": 0.0, "output": 0.0, "per_1k_chars": 0.030},
    # Vision models
    "gpt-4o": {"input": 0.005, "output": 0.015, "per_1k_chars": 0.0},
    "gpt-4o-mini": {"input": 0.00015, "output": 0.0006, "per_1k_chars": 0.0},
}


# =============================================================================
# Data Classes
# =============================================================================

@dataclass
class APICallRecord:
    """Record of a single API call."""
    id: str
    timestamp: str  # ISO8601
    endpoint: str
    model: Optional[str]
    latency_ms: float
    success: bool
    error_code: Optional[str] = None
    # Cost/usage data
    input_tokens: Optional[int] = None
    output_tokens: Optional[int] = None
    estimated_cost_usd: float = 0.0
    # Request metadata
    cached: bool = False
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict:
        """Convert to JSON-serializable dict."""
        return {
            "id": self.id,
            "timestamp": self.timestamp,
            "endpoint": self.endpoint,
            "model": self.model,
            "latencyMs": self.latency_ms,
            "success": self.success,
            "errorCode": self.error_code,
            "inputTokens": self.input_tokens,
            "outputTokens": self.output_tokens,
            "estimatedCostUsd": round(self.estimated_cost_usd, 6),
            "cached": self.cached,
            "metadata": self.metadata,
        }


@dataclass
class APIUsageSummary:
    """Aggregated usage summary for an API endpoint."""
    endpoint: str
    total_calls: int
    successful_calls: int
    failed_calls: int
    cached_calls: int
    total_latency_ms: float
    avg_latency_ms: float
    total_cost_usd: float
    period_start: str
    period_end: str


# =============================================================================
# In-Memory Store
# =============================================================================

_MAX_RECORDS = 10000  # Prevent unbounded growth

_records: List[APICallRecord] = []
_endpoint_counters: Dict[str, Dict[str, int]] = defaultdict(lambda: defaultdict(int))


# =============================================================================
# Core Functions
# =============================================================================

def estimate_cost(model: Optional[str], input_tokens: int = 0, output_tokens: int = 0, char_count: int = 0) -> float:
    """
    Estimate API call cost in USD.
    
    Args:
        model: Model name
        input_tokens: Input token count
        output_tokens: Output token count  
        char_count: Character count (for TTS)
        
    Returns:
        Estimated cost in USD
    """
    if not model:
        return 0.0
        
    pricing = OPENAI_PRICING.get(model, {})
    cost = 0.0
    
    # Token-based pricing
    if pricing.get("input") and input_tokens:
        cost += (input_tokens / 1000) * pricing["input"]
    if pricing.get("output") and output_tokens:
        cost += (output_tokens / 1000) * pricing["output"]
        
    # Character-based pricing (TTS)
    if pricing.get("per_1k_chars") and char_count:
        cost += (char_count / 1000) * pricing["per_1k_chars"]
        
    return cost


def record_api_call(
    endpoint: str,
    model: Optional[str] = None,
    latency_ms: float = 0.0,
    success: bool = True,
    error_code: Optional[str] = None,
    input_tokens: Optional[int] = None,
    output_tokens: Optional[int] = None,
    char_count: int = 0,
    cached: bool = False,
    metadata: Optional[Dict[str, Any]] = None,
) -> APICallRecord:
    """
    Record an API call.
    
    Args:
        endpoint: API endpoint URL
        model: Model name used
        latency_ms: Request latency in milliseconds
        success: Whether the call succeeded
        error_code: Error code if failed
        input_tokens: Input token count (if available)
        output_tokens: Output token count (if available)
        char_count: Character count (for TTS pricing)
        cached: Whether result was served from cache
        metadata: Additional metadata
        
    Returns:
        The recorded APICallRecord
    """
    from uuid import uuid4
    
    estimated_cost = estimate_cost(model, input_tokens or 0, output_tokens or 0, char_count)
    
    record = APICallRecord(
        id=str(uuid4()),
        timestamp=datetime.now(timezone.utc).isoformat(),
        endpoint=endpoint,
        model=model,
        latency_ms=latency_ms,
        success=success,
        error_code=error_code,
        input_tokens=input_tokens,
        output_tokens=output_tokens,
        estimated_cost_usd=estimated_cost,
        cached=cached,
        metadata=metadata or {},
    )
    
    # Store record
    _records.append(record)
    
    # Enforce max records limit
    if len(_records) > _MAX_RECORDS:
        _records.pop(0)
    
    # Update counters
    _endpoint_counters[endpoint]["total"] += 1
    if success:
        _endpoint_counters[endpoint]["success"] += 1
    else:
        _endpoint_counters[endpoint]["failed"] += 1
    if cached:
        _endpoint_counters[endpoint]["cached"] += 1
    
    return record


def get_recent_calls(limit: int = 100, endpoint_filter: Optional[str] = None) -> List[APICallRecord]:
    """
    Get recent API call records.
    
    Args:
        limit: Maximum records to return
        endpoint_filter: Optional endpoint to filter by
        
    Returns:
        List of APICallRecord (most recent first)
    """
    records = _records
    if endpoint_filter:
        records = [r for r in records if r.endpoint == endpoint_filter]
    return list(reversed(records))[:limit]


def get_summary(hours: int = 24) -> Dict[str, Any]:
    """
    Get usage summary for the specified period.
    
    Args:
        hours: Lookback period in hours
        
    Returns:
        Summary dict with totals and per-endpoint breakdown
    """
    from datetime import timedelta
    
    cutoff = datetime.now(timezone.utc) - timedelta(hours=hours)
    
    recent_records = [r for r in _records if r.timestamp >= cutoff.isoformat()]
    
    if not recent_records:
        return {
            "periodHours": hours,
            "totalCalls": 0,
            "totalCostUsd": 0.0,
            "avgLatencyMs": 0.0,
            "endpoints": {},
        }
    
    # Aggregate by endpoint
    endpoint_stats: Dict[str, Dict[str, Any]] = defaultdict(lambda: {
        "calls": 0,
        "success": 0,
        "failed": 0,
        "cached": 0,
        "costUsd": 0.0,
        "latencyMs": 0.0,
    })
    
    for r in recent_records:
        stats = endpoint_stats[r.endpoint]
        stats["calls"] += 1
        if r.success:
            stats["success"] += 1
        else:
            stats["failed"] += 1
        if r.cached:
            stats["cached"] += 1
        stats["costUsd"] += r.estimated_cost_usd
        stats["latencyMs"] += r.latency_ms
    
    # Calculate averages
    for endpoint, stats in endpoint_stats.items():
        if stats["calls"] > 0:
            stats["avgLatencyMs"] = round(stats["latencyMs"] / stats["calls"], 2)
            stats["costUsd"] = round(stats["costUsd"], 6)
            del stats["latencyMs"]  # Remove raw sum
    
    total_calls = len(recent_records)
    total_cost = sum(r.estimated_cost_usd for r in recent_records)
    avg_latency = sum(r.latency_ms for r in recent_records) / total_calls if total_calls > 0 else 0
    
    return {
        "periodHours": hours,
        "totalCalls": total_calls,
        "totalCostUsd": round(total_cost, 6),
        "avgLatencyMs": round(avg_latency, 2),
        "endpoints": dict(endpoint_stats),
    }


def clear_records() -> None:
    """Clear all records (for testing)."""
    _records.clear()
    _endpoint_counters.clear()


def get_cache_hit_rate(endpoint: Optional[str] = None) -> float:
    """
    Calculate cache hit rate.
    
    Args:
        endpoint: Optional endpoint to filter by
        
    Returns:
        Cache hit rate as percentage (0-100)
    """
    records = _records
    if endpoint:
        records = [r for r in records if r.endpoint == endpoint]
    
    if not records:
        return 0.0
    
    cached = sum(1 for r in records if r.cached)
    return round((cached / len(records)) * 100, 2)
