# Working Memory Storage And Injection

Status: DRAFT
Last updated: 2026-03-16

## Purpose

This document defines where the explicit/manual working-memory handoff lives and how it is injected into a fresh chat.

## First Practical Version

The first practical version is file-backed and manual.

That means:

- the active handoff lives in the repo
- a fresh chat or operator reads it explicitly
- a wake-up prompt includes the handoff

## Storage Location

Primary active handoff file:

- `docs/ops/ACTIVE_WORKING_MEMORY_HANDOFF.yaml`

This file should contain only the current active thought handoff.

It should be overwritten when a new active carry-over target replaces the previous one.

## Injection Path

Manual injection path:

1. run brain-stem bootstrap
2. read `docs/ops/ACTIVE_WORKING_MEMORY_HANDOFF.yaml`
3. use `docs/ops/NEW_CHAT_WAKEUP_PROMPT_TEMPLATE.md`
4. start the fresh chat with the wake-up payload

## Future Injection Paths

Later, this can be upgraded to:

- orchestrator injection
- VPS worker injection
- wrapper-assisted fresh chat startup

But the file-backed manual version is the first honest milestone.

## Trust Rules

Only trust the handoff if:

- the brain stem initialized cleanly
- the active stream matches
- the handoff is fresh enough to make sense
- the expected next response is clear

If those fail, fall back to brain-stem-only recovery.
