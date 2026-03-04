# S-PROT Vision: Proactive Protocol Discovery

**Status:** Vision document (not yet implemented)  
**Target:** Slice 4+ (after dashboard wiring complete)  
**Owner:** Ben  
**Date:** 2026-02-12

---

## Problem Statement

**Current state:**
- Protocols are **reactive** — user manually builds bet, then saves as protocol
- No discovery mechanism for opportunities matching user's strategy patterns
- Dashboard shows saved protocols but doesn't surface new edges

**Desired state:**
- Protocols are **proactive** — system finds bets matching user-defined patterns
- Dashboard highlights opportunities automatically
- User reviews DNA analysis → one-click to Builder with pre-filled legs

---

## Core Concept: Protocol Templates

### Two-Tier Protocol System

#### 1. Protocol Templates (Patterns/Filters)
User-defined criteria that describe a betting edge or strategy pattern.

**Examples:**

**"Home Dominance"**
```json
{
  "name": "Home Dominance",
  "sport": "NBA",
  "filters": {
    "home_win_pct": ">70%",
    "location": "home",
    "min_games_played": 10
  }
}
```

**"Back-to-Back Resilience"**
```json
{
  "name": "Back-to-Back Resilience",
  "sport": "NBA",
  "filters": {
    "back_to_back": "second_night",
    "back_to_back_win_pct": ">60%",
    "injury_status": "healthy"
  }
}
```

**"High Variance Fade"**
```json
{
  "name": "High Variance Fade",
  "sport": "NBA",
  "filters": {
    "team_variance": "high",
    "public_betting_pct": ">65%",
    "line_movement": "fading"
  }
}
```

**"Injury Bounce-Back"**
```json
{
  "name": "Injury Bounce-Back",
  "sport": "NBA",
  "filters": {
    "star_player_return": true,
    "games_missed": ">=5",
    "historical_return_performance": "positive"
  }
}
```

#### 2. Protocol Instances (Specific Bets)
Concrete bets that match a template, with DNA analysis attached.

**Example:**
- Template: "Home Dominance"
- Instance: "Lakers @ Crypto.com Arena vs Warriors, 2026-02-12"
  - Home win %: 76%
  - DNA confidence: 82% structural
  - Fragility: Low
  - User action: Review → Save → Submit

---

## User Workflow

### Setup Phase
1. User creates protocol templates in Dashboard
2. Defines filters (sport, team criteria, situational patterns)
3. Enables auto-discovery (optional)

### Discovery Phase
1. Background job runs every N minutes (or on-demand)
2. Scans upcoming games for matches
3. Generates "opportunities" feed
4. Surfaces in Dashboard

### Review Phase
1. User opens Dashboard
2. Sees "3 games match Home Dominance protocol today"
3. Clicks opportunity → Builder pre-fills with suggested legs
4. DNA engine runs analysis
5. User reviews confidence, fragility, correlations
6. User refines or submits as-is

### Learning Phase
1. User tracks which templates generate winning bets
2. Adjusts filters to improve edge
3. Templates evolve based on real outcomes

---

## Dashboard Enhancement

### Current (Post-Slice 2A)
- **Active Protocols** section (user-created saved bets)
- Empty protocol feed

### With Proactive Discovery
**New sections:**

#### 1. "Opportunities" Panel
```
🎯 3 games match your protocols today

Home Dominance (2)
  • Lakers vs Warriors (76% home win rate, fully healthy)
  • Celtics vs Heat (82% home win rate, line value detected)

Back-to-Back Resilience (1)
  • Nuggets @ Suns (2nd night, 68% B2B win rate)
```

#### 2. "Protocol Templates" Panel
```
Your Active Templates (4)
  • Home Dominance (2 opportunities today)
  • Back-to-Back Resilience (1 opportunity)
  • Injury Bounce-Back (0 opportunities)
  • High Variance Fade (inactive)

[+ Create New Template]
```

#### 3. "Recent Matches" Panel
```
Protocols That Hit This Week
  • Home Dominance: 3-1 (75% win rate)
  • Back-to-Back Resilience: 2-0 (100%)
  • Injury Bounce-Back: 1-2 (33% — consider adjusting filters)
```

---

## Technical Architecture

### Database Schema

#### `protocol_templates` table
```sql
CREATE TABLE protocol_templates (
  id UUID PRIMARY KEY,
  user_id UUID NOT NULL,
  name VARCHAR(255) NOT NULL,
  sport VARCHAR(50) NOT NULL,
  filters JSONB NOT NULL,  -- Structured filter criteria
  auto_discover BOOLEAN DEFAULT true,
  created_at TIMESTAMP,
  updated_at TIMESTAMP
);
```

#### `protocol_opportunities` table
```sql
CREATE TABLE protocol_opportunities (
  id UUID PRIMARY KEY,
  template_id UUID REFERENCES protocol_templates(id),
  game_id VARCHAR(255) NOT NULL,
  discovered_at TIMESTAMP,
  expires_at TIMESTAMP,  -- Game start time
  match_score FLOAT,     -- How well it matches filters (0-1)
  viewed BOOLEAN DEFAULT false,
  dismissed BOOLEAN DEFAULT false
);
```

### Background Job: Discovery Engine

**Frequency:** Every 15 minutes (or on-demand via Dashboard button)

**Algorithm:**
1. Fetch all active protocol templates
2. Query odds API for upcoming games (next 48 hours)
3. Fetch supplementary data:
   - Team stats (home/away splits, back-to-back records)
   - Injury reports (player availability)
   - Historical performance patterns
   - Line movement data
