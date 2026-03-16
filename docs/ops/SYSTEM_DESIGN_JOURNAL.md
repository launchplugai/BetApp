# System Design Journal

Status: ACTIVE
Last updated: 2026-03-16

## Purpose

This is the running design journal for the chat-side operating system.

Use it to capture:

- why the architecture changed
- what abstractions were introduced
- what worked
- what should be revisited later

Keep entries concise and date-stamped.

## Entries

### 2026-03-16

Built and canonized the foundational stack:

- `CONTEXT.md` as the lobby
- brain stem as the autonomic layer
- `SOUL.md` as enduring core orientation
- workflow canon and initialization loop as behavioral infrastructure
- working-memory module as the next continuity layer

Main design insight:

- storage alone is not continuity
- continuity requires reflexes, routing, and explicit startup behavior

Main systems decision:

- build the chat-side operating system modularly
- keep it separate from BetApp product behavior
- treat working memory as the next bridge from “same project” to “same thought”

### 2026-03-16: phase-driven coding loop launch

Tested a visible coding loop that does:

- target definition
- research session
- plan session
- execute session
- heartbeat between phases

Debrief:

- it improved clarity without stalling implementation
- the heartbeat made phase transitions legible to the user
- the loop works best when it ends in real edits, validation, and memory refresh instead of stopping after planning

Launch decision:

- treat this as the preferred pattern for substantive coding slices while heartbeat mode is active
- keep it lightweight and avoid forcing the loop onto trivial tasks
