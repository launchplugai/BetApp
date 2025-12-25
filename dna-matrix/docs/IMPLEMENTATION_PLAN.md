# DNA Matrix: Implementation Plan v0.1

> Build order that matches risk. Fastest path to a real MVP.

---

## Guiding Principles

| Principle | Why |
|-----------|-----|
| **Prove correctness before performance** | Fast wrong answers are worse than slow right ones |
| **Storage before API** | Can't serve what you can't persist |
| **Constraints before conflicts** | Conflicts are created by constraint evaluation |
| **Core before auth** | Security on a broken system is theater |
| **SQLite before Postgres** | Reduce variables during development |

---

## Phase Overview

```
┌─────────────────────────────────────────────────────────────────────┐
│ Phase 1: Foundation (Week 1-2)                                       │
│ Storage + Core Models + Mutation Engine                              │
├─────────────────────────────────────────────────────────────────────┤
│ Phase 2: Intelligence (Week 3-4)                                     │
│ Constraint Language + Conflict Detection + Coherence                 │
├─────────────────────────────────────────────────────────────────────┤
│ Phase 3: Surface (Week 5-6)                                          │
│ API Endpoints + Query Engine + Projections                           │
├─────────────────────────────────────────────────────────────────────┤
│ Phase 4: Polish (Week 7-8)                                           │
│ SDK + Auth + Rate Limiting + Observability                           │
└─────────────────────────────────────────────────────────────────────┘
```

---

# Phase 1: Foundation

**Goal**: Store and retrieve organisms, claims, mutations with lineage intact.

## Week 1: Storage Layer

### Day 1-2: Core Models

```
core/
├── models/
│   ├── __init__.py
│   ├── organism.py      # Organism dataclass
│   ├── claim.py         # Claim dataclass with Value, Baseline
│   ├── mutation.py      # Mutation, MutationChange, MutationStatus
│   ├── lens.py          # Lens definition
│   └── common.py        # Value, LensRef, Actor
```

**Deliverables**:
- [ ] All dataclasses with validation
- [ ] JSON serialization/deserialization
- [ ] Unit tests for model creation

### Day 3-4: SQLite Storage

```
storage/
├── __init__.py
├── base.py              # Abstract storage interface
├── sqlite/
│   ├── __init__.py
│   ├── connection.py    # Connection pool
│   ├── migrations.py    # Schema migrations
│   ├── organisms.py     # Organism CRUD
│   ├── claims.py        # Claim CRUD
│   └── mutations.py     # Mutation log
```

**Schema**:

```sql
-- Organisms
CREATE TABLE organisms (
    id TEXT PRIMARY KEY,
    organism_type TEXT NOT NULL,
    name TEXT NOT NULL,
    tags TEXT,  -- JSON array
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);

-- Lenses (reference data)
CREATE TABLE lenses (
    id TEXT PRIMARY KEY,
    cluster TEXT NOT NULL,
    key TEXT NOT NULL,
    name TEXT NOT NULL,
    value_type TEXT NOT NULL,
    schema TEXT,  -- JSON
    resolver TEXT,  -- JSON
    default_weight REAL,
    created_at TEXT NOT NULL,
    UNIQUE(cluster, key)
);

-- Claims
CREATE TABLE claims (
    id TEXT PRIMARY KEY,
    organism_id TEXT NOT NULL REFERENCES organisms(id),
    lens_id TEXT NOT NULL REFERENCES lenses(id),
    lens_cluster TEXT NOT NULL,
    lens_key TEXT NOT NULL,
    value_kind TEXT NOT NULL,
    value_data TEXT NOT NULL,  -- JSON
    weight REAL NOT NULL,
    constraints TEXT,  -- JSON array of constraint IDs
    baseline_mode TEXT,
    baseline_ref TEXT,
    baseline_value TEXT,  -- JSON
    baseline_captured_at TEXT,
    last_mutation_id TEXT,
    version INTEGER NOT NULL DEFAULT 1,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);

-- Mutations (append-only log)
CREATE TABLE mutations (
    id TEXT PRIMARY KEY,
    organism_id TEXT NOT NULL REFERENCES organisms(id),
    actor_type TEXT NOT NULL,
    actor_id TEXT NOT NULL,
    actor_label TEXT,
    intent TEXT,
    changes TEXT NOT NULL,  -- JSON array
    tradeoffs TEXT,  -- JSON array
    constraint_results TEXT,  -- JSON array
    conflicts_created TEXT,  -- JSON array of conflict IDs
    status TEXT NOT NULL,
    prev_mutation_id TEXT,
    created_at TEXT NOT NULL,
    committed_at TEXT
);

-- Indexes
CREATE INDEX idx_claims_organism ON claims(organism_id);
CREATE INDEX idx_claims_lens ON claims(lens_cluster, lens_key);
CREATE INDEX idx_mutations_organism ON mutations(organism_id);
CREATE INDEX idx_mutations_status ON mutations(status);
```

