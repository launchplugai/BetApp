"""
Provider factory for instantiating data sources.
"""

from typing import Optional
from app.providers.base import OddsProvider, ScoreProvider
from app.providers.mock import MockOddsProvider, MockScoreProvider


class ProviderFactory:
    """
    Factory for creating provider instances.
    
    Usage:
        odds_provider = ProviderFactory.get_odds_provider("mock")
        score_provider = ProviderFactory.get_score_provider("mock")
    """
    
    _odds_providers = {
        "mock": MockOddsProvider,
        # "odds_api": OddsAPIProvider,  # Future
    }
    
    _score_providers = {
        "mock": MockScoreProvider,
        # "sportsdata": SportsDataProvider,  # Future
    }
    
    @classmethod
    def get_odds_provider(cls, source: str = "mock", **kwargs) -> OddsProvider:
        """
        Get an odds provider by source name.
        
        Args:
            source: Provider identifier ("mock", "odds_api", etc.)
            **kwargs: Provider-specific config (latency_ms, api_key, etc.)
            
        Returns:
            OddsProvider instance
            
        Raises:
            ValueError: If source is unknown
        """
        if source not in cls._odds_providers:
            raise ValueError(
                f"Unknown odds provider: {source}. "
                f"Available: {list(cls._odds_providers.keys())}"
            )
        
        provider_class = cls._odds_providers[source]
        return provider_class(**kwargs)
    
    @classmethod
    def get_score_provider(cls, source: str = "mock", **kwargs) -> ScoreProvider:
        """
        Get a score provider by source name.
        
        Args:
            source: Provider identifier ("mock", "sportsdata", etc.)
            **kwargs: Provider-specific config
            
        Returns:
            ScoreProvider instance
            
        Raises:
            ValueError: If source is unknown
        """
        if source not in cls._score_providers:
            raise ValueError(
                f"Unknown score provider: {source}. "
                f"Available: {list(cls._score_providers.keys())}"
            )
        
        provider_class = cls._score_providers[source]
        return provider_class(**kwargs)
    
    @classmethod
    def register_odds_provider(cls, name: str, provider_class: type):
        """Register a new odds provider type."""
        cls._odds_providers[name] = provider_class
    
    @classmethod
    def register_score_provider(cls, name: str, provider_class: type):
        """Register a new score provider type."""
        cls._score_providers[name] = provider_class
    
    @classmethod
    def available_odds_providers(cls) -> list:
        """List available odds provider names."""
        return list(cls._odds_providers.keys())
    
    @classmethod
    def available_score_providers(cls) -> list:
        """List available score provider names."""
        return list(cls._score_providers.keys())
