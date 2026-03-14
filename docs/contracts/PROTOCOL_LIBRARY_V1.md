# PROTOCOL_LIBRARY_V1.md
# Protocol Library v1 Contract

**Version:** 1.0.0
**Status:** CANONICAL
**Last Updated:** 2026-03-08

---

## 1. Purpose

This contract defines the first canonical protocol library for DNA Matrix / BetApp.

Protocols are lightweight betting intelligence detectors that identify contextual risk, structural weakness, and market anomalies around a bet or parlay.

If the scoring model is the core evaluator, protocols are the fast pattern-recognition layer that says:

> "Something about this bet deserves extra caution or attention."

### 1.1 Product Role

Protocols exist to help users:

- catch hidden risk they might miss
- understand why a slip is fragile
- surface context faster than manual research
- improve betting judgment over time

### 1.2 Non-Goals

Protocols do NOT:

- guarantee bet outcomes
- replace the baseline probability model
- silently modify the user's bet
- function as a black-box pick generator

---

## 2. Relationship To DNA Scoring

This contract is subordinate to [DNA_SCORING_MODEL.md](/Users/benaiahross/development/projects/betapp/app-src/docs/contracts/DNA_SCORING_MODEL.md).

**Invariant:** Protocols MUST NOT override DNA Core probability.

Protocols MAY adjust:

- `fragility`
- `stability`
- contextual volatility annotations
- user-facing evidence and explanation

Protocols SHOULD NOT directly mutate baseline model probability except in a future version with an explicit contract change.

---

## 3. Protocol Schema

Each protocol implementation MUST conform conceptually to this shape:

```json
{
  "id": "string",
  "name": "string",
  "category": "schedule_fatigue | structural_parlay | market_intelligence | matchup | environmental",
  "version": "1.0.0",
  "enabled": true,
  "triggered": false,
  "trigger_confidence": 0.0,
  "impacts": {
    "stability_delta": 0,
    "fragility_delta": 0,
    "edge_delta": 0,
    "volatility_delta": 0
  },
  "evidence": [],
  "metadata": {}
}
```

### 3.1 Required Fields

- `id`: stable machine identifier
- `name`: user-facing name
- `category`: protocol group
- `triggered`: whether the protocol fired
- `trigger_confidence`: confidence in the protocol trigger itself
- `impacts`: bounded score deltas
- `evidence`: surfaced facts or explanations

### 3.2 Output Invariant

If a protocol fires, the system MUST be able to explain:

1. why it triggered
2. what evidence it used
3. how it affected score output

---

## 4. Categories

Protocol Library v1 contains 20 protocols grouped into five categories:

1. Schedule & Fatigue
2. Structural Parlay
3. Market Intelligence
4. Matchup
5. Environmental

---

## 5. Schedule & Fatigue Protocols

These protocols detect fatigue and travel-related stress that may reduce performance reliability.

### 5.1 Back-to-Back Fatigue

- `id`: `fatigue_back_to_back`
- Purpose: detect zero-rest scheduling disadvantage
- Trigger:
  - team played on the previous calendar day
- Impact:
  - `stability_delta = -8`
  - `fragility_delta = +5`
- Evidence:
  - `"Team playing on zero rest."`

### 5.2 Travel Stress

- `id`: `fatigue_travel_stress`
- Purpose: detect short-turn travel burden
- Trigger:
  - travel distance greater than 800 miles within 24 hours
- Impact:
  - `stability_delta = -6`
- Evidence:
  - `"Long travel window between games."`

### 5.3 Time Zone Shift

- `id`: `fatigue_time_zone_shift`
- Purpose: detect circadian disruption
- Trigger:
  - current game is in a different time zone than the team's previous game
- Impact:
  - `stability_delta = -3`
- Evidence:
  - `"Circadian rhythm disruption."`

### 5.4 Third Game In Four Nights

- `id`: `fatigue_third_in_four`
- Purpose: detect compressed schedule accumulation
- Trigger:
  - team has played three games within four days
- Impact:
  - `stability_delta = -7`
  - `fragility_delta = +4`
- Evidence:
  - `"Compressed schedule load: third game in four nights."`

### 5.5 Altitude Adjustment

- `id`: `fatigue_altitude_adjustment`
- Purpose: detect environmental conditioning disadvantage
- Trigger:
  - visiting team is playing in an altitude venue
- Impact:
  - `stability_delta = -4`
- Evidence:
  - `"Visiting team entering altitude environment."`

---

## 6. Structural Parlay Protocols

These protocols detect common structural reasons parlays fail.

### 6.1 Leg Count Risk

