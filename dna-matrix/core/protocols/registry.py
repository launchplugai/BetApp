# core/protocols/registry.py
"""
Protocol Registry — catalog of all available protocols.

Protocols self-register here. The pipeline queries the registry
to get all protocols for a given category or all protocols.
"""
from __future__ import annotations

from typing import Dict, List, Optional, Type

from core.protocols.models import Protocol, ProtocolCategory


class ProtocolRegistry:
    """
    Singleton registry of all protocol implementations.

    Usage:
        registry.register(BackToBackFatigueProtocol)
        all_protocols = registry.get_all()
        physical_only = registry.get_by_category(ProtocolCategory.PHYSICAL)
    """

    _instance: Optional[ProtocolRegistry] = None
    _protocols: Dict[str, Protocol]
    _by_category: Dict[ProtocolCategory, List[Protocol]]

    def __new__(cls) -> ProtocolRegistry:
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._protocols = {}
            cls._instance._by_category = {cat: [] for cat in ProtocolCategory}
        return cls._instance

    def register(self, protocol_class: Type[Protocol]) -> None:
        """Register a protocol class (instantiates it)."""
        instance = protocol_class()
        if instance.name in self._protocols:
            return  # already registered
        self._protocols[instance.name] = instance
        self._by_category[instance.category].append(instance)

    def get_all(self) -> List[Protocol]:
        """Get all registered protocols."""
        return list(self._protocols.values())

    def get_by_category(self, category: ProtocolCategory) -> List[Protocol]:
        """Get protocols for a specific category."""
        return list(self._by_category.get(category, []))

    def get_by_name(self, name: str) -> Optional[Protocol]:
        """Get a specific protocol by name."""
        return self._protocols.get(name)

    @property
    def count(self) -> int:
        return len(self._protocols)

    def catalog(self) -> Dict[str, List[str]]:
        """Return a catalog of all protocols by category."""
        return {
            cat.value: [p.name for p in protocols]
            for cat, protocols in self._by_category.items()
            if protocols
        }


# Singleton instance
registry = ProtocolRegistry()
