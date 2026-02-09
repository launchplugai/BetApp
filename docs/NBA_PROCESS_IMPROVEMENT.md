# NBA Analytics Process Improvement Plan

## Current State Assessment

### What's Working ✅
- Modular architecture (5 standalone components)
- Free data source (nba_api)
- <100ms cached response times
- 30 NBA teams loaded, heuristics calculating
- ESPN scraper ready for injuries

### Improvement Opportunities 🎯
1. **No automated testing** - Manual validation only
2. **No outcome tracking** - Can't measure heuristic accuracy
3. **Limited data sources** - Only nba_api + ESPN
4. **No feedback loop** - Adjustments based on theory, not results
5. **Documentation gaps** - API usage examples missing

---

## Improvement Initiatives

### 1. Automated Testing & Validation

**Goal:** Catch regressions, validate heuristics against historical data

**Actions:**
```python
# tests/nba/test_heuristics_validation.py

def test_rest_advantage_accuracy():
    """Validate rest adjustment against historical spreads."""
    # For all games 2023-24, compare:
    # - Predicted rest impact vs actual margin
    # - Assert correlation > 0.6
    
def test_tank_detector_precision():
    """Measure tank detection accuracy."""
    # Known tanking teams (2023: Pistons, Wizards, etc.)
    # Assert detection rate > 80%
    
def test_injury_impact_correlation():
    """Validate injury WAR estimates."""
    # Compare predicted WAR loss to actual team performance drop
```

**Schedule:** Run nightly against last 30 days

---

### 2. Outcome Tracking System

**Goal:** Measure actual ROI of NBA-informed bets

**Database Addition:**
```sql
CREATE TABLE bet_outcomes (
    id SERIAL PRIMARY KEY,
    bet_id VARCHAR REFERENCES bets(id),
    nba_context JSONB,  -- Snapshot of heuristics at bet time
    predicted_edge FLOAT,
    actual_result VARCHAR,  -- win/loss/push
    actual_margin FLOAT,    -- for spread bets
    closing_line FLOAT,     -- to measure closing line value
    created_at TIMESTAMP
);
```

**Metrics Dashboard:**
- Win rate by heuristic signal strength
- ROI by rest advantage tier
- Tank detection → actual underperformance
- Injury severity → actual ATS impact

---

### 3. Expand Data Sources

**Priority Matrix:**

| Source | Cost | Value | Effort | Priority |
|--------|------|-------|--------|----------|
| Basketball-Reference | Free | High | Medium | **P1** |
| Rotowire | Free | High | Low | **P1** |
| Dunks & Threes | Free | Medium | Low | **P2** |
| Cleaning the Glass | $$$ | Very High | N/A | P3 (deferred) |

**Basketball-Reference Scraper:**
```python
# app/nba/scrapers/bball_ref.py

class BasketballReferenceScraper:
    """Historical advanced stats."""
    
    def fetch_team_ratings(self, season):
        # Offensive/defensive ratings
        # Pace, strength of schedule
        pass
    
    def fetch_player_advanced(self, player_id):
        # BPM, VORP, WS/48
        # On/off splits
        pass
```

**Rotowire Scraper:**
```python
# app/nba/scrapers/rotowire.py

class RotowireScraper:
    """Real-time injury updates."""
    
    def scrape_injuries(self):
        # More frequent updates than ESPN
        # Expected return dates
        # Practice participation
        pass
```

---

### 4. Feedback Loop Implementation

**Weekly Review Process:**

1. **Generate Report** (auto-run Monday 6am)
```python
# scripts/weekly_nba_review.py

report = generate_weekly_report()
# - Bets placed with NBA context
# - Win/loss by signal type
# - Calibration (predicted vs actual)
# - Suggested model adjustments
```

2. **Calibration Analysis**
```
Rest Advantage Calibration:
Predicted B2B impact: -4.5 pts
Actual observed: -3.2 pts
Adjustment needed: +1.3 pts

Tank Detection Calibration:
Predicted 12 tanking teams
Actual tanking: 8 teams
Precision: 67% (need better signals)
```

3. **Model Updates**
- Tune rest coefficients monthly
- Retrain tank detection quarterly
- Update injury WAR weights based on outcomes

---

### 5. Documentation & Onboarding

**Code Documentation:**
```python
def calculate_rest_advantage(team_id: int, game_date: date) -> dict:
    """
    Calculate rest advantage based on days since last game.
    
    Research basis:
        - Kubatko (2015): B2B = -4.5 pts
        - Hollinger (2018): Fatigue accumulates over 3-in-4
    
    Args:
        team_id: NBA team ID
        game_date: Date of upcoming game
        
    Returns:
        {
            'days_rest': int,           # Days since last game
            'advantage_points': float,  # Research-based point adjustment
            'fatigue_score': float,     # 0-100 composite
            'games_in_7_days': int      # Recent game load
        }
        
    Example:
        >>> calculate_rest_advantage(1610612747, date(2025, 2, 10))
        {'days_rest': 0, 'advantage_points': -4.5, 'fatigue_score': 85, ...}
    """
```

**API Documentation:**
- Auto-generated from FastAPI (Swagger UI)
- Postman collection for testing
- Code examples in multiple languages

---

## Execution Timeline

### Week 1 (This Week)
- [x] Complete Phase 1 foundation
- [x] Create comprehensive documentation
- [ ] Add Basketball-Reference scraper
- [ ] Wire into DNA pipeline

### Week 2
- [ ] Build outcome tracking system
- [ ] Add automated tests (historical validation)
- [ ] Deploy to production with monitoring

### Week 3
- [ ] First weekly review report
- [ ] Add Rotowire scraper
- [ ] Begin calibration tuning

### Week 4
- [ ] Full feedback loop operational
- [ ] Optimization based on Week 1-3 outcomes
- [ ] Advanced metrics integration (Dunks & Threes)

---

## Success Metrics

| Metric | Target | Measurement |
|--------|--------|-------------|
| Cache hit rate | >90% | `/api/nba/cache/stats` |
| API response time | <100ms | Logging/monitoring |
| Data freshness | <1h | Timestamp tracking |
| Heuristic accuracy | >70% | Outcome tracking |
| Tank detection precision | >80% | Manual validation |
| Test coverage | >80% | pytest --cov |

---

## Risk Mitigation

| Risk | Mitigation |
|------|------------|
| nba_api rate limits | Cache aggressively, backoff on 429 |
| ESPN blocks scraper | Rotate user agents, respect robots.txt |
| Data quality issues | Multi-source validation, confidence scores |
| Heuristics don't improve ROI | A/B test, gradual rollout |
| Database bloat | Partition by season, archive old data |

---

*Plan Version: 1.0*
*Review Date: Weekly*
