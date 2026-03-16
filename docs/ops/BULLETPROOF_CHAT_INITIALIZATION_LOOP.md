# Bulletproof Chat Initialization Loop

Status: CANONICAL
Last updated: 2026-03-16

## Purpose

This is the hardened startup loop for new chats, reconnects, agent swaps, and recovery after context loss.

It is designed to answer one question reliably:

How do we go from a fresh thread to safe, momentum-preserving execution without depending on memory?

## Initialization Loop

### Phase 1: Orient

Read in order:

1. `docs/index/DOC_INDEX.md`
2. `docs/ops/CHAT_SIDE_WORKFLOW_CANON.md`
3. `docs/ops/ENVIRONMENT_BOOTSTRAP_CHAT_WORKFLOW.md`
4. `docs/ops/BOOTSTRAP_PROTOCOL.md`
5. `docs/ops/CURRENT_EXECUTION_STATE.md`
6. active stream bootstrap/build/context docs
7. `git -C /Users/benaiahross/development/projects/betapp/app-src status --short`

### Phase 2: Verify

Before starting implementation, the agent must be able to state:

- current objective
- current active stream
- most recent completed slice
- current blocker
- exact next move
- current continuity surfaces

If any item is unclear, pause and resolve it from repo docs before building.

### Phase 2.5: Preflight Checksum

Before writing code or changing files, the agent must produce a compact startup checksum:

- objective: `<one sentence>`
- stream: `<active lane>`
- blocker: `<main blocker or none>`
- next: `<single next move>`
- memory docs: `<which docs are now primary>`

If the checksum cannot be produced cleanly, initialization is incomplete.

If a memory-freshness checker exists for the repo, run it during startup or before wake-up proof whenever continuity confidence is low.

### Phase 3: Announce

Start work with a heartbeat-style update that includes:

- task
- status
- latest understanding
- continuity handling
- next move

If no visible heartbeat block is emitted after bootstrap, classify the startup as `boot failed` and do not treat initialization as complete.

### Phase 4: Execute

Do the smallest meaningful slice that advances the active objective.

### Phase 5: Lock

After the slice:

- update execution state if objective/next move changed
- update stream bootstrap/build/context docs if the stream changed
- update the docs index if new docs were added
- keep the next move singular

## Hardening Passes

This loop has been explicitly improved in seven passes.

### Pass 1: Canonical startup order

Problem:

- startup order could drift between chats

Safeguard:

- one fixed read order across repo index, chat canon, bootstrap, execution state, stream docs, and git status

### Pass 2: Initialization gate

Problem:

- an agent can start coding before it can actually state the current objective and next move

Safeguard:

- mandatory verification questions before implementation

### Pass 3: Conflict trap

Problem:

- instructions can conflict and get papered over with optimistic assumptions

Safeguard:

- explicit stop-and-escalate rule when meaningful conflicts exist

### Pass 4: Stream-specific recovery

Problem:

- generic bootstrap alone is not enough for active lanes like frontend-dev

Safeguard:

- every active lane gets its own bootstrap, build tracker, and context log

### Pass 5: Post-slice lock

Problem:

- implementation can outrun recoverability

Safeguard:

- after each meaningful slice, update repo memory before declaring the step stable

### Pass 6: Startup checksum and red flags

Problem:

- a startup sequence can be performed mechanically without proving real understanding
- continuity drift can begin quietly before anyone notices

Safeguard:

- require a compact startup checksum before implementation
- define red-flag triggers that force re-initialization before continuing

### Pass 7: Startup heartbeat proof

Problem:

- a startup can reconstruct state internally while leaving no visible sign that heartbeat mode is actually active

Safeguard:

- require a visible in-thread heartbeat block after bootstrap
- treat missing heartbeat proof as a `boot failed` startup rather than a style issue

### Pass 8: Freshness mismatch detection

Problem:

- memory docs can all exist yet quietly drift apart on stream, blocker, or next move

Safeguard:

- keep shared heartbeat metadata on active memory docs
- use a checker to flag stale or mismatched active surfaces before relying on them

## Operating Questions

At any point, the agent should be able to answer:

1. What are we trying to finish right now?
2. What doc proves that?
3. What is the single next move?
4. What would the next chat read first if this one died?
5. What changed in repo memory during this cycle?

## Red-Flag Triggers

Re-run initialization before continuing if any of these happen:

- the exact next move becomes fuzzy
- multiple possible active streams seem equally plausible
- a new instruction appears to conflict with canon or current state
- the agent cannot name which docs are the current memory surfaces
- the agent starts coding before it can restate objective, blocker, and next move
- the agent claims wake-up is complete without emitting a visible heartbeat
- the thread has drifted long enough that confidence in continuity drops materially
- active memory docs disagree on stream, blocker, or next move

## Failure Recovery Ritual

If momentum feels shaky:

1. stop coding
2. re-run the initialization loop
3. restate the objective and exact next move
4. only then continue
