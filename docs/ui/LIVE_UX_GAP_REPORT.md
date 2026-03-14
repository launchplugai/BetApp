# Live UX Gap Report

**Status:** DRAFT  
**Last Updated:** 2026-03-14

This report compares the current live BetApp screen behavior against:

- `docs/architecture/USER_FLOW_MAP.md`
- `docs/ui/SCREEN_COMPONENT_SPEC.md`

Its purpose is to identify the highest-value UX mismatches between:

- intended product flow
- current implementation

This is not a bug list.

It is a ranked product gap report.

## 1. Executive Summary

The live app already contains the right building blocks:

- OCR intake
- Evaluate flow
- Builder refinement flow
- protocol-aware analysis
- history and re-evaluation

The biggest issue is not missing surface area.

The issue is that the experience still feels partially split across:

- a strong Evaluate concept
- a still-prominent Builder-first mental model
- protocol intelligence that is present but not yet unified
- OCR confirmation that still overexposes raw extraction instead of parsed slip review

## 2. Overall Alignment

```text
Evaluate as home                70%
OCR trust gate                 55%
Evaluate → Builder seam        75%
Protocol visibility            60%
Results clarity                65%
History as learning surface    55%
Dashboard as hub               70%
```

## 3. Highest-Priority Gaps

## Gap 1: OCR confirmation is still too raw-text oriented

### Intended

The trust moment should be:

```text
upload image
→ parsed legs
→ confirm or repair
→ evaluate
```

### Current

The live Evaluate experience still exposes:

- extracted OCR text
- “use extracted text” flow
- “evaluate anyway” behavior from the OCR gate

This means the user is still being asked to trust raw extraction or proceed through uncertainty too easily.

### Why this matters

This weakens the trust gate and increases the chance of scoring the wrong slip.

### Priority

High

## Gap 2: Evaluate results are informative but visually overloaded

### Intended

Users should understand in 3 seconds:

1. is this structurally strong or shaky
2. why
3. what next

### Current

The Evaluate result stack includes a lot of useful material:

- signal bar
- primary failure
- delta preview
- warnings
- tips
- proof
- artifacts
- snapshot
- trend framing
- grounding score

The problem is not lack of information.

The problem is that the surface is still denser than the intended hierarchy.

### Why this matters

The product risks feeling “smart but muddy,” especially for serious-but-not-expert users.

### Priority

High

## Gap 3: Evaluate is conceptually the home, but Builder still feels like a co-primary destination

### Intended

Evaluate should be the identity.

Builder should feel like the refinement state of Evaluate.

### Current

Builder remains highly prominent in:

- dashboard quick actions
- bottom navigation emphasis
- direct manual construction posture

This is not wrong, but it still overstates Builder relative to the declared product hierarchy.

### Why this matters

It makes the app feel more like a parlay construction tool with analysis attached, rather than an evaluation-first intelligence product.

### Priority

High

## Gap 4: Protocols are present, but their UX role is still split

### Intended

Protocols should feel:

- automatic
- embedded in Evaluate and Builder
- visible when relevant
- secondarily available as a dedicated destination

### Current

The app has:

- embedded protocol-relevant signals
- protocol-triggered analysis behavior
- a dedicated protocol detail surface

But the protocol screen still feels more like a separate intelligence tool than a clearly secondary destination in a unified loop.

### Why this matters

The product’s moat is there, but not yet expressed with one clean UX story.

### Priority

Medium-high

## Gap 5: History still reads more like bet archive than learning replay

### Intended

History should prioritize:

1. what happened
2. what DNA said
3. what changed or was missed
4. which protocols fired

### Current

History has:

- status filters
- basic stats
- re-evaluate and edit actions

That is a good base, but the learning and reasoning layers are still less visible than the ledger layer.

### Why this matters

This is a long-term retention and moat surface.

If history is only archival, the product loses one of its strongest compounding advantages.

### Priority

Medium-high

## Gap 6: Dashboard still behaves more like a command center than a flow router

### Intended

Dashboard should be a daily hub that routes users quickly into the core loop.

### Current

Dashboard still leans into:

- command center framing
- active protocols
- system health
- risk profile

These are useful, but they compete with the simpler routing role the dashboard should play.

### Why this matters

This creates extra cognitive load before the user gets into the Evaluate loop.

### Priority

Medium

## 4. Best-Aligned Areas

## 4.1 Evaluate → Builder handoff exists and is real

The most important seam in the product already exists in live behavior:

- weak result
- fix context
- builder handoff
- re-evaluation loop

This is a strong foundation.

## 4.2 OCR intake already exists in the front door

OCR is not hypothetical.

The remaining work is shaping the confirmation experience correctly, not inventing it.

## 4.3 Builder already supports before/after style refinement

Builder is not just a dumb leg picker.

It already has analysis loop hooks and is positioned well for refinement-first UX once hierarchy is tightened.

## 4.4 History already includes re-evaluate behavior

That means the learning loop is structurally present.

It just needs clearer reasoning and replay emphasis.

## 5. Recommended Fix Order

## Priority 1

### Tighten OCR trust gate

Move from:

- raw extracted text emphasis

Toward:

- parsed slip confirmation
- confidence cues
- repair before scoring

## Priority 2

### Simplify and rebalance Evaluate results

Make the top hierarchy unmistakable:

1. confidence
2. fragility
3. why
4. what next

Push lower-signal technical material downward or into collapsible layers.

## Priority 3

### Reposition Builder as refinement, not co-home

Keep it powerful, but make the navigation and framing reinforce:

```text
Evaluate first
Builder second
```

## Priority 4

### Reframe Protocols as embedded intelligence first

The dedicated protocol destination should remain, but the main product story should say:

```text
Protocols make evaluation smarter
```

before it says:

```text
here is a separate protocol tool
```

## Priority 5

### Turn History into a learning replay surface

Increase emphasis on:

- original DNA reasoning
- what changed
- protocol triggers
- re-evaluation replay

## 6. Visual Summary

```text
CURRENT
OCR → text-heavy confirm
Evaluate → smart but dense
Builder → highly prominent
Protocols → partly split
History → archive-first

TARGET
OCR → parsed leg trust gate
Evaluate → clear first judgment
Builder → guided refinement state
Protocols → embedded intelligence
History → learning replay
```

## 7. Immediate Product Recommendation

If only one live UX seam is redesigned next, it should still be:

```text
Evaluate → Builder
```

But if one entry-trust issue is cleaned up in parallel, it should be:

```text
OCR → parsed slip confirmation
```

Those two changes would do the most to make the product feel like one coherent decision system instead of several strong pieces.

