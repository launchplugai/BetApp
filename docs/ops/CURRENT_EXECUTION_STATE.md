# Current Execution State

**Status:** ACTIVE  
**Last Updated:** 2026-03-15

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

Finished Sprint D by normalizing the history replay contract through Airlock
and restoring `/app/history` compatibility aliases for the mounted workbench.

Completed in:

- `app/airlock.py`
- `app/schemas/frontend_contracts.py`
- `app/routers/history.py`
- `app/tests/test_airlock.py`
- `app/tests/test_frontend_contracts.py`
- `docs/contracts/FRONTEND_SPLIT_CONTRACT_FREEZE_CHECKLIST.md`
- `docs/ops/ARCHITECTURE_RESTORATION_SPRINT_MAP.md`

## 3. Current Architecture State

Completed restoration milestones:

- Sprint A: architecture canonized
- Sprint B: Airlock minimum viable membrane restored for Evaluate
- Sprint C: Sherlock ↔ DNA boundary documented and first fragment seam implemented
- Sprint D: frontend-facing contracts normalized for the first slice

Current runtime truth:

- Airlock owns a real outbound Evaluate seam
- Evaluate emits explicit `builderHandoff`
- Tier 1 protocols can run from explicit DNA fragments
- pipeline builds and passes protocol fragments explicitly
- Sherlock-facing request/response shape now exists for the NBA fatigue/injury/pace bundle
- live Sherlock hook now carries bounded protocol-aware context for the NBA fatigue/injury/pace bundle
- explainability output now exposes that protocol context as a normalized summary block
- final verdict now includes a user-facing protocol context note when Sherlock context is active
- `next_action` can now point users to schedule/availability/pace context when that bundle is active
- Builder handoff now carries a user-safe `protocolContextNote` through Airlock
- Builder workbench now renders that `protocolContextNote` in a compact refinement card
- Builder Fastest Fix reasoning now incorporates the protocol-context note directly
- history list and replay detail now have Airlock-shaped frontend contracts
- `/app/history` and `/app/history/{item_id}` now resolve to the canonical history router

## 4. Latest Validation

Command:

```bash
cd /Users/benaiahross/development/projects/betapp/app-src && \
.venv312/bin/pytest app/tests/test_airlock.py app/tests/test_frontend_contracts.py -q
```

Result:

```text
38 passed
```

## 5. Known Debt

- protocols still contain local reasoning logic after request resolution
- Sherlock hook carries protocol-aware context, but the broader Sherlock engine still does not perform fragment refinement cycles
- persisted bet-history outputs are still separate from the in-memory replay/history contract
- broad legacy UI tests still contain historical expectations and are not sprint gates

## 6. Exact Next Step

Start Sprint E: reconcile the active Evaluate frontend so there is one clear
source of truth for Evaluate/OCR behavior instead of split workbench ownership.

Recommended first slice:

- audit the mounted `/app` history/evaluate workbench JS against the canonical `/app?screen=*` screen set and identify what still owns live Evaluate behavior

## 7. Bootstrap Docs For Next Chat

Read in this order:

1. `docs/ops/BOOTSTRAP_PROTOCOL.md`
2. `docs/index/DOC_INDEX.md`
3. `docs/ops/CURRENT_EXECUTION_STATE.md`
4. `docs/architecture/SYSTEM_RESTORATION_BLUEPRINT.md`
5. `docs/contracts/AIRLOCK_MEMBRANE_CONTRACT.md`
6. `docs/contracts/SHERLOCK_DNA_INTERACTION_CONTRACT.md`
7. `docs/contracts/SHERLOCK_DNA_REQUEST_CONTRACT.md`
8. `docs/architecture/SHERLOCK_DNA_TOUCHPOINT_AUDIT.md`
9. `docs/contracts/PROTOCOL_DNA_REQUIREMENT_MAP_V1.md`
10. `docs/ops/ARCHITECTURE_RESTORATION_SPRINT_MAP.md`
