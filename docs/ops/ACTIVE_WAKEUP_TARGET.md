# Active Wake-Up Target

Status: ACTIVE
Last updated: 2026-03-16

## Memory Heartbeat

- Active stream: `frontend-dev`
- Canonical blocker: `No major blocker; Next typecheck and build now pass locally`
- Canonical next move: `Visually verify the new route-controls and request-trace surfaces in the Next app, then choose the next dev-console refinement slice`
- Freshness cadence: `Re-verify after each meaningful slice or within 24 hours while active`
- Cross-check with: `CONTEXT.md`, `docs/ops/CURRENT_EXECUTION_STATE.md`, `docs/ops/FRONTEND_DEV_BOOTSTRAP.md`, `docs/ops/ACTIVE_WORKING_MEMORY_HANDOFF.yaml`

## Purpose

This is the shortest high-signal target doc for a fresh chat wake-up.

Use it when the goal is not broad orientation, but getting the next chat pointed at the real current work fast.

## Current Work Target

Product lane:

- keep turning the Next scaffold into a genuinely usable developer console for BetApp

Immediate next move:

- visually verify the new route-controls and request-trace surfaces in the Next app

Complete slice:

- shared trace/status panel pattern across Evaluate, OCR Review, Builder, and History
- route-visible mode controls on each major screen
- shell-level visibility that makes current route state obvious at a glance
- local Next verification is restored through typecheck and production build

Why this is next:

- the operator-visibility slice is now in place
- local Next verification is restored
- the next useful proof is direct visual verification of the new screens

## Current Chat-Side Target

- working memory carry-over package is defined
- wake-up proof should use the latest handoff and latest execution state
- no further chat-side expansion should outrun BetApp product progress right now

## Wake-Up Rule

If a fresh chat needs one fast target after loading `CONTEXT.md`, use this file alongside:

- `docs/ops/CURRENT_EXECUTION_STATE.md`
- `docs/ops/ACTIVE_WORKING_MEMORY_HANDOFF.yaml`
