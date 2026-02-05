# Truth × Experience Foundation

**Sprint S2-FND Charter**

This document defines the foundational principle for all feature development in the DNA Bet Engine.

---

## Core Principle

Every feature, metric, or output must satisfy **BOTH** dimensions:

1. **TRUTH** — Correct, defensible, verifiable
2. **EXPERIENCE** — Confidence, intuition, emotional credibility

**Neither alone is sufficient.**

---

## What is TRUTH?

Truth means the output is:

- **Factually correct**: No logical errors, no misrepresentation of data
- **Defensible**: Can be explained and justified with evidence
- **Testable**: Passes automated tests and manual verification
- **Deterministic**: Same input produces same output (where appropriate)
- **Traceable**: Source of truth can be identified and audited

**Examples:**
- ✅ Structural snapshot counts props correctly (2 props = 2 props)
- ✅ Correlation detection works when game_id matches
- ❌ Snapshot shows 0 props when 2 exist (bug)
- ❌ Score changes on identical input (non-determinism)

---

## What is EXPERIENCE?

Experience means the output:

- **Inspires confidence**: User trusts it without second-guessing
- **Matches intuition**: Aligns with user's mental model
- **Feels credible**: Tone and framing are appropriate
- **Reduces anxiety**: Doesn't create doubt or confusion
- **Provides context**: User understands *why*, not just *what*

**Examples:**
- ✅ "2 player props detected" (clear, confident)
- ✅ "Same-game correlation: both legs reference Lakers-Celtics" (grounded)
- ❌ "2 props (maybe)" (undermines confidence)
- ❌ "Correlation detected" (no context, feels arbitrary)

---

## The Intersection

Features must pass **BOTH** tests:

| Truth | Experience | Result |
|-------|-----------|--------|
| ✅ | ✅ | **Ship it** |
| ✅ | ❌ | Correct but untrustworthy → **Fix framing** |
| ❌ | ✅ | Feels good but wrong → **Fix logic** |
| ❌ | ❌ | Broken → **Reject** |

---

## Decision Rules

### When Truth and Experience Conflict

**Scenario 1: Truth exists, but experience suffers**
- **Example**: Correlation detected via heuristic (team bet + player prop), but no game_id proof
- **Action**: Add qualifier — "Likely same-game (team + player detected)"
- **Why**: Preserve truth while maintaining confidence

**Scenario 2: Experience demands something truth cannot deliver**
- **Example**: User wants "win probability" but engine only scores structure
- **Action**: Do NOT fake it — explain limitation clearly
- **Why**: False confidence is worse than acknowledged limitation

**Escalation Rule**: If you cannot satisfy both truth and experience, **stop and escalate**. Do not ship misleading output.

---

## Implementation Checklist

Before shipping any feature, verify:

### Truth Checklist
- [ ] Unit tests pass
- [ ] Integration tests pass
- [ ] Logic is deterministic (where appropriate)
- [ ] Edge cases handled
- [ ] Source of data is clear and auditable

### Experience Checklist
- [ ] Output is clear and unambiguous
- [ ] User knows *why* this result appeared
- [ ] Tone matches context (warning vs info vs confidence)
- [ ] No weasel words ("maybe", "possibly", "might")
- [ ] User can act on this information

---

## Examples from Sprint S2

### Ticket A1: Parser bet_type Correction
**Truth**: Parser now correctly identifies "O27.5 pts" as PLAYER_PROP (22/22 tests passing)
**Experience**: User inputs "LeBron O27.5 pts + Lakers ML" and sees accurate prop count

**Result**: ✅ Both satisfied → shipped

### Ticket 38B-C1: Structural Snapshot Panel
**Truth**: Snapshot accurately counts props, totals, correlations (12/12 tests passing)
**Experience**: User sees structured breakdown with clear labels

**Result**: ✅ Both satisfied → shipped

### Hypothetical: Grounding Score with No Structural Data
**Truth**: Score = 100% generic (no snapshot data available)
**Experience**: User sees "100% generic" and loses trust

**Conflict**: Truth is correct, but experience is degraded

**Resolution**: Add context — "No structural analysis available (text-only mode)"

**Result**: ✅ Both satisfied → can ship with qualifier

---

## Anti-Patterns

### ❌ Truth Without Experience
- Dumping raw JSON to user
- Correct calculations with no explanation
- Passing tests but confusing UI
- "It works" without "user understands why"

### ❌ Experience Without Truth
- Invented confidence scores
- Fake precision ("87.3% correlation")
- Marketing language masking unknowns
- Smooth UX with incorrect data

### ❌ Neither
- Bugs in production
- Misleading labels
- Inconsistent behavior
- Silent failures

---

## Maintenance

This document is **living** and should be updated when:

- New patterns emerge from sprint work
- Truth/experience conflicts require new decision rules
- Examples demonstrate the principle in action

**Owner**: Sprint team  
**Review cadence**: End of each sprint

---

## References

- Sprint S2-FND directive (2026-02-05 17:21 UTC)
- RALPH Loop (docs/RALPH.md) — no scope creep
- Frozen Engine Rule (docs/ARCHITECTURE.md) — truth layer separation

---

**Version**: 1.0  
**Created**: 2026-02-05 22:49 UTC  
**Sprint**: S2-FND  
**Status**: Active Charter
