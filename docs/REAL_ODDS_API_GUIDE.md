# Real Odds API Integration Guide

**Priority 3 - Get Real Data**

**Status:** Mock provider active, LiveProvider ready for API keys

---

## Quick Start (5 Minutes)

### 1. Choose Provider

**Recommended for DNA Bet Engine:**

| Provider | Cost | Coverage | Features |
|----------|------|----------|----------|
| **The Odds API** | $50-200/mo | 🌎 Global | Real-time odds, scores |
| **Rapid API** | $10-100/mo | 🌎 Global | Multiple sports, free tier |
| **API-Sports** | Free-$30/mo | 🌎 Global | Odds + scores + stats |

**Best Choice:** The Odds API (reliable, sports-focused)

---

### 2. Get API Key

```bash
# Sign up at https://the-odds-api.com
# Get free API key (500 requests/month)
# Copy your key: XXXXXXXXXXXXXXXXXXXXXXXX
```

---

### 3. Add to Environment

```bash
# Railway dashboard → DNA project → Variables
ODDS_API_KEY=your_key_here
ODDS_API_TYPE=theoddsapi  # or rapidapi, apisports
```

---

### 4. Update Code (One Line)

**File:** `app/routers/odds.py`

```python
# Line 35 - Change provider type
def get_odds_provider() -> any:
    provider_type = "live"  # <-- Change from "mock" to "live"
    
    if provider_type == "live":
        import os
        api_key = os.getenv("ODDS_API_KEY")
        config = ProviderConfig(provider_type="live", api_key=api_key)
        return LiveOddsProvider(config)
    else:
        return MockOddsProvider()
```

---

### 5. Implement LiveProvider

**File:** `app/providers/live_provider.py`

Replace stub with real API calls:

```python
import requests
from typing import List

class LiveOddsProvider(OddsProvider):
    def __init__(self, config: ProviderConfig):
        self.config = config
        self.api_key = config.api_key
        self.base_url = "https://api.the-odds-api.com/v4"
    
    def get_sports(self) -> List[Sport]:
        """Fetch real sports from API."""
        response = requests.get(
            f"{self.base_url}/sports",
            params={"apiKey": self.api_key}
        )
        data = response.json()
        
        # Map API response to canonical format
        return [
            Sport(
                id=s["key"].upper(),
                label=s["title"],
                active=s["active"]
            )
            for s in data
        ]
    
    def get_games(self, sport: str) -> List[Game]:
        """Fetch real games from API."""
        response = requests.get(
            f"{self.base_url}/sports/{sport.lower()}/odds",
            params={
                "apiKey": self.api_key,
                "regions": "us",
                "markets": "h2h,spreads,totals"
            }
        )
        data = response.json()
        
        # Map API response to canonical Game format
        games = []
        for event in data:
            games.append(Game(
                id=event["id"],
                league=sport.upper(),
                home=event["home_team"],
                away=event["away_team"],
                start_time=event["commence_time"],
                status="SCHEDULED"  # Check if live via separate endpoint
            ))
        return games
    
    def get_odds(self, game_id: str) -> List[MarketOdds]:
        """Fetch real odds for a game."""
        # Fetch event data
        response = requests.get(
            f"{self.base_url}/sports/basketball_nba/odds",
            params={
                "apiKey": self.api_key,
                "eventIds": game_id,
                "markets": "h2h,spreads,totals"
            }
        )
        data = response.json()
        
        if not data:
            return []
        
        event = data[0]
        markets = []
        
        # Map bookmaker odds to canonical MarketOdds
        for bookmaker in event.get("bookmakers", []):
            for market in bookmaker.get("markets", []):
                market_type = market["key"]  # h2h, spreads, totals
                
                selections = []
                for outcome in market["outcomes"]:
                    selections.append(Selection(
                        label=f"{outcome['name']} {outcome.get('point', '')}",
                        line=outcome.get("point"),
                        odds=self._convert_odds(outcome["price"])
                    ))
                
                markets.append(MarketOdds(
                    market=market_type,
                    selections=selections
                ))
        
        return markets
    
    def _convert_odds(self, decimal_odds: float) -> int:
        """Convert decimal odds to American odds."""
        if decimal_odds >= 2.0:
            return int((decimal_odds - 1) * 100)
        else:
            return int(-100 / (decimal_odds - 1))
```

---

### 6. Test Live Data

```bash
# Restart app
openclaw gateway restart

# Or redeploy Railway
git push origin main

# Test endpoints
curl https://dna-production-cb47.up.railway.app/api/sports
curl "https://dna-production-cb47.up.railway.app/api/games?sport=NBA"
```

---

## API Rate Limits

| Provider | Free Tier | Paid |
|----------|-----------|------|
| The Odds API | 500/mo | 10K-100K/mo |
| Rapid API | 100/day | 10K/day |
| API-Sports | 100/day | 30K/day |

**DNA Usage Estimate:**
- Browse screen load: 1-2 calls
- Builder load: 1 call per game
- **Total:** ~50-100 calls/day (well within free tier)

---

## Cost Calculator

```python
# The Odds API pricing example
FREE_TIER = 500  # requests/month
PAID_TIER_1 = 10000  # $50/month
PAID_TIER_2 = 50000  # $150/month

# DNA Bet Engine usage
users_per_day = 10
bets_per_user = 5
api_calls_per_bet = 3  # browse + odds + refresh

monthly_calls = users_per_day * bets_per_user * api_calls_per_bet * 30
print(f"Monthly: {monthly_calls} calls")  # = 4,500 calls

# Result: FREE_TIER insufficient, need PAID_TIER_1 ($50/month)
```

---

## Alternative: Build Own Scraper

**If API costs too high:**

```python
# Scrape odds from public sportsbook sites
# Legal for personal use, check ToS for commercial
import requests
from bs4 import BeautifulSoup

def scrape_draftkings_odds(game_id):
    """Example scraper (for reference only)."""
    url = f"https://sportsbook.draftkings.com/..."
    response = requests.get(url, headers={"User-Agent": "..."})
    soup = BeautifulSoup(response.text, "html.parser")
    
    # Parse odds from HTML
    # Map to canonical MarketOdds format
    # ...
    
# Pros: Free, no API limits
# Cons: Fragile (breaks when sites change), slower, legal risk
```

**Recommendation:** Start with paid API, consider scraper only if costs prohibit scaling.

---

## Deploy Checklist

- [ ] Sign up for API provider
- [ ] Add `ODDS_API_KEY` to Railway variables
- [ ] Update `get_odds_provider()` to return `"live"`
- [ ] Implement LiveOddsProvider API calls
- [ ] Test `/api/sports` endpoint
- [ ] Test `/api/games?sport=NBA` endpoint
- [ ] Test `/api/odds/{game_id}` endpoint
- [ ] Verify browse screen shows real games
- [ ] Verify builder shows real odds
- [ ] Monitor API usage in provider dashboard

---

## Status: READY TO IMPLEMENT

**Next Steps:**
1. Choose provider (recommend: The Odds API)
2. Sign up + get free key
3. Add to Railway env vars
4. Implement LiveProvider API calls (30-60 min)
5. Deploy + test

**Estimated Time:** 1-2 hours  
**Estimated Cost:** $0-50/month
