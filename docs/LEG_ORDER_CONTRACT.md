# Leg Order Contract

> **Version:** 1.0 | **Created:** 2026-02-01 | **Ticket:** 39

---

## Core Principle

**Leg order is semantic data, not presentation.**

If order changes without explicit user action, the system is incorrect.

---

## Canonical Order Authority

### Source of Truth: **Builder Array Index**

The order in which legs appear in `builderLegs[]` is the canonical order.

```javascript
builderLegs = [
    { leg_id: "leg_a1b2", entity: "Lakers", ... },  // Position 1
    { leg_id: "leg_c3d4", entity: "Celtics", ... }, // Position 2
    { leg_id: "leg_e5f6", entity: "Heat", ... }     // Position 3
]
```

- Position is determined by array index (`i + 1` for 1-indexed display)
- User adds legs → appended to end
- User removes legs → splice maintains sequence of remaining legs

---

## Leg Identity Authority

### Source of Truth: **leg_id (SHA-256 Hash)**

Each leg has a deterministic identity based on its content:

```javascript
leg_id = SHA256(entity|market|value|sport).substring(0, 16)
```

**Why content-based identity:**
- Survives re-evaluation (order may shift, but leg_id remains)
- Enables `lockedLegIds` tracking across refinements
- Decouples identity from position

---

## Order Flow Guarantee

```
Stage 1: Builder        → array index (canonical)
Stage 2: API Request    → JSON array (order preserved)
Stage 3: Airlock        → tuple (order preserved)
Stage 4: Pipeline       → list with position field (order preserved)
Stage 5: Engine         → tuple (order preserved)
Stage 6: UI Results     → array with originalIndex (order preserved)
```

Every stage uses order-preserving operations:
- `Array.push()`, `Array.map()`, `Array.forEach()`
- `tuple()`, `list comprehension`, `enumerate()`

---

## Correlation Independence

Correlations reference legs by `block_id: UUID`, not by position.

```python
Correlation(block_a=UUID("..."), block_b=UUID("..."))
```

This means:
- Leg reordering does NOT break correlations
- Removing a leg does NOT invalidate correlations for remaining legs
- Correlations are content-based, position-agnostic

---

## Invariants (Must Always Hold)

| Invariant | Enforcement |
|-----------|-------------|
| `evaluated_parlay.legs[i].position == i + 1` | Pipeline builds with enumerate() |
| `leg_id` is deterministic for same content | SHA-256 hash of canonical fields |
| Correlations use UUID, not index | Engine dataclass definition |
| Array operations never sort legs | No `.sort()` on canonical leg arrays |

---

## Prohibited Operations

Do NOT:
- Sort `builderLegs` or `resultsLegs` arrays
- Use Set or Dict for leg storage (loses order)
- Reference legs by position across re-evaluations
- Assume leg at position N is "the same leg" after modification

---

## Safe Operations

DO:
- Append new legs with `push()`
- Remove legs with `splice(index, 1)`
- Filter legs with list comprehension (preserves order)
- Track leg identity with `leg_id`, not index
- Store `originalIndex` for UI display reference

---

## Testing Requirements

Tests must verify:
1. Leg order preserved: Builder → API → Pipeline → UI
2. Removing leg N maintains order of legs N+1, N+2, ...
3. `leg_id` is stable across re-evaluation
4. Correlations survive leg removal (UUID-based)

---

## Change Policy

Any code that:
- Sorts legs
- Converts leg array to Set/Dict
- Reorders legs for "optimization"

Must be **explicitly approved** and **documented** with justification.
