# context/__init__.py
"""
Context Ingestion Module - Sprint 3

Provides external context (player availability, injury reports) to enhance
evaluation confidence without modifying core engine logic.

Module Structure:
- snapshot.py: ContextSnapshot schema (normalized data model)
- providers/: Data source implementations
- service.py: Orchestrates providers and caching
- apply.py: Converts snapshots to confidence modifiers
"""

from context.snapshot import ContextSnapshot, PlayerStatus, PlayerAvailability

__all__ = ["ContextSnapshot", "PlayerStatus", "PlayerAvailability"]
