"""
Data providers for live odds and scores.

This module abstracts data sources behind common interfaces.
Providers can be swapped without changing consumer code.

Example:
    from app.providers import ProviderFactory, OddsProvider
    
    # Get mock provider for development
    provider = ProviderFactory.get_odds_provider("mock")
    odds = await provider.get_odds("nba_001")
    
    # Later: swap to live provider
    provider = ProviderFactory.get_odds_provider("odds_api", api_key="xxx")
"""

from app.providers.base import (
    OddsProvider,
    ScoreProvider,
    OddsResponse,
    ScoreResponse,
    MarketsData,
    MarketLine,
    PlayerProp,
    ScoreData,
)

from app.providers.mock import (
    MockOddsProvider,
    MockScoreProvider,
)

from app.providers.factory import ProviderFactory

__all__ = [
    # Base classes
    "OddsProvider",
    "ScoreProvider",
    # Models
    "OddsResponse",
    "ScoreResponse",
    "MarketsData",
    "MarketLine",
    "PlayerProp",
    "ScoreData",
    # Implementations
    "MockOddsProvider",
    "MockScoreProvider",
    # Factory
    "ProviderFactory",
]
