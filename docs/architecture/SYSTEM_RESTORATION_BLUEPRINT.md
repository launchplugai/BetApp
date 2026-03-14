# System Restoration Blueprint

**Status:** CANONICAL  
**Last Updated:** 2026-03-14

This document canonizes the current architecture pivot.

BetApp is not being reorganized into two repos.

BetApp is being restored into one repository with hard internal module walls:

```text
Frontend
  ↓
Airlock
  ↓
Protocol Intent Layer
  ↓
Sherlock Synthesis Layer
  ↕
DNA Matrix Ontology / State Layer
  ↓
Governed output back through Airlock
  ↓
Frontend
```

## 1. Why This Pivot Exists

The repo drifted into a mixed runtime where:

- frontend behavior is split across overlapping templates and JS
- backend routes shape payloads for specific screens
- Airlock has shrunk into input normalization instead of acting as a membrane
- Sherlock and DNA are documented conceptually but not enforced as a conversational boundary

That shape is good enough to ship features, but weak for long-term product quality.

The restored architecture exists to:

- make the backend rock-solid
- make the frontend replaceable and evolvable
- keep Sherlock reasoning separate from DNA state
- keep protocols as structured asks instead of ad hoc UI logic
- create a governed path for future adaptive improvement

## 2. Canonical Module Model

## 2.1 Frontend Module

Owns:

- screens
- navigation
- client state
- OCR review experience
- Evaluate result hierarchy
- Builder refinement UX
- History replay UX

Must not own:

- scoring logic
- protocol trigger logic
- entity truth state
- direct persistence decisions

## 2.2 Airlock Module

Owns:

- request intake
- normalization
- sanitization
- schema enforcement
- authorization between layers
- outbound shaping
- audit trail for cross-layer movement

Airlock is the membrane.

Nothing user-facing should talk directly to backend internals without passing through it.

## 2.3 Protocol Intent Layer

Owns:

- protocol definitions
- protocol trigger recipes
- conversion of a betting ask into data requirements

Protocols are not raw data and not final reasoning.

They are structured asks.

## 2.4 Sherlock Synthesis Layer

Owns:

- interpreting the ask
- deciding what evidence is needed
- requesting DNA fragments
- weighing support and counterevidence
- producing conclusions, uncertainty, and failure modes

Sherlock must not become a hidden persistence layer.

## 2.5 DNA Matrix Layer

Owns:

- canonical entity/state representation
- structured attributes
- metrics
- events
- derived features
- ontology-level organization of facts

DNA does not decide bets.

DNA exposes the organism map that Sherlock reasons over.

## 2.6 Governance Layer

Owns:

- model registry
- evaluation logs
- learning proposals
- promotions
- rollback
- calibration reporting

Governance does not bypass Airlock, Sherlock, or DNA.

It governs changes to their behavior.

## 3. Core Directionality

The restored system is not a simple one-way pipeline.

It is a bounded conversation:

```text
Frontend request
→ Airlock normalizes and authorizes
→ Protocol intent identifies the ask
→ Sherlock requests relevant DNA fragments
→ DNA returns structured facts
→ Sherlock synthesizes and may refine its request
→ Sherlock returns a reasoned conclusion
→ Airlock sanitizes and shapes the output
→ Frontend renders the result
```

## 4. Canonical Example

User intent:

```text
LeBron James over points vs non-playoff team on the second night of a back-to-back
```

Flow:

1. Airlock normalizes the ask.
2. Protocol intent compiles the ask into data needs.
3. Sherlock requests:
   - player attributes for LeBron James
   - current team state
   - opponent state
   - schedule state
   - market state
   - league context
4. DNA returns structured fragments.
5. Sherlock weighs those fragments and produces:
   - support
   - counterevidence
   - confidence
   - failure modes
   - recommended structural interpretation
6. Airlock shapes that into frontend-safe output.

## 5. Guardrails

## 5.1 Hard Guardrails

- Frontend must not depend on backend-private payload fields.
- Airlock is the only sanctioned cross-layer membrane.
- Sherlock must not persist state directly.
- DNA must not invent reasoning or recommendations.
- Protocols must not bypass Sherlock by turning directly into frontend conclusions.
- Learning systems must not rewrite layer boundaries.

## 5.2 Soft Guardrails

- Prefer additive migrations over rewrites.
- Keep legacy template flows only as fallback during parity periods.
- Do not build new UX directly on top of duplicated frontend ownership.
- Freeze contracts before building a new frontend surface.

## 6. Implementation Order

1. Restore the architecture in docs and ADRs.
2. Re-expand Airlock from validator to membrane contract.
3. Freeze the Sherlock ↔ DNA interaction contract.
4. Normalize frontend-facing contracts through Airlock.
5. Reconcile active Evaluate frontend ownership.
6. Create the dedicated frontend module against the Airlock boundary.
7. Migrate Evaluate first, then Builder, then History.
8. Add governed adaptive improvement only after the architecture is stable.

## 7. Relationship To Existing Docs

This document supersedes the looser framing that treated the current move primarily as a generic frontend/backend split.

Read with:

- `docs/contracts/SYSTEM_CONTRACT_SDS.md`
- `docs/architecture/DNA-SHERLOCK-division.md`
- `docs/contracts/AIRLOCK_MEMBRANE_CONTRACT.md`
- `docs/contracts/SHERLOCK_DNA_INTERACTION_CONTRACT.md`
- `docs/ops/ARCHITECTURE_RESTORATION_SPRINT_MAP.md`
