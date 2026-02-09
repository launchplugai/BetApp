# NBA Analytics Module Documentation

## Overview

Modular NBA data pipeline for edge detection in sports betting. Provides real-time heuristics including rest advantage, injury impact, tank detection, playoff context, and matchup analysis.

**Architecture:** Star schema database + multi-tier cache + pluggable scrapers
**Cost:** $0/mo (nba_api free, SQLite local storage)
**Latency:** <100ms for cached data, <2s for fresh API calls

---

## Quick Start

### 1. Initialize Database

```python
from app.nba.database import full_bootstrap

# One-time setup: creates tables + loads 30 NBA teams
full_bootstrap()
```

### 2. Get Edge Analysis

```python
from app.nba.protocol_integration import enhance_nba_bet

context = enhance_nba_bet(
    bet_text="LAL -4.5",
    teams=["LAL", "GSW"]
)

print(context['confidence_adjustments']['total_adjustment'])
# Output: -6.75 (reduce confidence due to rest disadvantage)
```

### 3. Run Injury Scraper

```python
from app.nba.scrapers import run_injury_scraper
from app.nba.database import get_db_session

db = get_db_session()
count = run_injury_scraper(db)
print(f"Saved {count} injuries")
```

---

## API Endpoints

| Endpoint | Description | Cache |
|----------|-------------|-------|
| `GET /api/nba/teams` | All NBA teams | 24h |
| `GET /api/nba/games/today` | Today's schedule | 5min |
| `GET /api/nba/edge/{team_a}/{team_b}` | Full heuristics | 5min |
| `GET /api/nba/rest/{team}` | Rest advantage | 5min |
| `GET /api/nba/tank/{team}` | Tank detection | 5min |
| `GET /api/nba/injuries/{team}` | Injury impact | 5min |
| `GET /api/nba/standings/{team}` | Playoff context | 5min |
| `GET /api/nba/matchup/{team_a}/{team_b}` | H2H history | 24h |

---

## Heuristics Engine

### Rest Advantage

**Research basis:** Kubatko/Hollinger NBA analytics

| Days Rest | Point Impact | Notes |
|-----------|--------------|-------|
| 0 (B2B) | -4.5 | Severe fatigue |
| 1 | -2.0 | Mild fatigue |
| 2 | 0.0 | Normal baseline |
| 3 | +1.0 | Well-rested |
| 4+ | +1.5 | Very rested |

**API:**
```python
from app.nba.heuristics import NBAHeuristics

heuristics = NBAHeuristics(db)
rest = heuristics.calculate_rest_advantage(team_id, game_date)
# Returns: {days_rest, advantage_points, fatigue_score, games_in_7_days}
```

### Tank Detection

**Signals weighted by confidence:**
- Playoff elimination (>10 games back): 50% weight
- Star availability (load management): 20% weight
- Youth minutes in blowouts: 10% weight
- Defensive decline: 20% weight

**Threshold:** `confidence > 0.6` = likely tanking

**API:**
```python
tank = heuristics.detect_tanking(team_id, season, date)
# Returns: {is_tanking, confidence, signals}
```

### Injury Impact

**Calculation:**
```
WAR_lost = games_missed × 0.1 (rough estimate)
Severity: <2 WAR = minor, 2-5 WAR = moderate, >5 WAR = critical
```

**Future:** Integrate actual RAPTOR/BPM from external sources

**API:**
```python
injury = heuristics.calculate_injury_impact(team_id, date)
# Returns: {injured_players[], total_war_lost, severity}
```

### Playoff Context

**Leverage Index (0-100):**
- Base: 50 (normal game)
- Play-in territory (7-10 seed): +20
- Bubble (6/11 seed): +15
- Close to clinching (≤5 games): +15
- Elimination risk (≤5 games): +20

**API:**
```python
playoff = heuristics.get_playoff_context(team_id, season, date)
# Returns: {current_seed, games_back, clinch_number, elimination_number, leverage_index}
```

### Matchup Analysis

**Includes:**
- Head-to-head record this season
- Recent form (last 10 games, W-L, avg points)
- Style clash (pace differential, shooting profiles)
- Venue splits (home/away records)

**API:**
```python
matchup = heuristics.analyze_matchup(team_a_id, team_b_id, season)
```

---

## Protocol Integration

### DNA Pipeline Hook

The `enhance_nba_bet()` function is designed to be called from the DNA bet analysis pipeline:

```python
def analyze_bet_with_nba_context(bet_input):
    # Existing DNA analysis
    base_analysis = dna_analyze(bet_input)
    
    # Enhance with NBA context
    nba_context = enhance_nba_bet(
        bet_text=bet_input.text,
        teams=bet_input.teams
    )
    
    # Apply confidence adjustments
    adjusted_confidence = base_analysis.confidence + \
        nba_context['confidence_adjustments']['total_adjustment']
    
    # Add risk flags to verdict
    if nba_context['risk_flags']:
        base_analysis.warnings.extend(nba_context['risk_flags'])
    
    # Include context summary
    base_analysis.nba_context = nba_context['context_summary']
    
    return base_analysis
```

