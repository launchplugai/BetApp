# SPRINT PLAN (LOCKED)

**Status:** LOCKED
**Date Locked:** 2026-01-16
**Authority:** Product Owner Decision

---

## SPRINT 1: PARLAY BUILDER + EVALUATION FLOW (CURRENT)

**Status:** IN PROGRESS

### Sprint Goal
A regular user can:
- Build a parlay
- Run it through the engine
- Understand the result at a glance

No live data. No refactors. No "AI magic." Just usability.

---

### SCOPE (DO NOT EXCEED)

**Included:**
- Manual parlay construction
- Basketball only
- Thin UI over existing backend
- Tier-gated results display

**Explicitly Excluded:**
- Live injury data
- Odds movement
- Smart suggestions
- Alerts
- Builder "intelligence"

If it sounds cool, it's probably Sprint 2 or 3.

---

### UI REQUIREMENTS (/app)

#### 1. Parlay Builder
- Sport selector (Basketball only)
- Add / remove legs
- Each leg includes:
  - Team or Player
  - Market (spread / ML / total / prop)
  - Line / condition
  - Odds

Minimum legs: 2
Maximum legs: 6

#### 2. Run Evaluation
- Button disabled until ≥2 legs
- Submits payload to existing evaluation endpoint
- No backend changes allowed

#### 3. Results Panel

Render only what the tier allows:

**Always show:**
- Overall grade
- Short verdict (1–2 sentences)

**Tier behavior:**
- **GOOD:** locked sections visible but blurred/disabled
- **BETTER:** summary insights
- **BEST:** full explanation + narration flag (if enabled)

No raw JSON dumped on users. Ever.

---

### BACKEND CONSTRAINTS (NON-NEGOTIABLE)
- Use existing evaluation endpoints
- Do not modify:
  - Engine logic
  - Scoring
  - Tier gating
- UI adapts to backend, not the other way around

If something feels missing, note it. Do not "fix" it.

---

### DEFINITION OF DONE

Sprint 1 is complete only if:
- [ ] A user can build a parlay end-to-end
- [ ] Evaluation runs successfully
- [ ] Results render correctly per tier
- [ ] No test regressions
- [ ] No engine changes

If even one fails, Sprint 1 is not done.

---

## SPRINT 2: EXPLAINABILITY + TRUST

**Status:** PENDING

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

**Status:** PENDING

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

**Status:** PENDING

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

**Status:** PENDING

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
