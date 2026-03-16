# Working Memory Module

Status: ACTIVE
Last updated: 2026-03-16

## Purpose

The working memory module preserves the immediate active thought across chat boundaries.

This is the layer that enables:

- "new chat, same thought"
- continuation of the last unresolved prompt
- restoration of the expected immediate response mode

## Problem It Solves

The brain stem restores:

- identity
- workflow
- current project state
- active stream
- next move

But it does not yet restore:

- the exact last conversational prompt
- the exact unresolved assistant intent
- the immediate answer expected next

Working memory fills that gap.

## Module Boundary

This module is chat-side and workflow-side.

It is not product behavior.
It sits above the brain stem and below higher planning layers.

## Responsibilities

1. retain the last meaningful user prompt
2. retain the last unresolved assistant intent
3. retain the current expected reply mode
4. package a handoff for fresh-chat wake-up
5. allow re-entry into the active thought without re-deriving it from scratch

## Minimal Working-Memory Record

The module should eventually preserve at least:

- `last_user_message`
- `last_assistant_intent`
- `response_mode`
- `active_question`
- `handoff_timestamp`

## Example

If the final exchange in one thread is:

- user: `what is 2 + 2?`

then a fresh chat with working memory should be able to wake up and know:

- active question: `what is 2 + 2?`
- expected response mode: `direct answer`
- answer: `4`

## Relationship To Brain Stem

Brain stem says:

- wake up safely
- know who you are
- know what system you are in

Working memory says:

- here is the thought you were in the middle of

## Startup Dependency

Working memory should only be used after brain-stem initialization succeeds.

If the startup checksum fails, working memory should not be treated as trustworthy.

## Future Deliverables

- working-memory handoff schema
- working-memory bootstrap hook
- explicit carry-forward test
- recovery behavior when working-memory state is missing or stale

Current supporting docs:

- `docs/ops/WORKING_MEMORY_HANDOFF_CONTRACT.md`
- `docs/ops/NEW_CHAT_CARRYOVER_PROTOCOL.md`
- `docs/ops/WORKING_MEMORY_STORAGE_AND_INJECTION.md`
- `docs/ops/ACTIVE_WORKING_MEMORY_HANDOFF.yaml`
- `docs/ops/NEW_CHAT_WAKEUP_PROMPT_TEMPLATE.md`

## Next Design Question

How should working-memory handoff be stored and injected:

- repo-backed state
- wrapper/orchestrator injection
- external worker memory store
- or a combination

That question should be answered before implementation begins.