4. For each game, check against each template's filters
5. Generate match score (0-1, how well it fits)
6. Store opportunities with match_score >= 0.7
7. Trigger dashboard refresh

### API Endpoints

#### `GET /api/protocol/templates`
Returns user's saved protocol templates.

#### `POST /api/protocol/templates`
Create new protocol template.

#### `GET /api/protocol/opportunities`
Returns active opportunities (games matching user's templates).

#### `POST /api/protocol/opportunities/{id}/build`
Pre-fill Builder with opportunity legs, redirect to Builder.

#### `POST /api/protocol/opportunities/{id}/dismiss`
Mark opportunity as dismissed (hide from feed).

---

## Filter Types (Extensible)

### Team Performance Filters
- `home_win_pct`: Home win percentage threshold
- `away_win_pct`: Away win percentage threshold
- `back_to_back_win_pct`: Performance on 2nd night of back-to-backs
- `vs_spread_pct`: ATS (against the spread) win rate
- `ou_pct`: Over/under hit rate

### Situational Filters
- `back_to_back`: Boolean or "first_night" / "second_night"
- `rest_days`: Minimum rest days since last game
- `travel_distance`: Miles traveled (for fatigue signals)
- `time_zone_change`: Boolean (cross-country travel)

### Roster Health Filters
- `injury_status`: "healthy" / "key_player_out" / "rotation_player_out"
- `star_player_return`: Boolean (returning from 5+ game absence)
- `games_missed`: Number of games star missed

### Variance / Value Filters
- `team_variance`: "high" / "medium" / "low" (performance volatility)
- `public_betting_pct`: Public money percentage (fade or follow)
- `line_movement`: "moving_up" / "moving_down" / "stable"
- `sharp_money_indicator`: Boolean (reverse line movement)

### Correlation Filters (Advanced)
- `same_game_multi`: Allow multiple props from same game
- `same_player_multi`: Allow multiple props for same player
- `correlation_risk`: "low" / "medium" / "high"

---

## Example Templates (Starter Pack)

### 1. Home Court Advantage
**Strategy:** Target teams with dominant home records.

```json
{
  "name": "Home Court Advantage",
  "sport": "NBA",
  "filters": {
    "home_win_pct": ">70%",
    "location": "home",
    "min_games_played": 10,
    "opponent_away_win_pct": "<45%"
  }
}
```

### 2. Revenge Game Edge
**Strategy:** Teams playing opponents who beat them recently.

```json
{
  "name": "Revenge Game",
  "sport": "NBA",
  "filters": {
    "recent_loss_to_opponent": "within_30_days",
    "team_win_pct": ">55%",
    "location": "home",
    "injury_status": "healthy"
  }
}
```

### 3. Rested Favorites
**Strategy:** Good teams with rest advantage.

```json
{
  "name": "Rested Favorites",
  "sport": "NBA",
  "filters": {
    "team_win_pct": ">60%",
    "rest_days": ">=2",
    "opponent_back_to_back": true,
    "spread": "<=-5"
  }
}
```

### 4. Playoff Push
**Strategy:** Teams fighting for playoff seeding in final weeks.

```json
{
  "name": "Playoff Push",
  "sport": "NBA",
  "filters": {
    "games_remaining": "<=10",
    "playoff_position": "6-10_seed",
    "opponent_playoff_position": "eliminated",
    "injury_status": "healthy"
  }
}
```

---

## Implementation Phases

### Phase 1: Template CRUD (Slice 4A)
- Database schema for templates
- API endpoints for create/read/update/delete
- Basic UI in Dashboard for managing templates

### Phase 2: Discovery Engine (Slice 4B)
- Background job scaffold
- Integration with odds API + team stats
- Match scoring algorithm
- Store opportunities in DB

### Phase 3: Dashboard Integration (Slice 4C)
- "Opportunities" panel in Dashboard
- Click-through to Builder with pre-filled legs
- Dismiss/view tracking

### Phase 4: Learning Loop (Slice 4D)
- Track which templates generate wins
- Surface template performance metrics
- Suggest filter adjustments based on outcomes

### Phase 5: Advanced Filters (Slice 4E)
- Line movement tracking
- Sharp money indicators
- Correlation detection
- Public betting percentages

---

## Success Metrics

### Discovery Accuracy
- **Match quality:** % of opportunities user engages with (view + build)
- **Conversion rate:** % of opportunities that become submitted bets
- **Win rate:** % of template-generated bets that win

### User Engagement
- **Template creation:** # of templates per active user
- **Opportunity views:** # of opportunities viewed per day
- **Builder pre-fill usage:** % of Builder sessions starting from opportunity

### Strategic Value
- **Template ROI:** Win rate of template-based bets vs manual bets
- **Edge persistence:** Do templates maintain edge over time?
- **Template evolution:** % of users refining templates based on outcomes

---

## Open Questions

1. **How often should discovery run?**
   - Every 15 min? Hourly? On-demand only?

2. **How many opportunities to surface at once?**
   - Top 3? Top 10? Show all matches?

3. **Should templates auto-disable if they lose money?**
   - Or just flag for user review?

4. **How to handle overlapping templates?**
   - Same game matches multiple templates — show once or multiple times?

5. **Should templates be shareable?**
   - "Copy Ben's Home Dominance template" feature?

---

## Related Documents
- `docs/PRD.md` — Product requirements
- `docs/adr/ADR-001-protocol-primary-surface.md` — Protocol architecture decision
- `docs/sprints/S-PROT-4-completion-report.md` — Dashboard foundation work

---

**Next Steps:**
- Review with Ben (validate vision)
- Prioritize within sprint backlog (after Slice 2B/3 complete)
- Break into concrete tickets (Slice 4A-E)
