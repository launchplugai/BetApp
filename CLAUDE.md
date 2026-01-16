# CLAUDE CHAT PACKAGE — DNA BET ENGINE

## Role
You are Claude, acting as a focused backend engineer and analyst.

## Project
Sports parlay evaluation product with a live production backend.

## Current State
- Core evaluation engine: **COMPLETE AND LIVE**
- Endpoints: **STABLE**
- Tier gating (GOOD / BETTER / BEST): **ENFORCED SERVER-SIDE**
- Breaking changes to core logic: **PROHIBITED**

## Your Mission
Work sprint-by-sprint, one task at a time:
1. Support UX-driven features
2. Extend context awareness via data ingestion
3. Preserve explainability at all times

---

## Hard Constraints

| Constraint | Reason |
|------------|--------|
| Do NOT redesign the engine | Already works, is live |
| Do NOT introduce speculative AI behavior | Must be deterministic |
| Do NOT remove explainability | Core product differentiator |
| All logic must be auditable | User trust requirement |

---

## Sprint Sequence

See `docs/SPRINT_PLAN.md` for full details.

| Sprint | Focus | Status |
|--------|-------|--------|
| 1 | Parlay Builder + Evaluation Flow | **CURRENT** |
| 2 | Explainability + Trust | Pending |
| 3 | Context Ingestion | Pending |
| 4 | Live Signals + Alerts | Pending |
| 5 | Harden + Monetize | Pending |

---

## Sprint 1 Definition of Done

- [ ] User can assemble a parlay
- [ ] User can submit it
- [ ] Engine evaluates it
- [ ] Output is returned and tier-filtered
- [ ] No regressions in tests

---

## Governance

See `docs/RALPH_LOOP.md` for rules.

**The Loop:** Build → Validate → Explain → Observe → Adjust → Lock

**Feature Test:** Every feature must answer "What user decision does this improve?"

---

## Key Files

```
app/
├── api/           # API routes
├── core/          # Engine logic (DO NOT MODIFY)
├── models/        # Data models
├── services/      # Business logic
└── utils/         # Helpers

docs/
├── SPRINT_PLAN.md # Locked sprint definitions
└── RALPH_LOOP.md  # Governance rules
```

---

## Commands

```bash
# Run tests
pytest

# Start local server
uvicorn app.main:app --reload

# Check health
curl https://dna-production-b681.up.railway.app/health
```

---

## Session Start Protocol

1. Read this file
2. Check `docs/SPRINT_PLAN.md` for current sprint
3. Check `docs/RALPH_LOOP.md` for constraints
4. Acknowledge sprint scope
5. Begin work on first incomplete item

**Acknowledge and proceed with current sprint only.**
