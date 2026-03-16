# Chat-Side Workflow Canon

Status: CANONICAL
Last updated: 2026-03-16

## Purpose

This document defines the collaboration workflow for this environment.

It is not product behavior.
It is the operating canon for how the agent should preserve continuity, report progress, escalate conflicts, and improve the working rhythm over time.

## Core Rule

Repo docs are primary memory.
Chat memory is not trusted as the only source of truth.
This workflow is mandatory while heartbeat mode is active.

## Prime Directives

1. Preserve continuity while building.
2. Keep implementation and recoverability moving together.
3. Escalate meaningful instruction conflicts instead of guessing.
4. Improve the workflow in small reusable increments.
5. Keep chat-side process work separate from product features unless explicitly requested otherwise.
6. Use the bulletproof initialization loop on new chats, reconnects, or when continuity feels shaky.
7. Do not start implementation until a startup checksum can be stated cleanly.
8. Do not skip the self-improvement pass when a real workflow failure mode is discovered.
9. Do not fake freshness by auto-updating timestamps without a real cross-check of active memory surfaces.

## Standard Heartbeat

Use this block while heartbeat mode is active:

```text
++++++ HEARTBEAT +++++++

TASK: <current task>
STATUS: <state>
LATEST: <what just changed>
BLOCKER: <main blocker or none>
USING: <active skills/workflows>
CONTEXT: <how continuity is being protected>
NEXT: <single next move>
```

## Direct Address Convention

When the agent wants to explicitly bring something to the product owner's attention, it should use a clear direct-address label instead of assuming the whole heartbeat will be read closely.

Preferred forms:

- `TO BEN:`
- `CHAT:`
- `PRODUCT OWNER:`

Use direct address for:

- meaningful decisions
- instruction conflicts
- hidden risks
- important clarifications
- moments where the human should really notice the point

Do not bury those messages inside ordinary status text if they need human attention.

## Required Continuity Surfaces

For active implementation streams, maintain:

- `docs/ops/CURRENT_EXECUTION_STATE.md`
- a stream bootstrap doc
- a stream build tracker
- a stream context/continuity log
- `docs/index/DOC_INDEX.md` when adding new docs

These are guardrail surfaces, not optional documentation.
If they are stale enough to mislead the next cycle or next chat, refresh them before continuing.

When possible, keep the active stream, canonical blocker, and canonical next move aligned across those surfaces so drift can be checked mechanically.

## Improvement Loop

After meaningful cycles:

- identify one momentum source or failure mode
- make one small reusable workflow improvement if warranted
- avoid theory-heavy process churn

When a cycle exposes a real workflow weakness, this loop is part of the work itself.
Do not postpone it as cleanup.

Examples of valid improvements:

- better heartbeat formatting
- better context-lock timing
- better escalation wording
- better state-doc structure
- better separation between product work and chat-side process work
- better freshness and mismatch detection across memory surfaces

## Conflict Rule

If instructions conflict and the consequence is meaningful:

1. stop
2. state the conflict plainly
3. ask the product owner

Do not hide real conflict behind optimistic assumptions.

## Relationship To Skills

The local skill `anti-amnesia-heartbeat` implements this workflow behavior.

If the skill is unavailable, this canon still governs the expected behavior.

The canonical startup loop for this behavior is:

- `docs/ops/BULLETPROOF_CHAT_INITIALIZATION_LOOP.md`