- `id`: `structure_leg_count_risk`
- Purpose: penalize excessive parlay complexity
- Trigger:
  - parlay contains more than 4 legs
- Impact:
  - `fragility_delta = +8` per leg above 4
- Evidence:
  - `"Parlay complexity increases failure probability."`

### 6.2 Correlation Risk

- `id`: `structure_correlation_risk`
- Purpose: detect legs that depend on shared game conditions
- Trigger:
  - two or more legs depend on the same or tightly linked game environment
- Example:
  - team spread + game under
- Impact:
  - `fragility_delta = +10`
- Evidence:
  - `"Multiple legs depend on the same game conditions."`

### 6.3 Same-Game Variance Stack

- `id`: `structure_same_game_variance_stack`
- Purpose: detect stacked same-game exposure
- Trigger:
  - multiple props originate from the same game
- Impact:
  - `fragility_delta = +7`
- Evidence:
  - `"Same-game exposure concentrates variance."`

### 6.4 High-Volatility Prop

- `id`: `structure_high_volatility_prop`
- Purpose: identify props with historically unstable outcomes
- Trigger:
  - prop belongs to a high-variance market
- Examples:
  - first basket
  - long-shot props
- Impact:
  - `fragility_delta = +6`
- Evidence:
  - `"This prop type has historically high variance."`

### 6.5 Long Odds Stack

- `id`: `structure_long_odds_stack`
- Purpose: detect compounded long-shot exposure
- Trigger:
  - multiple legs have odds above `+200`
- Impact:
  - `fragility_delta = +8`
- Evidence:
  - `"Multiple long-odds legs stack failure probability."`

---

## 7. Market Intelligence Protocols

These protocols detect useful market behavior that may influence risk or value interpretation.

### 7.1 Sharp Line Movement

- `id`: `market_sharp_line_movement`
- Purpose: detect movement that may indicate professional action
- Trigger:
  - line moves materially against public betting direction
- Impact:
  - `edge_delta = +6` when movement supports the bet thesis
  - MAY emit warning-oriented evidence when movement is negative
- Evidence:
  - `"Market movement suggests professional betting activity."`

### 7.2 Public Money Trap

- `id`: `market_public_money_trap`
- Purpose: detect crowded public positioning with adverse market response
- Trigger:
  - public betting is heavy but line moves in the opposite direction
- Impact:
  - `fragility_delta = +5`
- Evidence:
  - `"Public positioning conflicts with line movement."`

### 7.3 Book Disagreement

- `id`: `market_book_disagreement`
- Purpose: detect pricing dispersion across sportsbooks
- Trigger:
  - large odds spread exists across books for the same market
- Impact:
  - `edge_delta = +4`
- Evidence:
  - `"Sportsbooks disagree materially on this market."`

### 7.4 Line Freeze

- `id`: `market_line_freeze`
- Purpose: detect suspiciously static pricing under active betting conditions
- Trigger:
  - line remains unchanged despite meaningful betting activity
- Impact:
  - `fragility_delta = +4`
- Evidence:
  - `"Line remains frozen despite market activity."`

---

## 8. Matchup Protocols

These protocols analyze gameplay and matchup dynamics relevant to the slip.

### 8.1 Pace Mismatch

- `id`: `matchup_pace_mismatch`
- Purpose: detect tempo-driven volatility
- Trigger:
  - large difference exists between team pace metrics
- Impact:
  - `volatility_delta = +5`
- Evidence:
  - `"Possession tempo mismatch increases scoring variance."`

### 8.2 Defensive Mismatch

- `id`: `matchup_defensive_mismatch`
- Purpose: detect exploitable strength-vs-weakness setup
- Trigger:
  - strong offense or player role faces a weak relevant defense
- Impact:
  - `edge_delta = +5`
- Evidence:
  - `"Defensive matchup may create value in this market."`

### 8.3 Player Usage Spike

- `id`: `matchup_player_usage_spike`
- Purpose: detect role expansion after an absence or limitation
- Trigger:
  - star player is out, limited, or removed from expected workload
- Impact:
  - `edge_delta = +6` for qualifying replacement or volume-linked props
- Evidence:
  - `"Projected usage increase due to teammate absence or limitation."`

### 8.4 Injury Instability

- `id`: `matchup_injury_instability`
- Purpose: detect uncertainty caused by questionable or unstable availability
- Trigger:
  - key player is questionable, returning uncertainly, or lineup status is unstable
- Impact:
  - `stability_delta = -7`
  - `fragility_delta = +5`
- Evidence:
  - `"Key availability uncertainty may destabilize this market."`

---

## 9. Environmental Protocols

