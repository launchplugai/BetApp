# DECISION_LOG.md
# Architectural Decision Log

**Status:** APPEND-ONLY
**Last Updated:** 2026-01-29

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

<!--
To add a new decision:
1. Add a new section at the bottom (before this comment)
2. Follow the format above
3. Link to relevant documents
4. Commit with message: "docs: add decision - [title]"
-->
