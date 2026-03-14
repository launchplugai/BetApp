# Current Execution State

**Status:** ACTIVE  
**Last Updated:** 2026-03-14

## 1. Current Objective

Restore the layered architecture in a way that is testable in live runtime code:

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

## 2. Most Recent Completed Slice

Tier 1 protocol runtime now consumes explicit DNA fragments first, with runtime fallback preserved.

Completed in:

- `app/services/dna_fragments.py`
- `app/services/dna_protocols.py`
- `app/pipeline.py`
- `app/tests/test_dna_fragments.py`
- `app/tests/test_dna_protocols.py`
- `app/tests/test_pipeline.py`

## 3. Current Architecture State

Completed restoration milestones:

- Sprint A: architecture canonized
- Sprint B: Airlock minimum viable membrane restored for Evaluate
- Sprint C: Sherlock ↔ DNA boundary documented and first fragment seam implemented

Current runtime truth:

- Airlock owns a real outbound Evaluate seam
- Evaluate emits explicit `builderHandoff`
- Tier 1 protocols can run from explicit DNA fragments
- pipeline builds and passes protocol fragments explicitly
- Sherlock is still not actively issuing fragment requests

## 4. Latest Validation

Command:

```bash
cd /Users/benaiahross/development/projects/betapp/app-src && \
.venv312/bin/pytest app/tests/test_dna_fragments.py app/tests/test_dna_protocols.py app/tests/test_pipeline.py -q
```

Result:

```text
73 passed
```

## 5. Known Debt

- protocols still contain local reasoning logic instead of asking Sherlock-style questions
- Sherlock is still mostly a bounded integration hook, not a live fragment requester
- bet/history outputs are not yet fully membrane-shaped
- broad legacy UI tests still contain historical expectations and are not sprint gates

## 6. Exact Next Step

Add a thin Sherlock-facing request shape on top of the current DNA fragments and route one real protocol path through it.

Recommended first slice:

- fatigue/injury/pace request bundle for NBA protocol reasoning

## 7. Bootstrap Docs For Next Chat

Read in this order:

1. `docs/ops/BOOTSTRAP_PROTOCOL.md`
2. `docs/index/DOC_INDEX.md`
3. `docs/ops/CURRENT_EXECUTION_STATE.md`
4. `docs/architecture/SYSTEM_RESTORATION_BLUEPRINT.md`
5. `docs/contracts/AIRLOCK_MEMBRANE_CONTRACT.md`
6. `docs/contracts/SHERLOCK_DNA_INTERACTION_CONTRACT.md`
7. `docs/architecture/SHERLOCK_DNA_TOUCHPOINT_AUDIT.md`
8. `docs/contracts/PROTOCOL_DNA_REQUIREMENT_MAP_V1.md`
9. `docs/ops/ARCHITECTURE_RESTORATION_SPRINT_MAP.md`
