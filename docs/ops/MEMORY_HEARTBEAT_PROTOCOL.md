# Memory Heartbeat Protocol

Status: ACTIVE
Last updated: 2026-03-16

## Purpose

Keep active memory surfaces fresh and mutually consistent without faking freshness through blind timestamp churn.

## Core Rule

Do not auto-update memory-file timestamps on a timer without a real cross-check.

A file is fresh only when someone actually re-read it against the active memory set and confirmed:

- active stream
- canonical blocker
- canonical next move
- freshness cadence

## Required Heartbeat Fields

Each active memory surface should expose:

- `Active stream`
- `Canonical blocker`
- `Canonical next move`
- `Freshness cadence`
- `Cross-check with`

For YAML handoff files, use equivalent keys.

## Freshness Cadence

While a stream is active:

- refresh after each meaningful implementation slice that changes state
- otherwise re-verify within 24 hours before relying on wake-up memory

If the stream goes quiet:

- do a verification pass before the next wake-up instead of fake auto-touching files

## Mismatch Rule

If active memory docs disagree on stream, blocker, or next move:

- classify the condition as `state stale`
- stop treating wake-up as reliable
- refresh the docs before continuing

## Checker

Run:

```bash
cd /Users/benaiahross/development/projects/betapp/app-src
python3 scripts/check_memory_freshness.py
```

Use the checker:

- during wake-up when continuity confidence is low
- before a wake-up proof
- after meaningful process-hardening changes

## Active Surfaces For Frontend-Dev

- `CONTEXT.md`
- `docs/ops/CURRENT_EXECUTION_STATE.md`
- `docs/ops/ACTIVE_WAKEUP_TARGET.md`
- `docs/ops/FRONTEND_DEV_BOOTSTRAP.md`
- `docs/ops/FRONTEND_DEV_BUILD_TRACKER.md`
- `docs/ops/FRONTEND_DEV_CONTEXT_LOG.md`
- `docs/ops/ACTIVE_WORKING_MEMORY_HANDOFF.yaml`
