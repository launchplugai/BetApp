# SCH_SDK_CONTRACT.md
# Sherlock SDK Contract

**Version:** 1.0.0
**Status:** CANONICAL
**Last Updated:** 2026-01-29

---

## 1. Overview

This contract defines the Sherlock library module interface. Sherlock is a standalone investigation engine that evaluates claims through a structured 6-step loop.

### 1.1 Module Identity

```
Package: sherlock
Location: /sherlock/
Entry Point: sherlock.SherlockEngine
Version: 1.0.0
```

### 1.2 Constraints (LOCKED)

| Constraint | Enforcement |
|------------|-------------|
| MUST NOT call external network | No urllib, requests, httpx, aiohttp |
| MUST NOT mutate application state | No database writes, no file writes |
| MUST be deterministic | Same input => same output, always |
| MUST NOT import app modules | sherlock/ is self-contained |
| Mutations are OFF by default | `mutations_enabled=False` |

---

## 2. ClaimInput Schema

The entry point for all investigations.

### 2.1 JSON Schema

```json
{
  "$schema": "https://json-schema.org/draft/2020-12/schema",
  "type": "object",
  "required": ["claim_text"],
  "properties": {
    "claim_text": {
      "type": "string",
      "minLength": 1,
      "description": "The claim to investigate"
    },
    "iterations": {
      "type": "integer",
      "minimum": 1,
      "maximum": 10,
      "default": 3,
      "description": "Maximum investigation iterations"
    },
    "validation_threshold": {
      "type": "number",
      "minimum": 0.0,
      "maximum": 1.0,
      "default": 0.85,
      "description": "Logic audit pass threshold"
    },
    "scope": {
      "type": "object",
      "default": {},
      "description": "Investigation scope constraints"
    },
    "evidence_policy": {
      "type": "object",
      "default": {},
      "description": "Evidence gathering policy"
    },
    "tone": {
      "type": ["string", "null"],
      "default": null,
      "description": "Output tone preference"
    },
    "time_bounds": {
      "type": ["object", "null"],
      "default": null,
      "description": "Temporal constraints"
    },
    "prior_assumptions": {
      "type": "array",
      "items": {"type": "string"},
      "default": [],
      "description": "Explicit prior assumptions"
    }
  },
  "additionalProperties": false
}
```

### 2.2 Python Type

```python
class ClaimInput(BaseModel):
    claim_text: str                          # Required, min 1 char
    iterations: int = 3                      # 1-10
    validation_threshold: float = 0.85       # 0.0-1.0
    scope: Dict[str, Any] = {}
    evidence_policy: Dict[str, Any] = {}
    tone: Optional[str] = None
    time_bounds: Optional[Dict[str, Any]] = None
    prior_assumptions: List[str] = []

    class Config:
        frozen = True  # Immutable
```

---

## 3. IterationArtifacts Schema

All artifacts from a single investigation iteration.

### 3.1 JSON Schema

```json
{
  "type": "object",
  "required": ["version", "locked_claim", "evidence_map", "argument_graph", "verdict", "audit"],
  "properties": {
    "version": {
      "type": "integer",
      "minimum": 1,
      "description": "Iteration number (1-indexed)"
    },
    "locked_claim": {
      "$ref": "#/definitions/LockedClaim"
    },
    "evidence_map": {
      "$ref": "#/definitions/EvidenceMap"
    },
    "argument_graph": {
      "$ref": "#/definitions/ArgumentGraph"
    },
    "verdict": {
      "$ref": "#/definitions/VerdictDraft"
    },
    "audit": {
      "$ref": "#/definitions/LogicAuditResult"
    },
    "mutations": {
      "type": "array",
      "items": {"$ref": "#/definitions/MutationEvent"},
      "default": [],
      "description": "Proposed mutations (empty if disabled)"
    }
  }
}
```

### 3.2 Sub-Artifact Schemas

#### LockedClaim

```json
{
  "type": "object",
  "required": ["version", "testable_claim"],
  "properties": {
    "version": {"type": "integer", "minimum": 1},
    "testable_claim": {"type": "string", "minLength": 1},
    "subclaims": {"type": "array", "items": {"type": "string"}, "default": []},
    "assumptions": {"type": "array", "items": {"type": "string"}, "default": []},
    "falsifiability": {"type": "array", "items": {"type": "string"}, "default": []}
  }
}
```

