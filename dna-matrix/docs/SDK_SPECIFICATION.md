# DNA Matrix: SDK Specification v0.1

> Make it usable. Make it hard to misuse.

---

## Design Principles

| Principle | Implementation |
|-----------|----------------|
| **Writes only through mutations** | No direct claim setters. MutationBuilder enforces lifecycle. |
| **Typed everything** | Models match API schemas exactly |
| **Errors are actionable** | Exceptions include repair hints |
| **Pagination is automatic** | Iterators handle cursors |
| **Retries are safe** | Idempotent ops retry automatically |

---

## Package Structure

```
dna_matrix/
├── __init__.py
├── client.py           # DNAMatrixClient
├── models/
│   ├── __init__.py
│   ├── organism.py
│   ├── claim.py
│   ├── mutation.py
│   ├── constraint.py
│   ├── conflict.py
│   ├── projection.py
│   └── common.py       # Value, LensRef, Actor, etc.
├── builders/
│   ├── __init__.py
│   ├── mutation.py     # MutationBuilder
│   └── query.py        # QueryBuilder
├── exceptions.py
├── pagination.py
├── retry.py
└── transport.py        # HTTP layer
```

---

## Core Client

```python
from dna_matrix import DNAMatrixClient

# Initialize
client = DNAMatrixClient(
    base_url="https://api.dna-matrix.io/api/v1",
    api_key="dm_live_...",
    # or
    jwt_token="eyJ...",
    
    # Optional
    timeout=30,
    max_retries=3,
    retry_backoff=1.5,
)

# Resource access
client.organisms      # OrganismResource
client.claims         # ClaimResource
client.mutations      # MutationResource
client.constraints    # ConstraintResource
client.conflicts      # ConflictResource
client.query          # QueryResource
client.projections    # ProjectionResource
client.lenses         # LensResource
```

---

## Models

### Common Types

```python
from dataclasses import dataclass
from typing import Optional, List, Dict, Any, Literal
from datetime import datetime
from enum import Enum

class ValueKind(Enum):
    STRING = "string"
    NUMBER = "number"
    BOOL = "bool"
    ENUM = "enum"
    JSON = "json"

@dataclass
class Value:
    kind: ValueKind
    data: Any

@dataclass
class LensRef:
    cluster: str
    key: str

@dataclass
class Actor:
    type: Literal["human", "agent", "system"]
    id: str
    label: str

@dataclass
class TradeoffEntry:
    gave_up: Dict[str, Any]
    gained: Dict[str, Any]
    weight: float
    cost: Optional[str] = None
    justification: Optional[str] = None

@dataclass
class ConstraintResult:
    constraint_id: str
    passed: bool
    severity: Literal["hard", "soft"]
    code: str
    message: str
    evidence: Dict[str, Any]
    repair_hints: List[Dict[str, Any]]
```

### Organism

```python
@dataclass
class Organism:
    id: str
    organism_type: str
    name: str
    tags: List[str]
    created_at: datetime
    updated_at: datetime
```

### Claim

```python
@dataclass
class Baseline:
    mode: Literal["snapshot", "declared", "ideal", "historical", "selected"]
    ref: Optional[str]
    value: Optional[Value]
    captured_at: Optional[datetime]

@dataclass
class Claim:
    id: str
    organism_id: str
    lens_id: str
    lens: LensRef
    value: Value
    weight: float
    constraints: List[str]
    baseline: Optional[Baseline]
    last_mutation_id: Optional[str]
    version: int
    created_at: datetime
    updated_at: datetime
```

### Mutation

