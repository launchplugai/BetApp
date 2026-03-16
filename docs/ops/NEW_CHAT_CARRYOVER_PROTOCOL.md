# New Chat Carry-Over Protocol

Status: DRAFT
Last updated: 2026-03-16

## Purpose

This protocol defines how a fresh chat should continue the immediate active thought from the prior chat.

It sits above the brain stem and uses the working-memory handoff contract.

## Preconditions

Before carry-over is trusted:

1. brain-stem initialization must succeed
2. startup checksum must be clean
3. a valid working-memory handoff record must be present

If any of those fail, fall back to brain-stem-only recovery.

## Carry-Over Sequence

### Step 1: Initialize

Run the standard brain-stem startup:

- bootstrap docs
- canon docs
- current execution state
- active stream docs
- git status

### Step 2: Verify

Produce the startup checksum:

- objective
- stream
- blocker
- next
- memory docs

### Step 3: Read Handoff

Read the working-memory handoff record.

Confirm:

- it is fresh enough to trust
- it matches the active stream
- it defines a clear response mode

### Step 4: Continue Thought

The fresh chat should answer or act according to:

- `active_question`
- `response_mode`
- `expected_next_response`

### Step 5: Resume Normal Operation

After the immediate carry-over is handled:

- return to normal heartbeat behavior
- continue using repo memory as primary long-lived state

## Fallback Rule

If the handoff is missing, stale, conflicting, or ambiguous:

- do not fake carry-over
- say continuity was partial
- fall back to the brain stem

## First Milestone

The first milestone is explicit/manual carry-over.

That means:

- a handoff record exists
- a fresh chat can read it
- the fresh chat can continue the exact last unresolved thought

Automatic carry-over is a later layer and should not be claimed early.

## Test Case

Prior chat ends with:

- user: `what is 2 + 2?`

Carry-over handoff defines:

- `active_question: "what is 2 + 2?"`
- `response_mode: direct_answer`
- `expected_next_response: "Answer: 4"`

Fresh chat result:

- `4`
