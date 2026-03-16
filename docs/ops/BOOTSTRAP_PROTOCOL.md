# Bootstrap Protocol

**Status:** CANONICAL  
**Last Updated:** 2026-03-16

This is the canonical bootstrap path for any new chat, agent, or reconnecting implementation thread.

If any older sprint, session, or planning document conflicts with this protocol, this protocol wins.

## 1. Purpose

Provide one reliable startup sequence for resuming work without depending on prior chat memory.

## 2. Required Bootstrap Order

Read these in order:

1. `README.md`
2. `CONTEXT.md`
3. `docs/index/DOC_INDEX.md`
4. `docs/ops/BRAIN_STEM_MODULE.md`
5. `docs/ops/SOUL.md`
6. `docs/ops/CHAT_SIDE_WORKFLOW_CANON.md`
7. `docs/ops/BULLETPROOF_CHAT_INITIALIZATION_LOOP.md`
8. `docs/ops/CURRENT_EXECUTION_STATE.md`
9. `docs/architecture/SYSTEM_RESTORATION_BLUEPRINT.md`
10. `docs/contracts/AIRLOCK_MEMBRANE_CONTRACT.md`
11. `docs/contracts/SHERLOCK_DNA_INTERACTION_CONTRACT.md`
12. active sprint-specific docs referenced by `CURRENT_EXECUTION_STATE.md`
13. `git status --short`

## 3. Startup Questions This Must Answer

After bootstrap, the agent must be able to answer:

- What architecture is current?
- What sprint or slice is active?
- What was just completed?
- What validation most recently passed?
- What is the exact next step?

Bootstrap is not complete until those answers are surfaced in a visible in-thread heartbeat update before implementation begins.

Minimum heartbeat proof:

- task
- status
- blocker
- continuity surfaces
- next move

## 4. Conflict Rule

Treat these as non-bootstrap historical artifacts unless explicitly needed:

- old sprint locks
- historical sprint plans
- old session reports
- speculative feature-planning docs

Do not start from them.

## 5. Canonical State Docs

The canonical handoff/state pair is:

- `docs/ops/CONTEXT_LOCK_PROTOCOL.md`
- `docs/ops/CURRENT_EXECUTION_STATE.md`

The canonical chat-side workflow document is:

- `docs/ops/CHAT_SIDE_WORKFLOW_CANON.md`

## 6. Git Rule

At coherent sprint boundaries:

- update the canonical state docs
- update the relevant sprint/architecture docs
- cut a local git commit

## 7. Current Restoration Context

The current architecture restoration sequence is tracked in:

- `docs/ops/ARCHITECTURE_RESTORATION_SPRINT_MAP.md`

The next step is always whatever is recorded in:

- `docs/ops/CURRENT_EXECUTION_STATE.md`