```python
class MutationOp(Enum):
    SET = "set"
    MERGE = "merge"
    DELETE = "delete"
    REWEIGHT = "reweight"
    REBASELINE = "rebaseline"
    CONSTRAIN = "constrain"

class MutationStatus(Enum):
    PROPOSED = "proposed"
    VALIDATED = "validated"
    COMMITTED = "committed"
    REJECTED = "rejected"
    ROLLED_BACK = "rolledBack"

@dataclass
class MutationChange:
    claim_id: str
    op: MutationOp
    before: Optional[Any]
    after: Any

@dataclass
class Mutation:
    id: str
    organism_id: str
    actor: Actor
    intent: Optional[str]
    changes: List[MutationChange]
    tradeoffs: List[TradeoffEntry]
    constraint_results: List[ConstraintResult]
    conflicts_created: List[str]
    status: MutationStatus
    prev_mutation_id: Optional[str]
    created_at: datetime
    committed_at: Optional[datetime]
```

### Conflict

```python
class ConflictType(Enum):
    EXCLUSION_CONSTRAINT = "exclusion-constraint"
    BASELINE_VIOLATION = "baseline-violation"
    DERIVED = "derived"

class ConflictStatus(Enum):
    ACTIVE = "active"
    RESOLVED = "resolved"
    SUPPRESSED = "suppressed"

class ConflictSeverity(Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    EXISTENTIAL = "existential"

@dataclass
class ConflictClaim:
    claim_id: str
    lens: str
    value: Any
    weight: float

@dataclass
class ConflictResolution:
    resolved_at: datetime
    resolved_by: str
    strategy: str
    chosen_claim_id: str
    sacrificed: List[Dict[str, Any]]
    tradeoff: TradeoffEntry
    mutation_id: str

@dataclass
class Conflict:
    id: str
    type: ConflictType
    status: ConflictStatus
    severity: ConflictSeverity
    organism_id: str
    claims: List[ConflictClaim]
    origin: Dict[str, Any]
    baseline: Optional[Dict[str, Any]]
    tradeoff_required: bool
    lineage: Dict[str, Any]
    resolution: Optional[ConflictResolution]
    created_at: datetime
    updated_at: datetime
```

---

## Exceptions

Map API error codes to typed exceptions.

```python
class DNAMatrixError(Exception):
    """Base exception for all SDK errors."""
    def __init__(self, code: str, message: str, details: Dict = None):
        self.code = code
        self.message = message
        self.details = details or {}
        super().__init__(message)

class ConstraintHardFailError(DNAMatrixError):
    """Hard constraint blocked the mutation."""
    
    @property
    def constraint_results(self) -> List[ConstraintResult]:
        return [ConstraintResult(**r) for r in self.details.get("constraintResults", [])]
    
    @property
    def repair_hints(self) -> List[Dict]:
        """Aggregate repair hints from all failed constraints."""
        hints = []
        for result in self.constraint_results:
            hints.extend(result.repair_hints)
        return hints
    
    def suggested_patches(self) -> List[Dict]:
        """Convert repair hints to mutation-ready patches."""
        patches = []
        for hint in self.repair_hints:
            if hint.get("action") == "set":
                patches.append({
                    "lens": hint["lens"],
                    "op": "set",
                    "value": hint["suggest"]
                })
        return patches

class ConstraintSoftFailError(DNAMatrixError):
    """Soft constraint failed, tradeoff required."""
    
    @property
    def constraint_results(self) -> List[ConstraintResult]:
        return [ConstraintResult(**r) for r in self.details.get("constraintResults", [])]

class TradeoffRequiredError(DNAMatrixError):
    """Mutation requires explicit tradeoff to commit."""
    pass

class ConflictUnresolvedError(DNAMatrixError):
    """Must resolve conflict before proceeding."""
    
    @property
    def conflict_id(self) -> str:
        return self.details.get("conflictId")

class LineageViolationError(DNAMatrixError):
    """Operation would break lineage integrity."""
    pass

class VersionConflictError(DNAMatrixError):
    """Concurrent modification detected."""
    
    @property
    def current_version(self) -> int:
        return self.details.get("currentVersion")
    
    @property
    def expected_version(self) -> int:
        return self.details.get("expectedVersion")

class NotFoundError(DNAMatrixError):
    """Resource not found."""
    pass

class InvalidOperationError(DNAMatrixError):
    """Invalid operation requested."""
    pass

# Error code mapping
ERROR_MAP = {
    "CONSTRAINT_HARD_FAIL": ConstraintHardFailError,
    "CONSTRAINT_SOFT_FAIL": ConstraintSoftFailError,
    "TRADEOFF_REQUIRED": TradeoffRequiredError,
    "CONFLICT_UNRESOLVED": ConflictUnresolvedError,
    "LINEAGE_VIOLATION": LineageViolationError,
    "VERSION_CONFLICT": VersionConflictError,
    "MUTATION_NOT_FOUND": NotFoundError,
    "CLAIM_NOT_FOUND": NotFoundError,
    "ORGANISM_NOT_FOUND": NotFoundError,
    "INVALID_OP": InvalidOperationError,
}
```

