# DNA Feature Layer Roadmap

**Status:** Implementation plan (Phase 2)  
**Prerequisites:** Dashboard foundation complete (Slices 1, 2A, 2B)  
**Goal:** Build structured state modules that transform raw data into computable signals  
**Date:** 2026-02-12

---

## Overview

**DNA's job:** Turn the messy world into stable variables your engine can compute with.

**DNA does NOT decide bets.**  
DNA creates the **feature layer** — structured state that the bet engine and Sherlock can reason about.

---

## Module Architecture

### Module 1: Team State (`app/intelligence/team_state.py`)

**Responsibility:** Compute team competitive state and structural metrics.

**Outputs:**
```python
{
  "team_competitive_state": "tanking" | "contending" | "bubble" | "eliminated" | "clinched",
  "playoff_pressure_index": 0-100,
  "tanking_score": 0.0-1.0,
  "rotation_stability_score": 0-100
}
```

**Inputs Required:**
- Current standings position
- Playoff elimination date (if applicable)
- Clinch date (if applicable)
- Rookie minute trends (last 10 games)
- Veteran rest patterns (DNP-Rest frequency)
- Lineup entropy (unique starting lineups / games played)
- Recent game margins (blowout frequency)

**Calculation Details:**

#### `teamCompetitiveState` Logic:
```python
if playoffs_clinched and seed_locked:
    return "clinched"
elif playoff_eliminated and tanking_score > 0.7:
    return "tanking"
elif playoff_eliminated:
    return "eliminated"
elif playoff_probability > 0.75:
    return "contending"
else:
    return "bubble"
```

#### `playoffPressureIndex` (0-100):
```python
if clinched or eliminated:
    return 0
elif bubble (play-in range):
    return 75 + (games_back * 5)  # cap at 100
elif contending:
    return 50 + (seed_importance * 10)
```

#### `tankingScore` (0.0-1.0):
```python
tanking_score = weighted_sum([
    playoff_eliminated * 0.30,
    rookie_minutes_increase * 0.25,
    veteran_rest_frequency * 0.20,
    lineup_entropy * 0.15,
    blowout_rotation_variance * 0.10
])
```

#### `rotationStabilityScore` (0-100):
```python
# Lower = more volatile
rotation_stability = 100 - (lineup_entropy * 100)
# Adjust for injury impacts
if key_injuries > 2:
    rotation_stability *= 0.7
```

**Backtest Requirements:**
- Historical ATS performance by `teamCompetitiveState` (last 3 seasons)
- Prop hit rate correlation with `tankingScore` (eliminated teams, final 20 games)
- Rotation volatility impact on Over/Under accuracy

---

### Module 2: Player Incentive (`app/intelligence/player_incentive.py`)

**Responsibility:** Model player motivation and incentive alignment.

**Outputs:**
```python
{
  "contract_pressure_index": 0.0-1.0,
  "award_chase_flag": True | False,
  "award_target": "25.0 PPG for All-NBA" | None,
  "role_security": "low" | "medium" | "high",
  "usage_spike_probability": 0.0-1.0,
  "minutes_cap_probability": 0.0-1.0
}
```

**Inputs Required:**
- Contract status (years remaining, UFA/RFA date, current salary)
- Award race position (current stats vs threshold)
- Recent injury return date (if applicable)
- Usage rate trend (last 10 games vs season avg)
- Role stability (starter/bench changes, DNP-CD frequency)
- Age (veteran preservation logic)

**Calculation Details:**

#### `contractPressureIndex` (0.0-1.0):
```python
if contract_year and UFA:
    base_pressure = 0.9
elif contract_year and RFA:
    base_pressure = 0.7
elif 1_year_remaining:
    base_pressure = 0.5
else:
    base_pressure = 0.2

# Adjust for current performance vs market value
if underperforming (stats down >10%):
    base_pressure *= 1.2  # cap at 1.0
    
return min(base_pressure, 1.0)
```

