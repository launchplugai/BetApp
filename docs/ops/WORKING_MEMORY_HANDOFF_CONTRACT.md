# Working Memory Handoff Contract

Status: DRAFT
Last updated: 2026-03-16

## Purpose

This contract defines the minimum record needed to carry the active thought from one chat into a fresh chat.

It is the payload layer for the working-memory module.

## Rule

The handoff should preserve the immediate unresolved thought, not the entire world.

It is intentionally compact.

## Minimum Record

The working-memory handoff should carry:

- `handoff_id`
- `created_at`
- `source_chat_state`
- `active_stream`
- `last_user_message`
- `active_question`
- `last_assistant_intent`
- `response_mode`
- `expected_next_response`
- `linked_memory_docs`

## Field Meanings

### `handoff_id`

Unique identifier for the carry-over record.

### `created_at`

Timestamp for freshness and stale-state detection.

### `source_chat_state`

Short description of the state being handed off.

Example:

- `awaiting_direct_answer`
- `awaiting_decision`
- `mid-implementation`

### `active_stream`

The currently active lane.

Example:

- `frontend-dev`
- `chat-workflow`
- `working-memory`

### `last_user_message`

The exact most recent meaningful user input that should be preserved.

### `active_question`

The distilled unresolved prompt the next chat should answer first.

### `last_assistant_intent`

The last meaningful assistant action or intended action.

Example:

- `answer_directly`
- `ask_for_decision`
- `continue_implementation`

### `response_mode`

The expected response shape for the immediate next reply.

Example:

- `direct_answer`
- `decision_support`
- `heartbeat_then_execute`

### `expected_next_response`

The short description of what the fresh chat should do next.

Example:

- `Answer: 4`
- `Give the next implementation step`
- `Ask the product owner to resolve the conflict`

### `linked_memory_docs`

The repo docs that the fresh chat should treat as primary context while honoring the handoff.

## Example Record

```yaml
handoff_id: wm_2026_03_16_001
created_at: 2026-03-16T15:00:00Z
source_chat_state: awaiting_direct_answer
active_stream: working-memory
last_user_message: "what is 2 + 2?"
active_question: "what is 2 + 2?"
last_assistant_intent: answer_directly
response_mode: direct_answer
expected_next_response: "Answer: 4"
linked_memory_docs:
  - docs/ops/BRAIN_STEM_MODULE.md
  - docs/ops/WORKING_MEMORY_MODULE.md
  - docs/ops/CURRENT_EXECUTION_STATE.md
```

## Acceptance Test

The contract is good enough if a fresh chat can read the handoff and know:

1. what the last unresolved user thought was
2. what response mode is expected
3. what it should say or do next
