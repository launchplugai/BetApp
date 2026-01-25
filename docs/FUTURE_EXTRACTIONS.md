# Future Extractions from PR #4 (audit-dependencies)

> **Source Branch:** `claude/audit-dependencies-mk44qyna6tfaezq4-dCbHr`
> **PR:** #4 (70 commits, closed without merge)
> **Reason:** Branch diverged significantly; contains valuable code to extract in future sprints

---

## Summary

PR #4 contained the original DNA Matrix architecture - a trait-based profiling system designed to serve the bet analyzer. The main branch evolved differently with a focused Sprint 1 approach. Rather than merge 70 conflicting commits, we document what to extract when needed.

---

## Extraction 1: User Profiling System

**Target Sprint:** 2 or 3 (Explainability + Trust / Context Ingestion)

**Source File:** `connectors/betting/dna_strategy.py`

**What It Does:**
- `BettingPersonality` class - stores user betting preferences as traits
- `PersonalizedRecommendation` - outputs accept/reduce/avoid based on profile
- Trait-based evaluation against user's risk tolerance

**Key Traits to Port:**
```python
{
    "risk.tolerance": 0.50,           # 0-1 scale
    "risk.max_parlay_legs": 4,        # Cap on legs
    "risk.max_stake_pct": 0.05,       # Bankroll %
    "risk.avoid_live_bets": False,
    "risk.avoid_props": False,
    "strategy.kelly_fraction": 0.50,  # Betting strategy
    "behavior.discipline": 0.75,      # Self-control score
    "focus.preferred_sports": ["nfl", "nba"],
}
```

**Integration Point:** Extend `auth/models.py` User class with preferences field, add `/app/profile` endpoint.

**Effort:** Medium (1-2 days)

---

## Extraction 2: Enhanced Airlock Validation

**Target Sprint:** 5 (Harden + Monetize)

**Source File:** `src/launchplug_dna/core/adapters/airlock.py`

**What It Does:**
- 7-chromosome validation pipeline
- Schema validation (Chr3)
- Security checks (Chr3)
- Confidence scoring (Chr4)
- Quarantine system (Chr4)
- Audit logging (Chr6)
- Duplicate detection (Chr7)

**Current State:** `app/airlock.py` has basic validation (length, tier). Works but not hardened.

**Integration Point:** Replace/extend `app/airlock.py` with chromosome-based validation.

**Effort:** Medium-High (2-3 days)

---

## Extraction 3: Coherence Analysis

**Target Sprint:** 3 (Context Ingestion)

**Source File:** `src/launchplug_dna/core/engine/engine.py`

**What It Does:**
- Detects conflicting traits in a profile
- Calculates "coherence score"
- Example: high discipline + chase_losses=True = incoherent

**Use Case:** Warn users when their stated preferences conflict with behavior.

**Effort:** Low (half day)

---

## How to Extract

When ready to implement:

```bash
# Fetch the old branch
git fetch origin claude/audit-dependencies-mk44qyna6tfaezq4-dCbHr

# View specific file
git show origin/claude/audit-dependencies-mk44qyna6tfaezq4-dCbHr:connectors/betting/dna_strategy.py

# Extract to local file for reference
git show origin/claude/audit-dependencies-mk44qyna6tfaezq4-dCbHr:connectors/betting/dna_strategy.py > /tmp/dna_strategy_reference.py
```

---

## Files to Reference

| Purpose | Path in PR Branch |
|---------|-------------------|
| User profiling | `connectors/betting/dna_strategy.py` |
| Enhanced airlock | `src/launchplug_dna/core/adapters/airlock.py` |
| DNA Matrix engine | `src/launchplug_dna/core/engine/engine.py` |
| Trait models | `src/launchplug_dna/core/models/` |
| SDK client | `src/launchplug_dna/sdk/client.py` |
| Live odds (Sprint 4) | `connectors/betting/odds/client.py` |

---

## Decision Log

| Date | Decision | Reason |
|------|----------|--------|
| 2026-01-25 | Close PR #4 without merge | 70 commits, massive conflicts, different architecture |
| 2026-01-25 | Document extractions | Preserve valuable work for future sprints |
| TBD | Extract user profiling | Sprint 2-3 when personalization needed |
| TBD | Extract enhanced airlock | Sprint 5 when hardening |

---

## Status

- [x] PR #4 investigated
- [x] Valuable components identified
- [x] Extraction plan documented
- [ ] PR #4 closed with reference to this doc
- [ ] Branch preserved (do not delete)