#### `awardChaseFlag`:
```python
# Check if player is within reach of major award threshold
award_targets = {
    "All-NBA": {"ppg": 25.0, "rpg": 10.0, "apg": 8.0},
    "All-Defense": {"stl": 1.5, "blk": 1.5},
    "scoring_title": {"ppg": league_leader - 1.0}
}

for award, thresholds in award_targets.items():
    if within_reach(player_stats, thresholds, games_remaining):
        award_chase_flag = True
        award_target = f"{threshold} {stat} for {award}"
        break
```

#### `usageSpikeProb` (0.0-1.0):
```python
# Historical: contract year players in tank phase see +3.2% usage
base_prob = 0.5
if contract_pressure_index > 0.7:
    base_prob += 0.2
if team_tanking_score > 0.7:
    base_prob += 0.15
if recent_usage_trend > 1.05:  # already spiking
    base_prob += 0.15
    
return min(base_prob, 1.0)
```

#### `minutesCapProb` (0.0-1.0):
```python
# Returning from injury
if games_since_return < 5:
    return 0.8
elif games_since_return < 10:
    return 0.5
else:
    return 0.1
```

**Backtest Requirements:**
- Contract year performance boost (quantify PPG/RPG/APG delta vs career avg)
- Award chase stat inflation (players within 1.0 of threshold, last 10 games)
- Usage spike correlation with `contractPressureIndex` + `tankingScore`

---

### Module 3: Travel & Fatigue (`app/intelligence/travel_fatigue.py`)

**Responsibility:** Model effort decay from travel, schedule density, and situational fatigue.

**Outputs:**
```python
{
  "travel_fatigue_index": 0-100,
  "effort_decay_modifier": 0.8-1.0,
  "rest_advantage": -3 to +3 (days delta vs opponent)
}
```

**Inputs Required:**
- Back-to-back status (first night | second night | none)
- Road trip game number (1-7)
- Travel distance (miles since last game)
- Timezone change (hours delta)
- Tip-off time (early tip after late game?)
- Days rest (since last game)
- Opponent days rest

**Calculation Details:**

#### `travelFatigueIndex` (0-100, higher = more fatigued):
```python
fatigue = 0

# Back-to-back
if back_to_back_second_night:
    fatigue += 30

# Road trip accumulation
if road_trip_game > 3:
    fatigue += (road_trip_game - 3) * 8  # +8 per game after 3rd

# Travel distance
if miles_traveled > 1500:
    fatigue += 20
elif miles_traveled > 1000:
    fatigue += 10

# Timezone change
if timezone_delta >= 2:
    fatigue += 15

# Early tip-off after late game
if tip_hour < 13 and prev_game_end_hour > 22:
    fatigue += 20

return min(fatigue, 100)
```

#### `effortDecayModifier` (0.8-1.0):
```python
# Convert fatigue index to multiplier
modifier = 1.0 - (travel_fatigue_index / 500)
return max(modifier, 0.80)
```

**Application:**
```python
# Player prop expectation
base_expectation = 24.5  # points
adjusted = base_expectation * effort_decay_modifier
# If fatigue_index = 60, modifier = 0.88 → 24.5 * 0.88 = 21.6
```

**Backtest Requirements:**
- Historical performance delta on 2nd night of back-to-back (PPG, pace, 4Q scoring)
- Road trip fatigue curve (game 1 vs 5 vs 7)
- Cross-country travel impact on ATS/O-U (3+ hour timezone change)

---

### Module 4: Alignment Engine (`app/intelligence/alignment.py`)

**Responsibility:** Detect objective misalignment between team and player goals.

**Outputs:**
```python
{
  "alignment_type": "aligned" | "misaligned" | "chaos",
  "scenario": "team_tanking_player_contract_year" | None,
  "prop_volatility_adjustment": 0.8-1.5,
  "correlation_suggestions": [
    {"type": "player_over", "edge": 0.12},
    {"type": "team_under", "edge": 0.08}
  ]
}
```

**Inputs:**
- `team_competitive_state` (from Module 1)
- `player_incentive_profile` (from Module 2)

**Alignment Matrix:**