---

## MutationBuilder

The only way to write. Enforces the mutation lifecycle.

```python
class MutationBuilder:
    """
    Fluent builder for mutations.
    
    Usage:
        mutation = (
            client.mutations.for_organism("org_...")
            .set("brand.voice.tone", "luxury", weight=0.83)
            .reweight("brand.positioning", 0.9)
            .with_intent("rebrand-2025")
            .with_actor(Actor(type="human", id="usr_alice", label="Alice"))
        )
        
        # Validate first (recommended)
        result = mutation.validate()
        if not result.valid:
            print(result.constraint_results)
        
        # Commit with tradeoffs if needed
        committed = mutation.commit(
            tradeoffs=[
                TradeoffEntry(
                    gave_up={"lens": "brand.accessibility", "delta": -0.2},
                    gained={"lens": "brand.exclusivity", "delta": 0.3},
                    justification="Brand integrity takes precedence"
                )
            ]
        )
    """
    
    def __init__(self, client: "DNAMatrixClient", organism_id: str):
        self._client = client
        self._organism_id = organism_id
        self._changes: List[Dict] = []
        self._actor: Optional[Actor] = None
        self._intent: Optional[str] = None
        self._proposed_mutation: Optional[Mutation] = None
    
    # --- Change operations ---
    
    def set(
        self, 
        lens: str, 
        value: Any, 
        weight: Optional[float] = None,
        claim_id: Optional[str] = None
    ) -> "MutationBuilder":
        """Set a claim value."""
        change = {
            "op": "set",
            "lens": lens,
            "after": {"kind": _infer_kind(value), "data": value}
        }
        if claim_id:
            change["claimId"] = claim_id
        if weight is not None:
            # Also reweight in same mutation
            self._changes.append(change)
            return self.reweight(lens, weight, claim_id)
        self._changes.append(change)
        return self
    
    def reweight(
        self, 
        lens: str, 
        weight: float,
        claim_id: Optional[str] = None
    ) -> "MutationBuilder":
        """Change claim weight."""
        if not 0.0 <= weight <= 1.0:
            raise ValueError("Weight must be between 0.0 and 1.0")
        change = {
            "op": "reweight",
            "lens": lens,
            "after": weight
        }
        if claim_id:
            change["claimId"] = claim_id
        self._changes.append(change)
        return self
    
    def rebaseline(
        self,
        lens: str,
        mode: str = "snapshot",
        claim_id: Optional[str] = None
    ) -> "MutationBuilder":
        """Update baseline reference."""
        change = {
            "op": "rebaseline",
            "lens": lens,
            "after": {"mode": mode}
        }
        if claim_id:
            change["claimId"] = claim_id
        self._changes.append(change)
        return self
    
    def delete(
        self, 
        lens: str,
        claim_id: Optional[str] = None
    ) -> "MutationBuilder":
        """Delete a claim."""
        change = {
            "op": "delete",
            "lens": lens
        }
        if claim_id:
            change["claimId"] = claim_id
        self._changes.append(change)
        return self
    
    # --- Metadata ---
    
    def with_actor(self, actor: Actor) -> "MutationBuilder":
        """Set the actor for this mutation."""
        self._actor = actor
        return self
    
    def with_intent(self, intent: str) -> "MutationBuilder":
        """Set the intent/reason for this mutation."""
        self._intent = intent
        return self
    
    # --- Lifecycle ---
    
    def propose(self) -> Mutation:
        """
        Submit mutation proposal to server.
        Returns proposed mutation with ID.
        """
        if not self._changes:
            raise ValueError("No changes specified")
        if not self._actor:
            raise ValueError("Actor required. Use .with_actor()")
        
        payload = {
            "organismId": self._organism_id,
            "actor": {
                "type": self._actor.type,
                "id": self._actor.id,
                "label": self._actor.label
            },
            "changes": self._changes
        }
        if self._intent:
            payload["intent"] = self._intent
        
        response = self._client._post("/mutations", payload)
        self._proposed_mutation = Mutation(**response["data"])
        return self._proposed_mutation
    
    def validate(self, dry_run: bool = True) -> "ValidationResult":
        """
        Validate mutation against constraints.
        Call after propose() or will auto-propose.
        """
        if not self._proposed_mutation:
            self.propose()
        
        response = self._client._post(
            f"/mutations/{self._proposed_mutation.id}/validate",
            {"dryRun": dry_run, "requireExplain": True}
        )
        return ValidationResult(**response["data"])
    
    def commit(
        self, 
        tradeoffs: List[TradeoffEntry] = None,
        comment: str = None
    ) -> Mutation:
        """
        Commit the mutation.
        Call after propose() or will auto-propose.
        
        Raises:
            ConstraintHardFailError: If hard constraints fail
            TradeoffRequiredError: If soft constraints fail without tradeoffs
        """
        if not self._proposed_mutation:
            self.propose()
        
        payload = {}
        if tradeoffs:
            payload["tradeoffs"] = [
                {
                    "gaveUp": t.gave_up,
                    "gained": t.gained,
                    "weight": t.weight,
                    "cost": t.cost,
                    "justification": t.justification
                }
                for t in tradeoffs
            ]
        if comment:
            payload["comment"] = comment
        
        response = self._client._post(
            f"/mutations/{self._proposed_mutation.id}/commit",
            payload
        )
        return Mutation(**response["data"])
    
    def simulate(self) -> "SimulationResult":
        """
        Simulate mutation without proposing.
        Shows impact on coherence, conflicts that would be created, etc.
        """
        response = self._client._post("/query/simulate", {
            "organismId": self._organism_id,
            "changes": self._changes,
            "include": {
                "coherenceDelta": True,
                "conflictsCreated": True,
                "constraintResults": True
            }
        })
        return SimulationResult(**response["data"])


@dataclass
class ValidationResult:
    mutation_id: str
    valid: bool
    hard_fails: int
    soft_fails: int
    constraint_results: List[ConstraintResult]
    conflicts_would_create: List[Dict]
    tradeoff_required: bool
    explain: Optional[Dict] = None


@dataclass
class SimulationResult:
    valid: bool
    coherence_before: float
    coherence_after: float
    coherence_delta: float
    conflicts_would_create: List[Dict]
    constraint_results: List[ConstraintResult]
    tradeoff_required: bool
    warnings: List[str]
```