#### EvidenceMap

```json
{
  "type": "object",
  "required": ["version"],
  "properties": {
    "version": {"type": "integer", "minimum": 1},
    "items": {
      "type": "array",
      "items": {
        "type": "object",
        "required": ["tier", "source_type", "citation", "summary", "reliability"],
        "properties": {
          "tier": {"enum": ["tier_1", "tier_2", "tier_3"]},
          "source_type": {"type": "string"},
          "citation": {"type": "string"},
          "summary": {"type": "string"},
          "reliability": {"type": "number", "minimum": 0.0, "maximum": 1.0}
        }
      },
      "default": []
    }
  }
}
```

#### ArgumentGraph

```json
{
  "type": "object",
  "required": ["version"],
  "properties": {
    "version": {"type": "integer", "minimum": 1},
    "nodes": {
      "type": "array",
      "items": {
        "type": "object",
        "required": ["id", "side", "claim"],
        "properties": {
          "id": {"type": "string"},
          "side": {"enum": ["pro", "con"]},
          "claim": {"type": "string"},
          "supports": {"type": "array", "items": {"type": "string"}, "default": []},
          "attacks": {"type": "array", "items": {"type": "string"}, "default": []}
        }
      },
      "default": []
    }
  }
}
```

#### VerdictDraft

```json
{
  "type": "object",
  "required": ["version", "verdict", "confidence"],
  "properties": {
    "version": {"type": "integer", "minimum": 1},
    "verdict": {
      "enum": ["true", "likely_true", "unclear", "likely_false", "false", "non_falsifiable"]
    },
    "confidence": {"type": "number", "minimum": 0.0, "maximum": 1.0},
    "score_breakdown": {"type": "object", "default": {}},
    "rationale_bullets": {"type": "array", "items": {"type": "string"}, "default": []}
  }
}
```

---

## 4. FinalReport Schema

The complete investigation output.

### 4.1 JSON Schema

```json
{
  "type": "object",
  "required": ["iterations", "final_verdict", "publishable_report", "algorithm_evolution_report", "logic_audit_appendix", "mutation_log"],
  "properties": {
    "iterations": {
      "type": "integer",
      "minimum": 1,
      "description": "Number of completed iterations"
    },
    "final_verdict": {
      "$ref": "#/definitions/VerdictDraft",
      "description": "Final verdict from last iteration"
    },
    "publishable_report": {
      "type": "object",
      "required": ["claim", "verdict", "confidence", "iterations", "rationale"],
      "properties": {
        "claim": {"type": "string"},
        "verdict": {"type": "string"},
        "confidence": {"type": "number"},
        "iterations": {"type": "integer"},
        "rationale": {"type": "array", "items": {"type": "string"}}
      },
      "description": "Structured report for UI rendering"
    },
    "algorithm_evolution_report": {
      "type": "object",
      "required": ["iterations", "audit_scores", "final_passed", "mutations_proposed"],
      "properties": {
        "iterations": {"type": "integer"},
        "audit_scores": {"type": "array", "items": {"type": "number"}},
        "final_passed": {"type": "boolean"},
        "mutations_proposed": {"type": "integer"}
      },
      "description": "How the investigation evolved"
    },
    "logic_audit_appendix": {
      "type": "array",
      "items": {"$ref": "#/definitions/LogicAuditResult"},
      "description": "All audit results from all iterations"
    },
    "mutation_log": {
      "type": "array",
      "items": {"$ref": "#/definitions/MutationEvent"},
      "default": [],
      "description": "All mutation events (empty if disabled)"
    }
  }
}
```

### 4.2 Python Type

```python
class FinalReport(BaseModel):
    iterations: int                                    # >= 1
    final_verdict: VerdictDraft
    publishable_report: Dict[str, Any]
    algorithm_evolution_report: Dict[str, Any]
    logic_audit_appendix: List[LogicAuditResult]
    mutation_log: List[MutationEvent]                  # Empty if mutations disabled

    class Config:
        frozen = True

    def to_json(self) -> str: ...
    @classmethod
    def from_json(cls, json_str: str) -> "FinalReport": ...
```

---

## 5. Audit Scoring Schema

### 5.1 Category Weights (LOCKED)

