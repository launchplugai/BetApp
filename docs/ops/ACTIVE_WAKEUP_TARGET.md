# Active Wake-Up Target

Status: ACTIVE
Last updated: 2026-03-16

## Memory Heartbeat

- Active stream: `frontend-dev`
- Canonical blocker: `Next/package toolchain instability still blocks trustworthy local Next verification`
- Canonical next move: `Add shared request/status tracing and route-visible live/mock mode controls to the Next dev console`
- Freshness cadence: `Re-verify after each meaningful slice or within 24 hours while active`
- Cross-check with: `CONTEXT.md`, `docs/ops/CURRENT_EXECUTION_STATE.md`, `docs/ops/FRONTEND_DEV_BOOTSTRAP.md`, `docs/ops/ACTIVE_WORKING_MEMORY_HANDOFF.yaml`

## Purpose

This is the shortest high-signal target doc for a fresh chat wake-up.

Use it when the goal is not broad orientation, but getting the next chat pointed at the real current work fast.

## Current Work Target

Product lane:

- keep turning the Next scaffold into a genuinely usable developer console for BetApp

Immediate next move:

- add shared request/status tracing and route-visible `live`/`mock` mode controls so the dashboard explains what it is doing

Why this is next:

- shared shell exists
- route-level mock behavior exists
- the main missing piece is clearer operational visibility

## Current Chat-Side Target

- working memory carry-over package is defined
- wake-up proof should use the latest handoff and latest execution state
- no further chat-side expansion should outrun BetApp product progress right now

## Wake-Up Rule

If a fresh chat needs one fast target after loading `CONTEXT.md`, use this file alongside:

- `docs/ops/CURRENT_EXECUTION_STATE.md`
- `docs/ops/ACTIVE_WORKING_MEMORY_HANDOFF.yaml`