**Deliverables**:
- [ ] Migration system (up/down)
- [ ] Connection pooling
- [ ] CRUD for organisms, claims
- [ ] Mutation log append
- [ ] Integration tests

### Day 5: Mutation Engine

```
core/
├── engine/
│   ├── __init__.py
│   ├── mutation_engine.py   # The only write path
│   └── lineage.py           # Lineage tracking
```

**MutationEngine responsibilities**:
1. Accept mutation proposal
2. Resolve claim IDs from lenses
3. Capture "before" state
4. Apply changes to claim store
5. Update `lastMutationId` on affected claims
6. Append to mutation log

```python
class MutationEngine:
    def propose(self, mutation: MutationProposal) -> Mutation:
        """Create proposed mutation, resolve claims."""
        pass
    
    def commit(self, mutation_id: str, tradeoffs: List[TradeoffEntry]) -> Mutation:
        """
        Apply mutation to claims.
        
        At this phase: no constraint checking yet.
        Just verify mutation exists and is in proposed state.
        """
        pass
    
    def rollback(self, mutation_id: str, reason: str, actor: Actor) -> Mutation:
        """Reverse a committed mutation."""
        pass
```

**Deliverables**:
- [ ] Propose/commit/rollback lifecycle
- [ ] Lineage chain maintained
- [ ] Rollback creates inverse mutation
- [ ] Integration tests

## Week 2: Core Engine Completion

### Day 1-2: Claim Resolution

Handle the case where mutations reference lenses, not claim IDs.

```python
class ClaimResolver:
    def resolve_or_create(
        self, 
        organism_id: str, 
        lens: LensRef, 
        value: Value
    ) -> Claim:
        """
        Find existing claim or create new one.
        Used by mutation engine when processing changes.
        """
        existing = self.storage.claims.find_by_lens(organism_id, lens)
        if existing:
            return existing
        return self.storage.claims.create(organism_id, lens, value)
```

**Deliverables**:
- [ ] Lens → Claim resolution
- [ ] Auto-create claims on first mutation
- [ ] Tests for resolution edge cases

### Day 3-4: Baseline Management

```python
class BaselineManager:
    def capture_snapshot(self, claim_id: str) -> Baseline:
        """Capture current state as baseline."""
        pass
    
    def update_baseline(
        self, 
        claim_id: str, 
        mode: str, 
        ref: Optional[str] = None
    ) -> Claim:
        """Change baseline reference."""
        pass
    
    def compute_drift(self, claim: Claim) -> float:
        """Compute drift from baseline."""
        if not claim.baseline:
            return 0.0
        return self._distance(claim.value, claim.baseline.value)
```

**Deliverables**:
- [ ] Snapshot capture
- [ ] Baseline modes (snapshot, declared, ideal, historical, selected)
- [ ] Drift computation
- [ ] Tests for drift calculation

### Day 5: Phase 1 Integration

- [ ] End-to-end test: Create organism → Add claims via mutation → Verify lineage
- [ ] Rollback test: Commit → Rollback → Verify state restored
- [ ] Baseline test: Capture baseline → Mutate → Compute drift

---

# Phase 2: Intelligence

**Goal**: System can evaluate constraints and detect conflicts.

## Week 3: Constraint Language

### Day 1-2: Constraint Models + Storage

```
core/
├── constraints/
│   ├── __init__.py
│   ├── models.py        # Constraint dataclass
│   ├── storage.py       # Constraint CRUD
│   └── registry.py      # Operator registry

storage/sqlite/
├── constraints.py       # Constraint table
```

**Schema addition**:

