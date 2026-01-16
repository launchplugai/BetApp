# context/providers/__init__.py
"""
Context Data Providers

Each provider fetches data from a specific source and normalizes it
into the ContextSnapshot format.

Sprint 3 scope: NBA availability only, one source.
"""

from context.providers.base import ContextProvider
from context.providers.nba_availability import NBAAvailabilityProvider

__all__ = ["ContextProvider", "NBAAvailabilityProvider"]
