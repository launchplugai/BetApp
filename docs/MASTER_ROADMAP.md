# DNA / BetApp Master Roadmap

*Strategic blueprint from stability to intelligence to strategic edge*

---

## PHASE 0 — INFRA STABILITY (NOW)

**Goal:** System does not crash. Data flows. Degraded mode works.

**Deliverables:**
- ✅ Odds API 200 responses
- ✅ Degraded mode fallback
- ✅ No 500s from external failure
- ✅ Canonical production URL
- ⬜ Runbook
- ⬜ Updated CLAUDE.md

**Definition of Done:** Browse games works even if API fails.

---

## PHASE 1 — DATA INTELLIGENCE FOUNDATION

Move beyond "it runs." Build the statistical backbone.

### Sprint 1 — Advanced Statistical Ingestion

**Goal:** Move from raw odds to context-aware analytics.

**Implement:**

**NBA:**
- Pace
- Offensive Rating
- Defensive Rating
- Net Rating
- Rest days
- Back-to-back flag
- Injury impact proxy

**NFL:**
- EPA/play
- Success rate
- Pace
- Injury starters impact
- Weather flag
- Line movement delta tracking
- Closing line tracking (optional)

**Architecture:**
```
Raw Odds
    ↓
Statistical Enrichment Layer
    ↓
Structured GameContext Object
```

No AI yet. Just structured signal enrichment.

---

### Sprint 2 — Heuristic Engine (Pre-DNA)

System stops being a spreadsheet.

**Build Heuristic Signals:**
- Pace shock
- Rest asymmetry
- Injury leverage
- Tank probability
- Playoff leverage
- Public betting skew
- Line freeze anomaly

**Each heuristic returns:**
```json
{
  "name": "rest_asymmetry",
  "score": 0.72,
  "explanation": "...",
  "volatility_impact": "medium"
}
```

No final verdict. Just signals.

---

## PHASE 2 — DNA STRUCTURAL INTELLIGENCE

Activate the actual genetic layer.

### Sprint 3 — DNA Matrix v2 (Structural Risk Model)

DNA is not prediction. DNA measures:
- Correlation between legs
- Volatility stacking
- Fragility score
- Structural redundancy
- Exposure overlap

**Each parlay becomes:**
```json
DNAProfile: {
  "fragility_score": 0.0-1.0,
  "correlation_index": 0.0-1.0,
  "volatility_density": 0.0-1.0,
  "grounding_score": 0.0-1.0,
  "risk_classification": "low|medium|high|extreme"
}
```

Deterministic math + heuristics. No "AI guessing."

---

### Sprint 4 — Sherlock Expansion

Sherlock explains why. Sherlock must:
- Explain heuristic triggers
- Explain DNA fragility drivers
- Identify weakest leg
- Simulate "remove this leg" delta
- Compare structural changes

**Sherlock Loop:**
```
Evaluate → Inspect → Remove → Re-evaluate → Compare
```

Sherlock becomes an auditor, not a predictor.

---

## PHASE 3 — STRATEGIC EDGE LAYER

Now it becomes powerful.

### Sprint 5 — Probability Matrix Engine

Introduce:
- Monte Carlo simulation
- Historical matchup weighting
- Line movement impact modeling
- Injury scenario modeling
- Pace shift simulation

**Produces:**
```json
probability_matrix: {
  "base_win_probability": 0.0-1.0,
  "scenario_adjusted_probability": 0.0-1.0,
  "variance_band": "low|medium|high",
  "confidence_index": 0.0-1.0
}
```

---

### Sprint 6 — Portfolio Intelligence

Stop evaluating single parlays. Evaluate portfolio risk:
- Correlated exposure across bets
- Team concentration risk
- League volatility risk
- Time window stacking risk

**This is where subscriptions become premium.**

---

## PHASE 4 — REAL-TIME EDGE SIGNALS

The elite tier.

### Sprint 7 — Real-Time Pattern Detection

- Whistle shift
- Pace shock
- Foul trouble leverage
- In-game live adjustments

**Requires:**
- Live feed ingestion
- Event diff engine
- Threshold triggers

**Best-tier only.**

---

## PHASE 5 — MACHINE AUGMENTATION (Optional)

Careful here. Only after deterministic systems are strong.

Add:
- Model-assisted probability refinement
- Pattern recognition across seasons
- Adaptive threshold tuning

**Always:** AI assists. DNA + heuristics decide.

---

## 🔬 Heuristic Categories (Explicitly Defined)

Ralph needs structure. Here it is.

### 1. Volatility Heuristics
- Pace variance
- 3PT reliance
- Injury dependency

### 2. Structural Risk Heuristics
- Same team exposure
- Same game stacking
- High-correlation legs

### 3. Situational Heuristics
- Rest mismatch
- Travel
- Short week
- Weather

### 4. Market Heuristics
- Reverse line movement
- Public % skew
- Line freeze

---

## 🧠 DNA vs Sherlock Roles (Crystal Clear)

| Component | Responsibility |
|-----------|----------------|
| Heuristics | Detect signals |
| DNA | Measure structure + fragility |
| Sherlock | Explain + simulate changes |
| Probability Engine | Model outcome variance |
| Portfolio Engine | Evaluate cross-bet exposure |

No overlap. No confusion.

---

## 🗺 PRIORITY ORDER

1. **Phase 0** — Data stability (finish)
2. **Phase 1** — Advanced stat ingestion
3. **Phase 2** — Heuristic engine
4. **Phase 3** — DNA structural refinement
5. **Phase 4** — Probability modeling
6. **Phase 5** — Portfolio intelligence

**Discipline:** Do NOT jump to Monte Carlo before heuristics exist. Do NOT add AI before deterministic signals are correct.

---

## 🧭 Next Sprint (After Phase 0)

**Sprint: Advanced Statistical Ingestion Layer**

- Create `analytics/enrichment.py`
- Define `GameContext` schema
- Integrate pace, rating, rest, injury flags
- Return enriched game object

No UI changes yet. Just foundation.

---

## Final Discipline Reminder

You are building a: **Risk Intelligence Engine**, not a sportsbook clone.

Structure first. Signals second. Simulation third. AI last.

---

*Document created: 2026-02-21*  
*Phase: 0 (In Progress)*