```sql
CREATE TABLE constraints (
    id TEXT PRIMARY KEY,
    version TEXT NOT NULL,
    name TEXT NOT NULL,
    description TEXT,
    severity TEXT NOT NULL,  -- hard/soft
    scope TEXT NOT NULL,     -- claim/lens/organism/cluster/global
    target TEXT NOT NULL,    -- JSON
    when_guard TEXT,         -- JSON
    rule TEXT NOT NULL,      -- JSON
    on_fail TEXT,            -- JSON
    tags TEXT,               -- JSON array
    owner TEXT,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);

CREATE INDEX idx_constraints_scope ON constraints(scope);
CREATE INDEX idx_constraints_severity ON constraints(severity);
```

**Deliverables**:
- [ ] Constraint model matching spec
- [ ] Storage CRUD
- [ ] Operator registry with v1 operators

### Day 3-4: Constraint Evaluator

```
core/
├── constraints/
│   ├── evaluator.py     # Main evaluation engine
│   ├── operators/
│   │   ├── __init__.py
│   │   ├── base.py      # Operator interface
│   │   ├── boolean.py   # and, or, not, xor
│   │   ├── comparison.py # eq, neq, gt, gte, lt, lte, in, not_in
│   │   ├── range.py     # between, within_tolerance, max_delta
│   │   ├── set.py       # exists, missing, count_gte, count_lte
│   │   ├── domain.py    # exclusion, requires, implies, compatible_with
│   │   └── drift.py     # drift_lte, weighted_drift_lte
│   └── results.py       # ConstraintResult with evidence
```

**Deliverables**:
- [ ] All v1 operators implemented
- [ ] Guard evaluation (when clause)
- [ ] Evidence generation
- [ ] Repair hint generation
- [ ] Unit tests for each operator

### Day 5: Constraint Integration with Mutations

```python
class MutationEngine:
    def validate(self, mutation_id: str, dry_run: bool = True) -> ValidationResult:
        """
        Evaluate all applicable constraints.
        Returns hard fails, soft fails, and whether tradeoff is required.
        """
        mutation = self.storage.mutations.get(mutation_id)
        
        # Get affected claims
        affected = self._get_affected_claims(mutation)
        
        # Collect applicable constraints
        constraints = self.constraint_collector.collect(affected)
        
        # Evaluate each
        results = []
        for constraint in constraints:
            result = self.evaluator.evaluate(constraint, affected)
            results.append(result)
        
        # Classify
        hard_fails = [r for r in results if not r.passed and r.severity == "hard"]
        soft_fails = [r for r in results if not r.passed and r.severity == "soft"]
        
        return ValidationResult(
            mutation_id=mutation_id,
            valid=len(hard_fails) == 0,
            hard_fails=len(hard_fails),
            soft_fails=len(soft_fails),
            constraint_results=results,
            tradeoff_required=len(soft_fails) > 0
        )
    
    def commit(self, mutation_id: str, tradeoffs: List[TradeoffEntry]) -> Mutation:
        """
        Now with constraint checking.
        """
        validation = self.validate(mutation_id, dry_run=False)
        
        if validation.hard_fails > 0:
            raise ConstraintHardFailError(validation.constraint_results)
        
        if validation.soft_fails > 0 and not tradeoffs:
            raise TradeoffRequiredError()
        
        # Proceed with commit...
```

**Deliverables**:
- [ ] Constraint collection by scope
- [ ] Validation integration
- [ ] Hard fail blocks commit
- [ ] Soft fail requires tradeoff
- [ ] Integration tests

## Week 4: Conflict Detection

### Day 1-2: Conflict Models + Storage

```
core/
├── conflicts/
│   ├── __init__.py
│   ├── models.py        # Conflict, ConflictResolution
│   ├── storage.py       # Conflict CRUD
│   └── severity.py      # Severity computation

storage/sqlite/
├── conflicts.py
```

**Schema addition**:

```sql
CREATE TABLE conflicts (
    id TEXT PRIMARY KEY,
    type TEXT NOT NULL,      -- exclusion-constraint/baseline-violation/derived
    status TEXT NOT NULL,    -- active/resolved/suppressed
    severity TEXT NOT NULL,  -- low/medium/high/existential
    organism_id TEXT NOT NULL REFERENCES organisms(id),
    claims TEXT NOT NULL,    -- JSON array
    origin TEXT NOT NULL,    -- JSON
    baseline TEXT,           -- JSON
    tradeoff_required INTEGER NOT NULL,
    lineage TEXT NOT NULL,   -- JSON
    resolution TEXT,         -- JSON
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);

CREATE INDEX idx_conflicts_organism ON conflicts(organism_id);
CREATE INDEX idx_conflicts_status ON conflicts(status);
CREATE INDEX idx_conflicts_severity ON conflicts(severity);
```

