# ADR-2026-03-14 Restored Layered Architecture

**Status:** ACCEPTED  
**Date:** 2026-03-14

## Context

BetApp drifted into a mixed runtime where frontend templates, frontend JS, backend route shaping, and reasoning/data-layer concerns were partially blurred.

The project direction is not a two-repo split.

The project direction is one repo with hard internal boundaries.

## Decision

BetApp will be organized around these layers:

```text
Frontend
  ↓
Airlock
  ↓
Protocol Intent
  ↓
Sherlock
  ↕
DNA
  ↓
Governed output
  ↓
Frontend
```

Airlock is restored as the membrane.

Sherlock and DNA are distinct but conversationally linked layers.

## Consequences

- frontend work must target Airlock contracts
- Airlock becomes a first-class refactor target
- frontend/backend separation work is reframed as boundary restoration, not repo splitting
- future adaptive systems must preserve this layered model

## References

- `docs/architecture/SYSTEM_RESTORATION_BLUEPRINT.md`
- `docs/contracts/AIRLOCK_MEMBRANE_CONTRACT.md`
- `docs/contracts/SHERLOCK_DNA_INTERACTION_CONTRACT.md`