---

## Resource Classes

### OrganismResource

```python
class OrganismResource:
    def __init__(self, client: "DNAMatrixClient"):
        self._client = client
    
    def create(
        self,
        name: str,
        organism_type: str,
        tags: List[str] = None
    ) -> Organism:
        """Create a new organism."""
        response = self._client._post("/organisms", {
            "name": name,
            "organismType": organism_type,
            "tags": tags or []
        })
        return Organism(**response["data"])
    
    def get(self, organism_id: str) -> Organism:
        """Get organism by ID."""
        response = self._client._get(f"/organisms/{organism_id}")
        return Organism(**response["data"])
    
    def list(
        self,
        organism_type: str = None,
        tag: str = None,
        limit: int = 50
    ) -> "PaginatedIterator[Organism]":
        """List organisms with optional filters."""
        params = {"limit": limit}
        if organism_type:
            params["type"] = organism_type
        if tag:
            params["tag"] = tag
        return PaginatedIterator(
            self._client,
            "/organisms",
            params,
            Organism
        )
    
    def claims(self, organism_id: str, **kwargs) -> "PaginatedIterator[Claim]":
        """Get claims for an organism."""
        return PaginatedIterator(
            self._client,
            f"/organisms/{organism_id}/claims",
            kwargs,
            Claim
        )
    
    def conflicts(self, organism_id: str, **kwargs) -> "PaginatedIterator[Conflict]":
        """Get conflicts for an organism."""
        return PaginatedIterator(
            self._client,
            f"/organisms/{organism_id}/conflicts",
            kwargs,
            Conflict
        )
    
    def mutations(self, organism_id: str, **kwargs) -> "PaginatedIterator[Mutation]":
        """Get mutation history for an organism."""
        return PaginatedIterator(
            self._client,
            f"/organisms/{organism_id}/mutations",
            kwargs,
            Mutation
        )
```

