# DECISION_LOG.md
# Architectural Decision Log

**Status:** APPEND-ONLY
**Last Updated:** 2026-03-14

---

## Format

Each decision entry follows this format:

```
## [DATE] Decision Title

**Context:** Why this decision was needed
**Decision:** What was decided
**Consequences:** What this means going forward
**References:** Related documents/tickets
```

---

## Decisions

---

### 2026-01-29 Sherlock Implemented as Library Module (v1)

**Context:**
The system needs a truth-finding/investigation engine to evaluate claims before they affect DNA Matrix state. Options considered:
1. External microservice with network calls
2. Inline code mixed with app logic
3. Standalone library module in-repo

**Decision:**
Sherlock is implemented as a standalone library module in this repository (`sherlock/`).

Key constraints:
- No network calls (deterministic, testable)
- No state mutation (pure functions)
- No external dependencies beyond Pydantic
- Integration is contract-first (see `docs/contracts/`)

**Consequences:**
- Sherlock can be tested in isolation
- Same input always produces same output (deterministic)
- Integration with DNA Matrix follows explicit contracts
- Future versions may extract to separate package, but contracts remain stable
- All Sherlock changes require contract review

**References:**
- `sherlock/` - Implementation
- `docs/contracts/SCH_SDK_CONTRACT.md` - Library contract
- `docs/contracts/SYSTEM_CONTRACT_SDS.md` - Integration contract
- `docs/mappings/MAP_SHERLOCK_TO_DNA.md` - Translation rules
- Ticket 16A - Sherlock skeleton implementation
- Ticket 16B - Contract documentation

---

### 2026-03-14 Restore Layered Architecture Around Airlock

**Context:**
The repo drifted toward a mixed runtime where frontend templates, frontend JS, backend route shaping, Airlock responsibilities, and Sherlock/DNA concerns were partially blurred. Product direction clarified that the goal is one repo with hard internal module walls, not a two-repo split.

**Decision:**
BetApp is now canonically organized around:

`Frontend -> Airlock -> Protocol Intent -> Sherlock <-> DNA -> governed output -> Frontend`

Key constraints:
- Airlock is restored as the membrane, not just a validator
- Sherlock and DNA are distinct layers in a bounded conversation
- frontend work must target Airlock contracts, not backend-private payloads
- adaptive improvement must preserve these boundaries

**Consequences:**
- frontend/backend separation work is reframed as boundary restoration
- Airlock becomes a first-class refactor target
- Sherlock and DNA must be refactored as explicit adjacent layers
- future adaptation work must wait for boundary restoration, not bypass it

**References:**
- `docs/architecture/SYSTEM_RESTORATION_BLUEPRINT.md`
- `docs/contracts/AIRLOCK_MEMBRANE_CONTRACT.md`
- `docs/contracts/SHERLOCK_DNA_INTERACTION_CONTRACT.md`
- `docs/ops/ARCHITECTURE_RESTORATION_SPRINT_MAP.md`
- `docs/adr/ADR-2026-03-14-restored-layered-architecture.md`
- `docs/adr/ADR-2026-03-14-governed-adaptation-after-boundary-restoration.md`

---

### 2026-03-14 Canonical Bootstrap And Context Lock

**Context:**
BetApp now spans enough architecture, governance, UX, and refactor state that chat memory is not a safe primary handoff surface. Older sprint/session docs can conflict with the current restoration path if an agent starts from the wrong place.

**Decision:**
BetApp now uses a canonical bootstrap and context-lock process.

Canonical bootstrap entrypoint:
- `docs/ops/BOOTSTRAP_PROTOCOL.md`

Canonical state pair:
- `docs/ops/CONTEXT_LOCK_PROTOCOL.md`
- `docs/ops/CURRENT_EXECUTION_STATE.md`

**Consequences:**
- new chats and reconnects must start from the canonical bootstrap path
- sprint state is locked into repo docs and local git, not only conversation history
- old sprint/session docs are historical unless explicitly referenced

**References:**
- `docs/ops/BOOTSTRAP_PROTOCOL.md`
- `docs/ops/CONTEXT_LOCK_PROTOCOL.md`
- `docs/ops/CURRENT_EXECUTION_STATE.md`
- `docs/adr/ADR-2026-03-14-canonical-bootstrap-and-context-lock.md`

---

<!--
To add a new decision:
1. Add a new section at the bottom (before this comment)
2. Follow the format above
3. Link to relevant documents
4. Commit with message: "docs: add decision - [title]"
-->
