# SPRINT PLAN (LOCKED)

**Status:** LOCKED
**Date Locked:** 2026-01-16
**Authority:** Product Owner Decision

---

## SPRINT 1: UX → CORE FLOW
**Goal:** A normal human can build a parlay, run it, understand the output.

### Deliverables
- Parlay Builder UI (manual leg selection)
- "Run Evaluation" button
- Results panel showing:
  - Overall grade
  - Top risks
  - Key insight nuggets
- Tier-aware messaging (locked content visible but gated)

### Invariants
- Engine logic unchanged
- UI is a thin shell over existing endpoints

---

## SPRINT 2: EXPLAINABILITY + TRUST
**Goal:** User understands why the engine said what it said.

### Deliverables
- Visual sections mapped to engine stages:
  - Structural Risk
  - Correlation
  - Fragility
  - Context Snapshot (static for now)
- Tier behavior:
  - **GOOD:** headlines only
  - **BETTER:** summaries
  - **BEST:** full breakdown + narration

### Invariants
- Every insight must map to a real engine signal
- No "AI vibes" text allowed

---

## SPRINT 3: CONTEXT INGESTION (DATA, NOT MAGIC)
**Goal:** Stop relying on user-fed facts.

### Deliverables
- External data adapter (start with ONE sport, ONE source)
  - Injury report
  - Lineup change
- Normalize into ContextSnapshot
- Apply weighted modifiers to engine inputs

### Invariants
- Core evaluation math untouched
- Context is additive, not foundational

---

## SPRINT 4: LIVE SIGNALS + ALERTS (BEST TIER)
**Goal:** Proactive intelligence.

### Deliverables
- Threshold triggers
- "This bet just changed" alerts
- "New opportunity detected" nudges

### Invariants
- BEST-only feature
- Alerts must be explainable after the fact

---

## SPRINT 5: HARDEN + MONETIZE
**Goal:** Survive users and make money.

### Deliverables
- Abuse tuning
- Observability dashboards
- Pricing hooks in UI
- Shareable result links

### Invariants
- No silent failures
- Every downgrade/up-sell is explicit

---

## Amendment Policy

This plan is **LOCKED**. Changes require:
1. Explicit product owner approval
2. Documented rationale
3. Impact assessment on subsequent sprints

No scope creep. No re-litigation. Execute.
