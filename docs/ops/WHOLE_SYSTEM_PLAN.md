# Whole System Plan

Status: CANONICAL
Last updated: 2026-03-16

## Purpose

This document places the chat-side operating system into one modular roadmap so higher layers can be added without destabilizing the foundation.

## Core Idea

Do not build higher cognition on top of a weak autonomic layer.

The system should be developed in this order:

1. brain stem
2. working memory
3. routing
4. correction
5. indexed memory
6. planning and orchestration

## Layer 1: Brain Stem

Status: packaged

Responsibilities:

- startup
- continuity
- recovery
- heartbeat
- conflict reflex
- post-slice lock

Primary docs:

- `docs/ops/BRAIN_STEM_MODULE.md`
- `docs/ops/BRAIN_STEM_PACKAGING_CHECKLIST.md`

## Layer 2: Working Memory

Status: active

Responsibilities:

- carry the immediate active thought across chat boundaries
- retain last user prompt and unresolved response intent
- preserve the current response mode for a fresh wake-up
- support "new chat, same thought" continuity

Primary doc:

- `docs/ops/WORKING_MEMORY_MODULE.md`

## Layer 3: Routing

Status: future

Responsibilities:

- determine which lane is active
- separate product work from process work
- prioritize urgent vs non-urgent tasks
- direct signals to the correct module

## Layer 4: Correction

Status: future

Responsibilities:

- detect execution drift quickly
- reduce repeated workflow mistakes
- improve smoothness and reliability of the operating loop

## Layer 5: Indexed Memory

Status: future

Responsibilities:

- retrieve prior decisions by relevance, not by brute-force file scanning
- strengthen recall of recent and important context
- support continuity beyond the immediate last thought

## Layer 6: Planning And Orchestration

Status: future

Responsibilities:

- multi-step strategy
- multi-stream coordination
- multi-agent or VPS worker delegation
- modular growth without loss of control

## Current Priority

Finish the working-memory layer next.

That is the missing piece between:

- safe wake-up
- and true carry-forward continuity

## Rule

Each new layer must:

- have a clear module boundary
- not duplicate the role of lower layers
- integrate with bootstrap and state docs
- be recoverable from repo memory
