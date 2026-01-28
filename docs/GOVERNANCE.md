# GOVERNANCE ENFORCEMENT

**Status:** ENFORCED
**Date Established:** 2026-01-27
**Authority:** Product Owner Decision

---

## 1. RALPH_LOOP (Authoritative)

```
Build → Validate → Explain → Observe → Adjust → Lock
```

Each phase must complete before advancing:

| Phase | Gate |
|-------|------|
| **Build** | Code compiles, tests pass |
| **Validate** | Working endpoint responds correctly |
| **Explain** | Output maps to real engine signals |
| **Observe** | Behavior confirmed in staging/prod |
| **Adjust** | Edge cases handled, no regressions |
| **Lock** | Feature documented, sprint advances |

**Lock** is a mandatory checkpoint that blocks further sprint advancement. A sprint cannot advance to the next until a formal Lock artifact has been produced, reviewed, and committed. Lock is not implicit — it requires an explicit document (e.g., `SPRINT_1_LOCK.md`) and product owner approval.

---

## 2. Sprint Advancement Rules

No sprint advances without:

- A Sprint Lock document committed to `docs/`
- Explicit product owner approval noted in the lock document

Additional rules:

- Features built early do NOT automatically advance sprint count.
- The presence of code related to a future sprint does not mean that sprint has started.
- Sprint status is determined by lock artifacts, not by code existence.
- Each sprint's Definition of Done must be fully satisfied before lock.

---

## 3. Claude Operating Rules

Claude operates under the following constraints at all times:

**Claude may only execute active sprint tickets.**

Claude must refuse:

- Feature additions without a ticket
- Sprint scope expansion mid-ticket
- Code changes outside the scope of the current ticket
- Modifications to locked engine logic
- Speculative or "nice to have" additions

Claude must ask for clarification instead of guessing when:

- A task's sprint assignment is ambiguous
- A requested change could affect engine logic
- A ticket's scope appears to conflict with governance rules
- Any deliverable is unclear or underspecified

**Escalation protocol:** If Claude identifies work that may be needed but falls outside the current ticket or sprint scope, Claude must document the observation and stop. Claude does not self-assign work.

---

## Amendment Policy

This governance document is **LOCKED**. Changes require:

1. Explicit product owner approval
2. Documented rationale
3. Impact assessment on active and future sprints

No exceptions.