**Deliverables**:
- [ ] Conflict model matching spec
- [ ] Storage CRUD
- [ ] Severity computation function

### Day 3-4: Conflict Detector

```
core/
├── conflicts/
│   ├── detector.py      # Detection pipeline
│   ├── detectors/
│   │   ├── __init__.py
│   │   ├── exclusion.py    # From exclusion constraints
│   │   ├── drift.py        # From drift threshold violations
│   │   └── derived.py      # From competing constraints
```

**Deliverables**:
- [ ] Exclusion detector (constraint fires → conflict created)
- [ ] Drift detector (weighted drift > threshold → self-conflict)
- [ ] Derived detector (placeholder for v1, full impl later)
- [ ] Integration with mutation commit

### Day 5: Conflict Resolution

```python
class ConflictResolver:
    def resolve(
        self,
        conflict_id: str,
        resolved_by: str,
        strategy: str,
        chosen_claim_id: str,
        sacrificed: List[Dict],
        tradeoff: TradeoffEntry
    ) -> Conflict:
        """
        Resolve a conflict.
        Creates a mutation for the sacrifice, updates conflict status.
        """
        conflict = self.storage.conflicts.get(conflict_id)
        
        # Create mutation for sacrificed claims
        if sacrificed:
            mutation = self.mutation_engine.propose(...)
            self.mutation_engine.commit(mutation.id, [tradeoff])
        
        # Update conflict
        conflict.status = ConflictStatus.RESOLVED
        conflict.resolution = ConflictResolution(
            resolved_at=now(),
            resolved_by=resolved_by,
            strategy=strategy,
            chosen_claim_id=chosen_claim_id,
            sacrificed=sacrificed,
            tradeoff=tradeoff,
            mutation_id=mutation.id if sacrificed else None
        )
        
        return self.storage.conflicts.update(conflict)
    
    def suppress(
        self,
        conflict_id: str,
        reason: str,
        expires_at: datetime,
        approved_by: str
    ) -> Conflict:
        """Suppress a conflict temporarily."""
        pass
```

**Deliverables**:
- [ ] Resolution creates mutation
- [ ] Resolution records tradeoff
- [ ] Suppression with expiration
- [ ] Auto-resolution (if policy allows)
- [ ] Integration tests

---

# Phase 3: Surface

**Goal**: API is functional and query engine works.

## Week 5: API Layer

### Day 1-2: FastAPI Setup + Resource Endpoints

```
api/
├── __init__.py
├── main.py              # FastAPI app
├── dependencies.py      # DI container
├── middleware/
│   ├── __init__.py
│   ├── error_handler.py
│   └── request_id.py
├── routes/
│   ├── __init__.py
│   ├── organisms.py
│   ├── claims.py
│   ├── mutations.py
│   ├── constraints.py
│   ├── conflicts.py
│   └── health.py
└── schemas/
    ├── __init__.py
    ├── requests.py
    ├── responses.py
    └── common.py
```

**Deliverables**:
- [ ] FastAPI app with proper structure
- [ ] Error handler mapping codes to HTTP status
- [ ] Request ID middleware
- [ ] All resource endpoints (organisms, claims, mutations, constraints, conflicts)
- [ ] Pagination support
- [ ] OpenAPI spec generation

### Day 3-4: Query Endpoints

```
api/routes/
├── query.py             # /query/* endpoints

core/
├── query/
│   ├── __init__.py
│   ├── evaluate.py      # Coherence, drift, conflicts
│   ├── simulate.py      # What-if analysis
│   ├── diff.py          # State comparison
│   ├── explain.py       # Lineage tracing
│   └── recommend.py     # Action suggestions
```

**Deliverables**:
- [ ] `/query/evaluate` - full organism evaluation
- [ ] `/query/simulate` - test mutations without commit
- [ ] `/query/diff` - compare organisms or time points
- [ ] `/query/explain` - trace lineage for a claim
- [ ] `/query/recommend` - suggest improvements (basic v1)

### Day 5: Coherence Computation

