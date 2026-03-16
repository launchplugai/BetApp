# System Memory Architecture

Status: CANONICAL
Last updated: 2026-03-16

## Purpose

This document is the stable memory map for the chat-side operating system.

Use it to understand where different kinds of memory live and which layer is responsible for them.

## Memory Layers

### 1. Core Identity Memory

Location:

- `docs/ops/SOUL.md`

Role:

- enduring orientation
- anti-drift posture
- stable traits and commitments

### 2. Workflow Memory

Location:

- `docs/ops/CHAT_SIDE_WORKFLOW_CANON.md`
- `docs/ops/BULLETPROOF_CHAT_INITIALIZATION_LOOP.md`

Role:

- heartbeat behavior
- initialization rules
- escalation rules
- recovery reflexes

### 3. Active State Memory

Location:

- `docs/ops/CURRENT_EXECUTION_STATE.md`
- active stream bootstrap/build/context docs

Role:

- what is happening now
- what just happened
- what is blocked
- exact next move

### 4. Working Memory

Location:

- `docs/ops/ACTIVE_WORKING_MEMORY_HANDOFF.yaml`
- `docs/ops/WORKING_MEMORY_HANDOFF_CONTRACT.md`
- `docs/ops/NEW_CHAT_CARRYOVER_PROTOCOL.md`

Role:

- immediate unresolved thought
- last user prompt
- expected next response mode
- fresh-chat carry-over

### 5. Entry Memory

Location:

- `CONTEXT.md`

Role:

- single-file lobby
- initial routing into the correct memory surfaces

## Rule

Do not overload one memory layer with the job of another.

Examples:

- `SOUL.md` should not carry active implementation state
- `CURRENT_EXECUTION_STATE.md` should not carry whole workflow canon
- working-memory handoff should not become a full project archive

## Next Layer

As the system grows, indexed memory and routing memory should be added above these layers, not by bloating the current ones.
