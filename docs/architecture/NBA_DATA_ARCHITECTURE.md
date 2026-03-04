# NBA Data Architecture v1.0
## Industry Best Practices Implementation

---

## Executive Summary

This architecture mirrors how professional NBA analytics teams structure their data pipelines:
- **Washington Wizards** (internal analytics platform)
- **Second Spectrum** (tracking data infrastructure)
- **Basketball-Index** (public-facing analytics)

**Cost Target:** <$50/mo for full pipeline vs $2,000+/mo for SportRadar/Stats Perform

---

## Data Sources & Priority

| Source | Data Type | Frequency | Priority | Implementation |
|--------|-----------|-----------|----------|----------------|
| **nba_api** (official) | Box scores, play-by-play, tracking | Real-time | P0 | Python package |
| **Basketball-Reference** | Historical, advanced stats | Daily | P0 | Scraping |
| **ESPN** | Injuries, news, odds | Hourly | P1 | Scraping |
| **Rotowire** | Injury reports | Every 15min | P1 | Scraping |
| **Cleaning the Glass** | Advanced metrics | Weekly | P2 | Manual/Export |
| **Dunks & Threes** | Shooting splits | Weekly | P2 | Manual/Export |

---

## Storage Architecture

### Layer 1: Raw Data Lake (S3/R2)
```
bucket/dna-nba-data/
├── raw/
│   ├── nba-api/
│   │   ├── games/YYYY/MM/DD/game_{id}.json
│   │   ├── players/{season}/players.json
│   │   └── teams/{season}/teams.json
│   ├── bball-ref/
│   │   └── ...
│   └── espn/
│       └── injuries/YYYY/MM/DD/HH.json
├── processed/
│   └── parquet/  # Columnar for analytics
└── cache/
    └── redis-dump/  # Periodic snapshots
```

**Why S3/R2?**
- $0.005/GB (R2) vs $0.10/GB (S3)
- Parquet format: 10x compression vs JSON
- 5 years of NBA data = ~50GB raw → ~5GB parquet = $0.25/mo

### Layer 2: Operational Database (PostgreSQL)

**Schema Design (Star Schema):**

```sql
-- FACT TABLES (high volume, append-only)
fact_box_scores
fact_play_by_play
fact_tracking_data
fact_line_movement

-- DIMENSION TABLES (relatively static)
dim_teams
dim_players
dim_games
dim_seasons

-- CONTEXT TABLES (business logic)
context_injuries
context_rest_days
context_playoff_standings
context_tank_probabilities
```

**Partitioning Strategy:**
- Partition `fact_*` tables by season
- Auto-archive seasons >3 years old to parquet

### Layer 3: Real-Time Cache (Redis/Memcached)

**Cache Tiers:**
```
L1: In-memory (app instance) - 60s TTL
  → Active games, live odds
  
L2: Redis - 5min TTL
  → Today’s schedule, injury reports
  → Player stats (last 10 games)
  
L3: Redis - 24h TTL
  → Season averages, team ratings
  → Historical matchup data
```

---

## Heuristics Engine

### 1. Rest Advantage Calculator
```python
def calculate_rest_advantage(team, game_date):
    """
    Industry standard: Back-to-backs = -3 to -5 point penalty
    Source: NBA analytics research (Kubatko, Hollinger)
    """
    last_game = get_last_game_date(team, before=game_date)
    days_rest = (game_date - last_game).days
    
    rest_tiers = {
        0: -4.5,   # Back-to-back (severe)
        1: -2.0,   # 1 day (mild)
        2: 0.0,    # Normal
        3: +1.0,   # Well-rested
        4: +1.5,   # Very rested
    }
    return rest_tiers.get(min(days_rest, 4), 0.0)
```

### 2. Tank Detector v1
```python
def detect_tanking(team_id, season_phase):
    """
    Signals:
    - Star players sitting "load management" in losses
    - Playing young players heavy minutes in blowouts
    - Trading away good players for picks
    - Worsening defense (easier to tank than offense)
    """
    signals = {
        'minutes_distribution': check_young_player_minutes(team_id),
        'defensive_effort': analyze_defensive_metrics(team_id),
        'player_availability': check_star_sitting(team_id),
        'trade_activity': check_recent_trades(team_id),
    }
    
    tank_score = weighted_score(signals)
    return {
        'is_tanking': tank_score > 0.7,
        'confidence': tank_score,
        'signals': signals
    }
```

