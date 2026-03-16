# Environment Bootstrap: Chat Workflow

Status: ACTIVE
Last updated: 2026-03-16

## Purpose

This is the bootstrap for the collaboration environment itself.

Use it when:

- a new chat starts
- a reconnect happens
- an external worker or VPS agent needs to understand how to operate here
- continuity feels at risk

## Read Order

1. `CONTEXT.md`
2. `docs/index/DOC_INDEX.md`
3. `docs/ops/BRAIN_STEM_MODULE.md`
4. `docs/ops/SOUL.md`
5. `docs/ops/CHAT_SIDE_WORKFLOW_CANON.md`
6. `docs/ops/BULLETPROOF_CHAT_INITIALIZATION_LOOP.md`
7. `docs/ops/BOOTSTRAP_PROTOCOL.md`
8. `docs/ops/CURRENT_EXECUTION_STATE.md`
9. `docs/ops/WHOLE_SYSTEM_PLAN.md`
10. `docs/ops/WORKING_MEMORY_MODULE.md`
11. `docs/ops/ACTIVE_WORKING_MEMORY_HANDOFF.yaml`
12. stream-specific bootstrap/build/context docs for the active lane
13. `git -C /Users/benaiahross/development/projects/betapp/app-src status --short`

## What This Bootstrap Must Answer

After reading this set, the agent should know:

- how to report progress
- how to preserve continuity
- how to escalate conflicts
- which docs are the current operational memory
- what active implementation stream is in progress

This bootstrap is only considered complete when the agent posts a compact heartbeat in-thread that makes the current task, blocker, continuity surfaces, and exact next move visible to the user.

If continuity confidence is low, run the repo memory-freshness checker before declaring wake-up complete.

Verification-only refreshes are allowed, but do not auto-touch timestamps without actually re-reading and cross-checking the active memory surfaces.

## Current Local Workflow Truth

- heartbeat mode is active by default unless the user says otherwise
- continuity notes should appear in progress updates
- repo docs must be updated during meaningful cycles, not only at the end
- the self-improvement pass is automatic when a real workflow weakness appears
- the product owner values visible planning, visible files, and durable recovery paths
- product work and chat-side workflow work must stay distinct

## Exact Next Recovery Step

If continuity feels shaky:

1. re-read `docs/ops/BULLETPROOF_CHAT_INITIALIZATION_LOOP.md`
2. re-read the active stream bootstrap doc
3. restate the exact next move before continuing
