# Sprint S2-FND Closeout

**Sprint Name:** Truth × Experience Foundation  
**Duration:** 2026-02-05 17:21 UTC — 2026-02-06 00:38 UTC  
**Status:** ✅ COMPLETE  

---

## A. User-Facing Changes

### What You Can Now See and Feel

**Grounding Score Display**  
When you evaluate a parlay, you now see "Analysis Foundation" — a plain-language explanation of where the insights come from. Instead of raw technical percentages, you get clarity:
- "This analysis is grounded mainly by structural features"
- "This analysis relies heavily on bet-type patterns"
- "This analysis uses general guidance"

**Why it matters:** You gain confidence without needing a PhD. The analysis tells you how much it's leaning on hard structure versus intuition, so you know what kind of signal you're getting.

**Improved Parser Accuracy**  
Real betting text like "Luka O27.5 pts" or "Lakers ML" is now understood correctly. Previously, shorthand props and over/under patterns could confuse the system.

**Why it matters:** You type naturally, and the system keeps up. Less friction, faster workflow, more trust that what you entered is what got analyzed.

**Structural Snapshot Visibility**  
The machine-readable "snapshot" of your parlay structure is now available as a collapsible panel. It shows exactly what the engine sees: leg types, correlations, counts.

**Why it matters:** When something feels off, you can peek under the hood. Transparency builds trust. You're not guessing — you're verifying.

**Change Delta Sentences**  
When you remove or lock a leg and re-evaluate, the system tells you what changed: "Removed 1 leg. Correlation risk reduced."

**Why it matters:** You understand cause and effect. You're not just getting a new grade — you're seeing why it changed.

---

## B. System-Level Changes

### Foundation Integrity

**Structural Snapshot Engine (Ticket 38B-A)**  
Introduced `app/structure_snapshot.py` — a pure function that generates machine-readable parlay state. Captures:
- Leg types (spread/total/prop/ML)
- Bet directions (over/under)
- Correlation flags (same_game, same_player)
- Entity canonicalization

**Truth impact:** Snapshot is deterministic. Same inputs always produce the same snapshot.  
**Tests:** 20/20 unit tests passing.

**Change Delta Engine (Ticket 38B-B)**  
Created `app/change_delta.py` — calculates structural differences between parlays (before/after refinement). Detects:
- Legs added/removed
- Correlation changes
- Bet type distribution shifts

**Truth impact:** Delta computation is accurate and edge-case hardened.  
**Tests:** 12/12 delta tests passing.

**Parser Bet Type Correction (Ticket A1)**  
Fixed `app/pipeline.py:567` (`_detect_leg_markets()`) to recognize:
- Common prop abbreviations: `pts`, `reb`, `ast`, `blk`, `stl`, `to`, `3pm`
- O/U patterns: `O27.5`, `U10.5`
- Moneyline indicators: `ML`, `moneyline`
- Spread vs prop distinction

**Truth impact:** Parser now correctly classifies real-world betting text.  
**Tests:** 22/22 parser tests passing, 3/3 snapshot integration tests passing.

**Grounding Score Pipeline (Ticket 38B-C2)**  
Created `app/grounding_score.py` — deterministic breakdown engine. Calculates:
- Structural: % from snapshot features (correlations, leg count)
- Heuristics: % from leg-type templates
- Generic: % from fallback language

**Truth impact:** Grounding score is reproducible and correct. Invariant: structural + heuristics + generic = 100.  
**Tests:** 15/15 grounding score tests passing.

**UI Integration (Tickets 38B-C1, D1)**  
Wired snapshot, delta, and grounding score into `/app/evaluate` API and UI display.

**Truth impact:** UI reflects backend state accurately. No disconnect between data and display.  
**Tests:** 933/933 web tests passing (no regressions).

---

## C. Risk Reduction

### Classes of Failure Now Prevented

**Parser Drift**  
Before: Shorthand betting text (`Luka O27.5 pts`) could be misclassified.  
After: 22 unit tests lock down prop/O/U/ML patterns. Parser regression is caught immediately.

**Snapshot Integrity Violations**  
Before: Ad-hoc snapshot generation across modules could diverge.  
After: Single `generate_structure_snapshot()` function with 20 tests. Structural state is centralized and verified.

**Grounding Score Inconsistency**  
Before: No visibility into whether analysis was structural or heuristic.  
After: 15 tests ensure grounding breakdown is deterministic and sums to 100%. UI presents this clearly.

**Charter Bypass**  
Before: TRUTH × EXPERIENCE charter was aspirational documentation.  
After: PR template enforces checklist. Ticket templates require dual impact statements. Charter violations are now valid grounds for PR rejection.

### Types of Drift Now Blocked

**Governance Drift**  
All PRs must satisfy TRUTH (correct, verified) and EXPERIENCE (confident, clear) criteria. New `.github/` templates enforce this at workflow level.