| Team State | Player State | Alignment | Behavior |
|------------|-------------|-----------|----------|
| Contending | Win-focused | Aligned | Stable, predictable |
| Contending | Contract year | Slight misalignment | Late-game usage spike |
| Tanking | Developing | Aligned | Rotation chaos (avoid) |
| Tanking | Contract year | **Misaligned** | Empty stats risk |
| Clinched | Any | Misaligned | Minutes suppression |
| Eliminated | Contract year | **Misaligned** | Stat inflation |

**Scenario Detection:**
```python
if team_state == "tanking" and contract_pressure > 0.7:
    scenario = "team_tanking_player_contract_year"
    alignment_type = "misaligned"
    prop_volatility_adjustment = 1.35
    correlation_suggestions = [
        {"type": "player_over", "edge": historical_boost},
        {"type": "team_under", "edge": historical_loss_rate}
    ]
```

**Historical Boost Calculation:**
```python
# Backtest: contract year players in tank phase (last 3 seasons)
contract_tank_games = filter(
    contract_year=True,
    team_tanking=True,
    games_remaining < 20
)
avg_ppg_boost = 2.1  # vs season average
edge = (avg_ppg_boost / prop_line) * confidence_factor
```

---

## Implementation Tickets

### DNA-1: Team State Module
**Effort:** 5 days  
**Deliverables:**
- `app/intelligence/team_state.py`
- Unit tests (15+ scenarios)
- Backtest validation (3 seasons)
- API endpoint: `GET /api/intelligence/team-state/{team_id}`

### DNA-2: Player Incentive Module
**Effort:** 5 days  
**Deliverables:**
- `app/intelligence/player_incentive.py`
- Unit tests (20+ scenarios)
- Backtest validation (contract year boost, award chase)
- API endpoint: `GET /api/intelligence/player-incentive/{player_id}`

### DNA-3: Travel & Fatigue Module
**Effort:** 3 days  
**Deliverables:**
- `app/intelligence/travel_fatigue.py`
- Unit tests (10+ scenarios)
- Backtest validation (back-to-back, road trip fatigue)
- API endpoint: `GET /api/intelligence/travel-fatigue/{game_id}`

### DNA-4: Alignment Engine
**Effort:** 4 days  
**Deliverables:**
- `app/intelligence/alignment.py`
- Unit tests (alignment matrix coverage)
- Backtest validation (misalignment edge)
- API endpoint: `GET /api/intelligence/alignment/{game_id}/{player_id}`

### DNA-5: Integration
**Effort:** 3 days  
**Deliverables:**
- Wire DNA modules into snapshot builder
- Add DNA features to protocol snapshots
- Update UI to display DNA signals
- Validation: compare DNA predictions vs actual outcomes (1 week forward test)

---

## Data Requirements

### New Data Sources Needed:
1. **Contract data:** Years remaining, UFA/RFA status, salary
2. **Award race tracking:** Real-time stat rankings vs thresholds
3. **Lineup tracking:** Starting lineup history (per game)
4. **Travel data:** Flight distance, timezone changes (can calculate from schedule)
5. **Tip-off times:** Game start times (local timezone)

### Existing Data (Already Have):
- Standings
- Injuries
- Game schedules
- Player stats (season, recent)

---

## Success Metrics

### Development Phase:
- ✅ All modules pass unit tests
- ✅ Backtest validation shows positive edge (>52% hit rate on flagged scenarios)
- ✅ API endpoints return stable data structure

### Production Phase (After 30 days):
- DNA-flagged bets hit rate > baseline (e.g., 55% vs 52%)
- Alignment engine correlation suggestions profitable (>3% ROI)
- Fatigue modifier improves prop accuracy (measured via hold-out test set)

---

## Related Documents
- `docs/architecture/DNA-SHERLOCK-division.md` — Architectural overview
- `docs/sprints/SHERLOCK-AUDIT-ENGINE-roadmap.md` — Audit layer implementation
- `docs/sprints/S-PROT-VISION-incentive-modeling.md` — Detailed incentive framework
