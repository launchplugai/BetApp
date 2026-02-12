# DNA ↔ Sherlock Division of Labor

**Status:** Architectural vision  
**Date:** 2026-02-12  
**Context:** Incentive modeling + structural intelligence architecture

---

## The Problem

Betting markets price **ability**. They underprice **motivation asymmetry**.

- Ability is stable (season averages, historical performance)
- Motivation shifts faster than lines adjust (contract year, tanking, award chase)

**Edge lives in incentive misalignment.**

But if you manually inject narrative every day, the system becomes "vibes engine v4."

**Solution:** Structured intelligence with validation.

---

## The Clean Division

### DNA = Structured State + Signals

**Role:** Turn the messy world into computable variables.

**DNA does NOT decide bets.**  
DNA creates the **feature layer** — stable, computable variables the engine can reason with.

**Output Example:**
```json
{
  "teamCompetitiveState": "tanking",
  "playoffPressureIndex": 12,
  "rotationStabilityScore": 34,
  "tankingScore": 0.85,
  "travelFatigueIndex": 68,
  "rookieRampTrend": "increasing",
  "minutesVolatility": 72,
  "playerIncentiveProfile": {
    "contractYear": true,
    "awardChase": false,
    "roleSecurity": "low",
    "usageSpikeProb": 0.78
  }
}
```

**DNA says:** "Usage spike probability is 0.78, tanking score is 0.85, alignment is misaligned."

**DNA does NOT say:** "Bet the over."

---

### Sherlock = Claim Audit + Anti-Narrative Engine

**Role:** Stop the system (and you) from lying to yourself. Politely, but firmly.

**Sherlock does NOT decide bets.**  
Sherlock validates claims with evidence, counterevidence, confidence, and failure modes.

**Output Example:**
```json
{
  "claim": "Team is tanking",
  "support": [
    "Rookie minutes up 18% (last 10 games)",
    "Veteran DNP spike (3 rest games in 2 weeks)",
    "Lineup entropy high (14 different starting lineups in 15 games)"
  ],
  "counter": [
    "Coach quote: 'We're competing every night'",
    "Recent close games (3 of last 5 within 5 points)",
    "Star player still playing 38 MPG"
  ],
  "confidence": 0.72,
  "recommendation": "Apply volatility penalty. Avoid unders on player minutes. Consider player-over + team-loss correlation.",
  "failureModes": [
    "Star injury could stabilize rotation",
    "Trade deadline acquisition could shift incentives",
    "Coach firing could reset competitive stance"
  ]
}
```

**Sherlock says:** "Here's the evidence. Here's what contradicts it. Here's how confident you should be. Here's how it could go wrong."

---

## The Workflow (End-to-End)

### Pipeline:

**1. DNA ingests data**
- Schedule (back-to-backs, road trips, travel distance, timezone changes)
- Standings context (playoff position, elimination date, clinch date)
- Injuries (who's out, who's returning, minutes cap expectations)
- Rotations (minutes trends, lineup stability, rookie ramp patterns)
- Player contracts (years remaining, UFA/RFA status, contract value)
- Award races (current stats vs thresholds, e.g., 25 PPG for All-NBA)

**2. DNA computes indices**
- `playoffPressureIndex` (0-100)
- `tankingScore` (0-1)
- `rotationStabilityScore` (0-100)
- `travelFatigueIndex` (0-100)
- `playerIncentiveProfile` (contract year, award chase, role security)
- `minutesVolatility` (0-100)
- `effortDecayModifier` (0.8-1.0)

**3. Sherlock audits claims**
- "This team is tanking" → Evidence? Counterevidence? Confidence?
- "Player is chasing stats" → Support? Contradictions? Failure modes?
- "This is an effort spot" → Signals? What could invalidate this?

**4. Bet engine consumes both**
- DNA features → Adjust expected value
- Sherlock audit → Adjust confidence + show receipts
- Output: Recommendation with explainability

---

## Where the Edge Lives

### Markets Price:
- Baseline performance (season averages)
- Obvious injuries
- Simple rest (back-to-back)

### Markets Underprice:
- **Objective misalignment** (team wants X, player wants Y)
- **Rotation entropy** (late-season chaos, tanking rotations)
- **Late-season incentives** (contract year stat inflation, award chase spikes)
- **Effort decay** (travel fatigue, "get on the plane" games, cross-country trips)

### Your System Detects:
- DNA → Surfaces the signals
- Sherlock → Validates they're real (not narrative)
- Bet engine → Quantifies edge

**That's the moat.**

---

## Example Output (User-Facing)

**Bet Recommendation:**
```
📊 Player Prop: Cade Cunningham Over 23.5 Points

Confidence: 78% (Structural)
Edge: +2.1 points above line

🧬 DNA Signals:
• Contract year (UFA summer 2026)
• Team tanking (score: 0.85)
• Usage spike probability: 0.78
• Rotation stability: LOW (34/100)
• Alignment: MISALIGNED (team lose, player stats)

🔍 Sherlock Audit:
✅ Support:
  • Rookie minutes up 18% (developing young core)
  • Veteran DNP spike (3 rest games in 2 weeks)
  • Cunningham usage +4.2% in tank phase (last 8 games)

⚠️ Counter:
  • Coach publicly committed to "competing"
  • Team won 2 of last 3 (could stabilize)

💡 Recommendation:
Player Over 23.5 + Team Loss correlation bet (if available)

🚨 Failure Modes:
• Blowout loss (garbage time suppression)
• Surprise veteran return (usage dilution)
• Coach firing (resets tank incentive)

Confidence: 72% after audit
```

---

## Anti-Narrative Rule

**You cannot manually inject narrative every day.**

If you do, the system becomes "Ben vibes engine v4."

**Solution:** Coefficients, not commentary.

### Wrong Way (Narrative):
"Pistons are tanking, avoid their props."

### Right Way (Structural):
```python
# Historical validation
tank_phase_games = games_where(
    playoff_eliminated=True,
    games_remaining < 20
)

# Calculate effect size
prop_hit_rate_normal = 0.52
prop_hit_rate_tank = 0.47
delta = -0.05  # 5% worse

# Tank score becomes coefficient
if tanking_score > 0.7:
    prop_confidence *= (1 + delta)
```

**Backtest everything:**
- Historical ATS delta for eliminated teams (last 15 games)
- Prop hit rate during tank phases
- Minutes volatility increase % in final 20 games for eliminated teams
- Contract year performance boost (quantify it)

**Turn instinct into coefficients.**

---

## The Core Principle

**DNA writes the feature vector.**  
**Sherlock writes the audit note.**  
**Bet engine consumes both.**

No vibes. No guessing. Just structured intelligence with receipts.

---

## Related Documents
- `docs/sprints/DNA-FEATURE-LAYER-roadmap.md` — Implementation plan for DNA modules
- `docs/sprints/SHERLOCK-AUDIT-ENGINE-roadmap.md` — Implementation plan for Sherlock audit system
- `docs/sprints/S-PROT-VISION-incentive-modeling.md` — Detailed incentive modeling framework
- `docs/sprints/S-PROT-VISION-proactive-discovery.md` — Protocol template discovery system
