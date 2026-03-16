# Brain Stem Packaging Checklist

Status: ACTIVE
Last updated: 2026-03-16

Use this checklist when recreating the environment foundation in a new chat, clone, or worker context.

## Required Files

- `docs/ops/SOUL.md`
- `docs/ops/CHAT_SIDE_WORKFLOW_CANON.md`
- `docs/ops/BULLETPROOF_CHAT_INITIALIZATION_LOOP.md`
- `docs/ops/ENVIRONMENT_BOOTSTRAP_CHAT_WORKFLOW.md`
- `docs/ops/BOOTSTRAP_PROTOCOL.md`
- `docs/ops/CURRENT_EXECUTION_STATE.md`
- active stream bootstrap/build/context docs
- `docs/index/DOC_INDEX.md`

## Required Behaviors

- heartbeat reporting
- startup checksum before implementation
- stop-and-escalate on meaningful conflict
- repo-memory updates after meaningful slices
- recovery ritual when continuity drops

## Packaging Test

The package is working if a fresh chat can answer:

1. What is the current objective?
2. What is the active stream?
3. What is blocked?
4. What is the exact next move?
5. What docs are the current memory?

## Current Status

- packaged in-repo
- canonized
- connected to bootstrap
- ready to serve as the modular foundation for higher layers