### MutationResource

```python
class MutationResource:
    def __init__(self, client: "DNAMatrixClient"):
        self._client = client
    
    def for_organism(self, organism_id: str) -> MutationBuilder:
        """
        Start building a mutation for an organism.
        This is the only way to modify claims.
        """
        return MutationBuilder(self._client, organism_id)
    
    def get(self, mutation_id: str) -> Mutation:
        """Get mutation by ID."""
        response = self._client._get(f"/mutations/{mutation_id}")
        return Mutation(**response["data"])
    
    def rollback(
        self,
        mutation_id: str,
        reason: str,
        actor: Actor
    ) -> Mutation:
        """Rollback a committed mutation."""
        response = self._client._post(f"/mutations/{mutation_id}/rollback", {
            "reason": reason,
            "actor": {
                "type": actor.type,
                "id": actor.id,
                "label": actor.label
            }
        })
        return Mutation(**response["data"])
```

### ConflictResource

```python
class ConflictResource:
    def __init__(self, client: "DNAMatrixClient"):
        self._client = client
    
    def list(
        self,
        status: str = None,
        severity: str = None,
        conflict_type: str = None,
        organism_id: str = None,
        limit: int = 50
    ) -> "PaginatedIterator[Conflict]":
        """List conflicts with filters."""
        params = {"limit": limit}
        if status:
            params["status"] = status
        if severity:
            params["severity"] = severity
        if conflict_type:
            params["type"] = conflict_type
        if organism_id:
            params["organismId"] = organism_id
        return PaginatedIterator(
            self._client,
            "/conflicts",
            params,
            Conflict
        )
    
    def get(self, conflict_id: str) -> Conflict:
        """Get conflict by ID."""
        response = self._client._get(f"/conflicts/{conflict_id}")
        return Conflict(**response["data"])
    
    def resolve(
        self,
        conflict_id: str,
        resolved_by: str,
        strategy: str,
        chosen_claim_id: str,
        sacrificed: List[Dict],
        tradeoff: TradeoffEntry
    ) -> Conflict:
        """Resolve a conflict."""
        response = self._client._post(f"/conflicts/{conflict_id}/resolve", {
            "resolvedBy": resolved_by,
            "strategy": strategy,
            "chosenClaimId": chosen_claim_id,
            "sacrificed": sacrificed,
            "tradeoff": {
                "gaveUp": tradeoff.gave_up,
                "gained": tradeoff.gained,
                "weight": tradeoff.weight,
                "justification": tradeoff.justification
            }
        })
        return Conflict(**response["data"])
    
    def suppress(
        self,
        conflict_id: str,
        reason: str,
        expires_at: datetime,
        approved_by: str
    ) -> Conflict:
        """Suppress a conflict temporarily."""
        response = self._client._post(f"/conflicts/{conflict_id}/suppress", {
            "reason": reason,
            "expiresAt": expires_at.isoformat(),
            "approvedBy": approved_by
        })
        return Conflict(**response["data"])
    
    def stats(self, organism_id: str = None) -> Dict:
        """Get conflict statistics."""
        params = {}
        if organism_id:
            params["organismId"] = organism_id
        response = self._client._get("/conflicts/stats", params)
        return response["data"]
```

