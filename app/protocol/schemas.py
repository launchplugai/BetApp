"""
Protocol Schemas - Pydantic models for API
"""

from pydantic import BaseModel
from typing import List, Optional, Dict, Any
from datetime import datetime


# =============================================================================
# Target Schemas
# =============================================================================

class ProtocolTargetCreate(BaseModel):
    """Create a protocol target."""
    target_type: str  # game|team|player
    provider: str  # nba_api|internal
    external_id: str
    meta: Optional[Dict[str, Any]] = None


class ProtocolTargetOut(BaseModel):
    """Protocol target response."""
    id: str
    target_type: str
    provider: str
    external_id: str
    meta: Dict[str, Any]
    created_at: str
    
    class Config:
        from_attributes = True


# =============================================================================
# Item Schemas
# =============================================================================

class ProtocolItemOut(BaseModel):
    """Protocol item response."""
    id: str
    type: str  # stats_snapshot|note|system_event
    payload: Dict[str, Any]
    created_at: str
    
    class Config:
        from_attributes = True


# =============================================================================
# Protocol Schemas
# =============================================================================

class ProtocolCreate(BaseModel):
    """Create a new protocol."""
    sport: str = "nba"
    title: str
    targets: Optional[List[ProtocolTargetCreate]] = None
    context: Optional[Dict[str, Any]] = None


class ProtocolUpdate(BaseModel):
    """Update protocol."""
    title: Optional[str] = None
    status: Optional[str] = None  # draft|active|archived
    context: Optional[Dict[str, Any]] = None


class ProtocolOut(BaseModel):
    """Basic protocol response (for lists)."""
    id: str
    sport: str
    title: str
    status: str
    context: Dict[str, Any]
    created_at: str
    updated_at: str
    target_count: int = 0
    item_count: int = 0
    
    class Config:
        from_attributes = True


class ProtocolDetailOut(ProtocolOut):
    """Detailed protocol with targets and recent items."""
    targets: List[ProtocolTargetOut] = []
    recent_items: List[ProtocolItemOut] = []


class ProtocolListOut(BaseModel):
    """List of protocols."""
    protocols: List[ProtocolOut]
    total: int


# =============================================================================
# Snapshot Schema
# =============================================================================

class SnapshotOut(BaseModel):
    """Stats snapshot response."""
    item_id: str
    type: str
    summary: Dict[str, Any]
    natural_language_summary: Optional[str] = None
    created_at: str