### 3. Playoff Context Engine
```python
def get_playoff_context(team_id, date):
    """
    Determine playoff relevance for each game.
    """
    standing = get_current_standings(team_id, date)
    games_remaining = get_games_remaining(team_id, date)
    
    # Magic number calculations
    clinch_number = calculate_clinch_number(team_id)
    elimination_number = calculate_elimination_number(team_id)
    
    # Position battles
    position_battles = identify_position_battles(team_id, date)
    
    return {
        'clinch_scenario': clinch_number,
        'elimination_scenario': elimination_number,
        'position_battles': position_battles,
        'game_importance': calculate_leverage_index(team_id, date)
    }
```

### 4. Matchup History with Context
```python
def get_matchup_context(team_a, team_b, date):
    """
    Not just head-to-head, but contextual matchup data.
    """
    return {
        'head_to_head_this_season': get_h2h_games(team_a, team_b, this_season),
        'last_5_vs_opponent': get_player_vs_opponent_stats(team_a, team_b),
        'style_matchup': analyze_style_clash(team_a, team_b),
        'rest_disparity': calculate_rest_diff(team_a, team_b, date),
        'venue_history': get_venue_specific_history(team_a, team_b),
        'referee_tendencies': get_ref_stats_for_matchup(team_a, team_b),
    }
```

### 5. Injury Impact Calculator
```python
def calculate_injury_impact(team_id, injuries):
    """
    Use RPM/RAPTOR/BPM to estimate wins lost.
    """
    total_impact = 0
    for injury in injuries:
        player = get_player(injury.player_id)
        impact = {
            'raptor': player.raptor_current,
            'minutes_replacement': estimate_replacement_minutes(player),
            'position_depth': check_position_depth(team_id, player.position),
        }
        total_impact += impact['raptor'] * impact['minutes_replacement'] / 48
    
    return {
        'wins_lost_estimate': total_impact * 2.7,  # Conversion factor
        'severity': 'critical' if total_impact > 5 else 'moderate' if total_impact > 2 else 'minor'
    }
```

---

## Pipeline Orchestration

### Airflow-style DAG (simplified)

```
 daily_etl_dag:
   00:00 → fetch_yesterday_games (nba_api)
   00:05 → fetch_injury_reports (espn, rotowire)
   00:10 → update_player_stats (rolling 10-game)
   00:15 → calculate_team_ratings (offensive/defensive)
   00:20 → update_standings (playoff context)
   00:25 → run_heuristics (rest, tank, etc.)
   00:30 → warm_cache (today's games)
   00:35 → notify_protocols (if significant changes)
```

### Real-time Components

```
 live_game_tracker:
   Every 30s during active games:
     - Fetch play-by-play
     - Update live stats
     - Calculate win probability
     - Check for injuries (sudden exits)
     - Notify protocols of significant events
```

---

## Cost Breakdown

| Component | Service | Monthly Cost |
|-----------|---------|--------------|
| Raw Storage | Cloudflare R2 | $0.25 (50GB) |
| Operational DB | Supabase PostgreSQL | $25 (8GB) |
| Cache | Upstash Redis | $10 (10K ops/day) |
| Compute | Railway / Fly.io | $15 (2 shared CPUs) |
| **Total** | | **~$50/mo** |

---

## Implementation Phases

### Phase 1: Foundation (Week 1)
- [ ] Set up PostgreSQL schema
- [ ] Integrate nba_api package
- [ ] Basic box score ingestion
- [ ] Rest advantage calculator

### Phase 2: Context Layer (Week 2)
- [ ] Injury tracking system
- [ ] Playoff context engine
- [ ] Tank detector v1
- [ ] Matchup history

### Phase 3: Scraping Layer (Week 3)
- [ ] Basketball-Reference scraper
- [ ] ESPN injury scraper
- [ ] Data validation & testing

### Phase 4: Integration (Week 4)
- [ ] DNA protocol integration
- [ ] Real-time cache warming
- [ ] Edge detection rules

---

## Open Source Tools to Leverage

1. **nba_api** - Official NBA stats (free, maintained)
2. **basketball-reference-web-scraper** - Community scraper
3. **nba-stats-tracker** - Historical data
4. **hoopR** / **nba_data** - R/Python ecosystems

Don't reinvent what exists — wrap and enhance.

---

## Success Metrics

- [ ] <5s latency for protocol queries
- [ ] 99.9% data freshness (within 1h of game end)
- [ ] <1% error rate on heuristics vs actual results
- [ ] Zero data loss (S3/R2 backup)

---

*Document Version: 2026-02-09*
*Status: Design Complete → Ready for Implementation*
