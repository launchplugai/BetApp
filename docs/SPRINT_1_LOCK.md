# SPRINT 1 LOCK ARTIFACT

**Status:** LOCKED
**Date Locked:** 2026-01-27
**Lock Commit:** `a95d8f66351722edf729fef9c66dcf626f79a54f`
**Authority:** Product Owner Decision

---

## 1. Sprint Objective

Sprint 1 set out to prove that a user can manually construct a sports parlay, submit it to a live deterministic evaluation engine, and receive a tier-gated result that is understandable at a glance — with no live data feeds, no speculative AI behavior, and no modifications to the core engine math. The goal was usability over capability: confirm the product loop works before adding intelligence.

The core user loop locked in by Sprint 1 is: **Build a parlay, evaluate it, understand the result, and optionally improve it — all through a minimal UI backed by a stable, auditable engine.**

---

## 2. Definition of Done (Checklist)

- [x] User can evaluate a parlay end-to-end
- [x] Evaluation engine is deterministic
- [x] Tier separation enforced server-side
- [x] Builder improves only evaluated slips
- [x] History persists evaluations
- [x] No engine math changed after validation
- [x] Tests passing with no regressions
- [x] UI delivery layer stabilized (web.py split into assets)

---

## 3. In-Scope (Explicit)

The following features are officially counted as Sprint 1 deliverables:

- Core evaluation engine
- Signal system
- Tier-gated outputs (GOOD / BETTER / BEST)
- Builder improvement workbench
- History MVP
- UI delivery split (templates + static assets)

---

## 4. Out-of-Scope but Present (Critical)

The following features exist in the codebase but were NOT part of the original Sprint 1 plan:

- Image slip upload
- Discover bundles
- Delta preview
- Alerts scaffolding
- Context modules
- Auth / billing / persistence folders

These features exist but are not activated as sprint drivers. Their presence does not advance sprint count.

---

## 5. Known Technical Debt (Accepted)

- Prior web.py monolith (now resolved)
- Feature flags not yet centralized
- Governance enforcement previously bypassed

---

## 6. Sprint Lock Statement (Hard Stop)

SPRINT 1 IS LOCKED. No additional functionality, UI, or logic changes are permitted under Sprint 1.

---

## Rationale

This ticket exists to prevent scope drift, protect evaluation integrity, and ensure future sprints add capability intentionally rather than accidentally.
