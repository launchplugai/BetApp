# New Chat Wake-Up Prompt Template

Status: DRAFT
Last updated: 2026-03-16

Use this template when starting a fresh chat that should continue the active thought from the working-memory handoff.

## Template

```text
Initialize from repo memory first.

Read in order:
1. CONTEXT.md
2. docs/ops/ACTIVE_WORKING_MEMORY_HANDOFF.yaml
3. git -C /Users/benaiahross/development/projects/betapp/app-src status --short

Then:
- produce the startup checksum
- verify whether the working-memory handoff is trustworthy
- if trustworthy, continue the active thought using:
  - active_question
  - response_mode
  - expected_next_response
- if not trustworthy, say continuity is partial and fall back to brain-stem recovery

Begin with a heartbeat block and then continue.
```
