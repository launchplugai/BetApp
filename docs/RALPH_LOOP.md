# RALPH LOOP (LOCKED GOVERNANCE)

**Status:** ENFORCED
**Date Locked:** 2026-01-16

---

## The Loop

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

---

## Sprint Advancement Rules

No sprint advances without:
- [ ] Working endpoint
- [ ] Visible UI proof
- [ ] Clear explanation mapping
- [ ] All tests passing

---

## Refactor Policy

**No refactors unless something is broken.**

If you think something needs refactoring:
1. Document the breakage
2. Propose minimal fix
3. Get approval before executing

"Clean code" is not a justification. "It works" is the standard.

---

## Feature Qualification Test

Every new feature must answer:

> "What user decision does this improve?"

If a feature can't answer that question clearly, it doesn't ship.

Examples:
- **PASS:** "Shows correlation risk so user knows if legs are too dependent"
- **FAIL:** "Makes the architecture more elegant"
- **FAIL:** "Prepares for future features"

---

## Enforcement

Ralph keeps everyone honest:
- Claude builds within constraints
- Product owner decides scope
- Ralph audits compliance

Violations are rolled back. No exceptions.
