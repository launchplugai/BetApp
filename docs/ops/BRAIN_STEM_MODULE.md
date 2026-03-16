# Brain Stem Module

Status: CANONICAL
Last updated: 2026-03-16

## Purpose

This document packages the minimum viable autonomic layer for this environment.

The brain stem is the part of the system responsible for:

- continuity
- wake-up / startup
- recovery
- rhythm
- interruption tolerance
- reflexive conflict handling

It exists so higher-order planning and execution can happen without constant collapse or drift.

## Module Boundary

This module is chat-side and workflow-side.

It is not BetApp product behavior.
It is the operating foundation that lets product work continue safely.

## Module Components

### 1. Core Orientation

- `docs/ops/SOUL.md`

Role:

- defines the enduring operating core
- keeps behavior aligned under stress or ambiguity

### 2. Workflow Canon

- `docs/ops/CHAT_SIDE_WORKFLOW_CANON.md`

Role:

- defines heartbeat, continuity, escalation, and improvement behavior

### 3. Startup Loop

- `docs/ops/BULLETPROOF_CHAT_INITIALIZATION_LOOP.md`

Role:

- defines the safe startup and recovery loop
- ensures initialization proves understanding before execution

### 4. Environment Bootstrap

- `docs/ops/ENVIRONMENT_BOOTSTRAP_CHAT_WORKFLOW.md`

Role:

- gives the read order for restoring chat-side operating context in this environment

### 5. Global Bootstrap

- `docs/ops/BOOTSTRAP_PROTOCOL.md`

Role:

- connects the brain stem to the wider project bootstrap path

### 6. Active State Memory

- `docs/ops/CURRENT_EXECUTION_STATE.md`
- stream bootstrap/build/context docs

Role:

- carries current objective, blockers, next move, and active-lane recovery state

## Reflexes

The brain stem module provides these reflexes:

- startup reflex
  - read canon, bootstrap, state, stream docs, git status
- checksum reflex
  - restate objective, stream, blocker, next move, memory docs
- conflict reflex
  - stop and escalate when instructions meaningfully conflict
- heartbeat reflex
  - report task, status, latest, blocker, skills, continuity, next
- lock reflex
  - update repo memory after meaningful slices
- recovery reflex
  - reinitialize when drift indicators appear
- freshness reflex
  - cross-check active memory surfaces for shared stream, blocker, next move, and freshness cadence

## Startup Checksum

The module is not considered initialized until the agent can state:

- objective
- active stream
- blocker
- next move
- memory docs

## Red Flags

Re-run the brain stem if:

- the next move gets fuzzy
- the active stream becomes ambiguous
- canon appears to conflict with a new instruction
- memory surfaces cannot be named
- work starts outrunning recoverability

## Packaging Rule

This module should be portable.

To recreate it elsewhere, the minimum package is:

1. core orientation doc
2. workflow canon doc
3. startup loop doc
4. environment bootstrap doc
5. current execution state doc
6. stream-specific bootstrap/build/context docs

## What Comes Next

Once the brain stem is stable, higher layers can be added modularly:

- routing layer
- correction layer
- indexed memory layer
- planning/orchestration layer

But those should be built on top of this module, not instead of it.

## Reliability Upgrades To Keep

- require visible startup heartbeat proof, not silent initialization
- keep shared memory-heartbeat metadata on active memory docs
- prefer freshness checks over fake auto-touched timestamps
- use a checker to flag stale or mismatched memory surfaces before wake-up proofs
