# User Flow Map

**Status:** CANONICAL  
**Last Updated:** 2026-03-14

This document defines the intended end-user journey for BetApp.

It is the canonical UX flow map for:

- bet idea intake
- OCR intake
- evaluation
- protocol activation
- builder refinement
- bet placement
- history and learning

If a screen or route conflicts with this flow, treat this map as the target product behavior and align the implementation toward it.

## 1. Product UX Thesis

BetApp should feel:

- evaluate-first
- screenshot-friendly
- protocol-smart by default
- cautious, not permissive
- collaborative during refinement
- learning-oriented after outcomes settle

The product is not a picks app.

The core user promise is:

> I have a bet idea. The app understands it quickly, shows me if it is structurally weak, explains why, and helps me tighten it without pretending certainty.

## 2. Core User Loop

```text
BET IDEA / SCREENSHOT / MANUAL BUILD
→ parse and confirm
→ evaluate
→ protocol detection
→ explain strengths and fragility
→ guided fix
→ builder refinement
→ re-evaluate
→ save / place / abandon
→ history and learning
```

This is the primary loop the product should optimize for.

## 3. Entry Points

Users may begin from three primary entry modes:

### 3.1 Typed Or Pasted Bet Idea

The user enters a parlay or bet idea directly.

This is the primary default flow.

### 3.2 Slip Screenshot / Image Upload

The user uploads a sportsbook screenshot or slip image.

OCR is part of the front door, but OCR text is not the trust moment.

The trust moment is:

```text
upload image
→ parsed legs displayed
→ confirm or repair
→ DNA runs
```

Raw OCR text should not be the primary confirmation surface.

### 3.3 Manual Builder Start

The user constructs a slip from scratch.

This is valid, but it is not the main product identity.

Builder is a refinement environment, not the home of the product.

## 4. Home Of The Product

`Evaluate` is the true home of BetApp.

Supporting roles:

- `Dashboard` is the entry hub and daily loop surface
- `Evaluate` is the core promise and decision engine
- `Builder` is the refinement state after evaluation
- `Protocols` are the embedded intelligence layer with a secondary destination for advanced users

If the product is reduced to one core verb, it is:

```text
Evaluate
```

## 5. Parse And Trust Gate

Before DNA scoring runs, the system must determine whether the slip is sufficiently understood.

### 5.1 High OCR Confidence

The app may auto-advance with a lightweight confirmation step.

### 5.2 Mixed OCR Confidence

The app should require user correction before evaluation.

### 5.3 Poor OCR Confidence

The app should route immediately into manual repair.

### Rule

Parsing is a trust gate.

Broken extraction must not silently flow into DNA scoring.

## 6. Core Analysis Loop

Once the slip is confirmed, the product enters the analysis loop.

```text
confirmed slip
→ evaluate structure
→ activate relevant protocols
→ compute DNA scores
→ explain why
→ suggest what to do next
```

Protocols are not a later add-on.

They are a core loop component of evaluation.

## 7. Protocol Role In The Experience

Protocols should be:

- automatic by default
- visible when relevant
- branded enough to feel differentiated
- not noisy or overbearing

When a protocol fires, it should appear as:

- a quick badge for scanning
- a named intelligence module for meaning
- a short explanation for trust

Example expression:

```text
Fatigue Protocol Triggered
Short rest plus travel increases variance for this leg.
```

Users should not be required to select protocols before analysis in the default flow.

Advanced customization can exist later, but detection should be automatic.

## 8. Evaluation Result Priorities

Within 3 seconds, the result surface must answer:

1. Is this structurally strong or shaky?
2. Why is it rated that way?
3. What should I do next?

### Visual hierarchy

1. Confidence
2. Fragility
3. Why
4. Next action

Confidence is the headline.

Fragility is the truth serum and must remain highly visible.

## 9. Product Tone

The product must never feel like permission software.

Even stronger slips should retain some tension and caution.

Preferred language:

- structurally strong
- lower fragility than average
- more stable than it first appears

Avoid language like:

- safe
- lock
- guaranteed
- you are good

## 10. Evaluate To Builder Seam

This is the most important seam in the product.

The relationship should be:

```text
Evaluate
→ weak or fragile result
→ guided fix
→ Builder refinement state
→ re-evaluate
```

Builder is not a disconnected tool.

It is the refinement state of the evaluation loop.

This seam determines whether BetApp feels like:

- a dead-end scorecard

or

- a living decision-support tool

## 11. Guided Fix Behavior

When a slip evaluates poorly, the next action should not be a vague generic instruction.

The preferred response is a guided protocol fix.

Examples:

- remove a correlated leg
- replace a high-volatility prop
- simplify from five legs to three
- resolve an injury-instability risk

The user experience should feel like:

> Here is what is making this slip fragile, and here is how I would tighten it.

This should feel collaborative, evidence-based, and slightly opinionated.

## 12. Builder Role

Builder should:

- show before/after delta clearly
- make fragility reduction visible
- preserve the evaluation context
- support fast re-evaluation

At launch, before/after delta is more important than full side-by-side compare.

Users primarily need to know:

- what changed
- why it improved or worsened
- which leg or protocol drove the difference

## 13. Protocol Surface Strategy

Protocols should have two modes of presence:

### Embedded Presence

This is the main experience.

Protocols appear inside:

- evaluation results
- builder refinement
- guided fixes

### Dedicated Destination

This is secondary, intended for:

- saved protocol workflows
- strategy presets
- advanced users
- premium education

Protocols are core-loop intelligence first and a standalone destination second.

## 14. Bet Placement

The transition from results or builder into bet placement should preserve:

- the current evaluated structure
- the related evaluation identity
- the context needed for later learning and calibration

Bet placement should feel like:

```text
I understand the structure
→ I choose whether to proceed
```

Not:

```text
the app approved this for me
```

## 15. History As Learning Surface

History should not behave like a simple ledger.

Its priority order is:

1. what happened
2. what DNA said
3. what the user changed or missed
4. which protocols fired

History should teach users over time, not just archive outcomes.

This is part of the product moat.

## 16. Primary UX Health Metric

The best leading indicator of UX quality is:

```text
re-evaluation rate
```

Why:

- it shows users trust the tool enough to iterate
- it proves the Evaluate → Builder loop is functioning
- it indicates decision improvement behavior instead of passive consumption

Secondary useful signals:

- fewer reckless parlays
- more protocol usage
- more saved bets

## 17. Priority UX Seams

If only one seam can be improved first:

1. Evaluate → Builder
2. OCR → parsed slip
3. Results → bet placement
4. Protocol visibility

This is the current UX priority order.

## 18. Canonical Product Journey

```text
ENTRY
├─ type or paste a bet idea
├─ upload a screenshot
└─ start manually in Builder

INGEST
├─ OCR if needed
├─ parse legs
└─ confirm or repair

CORE LOOP
├─ evaluate
├─ trigger protocols
├─ score structure
├─ explain risk and strengths
├─ recommend next action
├─ open guided fix
├─ refine in Builder
└─ re-evaluate

OUTCOME
├─ save or place bet
├─ continue researching
└─ abandon fragile structure

LEARNING
├─ revisit in History
├─ inspect what DNA said
├─ compare with actual outcome
└─ get smarter over time
```

## 19. Canonical User Feeling

The intended emotional flow is:

```text
I have a bet idea.
→ The app understood it quickly.
→ It showed me what was shaky.
→ It explained why.
→ It helped me tighten it.
→ I stayed in control.
```

That is the target user experience.