**Feature Drift**  
Snapshot and grounding score engines are frozen contracts. Future changes require explicit justification and cannot silently alter structure.

**Test Coverage Drift**  
Every foundation ticket added test coverage:
- Snapshot: 20 tests
- Delta: 12 tests
- Parser: 22 tests
- Grounding: 15 tests
- UI integration: 933 tests (no regressions)

**Total:** 69 new tests added during sprint, 933 total passing.

### Why Future Changes Are Safer

**Governance Scaffolding**  
Four new governance files lock in standards:
- `.github/pull_request_template.md` — mandatory charter checklist
- `.github/TICKET_TEMPLATE.md` — requires TRUTH + EXPERIENCE impact
- `.github/SPRINT_TEMPLATE.md` — dual objectives required
- `.github/CHARTER_ENFORCEMENT.md` — binding policy, no exceptions

**Outcome:** Future work inherits charter compliance by default. Violations are caught at PR review, not post-merge.

**Deterministic Foundations**  
Snapshot, delta, and grounding score are pure functions:
- No side effects
- No external calls
- Same inputs → same outputs

**Outcome:** Foundation behavior is predictable. Debugging is tractable. Changes can be verified mechanically.

**Test Moat**  
933 passing tests create a safety net. Any breaking change triggers immediate feedback.

**Outcome:** Refactors and extensions are safer. Regressions surface before deployment.

---

## D. Sprint Outcome

### Goals Met ✅

**Sprint S2-FND Objectives:**
1. ✅ Build TRUTH foundation (snapshot, parser, grounding engines)
2. ✅ Build EXPERIENCE foundation (UI clarity, plain-language framing)
3. ✅ Enforce TRUTH × EXPERIENCE governance (charter + workflow)

**Deliverables:**
- ✅ Structural Snapshot engine (20 tests)
- ✅ Change Delta engine (12 tests)
- ✅ Parser bet_type correction (22 tests)
- ✅ Grounding Score engine (15 tests)
- ✅ UI wiring for all artifacts (933 tests, no regressions)
- ✅ TRUTH_AND_EXPERIENCE.md charter (docs/)
- ✅ Governance enforcement templates (.github/)

**Test Summary:**
- Total tests passing: **933 / 933** ✅
- New tests added: **69**
- Regressions: **0**
- xfailed (pre-existing): **2**

**Commits:**
- Ticket 38B-A: Structural Snapshot (`1a133b1`)
- Ticket 38B-B: Change Delta (`bdb8906`, `33a2540`)
- Ticket 38B-C1: UI Wiring (`d86fe1c`, `91c94bf`)
- Ticket 38B-C2: Grounding Score (`f14ef55`)
- Ticket A1: Parser Correction (`850a6d3`)
- Ticket S2-FND-B1: Charter Document (`c5ef1aa`)
- Ticket S2-FND-C1: Governance Enforcement (`614faae`)
- Ticket D1 / 38B-C3: Grounding Score UI (`816144e`)

**Branch:** `claude/ticket-38b-c2-grounding-score` (pushed to origin)

### Foundation + Governance Locked 🔒

**What is now locked:**
- Snapshot structure contract
- Delta calculation logic
- Grounding score invariant (structural + heuristics + generic = 100)
- Charter enforcement workflow

**What this means:**
- Future changes to these areas require explicit charter review
- Breaking changes trigger governance escalation
- Drift is detectable via test suite
- TRUTH × EXPERIENCE compliance is non-negotiable

**Status:** Sprint S2-FND foundation is **stable, verified, and enforceable.**

---

## E. Suggestions for Next Sprint (Optional)

**These are SUGGESTIONS ONLY. No execution authorization implied.**

### 1. Display Grounding Score in Sherlock Context
**Context:** Grounding score exists in pipeline; Sherlock analysis could benefit from visibility into structural vs heuristic grounding.  
**Benefit:** Users see consistency — if Sherlock flags low confidence and grounding score shows high generic %, the signals align.  
**Scope:** UI wiring only (no Sherlock logic changes).

### 2. Snapshot-Based Regression Tests
**Context:** Structural snapshot is deterministic. Could snapshot 20 canonical parlays and lock their structure.  
**Benefit:** Future parser or pipeline changes that alter snapshot structure trigger immediate alerts.  
**Scope:** Test file + fixture snapshots (JSON).

### 3. Grounding Score Thresholds Documentation
**Context:** Current UI uses 50% as dominant threshold. No documented rationale.  
**Benefit:** Future adjustments (e.g., "structural dominant at 40%") are traceable and justified.  
**Scope:** Documentation only (add to `docs/TRUTH_AND_EXPERIENCE.md`).

---

**Sprint S2-FND Status:** ✅ COMPLETE  
**Next Sprint Authorization:** Awaiting Product Owner directive.