### QueryResource

```python
class QueryResource:
    def __init__(self, client: "DNAMatrixClient"):
        self._client = client
    
    def evaluate(
        self,
        organism_id: str,
        include_coherence: bool = True,
        include_drift: bool = True,
        include_conflicts: bool = True,
        include_constraints: bool = True,
        include_explain: bool = True
    ) -> "EvaluationResult":
        """Evaluate an organism's current state."""
        response = self._client._post("/query/evaluate", {
            "organismId": organism_id,
            "include": {
                "coherence": include_coherence,
                "drift": include_drift,
                "conflicts": include_conflicts,
                "constraintResults": include_constraints,
                "explain": include_explain
            }
        })
        return EvaluationResult(**response["data"])
    
    def diff(
        self,
        left_organism_id: str,
        right_organism_id: str = None,
        left_as_of: datetime = None,
        right_as_of: datetime = None
    ) -> "DiffResult":
        """
        Compare two organisms or an organism at two points in time.
        
        Examples:
            # Compare two organisms
            diff(left="org_a", right="org_b")
            
            # Compare organism to its past state
            diff(left="org_a", left_as_of=datetime(2024, 6, 1))
        """
        left = {"organismId": left_organism_id}
        if left_as_of:
            left["asOf"] = left_as_of.isoformat()
        
        right = {"organismId": right_organism_id or left_organism_id}
        if right_as_of:
            right["asOf"] = right_as_of.isoformat()
        
        response = self._client._post("/query/diff", {
            "left": left,
            "right": right,
            "include": {"claims": True, "weights": True, "drift": True}
        })
        return DiffResult(**response["data"])
    
    def explain(self, organism_id: str, lens: str) -> "ExplanationResult":
        """Explain how a claim value was computed."""
        response = self._client._post("/query/explain", {
            "organismId": organism_id,
            "lens": lens
        })
        return ExplanationResult(**response["data"])
    
    def recommend(
        self,
        organism_id: str,
        goal: str,
        max_changes: int = 5,
        preserve_lenses: List[str] = None
    ) -> "RecommendationResult":
        """Get recommendations for improving organism state."""
        response = self._client._post("/query/recommend", {
            "organismId": organism_id,
            "goal": goal,
            "constraints": {
                "maxChanges": max_changes,
                "preserveLenses": preserve_lenses or []
            }
        })
        return RecommendationResult(**response["data"])


@dataclass
class EvaluationResult:
    organism_id: str
    coherence: float
    drift: Dict
    conflicts: Dict
    constraint_results: Dict
    explain: Dict


@dataclass
class DiffResult:
    summary: Dict
    changes: List[Dict]


@dataclass
class ExplanationResult:
    lens: str
    value: Any
    computed: bool
    resolver: Optional[Dict]
    inputs: List[Dict]
    lineage: Dict


@dataclass
class RecommendationResult:
    recommendations: List[Dict]
    projected_coherence: float
```

---

## Pagination

Automatic cursor-based pagination.

