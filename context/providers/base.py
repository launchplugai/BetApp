# context/providers/base.py
"""
Base Context Provider Interface

All providers implement this interface to ensure consistent behavior
and enable the service layer to orchestrate multiple providers.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Optional

from context.snapshot import ContextSnapshot


class ContextProvider(ABC):
    """
    Abstract base class for context data providers.

    Each provider:
    1. Fetches data from an external source
    2. Parses the response
    3. Normalizes into ContextSnapshot format
    """

    @property
    @abstractmethod
    def sport(self) -> str:
        """Sport this provider covers (e.g., 'NBA')."""
        ...

    @property
    @abstractmethod
    def source_name(self) -> str:
        """Identifier for this data source."""
        ...

    @abstractmethod
    def fetch(self) -> Optional[ContextSnapshot]:
        """
        Fetch and return a context snapshot.

        Returns None if fetch fails. Does not raise exceptions -
        failures are captured in the snapshot's missing_data field.
        """
        ...

    def is_available(self) -> bool:
        """
        Check if this provider is currently available.

        Default implementation returns True. Override for providers
        that need health checks or rate limit awareness.
        """
        return True