```python
class CoherenceCalculator:
    def __init__(self, config: InteractionConfig):
        self.alpha = config.coefficients.conflict  # 0.4
        self.beta = config.coefficients.constraint  # 0.3
        self.gamma = config.coefficients.drift  # 0.3
    
    def compute(self, organism_id: str) -> float:
        """
        coherence = 1 - (α×conflictBurden + β×constraintBurden + γ×totalDrift)
        """
        conflict_burden = self._compute_conflict_burden(organism_id)
        constraint_burden = self._compute_constraint_burden(organism_id)
        total_drift = self._compute_total_drift(organism_id)
        
        raw = 1 - (
            self.alpha * conflict_burden +
            self.beta * constraint_burden +
            self.gamma * total_drift
        )
        
        return max(0.0, min(1.0, raw))
```

**Deliverables**:
- [ ] Conflict burden calculation
- [ ] Constraint burden calculation
- [ ] Weighted drift calculation
- [ ] Coherence formula implementation
- [ ] Tests for edge cases

## Week 6: Projections + Polish

### Day 1-2: Projection Engine

```
core/
├── projections/
│   ├── __init__.py
│   ├── generator.py     # Create projections
│   ├── cache.py         # Projection storage + invalidation
│   └── types.py         # matrix, timeline, summary, diff

storage/sqlite/
├── projections.py
```

**Schema addition**:

```sql
CREATE TABLE projections (
    id TEXT PRIMARY KEY,
    organism_id TEXT NOT NULL REFERENCES organisms(id),
    projection_type TEXT NOT NULL,
    version INTEGER NOT NULL,
    as_of TEXT NOT NULL,
    generated_at TEXT NOT NULL,
    data TEXT NOT NULL,      -- JSON
    computed TEXT NOT NULL,  -- JSON
    input_hash TEXT NOT NULL -- For cache invalidation
);

CREATE INDEX idx_projections_organism ON projections(organism_id);
CREATE INDEX idx_projections_type ON projections(organism_id, projection_type);
```

**Deliverables**:
- [ ] Matrix projection (current state grid)
- [ ] Timeline projection (change history)
- [ ] Summary projection (aggregated metrics)
- [ ] Cache with content hash
- [ ] Invalidation on mutation commit

### Day 3-4: Event System

```
core/
├── events/
│   ├── __init__.py
│   ├── bus.py           # Event bus
│   ├── types.py         # Event types
│   └── handlers/
│       ├── __init__.py
│       ├── conflict_rescorer.py
│       ├── projection_invalidator.py
│       └── drift_checker.py
```

**Events**:
- `claim.value.changed`
- `claim.weight.changed`
- `claim.baseline.changed`
- `conflict.created`
- `conflict.resolved`
- `mutation.committed`

**Deliverables**:
- [ ] Event bus (sync for v1, async later)
- [ ] Mutation commit emits events
- [ ] Conflict rescorer subscribes to weight changes
- [ ] Projection invalidator subscribes to claim changes
- [ ] Tests for event flow

### Day 5: API Finalization

- [ ] Idempotency key support for mutations
- [ ] Rate limiting headers (prep for Phase 4)
- [ ] Request/response logging
- [ ] API versioning in URL
- [ ] Health check with storage connectivity

---

# Phase 4: Polish

**Goal**: Production-ready with SDK, auth, and observability.

## Week 7: SDK + Auth

### Day 1-3: Python SDK

```
sdk/
├── dna_matrix/
│   ├── __init__.py
│   ├── client.py
│   ├── models/
│   ├── resources/
│   ├── builders/
│   ├── exceptions.py
│   ├── pagination.py
│   ├── retry.py
│   └── transport.py
├── setup.py
├── pyproject.toml
└── tests/
```

**Deliverables**:
- [ ] All models matching API schemas
- [ ] MutationBuilder with propose/validate/commit
- [ ] Rich exceptions with repair hints
- [ ] Pagination iterator
- [ ] Retry with backoff
- [ ] PyPI-ready package

### Day 4-5: Authentication

```
api/middleware/
├── auth.py              # JWT + API key validation
├── rate_limit.py        # Per-key rate limiting
```

**Deliverables**:
- [ ] JWT validation
- [ ] API key validation
- [ ] Rate limiting (per key, per endpoint)
- [ ] Tenant isolation (if multi-tenant)

