"""
Protocol Tracker Service - In-memory protocol state management.

Tracks active betting protocols (games being watched/built).
No persistence, expires after 24h.
"""

from datetime import datetime, timedelta
from typing import Dict, List, Optional
import uuid

from pydantic import BaseModel
from app.providers import OddsResponse, ScoreResponse


class TrackedProtocol(BaseModel):
    """In-memory protocol state."""
    protocol_id: str
    game_id: str
    league: str
    teams: List[str]
    created_at: datetime
    last_updated: datetime
    markets_watched: List[str]
    current_odds: Optional[OddsResponse] = None
    current_score: Optional[ScoreResponse] = None
    legs_snapshot: Optional[List[dict]] = None
    
    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }


class ProtocolTracker:
    """
    Singleton service for tracking active protocols.
    
    Thread-safe in-memory store. No persistence.
    Protocols expire after 24 hours.
    """
    
    _instance = None
    _protocols: Dict[str, TrackedProtocol] = {}
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance
    
    def create_protocol(
        self,
        game_id: str,
        league: str,
        teams: List[str],
        markets_watched: List[str],
        legs: Optional[List[dict]] = None
    ) -> TrackedProtocol:
        """
        Create and track a new protocol.
        
        Args:
            game_id: Game identifier
            league: League (NBA, NFL, etc.)
            teams: [home, away]
            markets_watched: ["spread", "player_props", etc.]
            legs: Initial legs snapshot
            
        Returns:
            TrackedProtocol with assigned ID
        """
        protocol_id = f"proto_{uuid.uuid4().hex[:8]}"
        now = datetime.utcnow()
        
        protocol = TrackedProtocol(
            protocol_id=protocol_id,
            game_id=game_id,
            league=league,
            teams=teams,
            created_at=now,
            last_updated=now,
            markets_watched=markets_watched,
            legs_snapshot=legs or []
        )
        
        self._protocols[protocol_id] = protocol
        return protocol
    
    def get_protocol(self, protocol_id: str) -> Optional[TrackedProtocol]:
        """Get protocol by ID."""
        return self._protocols.get(protocol_id)
    
    def update_odds(self, protocol_id: str, odds: OddsResponse) -> bool:
        """
        Update protocol with latest odds.
        
        Returns:
            True if updated, False if protocol not found
        """
        protocol = self._protocols.get(protocol_id)
        if not protocol:
            return False
        
        protocol.current_odds = odds
        protocol.last_updated = datetime.utcnow()
        return True
    
    def update_score(self, protocol_id: str, score: ScoreResponse) -> bool:
        """
        Update protocol with latest score.
        
        Returns:
            True if updated, False if protocol not found
        """
        protocol = self._protocols.get(protocol_id)
        if not protocol:
            return False
        
        protocol.current_score = score
        protocol.last_updated = datetime.utcnow()
        return True
    
    def update_legs(self, protocol_id: str, legs: List[dict]) -> bool:
        """Update protocol legs snapshot."""
        protocol = self._protocols.get(protocol_id)
        if not protocol:
            return False
        
        protocol.legs_snapshot = legs
        protocol.last_updated = datetime.utcnow()
        return True
    
    def list_active_protocols(self, max_age_hours: int = 24) -> List[TrackedProtocol]:
        """
        Get all active protocols (not expired).
        
        Args:
            max_age_hours: Maximum age before considering expired
            
        Returns:
            List of active TrackedProtocol instances
        """
        cutoff = datetime.utcnow() - timedelta(hours=max_age_hours)
        return [
            p for p in self._protocols.values()
            if p.created_at > cutoff
        ]
    
    def expire_old_protocols(self, max_age_hours: int = 24) -> int:
        """
        Remove protocols older than max_age_hours.
        
        Returns:
            Number of protocols expired
        """
        cutoff = datetime.utcnow() - timedelta(hours=max_age_hours)
        expired_ids = [
            pid for pid, p in self._protocols.items()
            if p.created_at <= cutoff
        ]
        
        for pid in expired_ids:
            del self._protocols[pid]
        
        return len(expired_ids)
    
    def delete_protocol(self, protocol_id: str) -> bool:
        """Delete a specific protocol."""
        if protocol_id in self._protocols:
            del self._protocols[protocol_id]
            return True
        return False
    
    def get_stats(self) -> dict:
        """Get tracker statistics."""
        return {
            "total_protocols": len(self._protocols),
            "active_protocols": len(self.list_active_protocols()),
            "oldest_protocol": min(
                (p.created_at for p in self._protocols.values()),
                default=None
            ),
            "newest_protocol": max(
                (p.created_at for p in self._protocols.values()),
                default=None
            )
        }


# Singleton instance
tracker = ProtocolTracker()
