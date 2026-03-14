# Screen Component Spec

**Status:** CANONICAL  
**Last Updated:** 2026-03-14

This document defines the intended role, priority components, and user actions for the active BetApp screens.

It should be read together with:

- `docs/architecture/USER_FLOW_MAP.md`
- `docs/UI_SPEC.md` only as historical context

If this document conflicts with older UI docs, this document reflects the active product direction.

## 1. Purpose

This spec translates the canonical user flow into screen-level requirements.

It defines:

- what each primary screen is for
- which components are primary versus secondary
- what the user should understand immediately
- where key seams connect across screens

## 2. Primary Screen Hierarchy

The current intended hierarchy is:

1. `Evaluate`
2. `Builder`
3. `Dashboard`
4. `History`
5. `Browse`
6. `Protocols`
7. `Notifications`
8. `Auth / Landing / Onboarding`

`Evaluate` is the product home.

`Builder` is the refinement state of the evaluation loop.

`Protocols` are core intelligence in the loop, but their dedicated destination is secondary.

## 3. Screen-by-Screen Requirements

## 3.1 Landing

### Purpose

Explain the product quickly and route the user into account creation or entry.

### Primary job

Answer:

- what this product does
- who it is for
- why it is different from a picks app

### Primary components

- value proposition headline
- screenshot or product preview
- tier/pricing entry
- primary CTA to start

### Secondary components

- deeper marketing copy
- social proof
- FAQ

### User should understand in 5 seconds

```text
This is a bettor intelligence tool that evaluates and improves slips.
```

## 3.2 Auth

### Purpose

Get the user into the product with minimal friction.

### Primary job

Route the user into the core app quickly after authentication.

### Primary components

- sign in
- sign up
- tier context if relevant

### Post-auth destination

Default destination should be the active product hub, usually `Dashboard`, unless a deeper in-progress flow should be restored.

## 3.3 Dashboard

### Purpose

Serve as the daily hub, not the core analytical identity.

### Primary job

Offer fast entry into the main loops:

- evaluate a bet
- continue refining a slip
- browse current betting context
- revisit history

### Primary components

- entry cards for Evaluate / Builder / Browse / History
- recent activity
- system or data freshness status
- quick status cards

### Secondary components

- deeper account/admin surfaces
- long-form content

### UX rule

Dashboard should route users into action quickly.

It should not compete with Evaluate as the main product identity.

## 3.4 Evaluate

### Purpose

This is the core product screen.

### Primary job

Take a bet idea and answer:

1. is it structurally strong or shaky
2. why
3. what next

### Input modes

- typed or pasted bet text
- uploaded slip image
- carry-forward from Builder or History

### OCR behavior

OCR is part of intake, not the trust moment.

The trust moment is parsed-leg confirmation.

### Primary components

- input area for bet idea
- image upload
- OCR review gate / parsed leg confirmation
- evaluate CTA
- result surface

### Result surface components

- confidence headline
- fragility score close behind
- recommendation / next action
- strengths
- risks
- protocol triggers
- Sherlock explanation

### Secondary components

- deeper technical metrics
- advanced breakdowns
- audit/proof details

### Visual priority

1. confidence
2. fragility
3. why
4. next step

### UX rule

Evaluate must not feel like a dead-end scorecard.

It must naturally hand off to Builder when refinement is needed.

## 3.5 OCR Review Gate

### Purpose

Prevent bad extraction from poisoning DNA.

### Primary job

Show parsed legs clearly enough that the user can confirm or repair them before scoring.

### Primary components

- parsed legs card list
- confidence or uncertainty cues
- edit or repair action
- proceed to evaluation action

### UX rule

Do not foreground raw OCR text as the main confirmation surface.

Parsed leg review is the canonical confirmation experience.

## 3.6 Evaluation Results

### Purpose

Turn the analysis into understandable action.

### Primary job

Give the user a clear understanding of:

- structural quality
- main sources of fragility
- what action is recommended

### Primary components

- confidence display
- fragility display
- recommendation block
- protocol modules
- why / explanation block
- guided fix CTA