```json
{
  "clarity": 0.10,
  "evidence_integrity": 0.30,
  "reasoning_validity": 0.25,
  "counterargument_handling": 0.20,
  "scope_control": 0.10,
  "conclusion_discipline": 0.05
}
```

**Invariant:** Weights MUST sum to exactly 1.0.

### 5.2 LogicAuditResult Schema

```json
{
  "type": "object",
  "required": ["version", "passed", "threshold", "category_scores", "weighted_score"],
  "properties": {
    "version": {"type": "integer", "minimum": 1},
    "passed": {"type": "boolean"},
    "threshold": {"type": "number", "minimum": 0.0, "maximum": 1.0},
    "category_scores": {
      "type": "object",
      "required": ["clarity", "evidence_integrity", "reasoning_validity", "counterargument_handling", "scope_control", "conclusion_discipline"],
      "properties": {
        "clarity": {"type": "number", "minimum": 0.0, "maximum": 1.0},
        "evidence_integrity": {"type": "number", "minimum": 0.0, "maximum": 1.0},
        "reasoning_validity": {"type": "number", "minimum": 0.0, "maximum": 1.0},
        "counterargument_handling": {"type": "number", "minimum": 0.0, "maximum": 1.0},
        "scope_control": {"type": "number", "minimum": 0.0, "maximum": 1.0},
        "conclusion_discipline": {"type": "number", "minimum": 0.0, "maximum": 1.0}
      }
    },
    "weighted_score": {"type": "number", "minimum": 0.0, "maximum": 1.0},
    "failures": {"type": "array", "items": {"type": "string"}, "default": []}
  }
}
```

### 5.3 Pass/Fail Threshold

```
DEFAULT_THRESHOLD = 0.85

passed = (weighted_score >= threshold)
```

| weighted_score | threshold | passed |
|----------------|-----------|--------|
| 0.90 | 0.85 | true |
| 0.85 | 0.85 | true |
| 0.84 | 0.85 | false |
| 0.50 | 0.85 | false |

---

## 6. Mutation Log Schema

### 6.1 MutationEvent Schema

```json
{
  "type": "object",
  "required": ["version", "trigger", "change", "risk", "expected_benefit"],
  "properties": {
    "version": {
      "type": "integer",
      "minimum": 1,
      "description": "Iteration when proposed"
    },
    "trigger": {
      "type": "string",
      "description": "What triggered the mutation proposal"
    },
    "change": {
      "type": "string",
      "description": "Proposed change description"
    },
    "risk": {
      "type": "string",
      "description": "Risk assessment"
    },
    "expected_benefit": {
      "type": "string",
      "description": "Expected benefit if applied"
    },
    "observed_outcome": {
      "type": ["string", "null"],
      "default": null,
      "description": "Outcome if applied (null if not applied)"
    }
  }
}
```

### 6.2 Mutation Policy

```
mutations_enabled = False  # DEFAULT

If mutations_enabled == False:
    mutation_log = []  # Always empty

If mutations_enabled == True:
    mutation_log = [proposed mutations from failed audits]
    # Mutations are LOGGED but NOT AUTO-APPLIED
```

---

## 7. Usage Examples

### 7.1 Basic Investigation

```python
from sherlock import SherlockEngine, ClaimInput

engine = SherlockEngine()  # mutations_enabled=False by default

claim = ClaimInput(
    claim_text="The Lakers will win the championship",
    iterations=3,
    validation_threshold=0.85
)

report = engine.run(claim)

# Check result
if report.logic_audit_appendix[-1].passed:
    print(f"Verdict: {report.final_verdict.verdict}")
else:
    print("Investigation incomplete - audit failed")
```

### 7.2 JSON Roundtrip

```python
# Serialize
json_str = report.to_json()

# Deserialize
restored = FinalReport.from_json(json_str)

assert restored.iterations == report.iterations
```

---

## 8. Compliance Checklist

Before using Sherlock SDK:

- [ ] ClaimInput has all required fields
- [ ] No network calls in evidence_policy
- [ ] threshold is reasonable (0.7-0.95 range)
- [ ] mutations_enabled is explicitly set
- [ ] FinalReport is validated before DNA persistence

---

## References

- `sherlock/models.py` - Pydantic model implementations
- `sherlock/audit.py` - Audit scoring implementation
- `sherlock/engine.py` - Investigation engine
- `docs/contracts/SYSTEM_CONTRACT_SDS.md` - System integration contract
