# DNA Bet Engine — Revised Execution Plan

## Version: v0.4.0
## Date: 2026-02-08
## Status: ACTIVE — BUILD PHASE
## Scope: Protocol → Parlay Builder → DNA → Live Data

---

## 1. REVISED THREE-SPRINT BLOCK (LOCKED)

### Sprint S16 — Protocol + Parlay Builder v1 (FOUNDATION)
Objective: User can select an event, build a parlay visually, and analyze it via DNA.
- No auth
- No wallets
- No persistence
- Mock data only
- Backend evaluation unchanged

---

### Sprint S17 — Live-Ready Data + Intelligence Layer (INTELLIGENCE ENTRY)
Objective: Protocol tracks games and surfaces advisory suggestions.
- Live-compatible data adapters
- DNA-driven suggestions (read-only)
- No auto-betting
- No notifications yet

---

### Sprint S18 — Dashboard + User State (PRODUCTIZATION)
Objective: System becomes a product with memory, stats, and tiers.
- User accounts
- History
- Metrics
- Tier gating

---

## 2. SPRINT S16 — TASK BREAKDOWN (DETERMINISTIC)

### S16-A: Protocol (Event Target Selection)

#### UI
- League selector (NBA only)
- Event cards (mock JSON)
- Featured event
- AI Insight strip (static text)

#### Data Object
```json
{
  "protocolId": "uuid",
  "league": "NBA",
  "gameId": "lal-gsw-2026-02-08",
  "teams": ["Lakers", "Warriors"],
  "status": "LIVE",
  "clock": "Q3 8:42",
  "score": {
    "home": 88,
    "away": 82
  },
  "marketsAvailable": ["spread", "total", "player_props"]
}
```

#### Acceptance Criteria
- Clicking "SELECT EVENT TARGET" routes to Parlay Builder
- ProtocolContext is passed intact
- No backend writes
- No persistence

---

### S16-B: Parlay Builder v1

#### UI
- Market tabs (Main Lines, Player Props)
- Odds grid (mock)
- Parlay slip (add/remove)
- Wager input
- Total odds + payout calculation

#### Canonical Leg Schema
```json
{
  "market": "spread",
  "team": "Lakers",
  "line": -4.5,
  "odds": -110
}
```

#### Logic
- Prevent duplicate/conflicting legs
- Recalculate odds on every mutation
- UI enforces constraints (no backend validation required)

#### Acceptance Criteria
- Zero typing required
- Add/remove leg updates totals instantly
- Builder state is deterministic

---

### S16-C: Builder → DNA Integration

#### API Call
```http
POST /app/evaluate
{
  "input": "Lakers -4.5 + LeBron O25.5",
  "tier": "good",
  "legs": [
    {
      "market": "spread",
      "team": "Lakers",
      "line": -4.5
    },
    {
      "market": "player_prop",
      "player": "LeBron James",
      "prop": "points",
      "line": 25.5
    }
  ]
}
```

#### Acceptance Criteria
- DNA response renders successfully
- No regression in analysis quality
- Existing endpoints unchanged

---

## 3. SPRINT S17 — LIVE-READY DATA + SUGGESTIONS

### S17-A: Live Data Ingestion (START IMMEDIATELY)

#### Interfaces
```typescript
interface OddsProvider {
  getOdds(gameId: string): OddsResponse;
}

interface ScoreProvider {
  getScore(gameId: string): ScoreResponse;
}
```

#### Implementation
- MockProvider implements both interfaces
- Live providers plug in later without UI changes

---

### S17-B: Protocol Tracking

#### In-Memory Structure
```json
{
  "protocolId": "uuid",
  "gameId": "lal-gsw-2026-02-08",
  "marketsWatched": ["spread", "player_props"],
  "createdAt": "timestamp"
}
```

- No persistence
- No user binding yet

---

### S17-C: DNA Suggestions (Read-Only)

#### Behavior
- DNA observes odds/score deltas
- Emits advisory signals only

#### UI Examples
- "Spread tightening rapidly"
- "Player minutes spike detected"

#### Constraints
- No auto-add legs
- No forced actions
- User always opts in

---

## 4. SPRINT S18 — DASHBOARD + USER STATE

### S18-A: User Accounts
- Email/password auth
- Preferences
- Protocol ownership

### S18-B: Dashboard Metrics
- Total protocols
- Win rate
- Recent analyses
- Active protocols

### S18-C: Tier Gating
- GOOD / BETTER / BEST
- Feature flags only
- No branching analysis logic

---

## 5. PROTOCOL → BUILDER → DNA PIPELINE (CANONICAL)

### Lifecycle
```
CREATE PROTOCOL → LOCK CONTEXT → BUILD PARLAY → ANALYZE (DNA) → OBSERVE (S17+) → SUGGEST (OPTIONAL)
```

### Rules
- Builder never discovers data
- Protocol owns context
- DNA is stateless
- Suggestions are advisory
- No hidden side effects

---

## 6. LIVE DATA INGESTION — SAFETY RULES

### DO NOW
- Build adapters
- Normalize schemas
- Mock responses

### DO NOT YET
- No API keys
- No aggressive polling
- No uptime dependency

### Target Providers (Later)
- Odds: The Odds API / SportsDataIO
- Scores: SportsDataIO / Sportradar

### Architecture
```
[Live API]
    ↓
[Provider Adapter]
    ↓
[Normalizer]
    ↓
[Protocol Observer]
    ↓
[DNA Suggestions]
```

UI remains fully decoupled.

---

## 7. LOCKED NON-GOALS (IMPORTANT)

- No bet execution
- No wallets
- No money movement
- No auto-betting
- No regulatory exposure

---

## 8. FINAL STATE CHECK

This plan is successful when:
- Builder is usable without DNA
- DNA multiplies value when added
- Live data enhances, not destabilizes
- Dashboard summarizes reality, not guesses

---

**STATUS:** READY TO IMPLEMENT  
**NEXT STEP:** Convert S16 into sprint tickets with estimates and tests
