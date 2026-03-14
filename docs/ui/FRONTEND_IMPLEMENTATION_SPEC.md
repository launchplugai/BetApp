# Frontend Implementation Spec

**Status:** DRAFT  
**Last Updated:** 2026-03-14

This document converts the current UX direction into an implementation plan for the frontend.

It should be read after:

- `docs/architecture/USER_FLOW_MAP.md`
- `docs/ui/SCREEN_COMPONENT_SPEC.md`
- `docs/ui/LIVE_UX_GAP_REPORT.md`

## 1. Purpose

This spec exists to make the next frontend pass buildable.

It defines:

- the implementation order
- the required frontend seams
- the state and component responsibilities
- the acceptance criteria for each pass

## 2. Current Frontend Reality

Before new UX work lands, one important condition must be acknowledged:

```text
The Evaluate frontend is currently split across multiple partially overlapping implementations.
```

Observed signals:

- `app/templates/app/index.html` contains a chat-style Evaluate entry and OCR surfaces
- `app/web_assets/static/app.js` still contains a tabbed Evaluate flow with IDs and behaviors that do not cleanly map one-to-one onto the active template
- some OCR and review-gate elements appear only partially wired

### Implementation rule

Do not stack major UX work on top of unresolved frontend duplication.

The first step of the next UI pass must be:

```text
reconcile the active Evaluate entrypoint and its JS ownership
```

See:

```text
docs/ui/ACTIVE_FRONTEND_OWNERSHIP_MAP.md
```

for the current mounted-versus-parallel ownership split.

## 3. Frontend Priorities

Implementation order:

1. reconcile active Evaluate frontend path
2. tighten OCR trust gate
3. simplify Evaluate results hierarchy
4. strengthen Evaluate → Builder handoff
5. reframe Builder as refinement
6. improve History as learning replay
7. rebalance Dashboard as flow router

## 4. Phase 0: Frontend Source-of-Truth Cleanup

### Goal

Establish one active Evaluate implementation path.

### Required output

- one canonical Evaluate template
- one canonical JS controller for Evaluate
- one clear ownership map for OCR, results, and Builder handoff

### Tasks

- identify whether `app/templates/app/index.html` is the active Evaluate surface
- identify which parts of `app/web_assets/static/app.js` are still live versus legacy
- remove or isolate dead/duplicated Evaluate behaviors
- align DOM IDs and JS assumptions

### Acceptance criteria

- one screen map exists for Evaluate
- OCR controls, results controls, and Builder handoff all belong to the same frontend path
- no duplicate control logic for the same user action

## 5. Phase 1: OCR Trust Gate

### Goal

Move OCR from raw-text-first to parsed-slip-confirmation-first.

### Intended flow

```text
upload image
→ extract
→ detect or parse slip structure
→ show parsed legs
→ confirm or repair
→ evaluate
```

### Current problem

The live UI still emphasizes extracted text and soft “evaluate anyway” behavior.

### Required UI changes

- replace raw extracted text as the primary confirmation surface
- add parsed leg cards as the main OCR review UI
- visually indicate confidence or uncertainty per detected leg if available
- route uncertain OCR into review/repair before scoring

### Minimal fallback if parsed-leg parsing is not yet rich enough

If the system cannot produce fully structured detected legs yet:

- keep extracted text available only as a secondary debug/support view
- primary UI should still frame this as a review step, not a ready-to-trust final input

### Primary components

- image preview
- extraction status
- parsed leg review list
- “Edit before evaluation”
- “Use reviewed slip”

### Avoid

- raw OCR text as the hero element
- “Evaluate anyway” as the main CTA

### Acceptance criteria

- users do not move from OCR to scoring without a confirmation step when confidence is mixed
- parsed slip review is visually primary
- raw text is secondary or hidden behind details

## 6. Phase 2: Evaluate Result Rebalance

### Goal

Make the result screen readable in 3 seconds.

### Required hierarchy

1. confidence
2. fragility
3. why
4. what next

### Implementation approach

#### Top layer

- confidence headline
- fragility headline
- top recommendation
- main protocol triggers

#### Middle layer

- key strengths
- key risks
- primary failure
- guided fix CTA

#### Lower layer

- structural snapshot
- trend data
- proof/debug
- technical artifacts

### UI rules