### Confidence Adjustment Logic

| Factor | Adjustment Range | Triggers |
|--------|------------------|----------|
| Rest | -10 to +10 | B2B vs well-rested |
| Injury | -15 to +15 | WAR differential |
| Tank | -20 to +10 | Tanking detection |
| Playoff | -5 to +5 | Leverage index diff |

**Caps:**
- Maximum single adjustment: ±20
- Maximum total adjustment: ±30
- Never reduce confidence below 10

---

## Data Pipeline

### Daily ETL (6am ET)

```
00:00 → Fetch yesterday's games from nba_api
00:05 → Ingest box scores (player + team)
00:15 → Update playoff standings
00:20 → Calculate rest days for upcoming games
00:25 → Warm cache for today's matchups
00:30 → Notify protocols of significant changes
```

**Setup:**
```bash
sudo bash scripts/setup_nba_cron.sh
```

### Injury Scraping (every 15min during season)

```python
# Manual run
from app.nba.scrapers import run_injury_scraper
count = run_injury_scraper(db)

# Cron setup (add separately)
*/15 * * * * /path/to/python /path/to/scripts/scrape_injuries.py
```

---

## Cache Strategy

| Tier | TTL | Use Case |
|------|-----|----------|
| L1 | 60s | Live scores, active games |
| L2 | 5min | Today's schedule, injuries |
| L3 | 24h | Season averages, H2H history |

**Cache Keys:**
```python
NBACache.key_game_odds(game_id)
NBACache.key_heuristics(team_a_id, team_b_id, date)
NBACache.key_matchup(team_a_id, team_b_id, date)
```

---

## Adding New Scrapers

**Template:**

```python
# app/nba/scrapers/new_source.py

class NewSourceScraper:
    def scrape_data(self) -> List[Dict]:
        # 1. Fetch data
        # 2. Parse HTML/JSON
        # 3. Normalize to schema
        pass
    
    def save_to_database(self, db: Session, data: List[Dict]) -> int:
        # 1. Match to existing records
        # 2. Insert/update
        # 3. Return count
        pass
```

**Register:**
```python
# app/nba/scrapers/__init__.py
from .new_source import NewSourceScraper

__all__ = [..., 'NewSourceScraper']
```

---

## Testing

### Unit Tests

```bash
pytest app/nba/tests/ -v
```

### Integration Test

```bash
python test_nba_setup.py
```

### Live API Test

```bash
curl http://localhost:8000/api/nba/edge/LAL/GSW
```

---

## Database Schema

See `app/nba/models.py` for full definitions.

**Key Tables:**
- `dim_teams` - 30 NBA teams
- `dim_players` - Active roster
- `dim_games` - Schedule & results
- `fact_box_scores` - Player stats per game
- `context_rest_days` - Pre-calculated rest
- `context_injuries` - Injury reports
- `cache_analytics` - Pre-computed heuristics

---

## Roadmap

**Phase 1: Foundation** ✅ COMPLETE
- [x] Database schema (star schema)
- [x] nba_api integration
- [x] Heuristics engine
- [x] REST API
- [x] Cache layer

**Phase 2: Data Sources** 🔄 IN PROGRESS
- [x] ESPN injury scraper
- [ ] Basketball-Reference historical
- [ ] Rotowire injury updates
- [ ] Dunks & Threes advanced metrics

**Phase 3: Protocol Integration** 🔄 IN PROGRESS
- [x] Protocol integration module
- [ ] Wire into DNA pipeline
- [ ] A/B test confidence adjustments
- [ ] Feedback loop (outcome tracking)

**Phase 4: Advanced Analytics**
- [ ] Player tracking data (if available)
- [ ] Referee assignment impact
- [ ] Weather/venue effects
- [ ] Sharp money detection

---

## Troubleshooting

### No teams in database
```python
from app.nba.database import bootstrap_teams
bootstrap_teams()
```

### Cache stale data
```bash
curl -X POST http://localhost:8000/api/nba/cache/clear
```

### nba_api timeout
```python
# Increase timeout in ingestion.py
nba_api.stats.endpoints.leaguegamefinder.LeagueGameFinder(
    timeout=60
)
```

---

## References

- **nba_api docs:** https://github.com/swar/nba_api
- **NBA analytics research:** https://www.basketball-reference.com/about/glossary.html
- **Rest impact study:** https://www.nbastuffer.com/analytics-101/rest-advantage/
- **Tank detection methodology:** Based on Kevin Pelton's ESPN analysis

---

*Last Updated: 2026-02-09*
*Version: 1.0*
