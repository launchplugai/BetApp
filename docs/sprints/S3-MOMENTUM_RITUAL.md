# Sprint S3 — MOMENTUM × RITUAL

**Status:** IN PROGRESS  
**Started:** 2026-02-06 01:48 UTC  
**Priority:** HIGH  
**Branch:** `claude/sprint-s3-momentum-ritual`

---

## Sprint Goal

**Primary Objective:**  
A user completes an evaluation and feels an immediate urge to adjust, re-run, or explore — not stop.

**Optimize:**
- Engagement momentum
- Emotional continuity
- Confidence without delusion

---

## TRUTH × EXPERIENCE Philosophy

This sprint must advance BOTH dimensions:

### Sprint TRUTH Objectives
- No new math or scoring logic
- No API contract changes
- No correlation logic mutations
- All existing tests continue passing
- Copy changes only (no business logic)

### Sprint EXPERIENCE Objectives
- Replace binary pass/fail psychology with directional confidence
- Make re-evaluation feel intentional, not corrective
- Turn leg explanations into story
- Reinforce "edge" feeling without false promises
- Increase user interaction and momentum

---

## Scope Boundaries (NON-NEGOTIABLE)

### ✅ IN SCOPE
- Copy changes
- Framing logic
- UI sequencing
- Narrative emphasis
- CTA language

### ❌ OUT OF SCOPE
- New math
- New models
- Win-rate claims
- Correlation logic changes
- ML escalation
- Scoring formula changes

---

## Tickets

### S3-A — Confidence Gradient System

**Purpose:** Replace binary-feeling grades with directional confidence language.

**Implementation:**
- Introduce confidence ladder (e.g., Stable → Pressured → Fragile)
- Derive language from existing:
  - `groundingScore`
  - `structureSnapshot`
- NO new calculations

**TRUTH:**
- Uses existing outputs only
- No mutation of scores

**EXPERIENCE:**
- Removes pass/fail psychology
- Introduces pressure/relief framing

**Acceptance Criteria:**
- User can describe confidence direction in one sentence
- No numeric emphasis added

---

### S3-B — Ritualized Re-evaluation Loop

**Purpose:** Make re-evaluation feel like intentional refinement, not correction.

**Implementation:**
- Rewrite CTA copy:
  - "Edit Builder" → "Refine Structure"
  - "Re-evaluate" → "Test This Adjustment"
- Emphasize `deltaSentence` as progress feedback
- Add subtle language:
  - "You traded X for Y"
  - "Structure tightened / loosened"

**TRUTH:**
- Delta logic unchanged

**EXPERIENCE:**
- User feels like they are crafting, not fixing mistakes

**Acceptance Criteria:**
- User instinctively clicks re-evaluate at least once
- No scolding or warning tone

---

### S3-C — Notable Legs Narrative Upgrade

**Purpose:** Turn leg explanations into story, not sportsbook justification.

**Implementation:**
- Rewrite Notable Legs copy to answer: "What's doing the work here?"
- Remove explanatory hedging language
- Emphasize intent and role of each leg

**TRUTH:**
- No logic changes
- Same legs, same data

**EXPERIENCE:**
- Legs feel chosen, not accidental

**Acceptance Criteria:**
- User understands why a leg matters without rereading

---

### S3-D — Edge Framing Pass (Copy Only)

**Purpose:** Reinforce "this gives me an edge" feeling without false promises.

**Implementation:**
- Copy pass on:
  - Summary
  - Grade subtitle
  - Analysis badges
- Remove academic phrasing
- Calm, confident tone

**TRUTH:**
- No guarantees
- No outcome promises

**EXPERIENCE:**
- Hope without bullshit
- Confidence without deception

**Acceptance Criteria:**
- Language feels assistive, not authoritative
- No legal/academic tone remains

---

## Testing Criteria

### Functional
- ✅ No regression in existing tests
- ✅ No API contract changes

### Experience
- ✅ 10-second comprehension test passes
- ✅ User reports increased confidence, not confusion
- ✅ User chooses to interact again

---

## Sprint Completion Rule

Sprint is COMPLETE only when:
- ✅ All tickets satisfy TRUTH × EXPERIENCE
- ✅ No new math introduced
- ✅ User interaction increases, not decreases

**STOP if any ticket violates scope or guardrails.**

---

## Progress Tracking

- [ ] S3-A — Confidence Gradient System
- [ ] S3-B — Ritualized Re-evaluation Loop
- [ ] S3-C — Notable Legs Narrative Upgrade
- [ ] S3-D — Edge Framing Pass (Copy Only)

---

**Charter Reference:** [`docs/TRUTH_AND_EXPERIENCE.md`](../TRUTH_AND_EXPERIENCE.md)
