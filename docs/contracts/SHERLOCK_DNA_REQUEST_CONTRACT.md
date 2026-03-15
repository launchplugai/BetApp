# Sherlock DNA Request Contract

**Version:** 1.0.0  
**Status:** CANONICAL  
**Last Updated:** 2026-03-15

## 1. Purpose

This contract defines the first thin Sherlock-facing request shape over current DNA fragments.

It exists to prevent protocol reasoning from reaching into ad hoc runtime state directly while the broader Sherlock ↔ DNA architecture is still being restored.

## 2. Scope

Current scope is intentionally narrow:

- NBA fatigue context
- NBA injury/availability context
- NBA pace/tempo context
- market sensitivity context

This is the first request bundle used by active Tier 1 protocol reasoning.

## 3. Request Shape

The request contains:

- `request_id`
- `protocol_bundle_id`
- `sport`
- `requirements`
- `assumptions`

Each requirement contains:

- `fragment_type`
- `rationale`
- `required`

## 4. First Active Bundle

Current active bundle:

```text
nba_fatigue_injury_pace_v1
```

Required fragments:

- `team_schedule_context`
- `player_availability`
- `game_tempo_context`
- `market_sensitivity`

## 5. Response Shape

The response contains:

- `request`
- `fragments`
- `missing_fragments`

This allows Sherlock-facing code and protocol code to:

- request only what is needed
- inspect what was resolved
- detect missing fragment coverage explicitly

## 6. Working Rule

Protocols may continue to contain local reasoning logic during migration.

But whenever a protocol needs cross-fragment context, it should prefer a Sherlock-facing request/response bundle over raw runtime field reads.

## 7. Guardrails

- requests do not expose raw persistence access
- requests do not bypass Airlock or frontend contracts
- requests do not replace core evaluation math
- requests remain additive until broader Sherlock orchestration is restored

## 8. Current Runtime Use

Current runtime use:

- `app/services/sherlock_dna_requests.py`
- `app/services/dna_protocols.py`

The first live path using this contract is the NBA fatigue/injury/pace protocol bundle.
