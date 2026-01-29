# SPRINT 1 LOCK — PARLAY BUILDER + EVALUATION FLOW

**Status:** LOCKED
**Lock Date:** 2026-01-26T00:00:00Z
**Branch:** `claude/lock-sprints-chat-package-QXI7T`
**Commit Hash:** `4900d4a401474234680add5fbb45a3dcdd0e1acb`
**Authority:** Ticket 11 — Sprint Lock + Governance Snapshot

---

## Definition of Done Checklist

| # | Criterion | Status |
|---|-----------|--------|
| 1 | User can build a parlay end-to-end | PASS |
| 2 | Evaluation runs successfully | PASS |
| 3 | Results render correctly per tier | PASS |
| 4 | No test regressions | PASS |
| 5 | No engine changes | PASS |

All five gates passed. Sprint 1 is formally complete.

---

## Live User-Visible Surfaces

| Route | Description | Ticket |
|-------|-------------|--------|
| `/app` | Main parlay builder UI (Discover / Evaluate / Builder / History tabs) | Ticket 1+ |
| `/app/evaluate` | Evaluation submission endpoint (POST) | Ticket 2 |
| `/panel` | Developer testing panel (image + text evaluation) | Pre-sprint |
| `/build` | Build info endpoint (deployment stamp) | Ticket 10 |
| `/health` | Health check with service metadata | Pre-sprint |
| `/history` | Evaluation history API (`GET /history`, `GET /history/{id}`) | Ticket 6/6B |
| `/leading-light/evaluate/text` | Core text evaluation API | Pre-sprint |
| `/leading-light/evaluate/image` | Core image evaluation API (bet slip OCR) | Pre-sprint |
| `/voice/*` | Voice narration endpoints | Pre-sprint |

---

## Out-of-Scope Modules Present in Repository

These modules exist in the codebase but are **not part of Sprint 1** and must not be activated, modified, or depended upon until their designated sprint:

| Module | Path | Designated Sprint |
|--------|------|-------------------|
| **alerts/** | `/alerts/` | Sprint 4 — Live Signals + Alerts |
| **context/** | `/context/` | Sprint 3 — Context Ingestion |
| **auth/** | `/auth/` | Future (not yet scheduled) |
| **billing/** | `/billing/` | Sprint 5 — Harden + Monetize |
| **persistence/** | `/persistence/` | Future (not yet scheduled) |

These modules are scaffolded but dormant. Any activation requires a new ticket approved by the Product Owner.

---

## Sprint 1 Delivered Tickets

| Ticket | Title |
|--------|-------|
| 1 | UI Flow Lock |
| 2 | Core Loop Reinforcement |
| 3 | GOOD Tier Structured Evaluation Output |
| 4 | primaryFailure + deltaPreview (Evaluate Intelligence) |
| 6 | History MVP |
| 6B | Canonical /history endpoints + evaluationId contract |
| 7A | Fix default tab to Discover |
| 8 | Bet Slip-First Evaluate UX |
| 9 | Builder Improvement Workbench (No Manual Parlay Typing) |
| 10 | Deployment Stamp — build visibility for UI and API |
| 11 | Lock Sprint 1 + Governance Snapshot (this document) |

---

## Advancement Gate

> **No sprint advances without a new ticket set approved by Product Owner.**

To proceed to Sprint 2 (Explainability + Trust):
1. This lock document must be merged and present in the main branch
2. A new ticket set for Sprint 2 must be drafted and approved
3. The RALPH_LOOP lock step checklist (see CLAUDE.md) must be completed
4. Product Owner sign-off is required before any Sprint 2 work begins
