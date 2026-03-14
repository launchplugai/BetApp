# Protocol DNA Requirement Map v1

**Version:** 1.0.0  
**Status:** CANONICAL  
**Last Updated:** 2026-03-14

This contract maps active Tier 1 protocols to the structured DNA fragments they conceptually require.

It is the execution bridge between:

- protocol intent
- Sherlock data requirements
- DNA fragment retrieval

## 1. Purpose

Protocols should not remain forever as free-floating heuristics over whatever runtime state happens to be nearby.

This map defines what each protocol is actually asking for.

## 2. Tier 1 Protocol Requirement Table

| Protocol | Current Runtime Inputs | Required DNA Fragment Types | First Vertical Slice Status |
|----------|------------------------|-----------------------------|-----------------------------|
| `fatigue_back_to_back` | NBA heuristics summary, risk flags | team schedule context, rest state, travel state | `READY` |
| `structure_leg_count_risk` | leg count | slip structure fragment | `READY` |
| `structure_correlation_risk` | correlation count, correlation penalty | slip structure fragment, leg relationship fragment | `READY` |
| `matchup_pace_mismatch` | markets detected, same-game count, heuristics summary | game tempo context, market sensitivity fragment | `READY` |
| `matchup_injury_instability` | context modifiers, missing data, injury language | player availability fragment, team lineup stability fragment | `READY` |

## 3. Fragment Types

## 3.1 Slip Structure Fragment

Represents:

- leg count
- same-game concentration
- correlation count
- correlation penalty
- market mix

## 3.2 Team Schedule Context Fragment

Represents:

- rest days
- back-to-back state
- games in rolling windows
- travel burden
- time zone transitions

## 3.3 Player Availability Fragment

Represents:

- injury/availability state
- confidence of availability signal
- negative impact modifiers
- missing-data fallback indicators

## 3.4 Team Lineup Stability Fragment

Represents:

- lineup uncertainty
- rotation instability
- availability-driven volatility

## 3.5 Game Tempo Context Fragment

Represents:

- pace environment
- pace mismatch
- same-game tempo sensitivity
- context summary for explanation

## 3.6 Market Sensitivity Fragment

Represents:

- whether a market is pace-sensitive
- whether a slip structure is volatility-sensitive

## 4. Working Rule

Protocols may continue using current runtime data during migration.

But each protocol should be progressively refactored to request these fragment types explicitly.

## 5. Guardrails

- protocols do not query raw persistence directly
- protocols do not receive arbitrary backend internals
- fragment types should remain explainable
- this map should expand only as real protocol needs justify it
