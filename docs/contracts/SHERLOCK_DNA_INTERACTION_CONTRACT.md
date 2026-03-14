# Sherlock DNA Interaction Contract

**Version:** 1.0.0  
**Status:** CANONICAL  
**Last Updated:** 2026-03-14

## 1. Purpose

This contract defines how Sherlock and DNA interact in the restored architecture.

Sherlock and DNA are not a single blended engine.

They are distinct layers in a bounded conversation.

## 2. Layer Roles

## 2.1 DNA Matrix

DNA owns structured truth representation:

- entities
- attributes
- metrics
- events
- relationships
- derived features

DNA does not decide bets or recommendations.

## 2.2 Sherlock

Sherlock owns synthesis:

- interpreting the ask
- translating asks into data requirements
- requesting relevant DNA fragments
- weighing support and counterevidence
- producing conclusions, uncertainty, and failure modes

Sherlock does not persist canonical truth.

## 2.3 Protocols

Protocols are structured asks.

They compile a betting concept into data needs for Sherlock.

## 3. Canonical Query Model

Example protocol ask:

```text
LeBron James over points vs non-playoff team on back half of a back-to-back
```

Protocol-derived data requirements:

- player entity
- player role and usage
- player recent performance
- player fatigue context
- team state
- opponent state
- schedule state
- league state
- market state

Sherlock uses those requirements to query DNA.

## 4. DNA Exposure Model

DNA should expose information at multiple levels:

### Entity level

- player
- team
- game
- market
- league

### Attribute level

- age
- handedness
- health state
- role
- ranking
- team assignment
- motivation/incentive descriptors

### Metric level

- usage rate
- minutes
- offensive rating
- pace
- volatility
- hit rates

### Event level

- injury update
- lineup change
- trade
- rest day
- travel transition

### Derived feature level

- fatigue index
- stability score
- incentive profile
- matchup volatility
- protocol-relevant composite indicators

## 5. Sherlock Request Rules

Sherlock may request:

- named entities
- related entities
- attributes
- metrics
- events
- derived features
- time-bounded snapshots
- comparison slices

Sherlock must not request:

- raw database access
- unauthorized governance internals
- arbitrary ORM objects
- direct frontend-bound formatting

## 6. Recursion And Refinement

Sherlock may refine its request when initial DNA fragments are insufficient.

Example:

1. Sherlock requests player fatigue context.
2. DNA returns low-confidence availability state.
3. Sherlock requests supporting schedule and lineup volatility fragments.
4. Sherlock recomputes confidence and failure modes.

This is allowed.

Unbounded recursive wandering is not.

## 7. Output Rules

Sherlock returns:

- conclusion
- confidence
- support
- counterevidence
- failure modes
- recommended structural interpretation

Sherlock must not return:

- direct persistence operations
- unreviewed model mutations
- frontend-private formatting assumptions

## 8. DNA Rules

DNA must:

- expose structured fragments consistently
- preserve entity identity
- preserve provenance where possible
- avoid embedding narrative conclusions

DNA must not:

- generate recommendation copy
- override Sherlock conclusions
- invent protocol outcomes

## 9. Guardrails

Hard guardrails:

- Sherlock never writes canonical DNA state directly.
- DNA never writes reasoning conclusions directly.
- Protocols never skip Sherlock and turn directly into recommendations.
- Frontend never queries DNA directly.

Soft guardrails:

- prefer structured feature retrieval over narrative shortcuts
- prefer explicit provenance over hidden inferred leaps
- keep derived features explainable

## 10. Implications For Refactor Work

This contract implies:

- Airlock contracts should shape asks before Sherlock sees them
- frontend contracts should not bind directly to DNA structures
- protocol work should define data requirements explicitly
- future adaptive systems may tune weights and retrieval strategy, but not erase the Sherlock/DNA boundary
