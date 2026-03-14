# Context Lock Protocol

**Status:** CANONICAL  
**Last Updated:** 2026-03-14

Use this protocol at sprint boundaries, before likely context compaction, and before handing work to a new chat.

## 1. Purpose

Make the repo the primary handoff surface.

Context must survive:

- long implementation threads
- reconnects
- sprint transitions
- agent changes

## 2. Required Actions

1. Update `docs/ops/CURRENT_EXECUTION_STATE.md`.
2. Update the relevant sprint doc or sprint map if scope/status changed.
3. Update `docs/index/DOC_INDEX.md` if new lock/state docs were added.
4. Record the latest validation command and result.
5. Record the exact next implementation step.
6. Cut a local git commit when the repo is coherent.

## 3. Minimum State To Capture

Every context lock must capture:

- current objective
- most recent completed slice
- files or seams touched
- validation command
- validation result
- known debt or risks
- exact next move
- bootstrap docs for the next chat

## 4. Commit Rule

Commit at meaningful sprint or milestone boundaries.

Do not commit:

- half-broken states
- throwaway experiments
- junk or ephemeral files

Use milestone-oriented commit messages.

## 5. Bootstrap Order For New Chats

Start with:

1. `README.md`
2. `docs/index/DOC_INDEX.md`
3. `docs/ops/CURRENT_EXECUTION_STATE.md`
4. the current architecture/contracts for the active sprint
5. `git status --short`

## 6. Guardrails

- Do not rely on chat memory as primary state.
- Do not let final responses substitute for repo-state docs.
- Do not leave “next step” ambiguous.
- Prefer one clear next move over a menu of possible directions.