```python
from typing import TypeVar, Generic, Iterator

T = TypeVar("T")

class PaginatedIterator(Generic[T]):
    """
    Lazy iterator that handles pagination automatically.
    
    Usage:
        for organism in client.organisms.list():
            print(organism.name)
        
        # Or collect all
        all_orgs = list(client.organisms.list())
        
        # Or get first page only
        first_page = client.organisms.list().page()
    """
    
    def __init__(
        self,
        client: "DNAMatrixClient",
        endpoint: str,
        params: Dict,
        model_class: type
    ):
        self._client = client
        self._endpoint = endpoint
        self._params = params
        self._model_class = model_class
        self._cursor: Optional[str] = None
        self._exhausted = False
    
    def __iter__(self) -> Iterator[T]:
        while not self._exhausted:
            page = self._fetch_page()
            for item in page:
                yield item
    
    def page(self) -> List[T]:
        """Fetch a single page."""
        return self._fetch_page()
    
    def all(self) -> List[T]:
        """Fetch all pages (use with caution for large datasets)."""
        return list(self)
    
    def _fetch_page(self) -> List[T]:
        params = {**self._params}
        if self._cursor:
            params["cursor"] = self._cursor
        
        response = self._client._get(self._endpoint, params)
        
        self._cursor = response.get("meta", {}).get("cursor")
        if not self._cursor:
            self._exhausted = True
        
        return [self._model_class(**item) for item in response["data"]]
```

---

## Retry Logic

Safe retries for idempotent operations.

```python
import time
from functools import wraps

class RetryConfig:
    def __init__(
        self,
        max_retries: int = 3,
        backoff_factor: float = 1.5,
        retry_on: tuple = (502, 503, 504),
        idempotent_methods: tuple = ("GET", "HEAD", "OPTIONS")
    ):
        self.max_retries = max_retries
        self.backoff_factor = backoff_factor
        self.retry_on = retry_on
        self.idempotent_methods = idempotent_methods

def with_retry(config: RetryConfig):
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            last_error = None
            method = kwargs.get("method", "GET")
            
            for attempt in range(config.max_retries + 1):
                try:
                    return func(*args, **kwargs)
                except HTTPError as e:
                    last_error = e
                    
                    # Only retry idempotent methods or if explicitly safe
                    if method not in config.idempotent_methods:
                        if not kwargs.get("idempotency_key"):
                            raise
                    
                    if e.status_code not in config.retry_on:
                        raise
                    
                    if attempt < config.max_retries:
                        sleep_time = config.backoff_factor ** attempt
                        time.sleep(sleep_time)
            
            raise last_error
        return wrapper
    return decorator
```

---

## Idempotency

For safe mutation commits.

```python
import uuid

class DNAMatrixClient:
    def commit_mutation(
        self,
        mutation_id: str,
        tradeoffs: List[TradeoffEntry] = None,
        idempotency_key: str = None
    ) -> Mutation:
        """
        Commit mutation with idempotency protection.
        
        Args:
            mutation_id: The mutation to commit
            tradeoffs: Required tradeoffs for soft constraint failures
            idempotency_key: Optional key for duplicate prevention.
                             If not provided, generates one.
        """
        if not idempotency_key:
            idempotency_key = str(uuid.uuid4())
        
        headers = {"Idempotency-Key": idempotency_key}
        
        response = self._post(
            f"/mutations/{mutation_id}/commit",
            payload={"tradeoffs": tradeoffs},
            headers=headers
        )
        return Mutation(**response["data"])
```

---

## Complete Example