These protocols detect external factors that can alter game behavior or user perception of risk.

### 9.1 Referee Bias Pattern

- `id`: `environment_referee_bias_pattern`
- Purpose: detect officiating tendencies that may increase variance
- Trigger:
  - officiating crew historically produces materially elevated foul or whistle patterns
- Impact:
  - `volatility_delta = +4`
- Evidence:
  - `"Officiating profile may increase variance in this game environment."`

### 9.2 Revenge Game Narrative

- `id`: `environment_revenge_game_narrative`
- Purpose: track a low-weight narrative factor users care about
- Trigger:
  - player is facing a former team within a meaningful recent window after a move
- Impact:
  - `edge_delta = +3`
- Evidence:
  - `"Player is facing a recent former team."`

**Policy:** This protocol is low-weight and MUST remain subordinate to statistical and structural signals.

---

## 10. Protocol Output Contract

When protocols fire, downstream systems SHOULD receive payloads in this form:

```json
{
  "triggeredProtocols": [
    {
      "id": "fatigue_back_to_back",
      "name": "Back-to-Back Fatigue",
      "category": "schedule_fatigue",
      "trigger_confidence": 0.84,
      "impact": {
        "stability_delta": -8,
        "fragility_delta": 5,
        "edge_delta": 0,
        "volatility_delta": 0
      },
      "evidence": [
        "Team played yesterday",
        "Travel distance 950 miles"
      ]
    }
  ]
}
```

### 10.1 Binding Requirements

- protocol IDs MUST be machine-stable
- impacts MUST be explicit
- evidence MUST be user-displayable
- trigger confidence MUST reflect confidence in the trigger, not confidence in the bet

---

## 11. Launch Priority

Not all 20 protocols MUST ship on day one.

### 11.1 Tier 1 Launch Set

These SHOULD be prioritized first:

1. `fatigue_back_to_back`
2. `structure_leg_count_risk`
3. `structure_correlation_risk`
4. `matchup_pace_mismatch`
5. `matchup_injury_instability`

These cover the largest share of common bettor mistakes and trust-critical warnings.

### 11.2 Tier 2

- `fatigue_travel_stress`
- `market_sharp_line_movement`
- `market_book_disagreement`
- `matchup_player_usage_spike`
- `market_public_money_trap`

### 11.3 Tier 3

- referee tendencies
- narrative protocols
- more advanced correlation logic

---

## 12. Weight Tuning

Protocol weights in v1 are initial defaults, not permanently frozen truth.

### 12.1 Tuning Rules

- protocol weights MUST be versioned
- weight changes SHOULD be based on logged outcomes and calibration review
- high-noise narrative protocols SHOULD remain low-impact unless evidence supports promotion

### 12.2 Calibration Intent

Over time the protocol system SHOULD produce:

- logged trigger frequency
- score impact history
- confidence bucket comparisons
- protocol usefulness metrics

---

## 13. User-Facing Explanation Rules

When a protocol materially affects scoring, the UI or explanation layer SHOULD surface:

- the protocol name
- the reason it triggered
- the relevant evidence
- the directional score effect where helpful

Example:

> "Back-to-back fatigue lowered stability because the team is playing on zero rest."

### 13.1 Explanation Guardrail

Protocols MUST sound like evidence-based heuristics, not superstition.

Narrative protocols MAY exist, but they MUST remain clearly low-weight and secondary.

---

## 14. Guardrails

The protocol system MUST obey these rules:

### 14.1 No Probability Override

Protocols MUST NOT silently replace DNA Core probability.

### 14.2 No Hidden Impact

If a protocol meaningfully affects output, it MUST be loggable and explainable.

### 14.3 No Silent Bet Mutation

Protocols MAY suggest simplification or caution. They MUST NOT rewrite user intent.

### 14.4 No Fluff Inflation

Low-signal narrative protocols MUST remain low weight and secondary to real data.

---

## 15. Future Expansion

This contract is compatible with future additions such as:

- user-created protocols
- protocol templates and discovery feeds
- protocol registries with dynamic weighting
- real-time triggers
- protocol performance dashboards

Future work MUST preserve the scoring-model invariant that protocols modify context-sensitive risk, not hidden core probability.

---

## 16. Invariants

```
INVARIANT: Protocols are contextual detectors, not guaranteed predictors.
INVARIANT: Protocols MUST NOT silently override DNA Core probability.
INVARIANT: Every fired protocol MUST have evidence and explicit impact.
INVARIANT: Trigger confidence refers to the protocol trigger, not the bet outcome.
INVARIANT: Structural and fatigue protocols SHOULD be prioritized before narrative protocols.
```
