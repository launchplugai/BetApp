# Multi-Sport Heuristics Framework

Standardized analytics modules for all supported sports.

## Architecture

Each sport has its own heuristics module:
- `nba/` - NBA analytics (✅ exists)
- `nfl/` - NFL analytics (new)
- `mlb/` - MLB analytics (new)
- `nhl/` - NHL analytics (new)
- `soccer/` - Soccer analytics (new)
- `ufc/` - UFC analytics (new)
- `tennis/` - Tennis analytics (new)

## Heuristics Interface

```python
class SportHeuristics(Protocol):
    def get_game_context(self, game_id: str) -> GameContext
    def get_player_stats(self, player_id: str) -> PlayerStats
    def calculate_edges(self, bet: Bet) -> EdgeAssessment
    def generate_insights(self, game_id: str) -> List[Insight]
```

## Tiers

- **GOOD**: Basic trends, last 5 games, season averages
- **BETTER**: Matchup analysis, situational stats, splits
- **BEST**: Full analytics, player matchups, coaching trends, weather/venue

## Data Sources (Future)

- Sport-specific APIs
- Historical databases
- Real-time feeds
- Injury reports
- Weather services
