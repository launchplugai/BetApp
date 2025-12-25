# DNA Matrix: Primitive Discovery

> Primitives are discovered, not designed.

---

## Method

1. Pick use cases that hate each other (maximum conceptual distance)
2. Ask 5 brutal questions for each
3. Extract candidate primitives (raw, ugly)
4. Kill ruthlessly (must appear in 3+ unrelated cases)
5. Freeze v0.1

---

## The Five Use Cases

| # | Use Case | Domain | Why It's Here |
|---|----------|--------|---------------|
| 1 | Brand family generation | Marketing | Creative, identity-focused |
| 2 | Organizational drift detection | Operations | Cultural, behavioral |
| 3 | AI agent identity governance | Infrastructure | Technical, constraint-based |
| 4 | Product roadmap evolution | Product | Feature-based, temporal |
| 5 | Individual decision modeling | Human | Psychological, personal |

These share almost nothing on the surface. Perfect.

---

# Use Case 1: Brand Family Generation

## Context

Generate coherent brand variants (siblings, regional, demographic, price-tier) from a core archetype while maintaining family identity.

## The Five Questions

### Q1: What must be represented for this to work?

- Core identity traits (what makes it "this brand")
- Allowed variation ranges (how far can traits drift)
- Trait relationships (which traits constrain others)
- Hierarchy of importance (which traits are sacred vs. flexible)
- Target context (who/where/when this variant serves)

### Q2: What cannot be removed without breaking explanation?

- **Weight/priority** — not all traits are equal
- **Constraint boundaries** — what's allowed to change
- **Relationship/dependency** — traits that move together
- **Confidence** — how certain is this trait assignment
- **Source/lineage** — where did this trait come from

### Q3: What changes over time?

- Market positioning
- Audience perception
- Competitive pressure response
- Trait emphasis (same traits, different weights)
- Expression (same identity, different manifestation)

### Q4: What conflicts?

- Innovation vs. recognition (novelty vs. consistency)
- Local relevance vs. global coherence
- Price positioning vs. quality signal
- Accessibility vs. exclusivity
- Tradition vs. evolution

### Q5: What stays invariant?

