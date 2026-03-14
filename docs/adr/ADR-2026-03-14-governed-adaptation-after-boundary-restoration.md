# ADR-2026-03-14 Governed Adaptation After Boundary Restoration

**Status:** ACCEPTED  
**Date:** 2026-03-14

## Context

BetApp is intended to improve over time through calibration, protocol tuning, and governed learning behavior.

There is interest in `autoresearch`-style iterative improvement systems.

That is valuable only if the system boundaries are already trustworthy.

## Decision

BetApp will not implement a self-improving research loop ahead of Airlock restoration and Sherlock ↔ DNA boundary clarification.

Adaptive improvement is allowed only after:

- Airlock contracts are explicit
- Sherlock ↔ DNA interaction is explicit
- frontend-facing contracts are normalized
- governed learning guardrails remain in force

## Consequences

- no premature self-modifying or self-rewriting loop
- calibration and governed learning continue, but within the existing proposal/review/promotion model
- future experimentation must improve the system without erasing explainability or layer boundaries

## References

- `docs/contracts/LEARNING_SYSTEM_V1.md`
- `docs/contracts/AIRLOCK_MEMBRANE_CONTRACT.md`
- `docs/contracts/SHERLOCK_DNA_INTERACTION_CONTRACT.md`
- `docs/ops/ARCHITECTURE_RESTORATION_SPRINT_MAP.md`