## Week 8: Observability + Launch

### Day 1-2: Logging + Metrics

```
core/
├── observability/
│   ├── __init__.py
│   ├── logging.py       # Structured logging
│   ├── metrics.py       # Prometheus metrics
│   └── tracing.py       # OpenTelemetry (optional)
```

**Metrics**:
- `dna_matrix_mutations_total` (by status)
- `dna_matrix_constraints_evaluated_total` (by severity, passed/failed)
- `dna_matrix_conflicts_total` (by type, status)
- `dna_matrix_coherence_histogram` (distribution)
- `dna_matrix_request_duration_seconds` (by endpoint)

**Deliverables**:
- [ ] Structured JSON logging
- [ ] Prometheus /metrics endpoint
- [ ] Request duration tracking
- [ ] Error rate tracking

### Day 3-4: Documentation

```
docs/
├── getting-started.md
├── api-reference.md     # Generated from OpenAPI
├── sdk-guide.md
├── concepts/
│   ├── organisms.md
│   ├── claims.md
│   ├── mutations.md
│   ├── constraints.md
│   └── conflicts.md
└── examples/
    ├── brand-management.md
    ├── agent-governance.md
    └── product-evolution.md
```

**Deliverables**:
- [ ] Getting started guide
- [ ] API reference (from OpenAPI)
- [ ] SDK usage guide
- [ ] Concept explanations
- [ ] Domain-specific examples

### Day 5: Launch Prep

- [ ] Docker image
- [ ] docker-compose for local dev
- [ ] Environment variable configuration
- [ ] Health check verification
- [ ] Load test (basic)
- [ ] README with quickstart

---

# Success Criteria

## Phase 1 Complete When:
- [ ] Can create organisms
- [ ] Can mutate claims
- [ ] Lineage chain is intact
- [ ] Rollback works

## Phase 2 Complete When:
- [ ] Constraints block invalid mutations
- [ ] Conflicts are created automatically
- [ ] Conflicts can be resolved
- [ ] Soft fails require tradeoffs

## Phase 3 Complete When:
- [ ] API serves all endpoints
- [ ] Evaluate returns coherence
- [ ] Simulate shows impact
- [ ] Diff compares states
- [ ] Projections are cached

## Phase 4 Complete When:
- [ ] SDK is published
- [ ] Auth works
- [ ] Metrics are exposed
- [ ] Docs exist
- [ ] Docker image runs

---

# Risk Mitigation

| Risk | Mitigation |
|------|------------|
| Constraint language too complex | Start with 10 operators, add more as needed |
| Conflict detection too slow | Index on organism_id, batch evaluation |
| Projection cache stale | Event-driven invalidation from day 1 |
| SDK doesn't match API | Generate from OpenAPI spec |
| Multi-tenant leaks | Tenant ID on every query from day 1 |

---

# What's Not In v0.1

Explicitly deferred:

- [ ] GraphQL (REST is enough for MVP)
- [ ] TypeScript SDK (Python first)
- [ ] Kubernetes manifests (docker-compose is fine)
- [ ] Derived conflict detection (placeholder only)
- [ ] AI-powered recommendations (rule-based first)
- [ ] Real-time subscriptions (polling is fine)
- [ ] Postgres backend (SQLite first)

These are v0.2+ features after the core is proven.

---

# Total Timeline

| Phase | Duration | Outcome |
|-------|----------|---------|
| Phase 1 | 2 weeks | Core engine works |
| Phase 2 | 2 weeks | Intelligence works |
| Phase 3 | 2 weeks | API works |
| Phase 4 | 2 weeks | Production ready |
| **Total** | **8 weeks** | **Shippable MVP** |

This is aggressive but achievable with focus.

---

## Start Here

```bash
# Day 1, Hour 1
mkdir dna-matrix
cd dna-matrix
git init
python -m venv .venv
source .venv/bin/activate
pip install pydantic fastapi uvicorn pytest

# Create structure
mkdir -p core/{models,engine,constraints,conflicts,query,projections,events}
mkdir -p storage/sqlite
mkdir -p api/{routes,schemas,middleware}
mkdir -p sdk/dna_matrix
mkdir -p tests/{core,api,integration}
mkdir -p docs

# First file
touch core/models/organism.py
```

Then write the Organism dataclass. Then write the test. Then make it pass.

That's how systems that work get built.
