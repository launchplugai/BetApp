# Sportsbook Accuracy Canon (SAC)

**Version:** 1.0  
**Status:** DRAFT  
**Purpose:** Ensure DNA Engine data matches sportsbook reality exactly—no compromises.

---

## Core Principle

> **If it doesn't match the sportsbook, it's wrong.**

Accuracy is credibility. One mismatched line or stale odds destroys trust. This canon establishes the non-negotiable standards for data integrity.

---

## 1. Data Freshness Standards

### Odds TTL (Time-To-Live)
| Market Type | Max Age | Rationale |
|-------------|---------|-----------|
| Live/In-Game | 30 seconds | Lines move fast |
| Pre-Game (< 1hr) | 60 seconds | Sharp action incoming |
| Pre-Game (1-24hr) | 5 minutes | Standard refresh |
| Futures | 1 hour | Stable markets |

### Score/Status TTL
| Status | Max Age |
|--------|---------|
| LIVE | 15 seconds |
| HALFTIME | 60 seconds |
| FINAL | 1 hour (for confirmation) |

### Last-Updated Contract
Every data response MUST include:
```json
{
  "data": {...},
  "meta": {
    "last_updated": "2026-02-15T12:34:56Z",
    "stale": false,
    "source": "the_odds_api",
    "cache_hit": false
  }
}
```

---

## 2. Provider Accuracy Requirements

### Primary: The Odds API
- **Regions:** `us` (American odds)
- **Markets:** `h2h,spreads,totals` minimum
- **Bookmaker Priority:**
  1. DraftKings (industry standard)
  2. FanDuel (market maker)
  3. First available (fallback)

### Secondary: Direct Sportsbook Scrapers (Future)
- DraftKings API
- FanDuel API
- BetMGM API
- Consensus aggregator

### Provider Health Grading
| Grade | Accuracy | Latency | Uptime |
|-------|----------|---------|--------|
| A+ | 99.9% | < 500ms | 99.9% |
| A | 99.5% | < 1s | 99.5% |
| B | 98% | < 3s | 99% |
| F | < 98% | > 3s | < 99% |

**Action Threshold:** Drop to backup provider at Grade B or below.

---

## 3. Canonical Team Naming

### Name Resolution Strategy
Sportsbooks use abbreviated names. We must map to canonical full names.

```python
# NBA Examples
"GS" → "Golden State Warriors"
"LAL" → "Los Angeles Lakers"
"PHI" → "Philadelphia 76ers"

# NFL Examples  
"NE" → "New England Patriots"
"KC" → "Kansas City Chiefs"
"SF" → "San Francisco 49ers"
```

### Name Matching Algorithm
1. **Exact match** on canonical name
2. **Fuzzy match** on tokenized words (Levenshtein distance < 3)
3. **Manual override** for edge cases
4. **Log unknown** for mapping updates

### Team Mapping Registry
Location: `app/data/team_mappings.json`
Must include:
- Canonical full name
- All known abbreviations
- Sport/league
- Primary color (for UI consistency)

---

## 4. Odds Format Standardization

### American Odds (Canonical)
- Positive (+150): Win $150 on $100 bet
- Negative (-110): Bet $110 to win $100
- Zero (0): Even money (display as "EVEN")

### Validation Rules
```python
assert -10000 <= odds <= 10000  # Sanity bounds
assert odds != 0 or display == "EVEN"
assert isinstance(odds, int)  # No decimals
```

### Display Rules
| Range | Display Example |
|-------|-----------------|
| +100 | +100 (or EVEN) |
| +105 to +150 | +150 |
| +150 to +500 | +250 |
| +500+ | +1000 |
| -101 to -150 | -110 |
| -150 to -500 | -200 |
| -500+ | -1000 |

---

## 5. Line/Total Precision

### Spread Lines
- Display: `LAL -4.5` (always show half points)
- Internal: Float with .0 or .5 only
- Validation: Must be multiples of 0.5

### Totals
- Display: `O 220.5` / `U 220.5`
- Internal: Float with .0 or .5 only
- Key numbers: 220, 220.5, 221 (NBA average context)

### Player Props
- Points: Whole numbers (O 27.5, U 27.5)
- Rebounds/Assists: Half points common
- Combos: Follow sportsbook convention

