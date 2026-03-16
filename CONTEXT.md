# CONTEXT

Status: CANONICAL
Last updated: 2026-03-16

## Memory Heartbeat

- Active stream: `frontend-dev`
- Canonical blocker: `No major blocker; Next typecheck and build now pass locally`
- Canonical next move: `Visually verify the new route-controls and request-trace surfaces in the Next app, then choose the next dev-console refinement slice`
- Freshness cadence: `Re-verify after each meaningful slice or within 24 hours while active`
- Cross-check with: `docs/ops/CURRENT_EXECUTION_STATE.md`, `docs/ops/ACTIVE_WAKEUP_TARGET.md`, `docs/ops/FRONTEND_DEV_BOOTSTRAP.md`, `docs/ops/ACTIVE_WORKING_MEMORY_HANDOFF.yaml`

## Purpose

This is the single-file wake-up entry point for a fresh chat, reconnect, or external worker.

If you only know one file to load, load this one first.

## Wake-Up Rule

Start here, then follow the linked docs in order.

## Read Order

1. `docs/index/DOC_INDEX.md`
2. `docs/ops/BRAIN_STEM_MODULE.md`
3. `docs/ops/SOUL.md`
4. `docs/ops/CHAT_SIDE_WORKFLOW_CANON.md`
5. `docs/ops/BULLETPROOF_CHAT_INITIALIZATION_LOOP.md`
6. `docs/ops/BOOTSTRAP_PROTOCOL.md`
7. `docs/ops/CURRENT_EXECUTION_STATE.md`
8. `docs/ops/WHOLE_SYSTEM_PLAN.md`
9. `docs/ops/WORKING_MEMORY_MODULE.md`
10. `docs/ops/WORKING_MEMORY_HANDOFF_CONTRACT.md`
11. `docs/ops/NEW_CHAT_CARRYOVER_PROTOCOL.md`
12. `docs/ops/WORKING_MEMORY_STORAGE_AND_INJECTION.md`
13. `docs/ops/SYSTEM_MEMORY_ARCHITECTURE.md`
14. `docs/ops/SYSTEM_DESIGN_JOURNAL.md`
15. `docs/ops/ACTIVE_WORKING_MEMORY_HANDOFF.yaml`
16. `docs/ops/ACTIVE_WAKEUP_TARGET.md`
17. active stream docs referenced by `CURRENT_EXECUTION_STATE.md`
18. `git -C /Users/benaiahross/development/projects/betapp/app-src status --short`

## Required Startup Output

After loading this context, the agent should be able to state:

- current objective
- active stream
- blocker
- exact next move
- primary memory docs
- whether a working-memory handoff should be used

Startup is not complete until the agent emits a compact visible heartbeat block in-thread that names:

- task
- status
- blocker
- continuity surfaces
- next move

## Active Short Prompt

The minimal wake-up prompt for this environment is:

`Wake up from repo memory. Load CONTEXT.md.`
