"""
Odds API Provider with TTL Caching

This enhances the existing OddsApiProvider to include TTL (Time to Live) caching for response accuracy.
"""

import time
from datetime import datetime
from typing import Optional, List
from app.providers.odds_api import OddsApiProvider
from app.providers import MarketOdds


class CachedOddsApiProvider(OddsApiProvider):
    TTL = 60  # Time-to-Live for cache in seconds
    cache = {}  # Cached responses
    last_updated = {}  # Timestamps for cache expiry

    async def get_odds(self, game_id: str) -> List[MarketOdds]:
        current_time = time.time()  # Current time for TTL checking

        # Check if we have cached data that hasn't expired
        if game_id in self.cache and (current_time - self.last_updated[game_id]) < self.TTL:
            return self.cache[game_id]

        # Call the base class method to fetch fresh odds
        odds = await super().get_odds(game_id)

        # Cache the fresh odds and update timestamp
        if odds is not None:
            self.cache[game_id] = odds
            self.last_updated[game_id] = current_time

        return odds

    async def clear_cache(self):
        current_time = time.time()
        # Clear stale cache entries
        for game_id in list(self.last_updated.keys()):
            if (current_time - self.last_updated[game_id]) >= self.TTL:
                del self.cache[game_id]
                del self.last_updated[game_id]
