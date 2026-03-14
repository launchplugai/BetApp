# Architecture Restoration Sprint Map

**Status:** CANONICAL  
**Last Updated:** 2026-03-14

This sprint map defines the refactor path required to restore the BetApp architecture without stalling product momentum.

## 1. Objective

Restore the architecture to:

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

## 2. Working Rules

- one repo
- hard module walls
- additive migration over rewrite
- contracts before scaffolds
- no new frontend surface that bypasses Airlock
- no adaptive layer that bypasses governance

## 3. Sprint Sequence

## Sprint A: Canonize The Architecture

**Status:** COMPLETE

Deliverables:

- system restoration blueprint
- Airlock membrane contract
- Sherlock DNA interaction contract
- ADRs for the pivot
- decision log entry

Exit criteria:

- docs indexed
- future work has a stable bootstrap pack

## Sprint B: Restore Airlock As Membrane

**Status:** COMPLETE

Deliverables:

- audit current `app/airlock.py`
- map current frontend-facing routes to Airlock responsibilities
- identify missing normalization and output shaping seams
- define explicit builder handoff through Airlock

Exit criteria:

- Airlock role is no longer “validator only” in active implementation planning
- route-by-route gap list exists

## Sprint C: Freeze Sherlock ↔ DNA Boundary

**Status:** COMPLETE

Deliverables:

- inventory current Sherlock calls and DNA touchpoints
- map protocol asks to DNA data requirements
- define the first query/fragment interfaces

Exit criteria:

- Sherlock and DNA no longer treated as a single blended backend concern

## Sprint D: Normalize Frontend-Facing Contracts

**Status:** NEXT

Deliverables:

- normalize evaluate payload
- normalize OCR review payload
- normalize builder handoff payload
- normalize history replay payload

Exit criteria:

- frontend-safe contracts are explicit
- legacy additive fields documented as compatibility only

## Sprint E: Reconcile Active Evaluate Frontend

Deliverables:

- identify one active Evaluate surface
- remove duplicate ownership between templates and JS
- make OCR trust gate and Evaluate result hierarchy coherent

Exit criteria:

- frontend source-of-truth is singular for Evaluate

## Sprint F: Introduce Dedicated Frontend Module

Deliverables:

- scaffold `frontend/`
- build Evaluate against frozen Airlock contracts
- keep legacy templates as fallback only

Exit criteria:

- first frontend slice works without backend-template coupling

## Sprint G: Migrate Builder And History

Deliverables:

- Builder refinement loop
- before/after delta
- history replay and learning flow

Exit criteria:

- Evaluate → Builder → History works through the new boundary

## Sprint H: Governed Adaptation

Deliverables:

- expand calibration analyzer
- proposal-driven tuning
- safe research/learning loop

Exit criteria:

- adaptation improves the system without erasing contracts or layer boundaries

## 4. Guardrails

Do not:

- scaffold frontend before contract normalization work starts
- let frontend talk directly to Sherlock or DNA internals
- teach the system to mutate itself before architecture is stable
- collapse Sherlock and DNA into one “model” bucket
- let Airlock become optional

## 5. Bootstrap Pack

Every future implementation thread should start from:

- `docs/ops/BOOTSTRAP_PROTOCOL.md`
- `docs/ops/CURRENT_EXECUTION_STATE.md`
- `docs/architecture/SYSTEM_RESTORATION_BLUEPRINT.md`
- `docs/contracts/AIRLOCK_MEMBRANE_CONTRACT.md`
- `docs/contracts/SHERLOCK_DNA_INTERACTION_CONTRACT.md`
- `docs/ops/ARCHITECTURE_RESTORATION_SPRINT_MAP.md`
- `docs/contracts/FRONTEND_SPLIT_CONTRACT_FREEZE_CHECKLIST.md`