- lower-signal material should become collapsible or visually subordinate
- “What’s New” style release-note content should not occupy prime result real estate
- the first screenful should answer the three-second questions without scrolling

### Acceptance criteria

- a serious-but-not-expert user can explain the recommendation after one screenful
- technical detail is still available but no longer competes with the main judgment

## 7. Phase 3: Evaluate → Builder Seam

### Goal

Make Builder feel like refinement, not a separate jump.

### Required behavior

Weak result should lead naturally into:

```text
guided fix
→ Builder with context
→ before/after delta
→ re-evaluate
```

### Required state payload

At minimum, Builder handoff should preserve:

- `evaluationId`
- input text or normalized slip
- primary failure
- fastest fix
- signal info
- delta preview if available
- tier

### UI changes

- result CTA copy should focus on fixing structure, not generic navigation
- Builder should visibly show what it is trying to improve
- Builder should preserve “before” context and not feel reset

### Acceptance criteria

- a weak evaluation can be refined in one continuous session without re-entering context manually
- before/after delta remains visible through the refinement loop

## 8. Phase 4: Builder Reframing

### Goal

Keep Builder powerful while reducing its identity as a co-home.

### Changes

- navigation and labels should reinforce that Builder is refinement
- Builder hero copy should focus on improving a slip, not merely constructing one
- direct manual-build mode remains supported, but should not dominate product framing

### Acceptance criteria

- the product reads as Evaluate-first in both navigation and messaging
- Builder still works for advanced/manual users without defining the entire product

## 9. Phase 5: Protocol Visibility

### Goal

Make protocols feel embedded and useful rather than split and abstract.

### Required behavior

- protocol triggers appear in Evaluate results
- protocol triggers appear in Builder refinements when relevant
- dedicated protocol destination remains for advanced workflows and saved strategies

### UI expression

- named modules
- short explanation
- light badge/scanning layer

### Avoid

- protocol clutter
- protocol jargon without consequence
- protocol screen becoming the only place protocols feel real

## 10. Phase 6: History As Learning Replay

### Goal

Shift History from archive-first to replay-and-learning-first.

### Needed additions

- what DNA originally said
- what changed in Builder if relevant
- protocol triggers
- clear re-evaluate path
- learning summary or “what we caught / missed” framing

### Acceptance criteria

- history item detail helps the user learn, not just recall a result
- re-evaluation is a natural next action from history

## 11. Phase 7: Dashboard Rebalance

### Goal

Reduce command-center drag and improve routing into the main loop.

### Keep

- quick access to Evaluate, Builder, Browse, History
- lightweight status cues

### De-emphasize

- heavy operational framing
- system-health dominance
- protocol/system panels that distract from action

### Acceptance criteria

- Dashboard feels like a launchpad, not a control room

## 12. Frontend State Contracts

The frontend implementation should stabilize the following state objects.

## 12.1 OCR Review State

```json
{
  "source": "image",
  "fileName": "slip.png",
  "rawText": "optional secondary field",
  "detectedLegs": [],
  "confidence": 0.0,
  "requiresReview": true
}
```

## 12.2 Evaluation Result State

```json
{
  "evaluationId": "eval_123",
  "input": {},
  "signalInfo": {},
  "primaryFailure": {},
  "deltaPreview": {},
  "triggeredProtocols": [],
  "dnaScoring": {}
}
```

## 12.3 Builder Context State

```json
{
  "evaluationId": "eval_123",
  "inputText": "original or current slip text",
  "primaryFailure": {},
  "fastestFix": {},
  "deltaPreview": {},
  "signalInfo": {},
  "tier": "good"
}
```

These should be normalized once and shared consistently across Evaluate, Builder, and History replay.

## 13. UI Metrics

Primary frontend metric:

```text
re-evaluation rate
```

Secondary metrics:

- OCR review completion rate
- OCR correction rate before evaluation
- guided-fix click-through rate
- Builder re-evaluation completion rate
- history re-evaluation rate

## 14. Immediate Implementation Recommendation

The first engineering pass should not try to redesign everything.

The best next implementation sequence is:

```text
1. unify Evaluate frontend ownership
2. implement OCR trust gate properly
3. simplify top-level result hierarchy
```

That is the shortest path to making the product feel materially more coherent.