- Core archetype (the irreducible "what is this")
- Constraint logic (rules don't change, values do)
- Relationship structure (dependencies persist)
- Lineage (history is immutable)

## Extracted Primitives (Raw)

```
weight
priority
constraint
boundary
tolerance
dependency
relationship
confidence
source
lineage
archetype
invariant
context
target
expression
signal
tension
tradeoff
coherence
drift
```

---

# Use Case 2: Organizational Drift Detection

## Context

Detect when an organization's actual behavior diverges from stated values, before visible failure.

## The Five Questions

### Q1: What must be represented for this to work?

- Declared values/intentions
- Actual behaviors/decisions
- Incentive structures
- Resource allocation patterns
- Leadership signals
- Gap between stated and actual

### Q2: What cannot be removed without breaking explanation?

- **Delta/gap** — difference between declared and actual
- **Incentive** — what drives behavior
- **Signal** — observable indicator of hidden state
- **Alignment** — degree of match
- **Trajectory** — direction of movement over time

### Q3: What changes over time?

- Incentive structures (quietly)
- Decision patterns (gradually)
- Resource allocation (measurably)
- Leadership behavior (visibly)
- Cultural norms (slowly)

### Q4: What conflicts?

- Short-term gains vs. long-term values
- Individual incentives vs. collective goals
- Stated mission vs. market pressure
- Growth vs. coherence
- Efficiency vs. resilience

### Q5: What stays invariant?

- Core mission (or should)
- Constraint logic (governance rules)
- Accountability structure
- Historical decisions (lineage)

## Extracted Primitives (Raw)

```
delta
gap
incentive
signal
alignment
trajectory
behavior
intention
declared
actual
pressure
conflict
tension
tradeoff
resource
allocation
authority
accountability
drift
threshold
warning
```

---

# Use Case 3: AI Agent Identity Governance

## Context

Maintain coherent agent behavior as prompts, tools, memory, and constraints evolve. Prevent agent schizophrenia.

## The Five Questions

### Q1: What must be represented for this to work?

- Base behavioral genome
- Constraint boundaries
- Tool capabilities and limits
- Memory state
- Prompt influence weights
- Allowed deviation range

### Q2: What cannot be removed without breaking explanation?

- **Constraint** — hard boundaries
- **Weight** — relative influence of inputs
- **Capability** — what agent can do
- **Boundary** — where behavior stops
- **State** — current configuration
- **Drift** — deviation from baseline

### Q3: What changes over time?

- Memory accumulation
- Prompt tuning
- Tool additions
- Constraint adjustments
- Behavioral adaptation

### Q4: What conflicts?

- User request vs. safety constraint
- Helpfulness vs. harm avoidance
- Consistency vs. adaptation
- Memory vs. context limits
- Capability vs. permission

### Q5: What stays invariant?

- Core safety constraints
- Identity baseline
- Capability limits (hard)
- Lineage of changes

## Extracted Primitives (Raw)

```
constraint
weight
capability
boundary
state
drift
baseline
deviation
permission
limit
memory
adaptation
conflict
safety
identity
coherence
influence
input
output
threshold
```

---

# Use Case 4: Product Roadmap Evolution

## Context

Track feature lineage, detect incoherent additions, simulate variant product lines, prevent Frankenstein products.

## The Five Questions

### Q1: What must be represented for this to work?

- Product essence (core value proposition)
- Feature dependency graph
- User segment mapping
- Technical constraints
- Business constraints
- Coherence scoring

### Q2: What cannot be removed without breaking explanation?

- **Dependency** — what requires what
- **Coherence** — does this fit
- **Priority** — what matters more
- **Constraint** — what's not allowed
- **Lineage** — where did this come from
- **Compatibility** — can these coexist

### Q3: What changes over time?

- Feature set
- Priority weights
- User segment focus
- Technical capabilities
- Market positioning

### Q4: What conflicts?

- Feature bloat vs. simplicity
- User segment A vs. segment B needs
- Technical debt vs. new features
- Short-term revenue vs. long-term coherence
- Innovation vs. stability

### Q5: What stays invariant?

- Core value proposition
- Fundamental constraints
- Dependency structure (mostly)
- Historical decisions

## Extracted Primitives (Raw)

```
dependency
coherence
priority
constraint
lineage
compatibility
essence
segment
capability
limit
bloat
simplicity
tradeoff
conflict
stability
innovation
debt
weight
fit
score
```

---

# Use Case 5: Individual Decision Modeling

## Context

Model a person's decision patterns, predict likely choices, surface internal conflicts, track evolution over time.

## The Five Questions

### Q1: What must be represented for this to work?

- Value hierarchy
- Risk tolerance
- Decision patterns
- Constraint awareness
- Goal structure
- Conflict tolerance

### Q2: What cannot be removed without breaking explanation?

- **Weight** — relative importance of values
- **Tolerance** — how much variance is acceptable
- **Conflict** — competing drives
- **Pattern** — repeated behavior
- **Constraint** — external limits
- **Goal** — desired end state

### Q3: What changes over time?

- Priority weights
- Risk tolerance
- Goal structure
- Constraint perception
- Pattern reinforcement or decay

### Q4: What conflicts?

- Short-term desire vs. long-term goal
- Security vs. growth
- Independence vs. belonging
- Consistency vs. adaptation
- Stated values vs. revealed preferences

### Q5: What stays invariant?

- Core values (mostly)
- Deep constraints
- Historical patterns
- Identity baseline

## Extracted Primitives (Raw)

```
weight
tolerance
conflict
pattern
constraint
goal
risk
value
hierarchy
priority
preference
revealed
stated
gap
adaptation
baseline
identity
drive
desire
limit
```

---

# Primitive Frequency Analysis

Now we count. A primitive survives if it appears in **3+ unrelated use cases**.

| Primitive | Brand | Org | Agent | Product | Person | Count | Survives |
|-----------|-------|-----|-------|---------|--------|-------|----------|
| weight | ✓ | | ✓ | ✓ | ✓ | 4 | ✓ |
| priority | ✓ | | | ✓ | ✓ | 3 | ✓ |
| constraint | ✓ | | ✓ | ✓ | ✓ | 4 | ✓ |
| boundary | ✓ | | ✓ | | | 2 | ✗ |
| tolerance | ✓ | | | | ✓ | 2 | ✗ |
| dependency | ✓ | | | ✓ | | 2 | ✗ |
| confidence | ✓ | | | | | 1 | ✗ |
| lineage | ✓ | | | ✓ | | 2 | ✗ |
| drift | ✓ | ✓ | ✓ | | | 3 | ✓ |
| coherence | ✓ | | ✓ | ✓ | | 3 | ✓ |
| conflict | ✓ | ✓ | ✓ | ✓ | ✓ | 5 | ✓ |
| tension | ✓ | ✓ | | | | 2 | ✗ |
| tradeoff | ✓ | ✓ | | ✓ | | 3 | ✓ |
| signal | ✓ | ✓ | | | | 2 | ✗ |
| incentive | | ✓ | | | | 1 | ✗ |
| alignment | | ✓ | | | | 1 | ✗ |
| trajectory | | ✓ | | | | 1 | ✗ |
| gap | | ✓ | | | ✓ | 2 | ✗ |
| baseline | | | ✓ | | ✓ | 2 | ✗ |
| capability | | | ✓ | ✓ | | 2 | ✗ |
| limit | | | ✓ | ✓ | ✓ | 3 | ✓ |
| state | | | ✓ | | | 1 | ✗ |
| identity | | | ✓ | | ✓ | 2 | ✗ |
| adaptation | | | ✓ | | ✓ | 2 | ✗ |
| goal | | | | | ✓ | 1 | ✗ |
| pattern | | | | | ✓ | 1 | ✗ |
| compatibility | | | | ✓ | | 1 | ✗ |
| essence | | | | ✓ | | 1 | ✗ |

---

# Survivors: v0.1 Primitive Set

| Primitive | Count | What It Represents |
|-----------|-------|-------------------|
| **weight** | 4 | Relative importance of a trait |
| **priority** | 3 | Ordering of importance |
| **constraint** | 4 | Hard boundary that cannot be crossed |
| **drift** | 3 | Deviation from baseline over time |
| **coherence** | 3 | Internal consistency of the whole |
| **conflict** | 5 | Competing forces that cannot both win |
| **tradeoff** | 3 | Deliberate exchange of one value for another |
| **limit** | 3 | Soft boundary that can be approached |

---

## Candidate Consolidation

Some of these overlap. Let's merge:

| Merged Primitive | Absorbs | Definition |
|------------------|---------|------------|
| **weight** | priority | Relative importance (0.0-1.0), determines ordering |
| **constraint** | limit | Boundary on variation (hard or soft, with threshold) |
| **drift** | — | Deviation from baseline over time |
| **coherence** | — | Internal consistency score |
| **conflict** | tension | Competing forces with winner/loser |
| **tradeoff** | — | Explicit exchange between values |

---

# The v0.1 Genome: 7 Primitives

After stress-testing:

- **lineage** promoted (Law 3: Lineage Is Sacred — without it, explanation collapses)
- **baseline** promoted (drift is undefined without reference)
- **coherence** demoted (computed from other primitives, not stored)

```
1. weight      →  how much this matters
2. constraint  →  what bounds this
3. conflict    →  what opposes this
4. baseline    →  reference state for comparison
5. drift       →  deviation from baseline over time
6. tradeoff    →  what was sacrificed for this
7. lineage     →  where this came from, what it replaced
```

---

## Why Coherence Is Not Primitive

Coherence is a **judgment**, not a fact.

It is computed from:
- conflict (how many, how severe)
- constraint (how many violated)
- drift (how far from baseline)
- tradeoff (what costs were incurred)
- weight (which violations matter most)

If you store coherence, you bake opinion into the substrate.

**Correct role**: Coherence is a query result, not a gene.

Store the causes. Compute the verdict.

---

## Why Watch-List Items Didn't Make It

| Candidate | Verdict | Reason |
|-----------|---------|--------|
| signal | Not primitive | Observable projection, not core |
| dependency | Not primitive | Graph structure derived from constraints |
| tolerance | Not primitive | Constraint parameter |
| identity | Not primitive | Emergent invariant across lineage |
| confidence | Not primitive | Epistemic layer, not ontological |

They may return as typed compositions, not primitives.

---

## Critical Clarification

These primitives are **not fields**.

They are:
- Relations
- Forces
- Dimensions
- Axes of variation

Model them like columns and the system flattens into a spreadsheet.

---

# The Brutal Question

For each primitive, answer:

> What real-world phenomenon becomes impossible to explain if this primitive is removed?

---

## 1. weight

**Without weight, you cannot explain:**

- Why some traits matter more than others
- Why the same violation in different places has different consequences
- Why evolution favors certain mutations
- Why two organisms with identical traits behave differently

**Real-world anchor**: Gravity. Mass. Significance. Priority.

**Removal consequence**: Everything becomes flat. No hierarchy. Random evolution.

---

## 2. constraint

**Without constraint, you cannot explain:**

- Why some variations are invalid
- Why certain states never occur
- Why mutation has limits
- Why identity persists under change

**Real-world anchor**: Laws. Boundaries. Physics. Rules.

**Removal consequence**: Generation becomes noise. Validity disappears.

---

## 3. conflict

**Without conflict, you cannot explain:**

- Why tradeoffs exist
- Why decisions are hard
- Why systems oscillate
- Why drift happens
- Why coherence breaks

**Real-world anchor**: Competition. Scarcity. Opposition. Tension.

**Removal consequence**: The system lies. It pretends everything is harmonious.

---

## 4. baseline

**Without baseline, you cannot explain:**

- What "drift" means
- What "normal" was
- What promises were made
- What expectations exist

**Real-world anchor**: Reference frames. Expectations. Norms. Commitments.

**Removal consequence**: Drift becomes meaningless. Comparison becomes impossible.

---

## 5. drift

**Without drift, you cannot explain:**

- How things change over time
- When intervention is needed
- Why current state differs from intended state
- How decay accumulates

**Real-world anchor**: Entropy. Decay. Evolution. Movement.

**Removal consequence**: Time becomes decorative. Change becomes invisible.

---

## 6. tradeoff

**Without tradeoff, you cannot explain:**

- Why choices have costs
- Why gains require losses
- Why optimization is bounded
- Why "having it all" is impossible

**Real-world anchor**: Scarcity. Opportunity cost. Conservation laws.

**Removal consequence**: The system promises magic. Decisions have no weight.

---

## 7. lineage

**Without lineage, you cannot explain:**

- Where anything came from
- Why two identical states are different
- Who is accountable
- What was tried before

**Real-world anchor**: Causality. History. Provenance. Memory.

**Removal consequence**: Two identical states with different histories become indistinguishable. Accountability vanishes. Explanation collapses.

---

# Verdict

All seven pass.

Removing any one makes real phenomena unexplainable.

---

# Genome v0.1 — FROZEN

```
┌─────────────────────────────────────────────────────────┐
│                    DNA MATRIX GENOME v0.1                │
├─────────────────────────────────────────────────────────┤
│                                                          │
│   1. weight      Relative importance (scalar/vector)     │
│   2. constraint  Boundary on valid states                │
│   3. conflict    Competing forces                        │
│   4. baseline    Reference state for comparison          │
│   5. drift       Deviation from baseline over time       │
│   6. tradeoff    Exchange of one value for another       │
│   7. lineage     Provenance and causal history           │
│                                                          │
├─────────────────────────────────────────────────────────┤
│   Computed (not primitive):                              │
│   - coherence (derived from above)                       │
│   - identity (emergent from lineage + constraint)        │
│   - signal (observable projection)                       │
│   - score (query result)                                 │
│                                                          │
└─────────────────────────────────────────────────────────┘
```

This is now constitutional. Changes require ADR.

---

# Next Pass

Map each primitive to:

1. Data structure (how it's stored)
2. Operations (how it's mutated)
3. Queries (how it's accessed)
4. Interactions (how primitives affect each other)
