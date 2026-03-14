# ADR-2026-03-14 Canonical Bootstrap And Context Lock

**Status:** ACCEPTED  
**Date:** 2026-03-14

## Context

BetApp now has enough architecture, governance, UX, and refactor state that chat memory alone is an unsafe handoff surface.

Older sprint and session documents still exist in the repo and can conflict with the current architecture-restoration path if an agent starts from the wrong place.

## Decision

BetApp will use a canonical bootstrap and context-lock process.

The canonical bootstrap entrypoint is:

- `docs/ops/BOOTSTRAP_PROTOCOL.md`

The canonical state/handoff pair is:

- `docs/ops/CONTEXT_LOCK_PROTOCOL.md`
- `docs/ops/CURRENT_EXECUTION_STATE.md`

At coherent sprint boundaries, the repo state must be locked into docs and a local git commit should be created.

## Consequences

- new chats and reconnects must bootstrap from the canonical sequence, not from old sprint or session docs
- context preservation becomes a repo process, not only a conversation habit
- older sprint/session docs are historical unless explicitly referenced
- future agents can resume from repo docs plus git without relying on lost chat context

## References

- `docs/ops/BOOTSTRAP_PROTOCOL.md`
- `docs/ops/CONTEXT_LOCK_PROTOCOL.md`
- `docs/ops/CURRENT_EXECUTION_STATE.md`
- `docs/ops/ARCHITECTURE_RESTORATION_SPRINT_MAP.md`