```python
from dna_matrix import DNAMatrixClient, Actor, TradeoffEntry
from dna_matrix.exceptions import ConstraintHardFailError, TradeoffRequiredError

# Initialize
client = DNAMatrixClient(
    base_url="https://api.dna-matrix.io/api/v1",
    api_key="dm_live_..."
)

# Create an organism
apple = client.organisms.create(
    name="Apple",
    organism_type="brand",
    tags=["portfolio:consumer-tech"]
)

# Build a mutation
mutation = (
    client.mutations.for_organism(apple.id)
    .set("brand.voice.tone", "luxury", weight=0.83)
    .set("brand.positioning", "premium")
    .reweight("brand.exclusivity", 0.9)
    .with_intent("rebrand-2025")
    .with_actor(Actor(type="human", id="usr_alice", label="Alice Chen"))
)

# Simulate first (optional but recommended)
sim = mutation.simulate()
print(f"Coherence delta: {sim.coherence_delta}")
if sim.warnings:
    print(f"Warnings: {sim.warnings}")

# Validate
validation = mutation.validate()
if not validation.valid:
    for result in validation.constraint_results:
        if not result.passed:
            print(f"Constraint failed: {result.message}")
            print(f"Repair hints: {result.repair_hints}")

# Try to commit
try:
    committed = mutation.commit()
    print(f"Mutation committed: {committed.id}")
except ConstraintHardFailError as e:
    print(f"Hard constraint failed: {e.message}")
    # Use suggested patches for next attempt
    patches = e.suggested_patches()
    print(f"Suggested fixes: {patches}")
except TradeoffRequiredError as e:
    # Soft constraint failed, need explicit tradeoff
    committed = mutation.commit(
        tradeoffs=[
            TradeoffEntry(
                gave_up={"lens": "brand.accessibility", "delta": -0.2},
                gained={"lens": "brand.exclusivity", "delta": 0.3},
                justification="Brand integrity takes precedence"
            )
        ]
    )

# Evaluate the organism
evaluation = client.query.evaluate(apple.id)
print(f"Coherence: {evaluation.coherence}")
print(f"Open conflicts: {evaluation.conflicts['active']}")

# Handle conflicts
for conflict in client.conflicts.list(organism_id=apple.id, status="active"):
    print(f"Conflict: {conflict.claims[0].lens} vs {conflict.claims[1].lens}")
    print(f"Severity: {conflict.severity.value}")
    
    # Resolve it
    client.conflicts.resolve(
        conflict_id=conflict.id,
        resolved_by="usr_alice",
        strategy="prefer-weight",
        chosen_claim_id=conflict.claims[0].claim_id,
        sacrificed=[{
            "claimId": conflict.claims[1].claim_id,
            "action": "changed",
            "newValue": {"kind": "enum", "data": "minimal"}
        }],
        tradeoff=TradeoffEntry(
            gave_up={"lens": conflict.claims[1].lens},
            gained={"lens": conflict.claims[0].lens, "preserved": True},
            weight=0.7,
            justification="Brand positioning takes precedence"
        )
    )

# Time travel
from datetime import datetime, timedelta

past_eval = client.query.diff(
    left_organism_id=apple.id,
    left_as_of=datetime.now() - timedelta(days=30)
)
print(f"Changes in last 30 days: {past_eval.summary['changedClaims']}")

# Explain a computed value
explanation = client.query.explain(apple.id, "brand.strength.index")
print(f"Value: {explanation.value}")
print(f"Formula: {explanation.resolver['formula']}")
for inp in explanation.inputs:
    print(f"  {inp['lens']}: {inp['value']}")
```

---

## File Structure (Final)

```
dna_matrix/
├── __init__.py          # Exports: DNAMatrixClient, models, exceptions
├── client.py            # Main client class
├── models/
│   ├── __init__.py
│   ├── organism.py
│   ├── claim.py
│   ├── mutation.py
│   ├── constraint.py
│   ├── conflict.py
│   ├── projection.py
│   ├── lens.py
│   └── common.py
├── resources/
│   ├── __init__.py
│   ├── organisms.py
│   ├── claims.py
│   ├── mutations.py
│   ├── constraints.py
│   ├── conflicts.py
│   ├── query.py
│   ├── projections.py
│   └── lenses.py
├── builders/
│   ├── __init__.py
│   ├── mutation.py      # MutationBuilder
│   └── query.py         # QueryBuilder (optional)
├── exceptions.py
├── pagination.py
├── retry.py
├── transport.py
└── tests/
    ├── test_client.py
    ├── test_mutation_builder.py
    ├── test_pagination.py
    └── test_exceptions.py
```

---

## Next Pass

**Implementation Plan**

Build order that matches risk:
1. Storage layer (SQLite first)
2. Core engine (Organisms + Claims + Mutations + Lineage)
3. Constraint evaluation
4. Conflict detection
5. Query endpoints
6. Auth + rate limiting