### Secondary components

- edge and stability details
- advanced metrics
- governance or proof surfaces

### UX rule

The language should remain cautious.

The screen should never imply the app is guaranteeing outcomes.

## 3.7 Guided Fix

### Purpose

Convert a weak result into an actionable refinement path.

### Primary job

Map the weakness to a concrete next step.

### Preferred forms

- remove correlated leg
- replace high-volatility leg
- reduce leg count
- address injury instability

### UX rule

Guided fix should feel protocol-aware and specific, not generic.

## 3.8 Builder

### Purpose

Builder is the refinement environment.

### Primary job

Help the user tighten a slip after evaluation.

### Primary components

- current legs
- modification controls
- before/after delta
- updated signal state
- re-evaluate loop
- place/save bet action

### Secondary components

- advanced market exploration
- bulk compare views

### UX rule

Builder should preserve evaluation context and feel like a continuation of Evaluate, not a separate tool.

## 3.9 Browse

### Purpose

Support research and discovery before or during slip construction.

### Primary job

Let users inspect games, odds, and context without losing sight of the evaluation loop.

### Primary components

- games list
- market view
- data provenance / freshness
- route into Builder

### Secondary components

- deeper analytics
- protocol education

### UX rule

Browse should support the core loop, not become a detached odds portal.

## 3.10 Protocols

### Purpose

Provide a deeper destination for protocol-based workflows and saved strategy intelligence.

### Primary job

Expose protocols as reusable intelligence, not just hidden triggers.

### Primary components

- saved protocols or strategy setups
- protocol explanations
- protocol status/preferences
- advanced protocol management

### Embedded role

Protocols should mostly appear inside Evaluate and Builder.

This dedicated screen is secondary and more useful for advanced users and premium retention.

## 3.11 History

### Purpose

Act as a learning and replay surface.

### Primary job

Show:

1. what happened
2. what DNA said
3. what changed or was missed
4. which protocols fired

### Primary components

- bet/evaluation list
- result status
- original evaluation context
- re-evaluate action
- learning-oriented detail

### Secondary components

- pure ledger/accounting detail

### UX rule

History is not just archival.

It should teach the user over time.

## 3.12 Notifications

### Purpose

Bring the user back into a relevant decision flow.

### Primary job

Route the user into a useful action, not just announce events.

### Primary components

- notification list
- alert reason
- route target back into Evaluate / Builder / Browse / History

### UX rule

Notifications should point back into the core evaluation loop whenever possible.

## 4. Key UX Seams

## 4.1 OCR → Parsed Slip

This is the trust gate seam.

If this feels unreliable, the whole product feels unreliable.

## 4.2 Evaluate → Builder

This is the most important seam in the product.

If this is weak, the product becomes a scorecard instead of a decision tool.

## 4.3 Results → Bet Placement

This seam must preserve user agency.

The product informs the decision; it does not bless it.

## 4.4 Protocol Visibility

Protocols must be visible enough to feel meaningful, but not so loud that they clutter the experience.

## 5. Screen-Level Success Conditions

### Evaluate succeeds when

- users understand the top-line judgment immediately
- users can see why
- users know what to do next

### Builder succeeds when

- users can tighten a slip quickly
- re-evaluation feels natural
- the before/after delta is obvious

### OCR intake succeeds when

- users trust the parsed output
- repair is easy when needed
- bad OCR does not silently flow into DNA

### History succeeds when

- users can replay the reasoning
- outcomes feel educational
- re-evaluation is a natural next action

## 6. Primary UX Metric

The strongest leading indicator for this screen system is:

```text
re-evaluation rate
```

That metric most directly proves that the Evaluate → Builder loop is working.

## 7. Anti-Drift Rules

- Do not treat Builder as the primary home of the product.
- Do not treat Protocols as a detached add-on.
- Do not skip parsed-leg confirmation when OCR confidence is uncertain.
- Do not let result screens feel like permission slips.
- Do not reduce History to a ledger-only experience.