---

## 6. Game Status Synchronization

### Status States
```python
class GameStatus:
    SCHEDULED = "scheduled"      # Not yet started
    WARMUP = "warmup"            # Pre-game (30 min before)
    LIVE = "live"                # In progress
    HALFTIME = "halftime"        # Mid-game break
    SUSPENDED = "suspended"      # Weather/delay
    FINAL = "final"              # Game complete
    POSTPONED = "postponed"      # Rescheduled
    CANCELLED = "cancelled"      # Never happened
```

### Transition Rules
1. `SCHEDULED` → `WARMUP` 30 minutes before start
2. `WARMUP` → `LIVE` at actual game start
3. `LIVE` ↔ `HALFTIME` based on period/clock
4. `LIVE` → `FINAL` when game ends
5. Any status → `SUSPENDED` / `POSTPONED` / `CANCELLED` on official announcement

### Score Validation
- Never allow score to decrease (logging error if it does)
- Period must advance monotonically
- Clock must count down within period

---

## 7. Error Handling & Fallbacks

### Provider Failure Cascade
1. **Primary fails** → Use cached data with `stale: true` flag
2. **Cache expired** → Query secondary provider
3. **All providers fail** → Return error with last known data timestamp
4. **Never** return fabricated/mock data in production

### Stale Data Display
When showing stale data:
- UI must show "⚠️ Odds may be outdated (2m old)"
- Disable bet confirmation buttons
- Auto-refresh on user action

### Circuit Breaker Pattern
- 5 consecutive provider failures = open circuit
- Circuit open for 60 seconds
- Return error with explanatory message
- Health check endpoint reflects degraded status

---

## 8. Validation & Monitoring

### Real-Time Validation
```python
@dataclass
class AccuracyCheck:
    timestamp: datetime
    game_id: str
    market: str
    our_line: float
    provider_line: float
    delta: float
    acceptable: bool  # |delta| < threshold
```

### Sampling Strategy
- Validate 5% of all lines continuously
- 100% of featured/live games
- 100% of odds changes > 10 points

### Alert Thresholds
| Severity | Condition | Action |
|----------|-----------|--------|
| CRITICAL | > 5% of lines mismatch | Page on-call, switch provider |
| HIGH | Specific game mismatch > 2 points | Log, flag for review |
| MEDIUM | Latency > 3 seconds | Log, investigate |
| LOW | Cache miss rate > 20% | Optimize cache strategy |

### Accuracy Dashboard Metrics
- Match rate vs. primary provider
- Average delta (our line - true line)
- Stale data percentage
- Provider health grades
- Mean time to detect (MTTD) discrepancies

---

## 9. Testing Requirements

### Unit Tests
- Line parsing for all supported sports
- Name normalization edge cases
- Odds format conversion (decimal ↔ american)
- TTL expiration logic

### Integration Tests
- End-to-end provider fetch
- Cache hit/miss scenarios
- Circuit breaker behavior
- Fallback provider activation

### Accuracy Audit
Daily automated check:
1. Sample 50 random live games
2. Compare our displayed odds vs. DraftKings website
3. Report mismatch rate
4. Flag for manual review if > 1% delta

---

## 10. Implementation Checklist

### Phase 1: Foundation
- [ ] Implement team mapping registry
- [ ] Add metadata to all API responses
- [ ] Create accuracy monitoring middleware
- [ ] Implement TTL enforcement

### Phase 2: Validation
- [ ] Build accuracy checker service
- [ ] Add provider health grading
- [ ] Implement circuit breaker
- [ ] Create accuracy dashboard

### Phase 3: Optimization
- [ ] Multi-provider consensus mode
- [ ] Predictive pre-fetching
- [ ] Client-side stale data warnings
- [ ] Automated mapping updates

---

## Appendix A: Team Abbreviation Reference

See: `app/data/team_mappings.json`

## Appendix B: Provider Response Contracts

See: `docs/contracts/odds_provider.md`

## Appendix C: Accuracy Test Suite

See: `app/tests/test_accuracy_canon.py`

---

**Enforcement:** Any PR affecting odds, scores, or game data MUST:
1. Reference this canon
2. Include accuracy tests
3. Pass manual spot-check against real sportsbook
4. Update this doc if changing standards
