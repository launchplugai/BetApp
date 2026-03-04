"""
S19-A: Live Provider Stub

Placeholder for live API integration.
Currently returns empty/mock data until API keys are configured.
"""

from typing import List, Optional

from app.providers import (
    OddsProvider,
    ScoreProvider,
    Sport,
    Game,
    MarketOdds,
    LiveScore,
    ProviderConfig
)


class LiveOddsProvider(OddsProvider):
    """
    Live odds provider (stubbed).
    
    TODO: Integrate with external odds API when keys are available.
    For now, falls back to mock behavior or returns empty.
    """
    
    def __init__(self, config: ProviderConfig):
        self.config = config
        self.api_key = config.api_key
        
        if not self.api_key:
            print("WARNING: LiveOddsProvider initialized without API key. Using fallback mode.")
    
    def get_sports(self) -> List[Sport]:
        """
        Get available sports from live API.
        
        TODO: Implement API call.
        """
        # Stub: Return empty or basic sports
        return [
            Sport(id="NBA", label="NBA", active=True),
            Sport(id="NFL", label="NFL", active=True),
        ]
    
    def get_games(self, sport: str) -> List[Game]:
        """
        Get games from live API.
        
        TODO: Implement API call.
        """
        # Stub: Return empty
        print(f"LiveOddsProvider.get_games({sport}) - Not implemented, returning empty")
        return []
    
    def get_odds(self, game_id: str) -> List[MarketOdds]:
        """
        Get odds from live API.
        
        TODO: Implement API call.
        """
        # Stub: Return empty
        print(f"LiveOddsProvider.get_odds({game_id}) - Not implemented, returning empty")
        return []


class LiveScoreProvider(ScoreProvider):
    """
    Live score provider (stubbed).
    
    TODO: Integrate with external score API when keys are available.
    """
    
    def __init__(self, config: ProviderConfig):
        self.config = config
        self.api_key = config.api_key
        
        if not self.api_key:
            print("WARNING: LiveScoreProvider initialized without API key. Using fallback mode.")
    
    def get_score(self, game_id: str) -> Optional[LiveScore]:
        """
        Get live score from API.
        
        TODO: Implement API call.
        """
        # Stub: Return None
        return None
