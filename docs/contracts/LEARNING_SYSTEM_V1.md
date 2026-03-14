# LEARNING_SYSTEM_V1.md
# Learning System v1 Contract

**Version:** 1.0.0
**Status:** CANONICAL
**Last Updated:** 2026-03-08

---

## 1. Purpose

The Learning System exists to improve DNA Matrix / BetApp over time without compromising:

- trust
- explainability
- stability
- compliance posture

It is designed to make the system:

- better calibrated
- more relevant
- more personalized
- more useful in recommendations
- more accurate in fragility detection

### 1.1 Core Principle

The learning layer is a governed adaptive layer around a stable scoring core.

---

## 2. Product Goal

The Learning System SHOULD improve the product at these outcomes:

1. detect structurally bad bets more reliably
2. calibrate confidence more honestly
3. improve protocol relevance and weighting
4. improve recommendation usefulness
5. improve user-specific personalization

The system MUST NOT optimize for:

- maximum excitement
- maximum bets placed
- maximum engagement at any cost

---

## 3. Non-Goals

The Learning System MUST NOT:

- silently rewrite the core scoring formula
- silently alter legal or compliance language
- generate reckless or pressure-based betting advice
- optimize for user loss-making behavior
- auto-promote new heuristics directly into production
- mutate odds parsing or settlement logic
- inflate confidence scores to drive usage
- learn from inadequate sample sizes
- hide uncertainty

---

## 4. Scope

### 4.1 In Scope For v1

- outcome logging
- confidence calibration
- protocol weight tuning proposals
- recommendation ranking improvements
- user preference and risk identity learning
- alert relevance tuning
- model and config version tracking
- admin review workflow for learning proposals

### 4.2 Out Of Scope For v1

- autonomous bet generation
- autonomous bankroll aggression
- direct self-modification of protocol definitions
- real-time self-rewriting of production scoring
- unsupervised model deployment
- black-box neural optimization without auditability

---

## 5. System Philosophy

The Learning System uses a proposal -> review -> promotion model.

### 5.1 Canonical Loop

```text
Evaluate
-> Log
-> Observe outcome
-> Analyze
-> Generate proposal
-> Review proposal
-> Approve or reject
-> Promote approved change
-> Monitor impact
```

### 5.2 Rule

No production-affecting learning change may occur without:

- recorded proposal
- versioned config
- audit trail
- approval event
- rollback path

---

## 6. Learning Layers

The Learning System is divided into five layers:

1. Outcome Logging
2. Calibration Learning
3. Protocol Weight Tuning
4. Personalization Learning
5. Strategy Discovery

---

## 7. Layer 1: Outcome Logging

### 7.1 Purpose

Record enough structured truth to learn from system behavior and real-world outcomes.

### 7.2 Required Log Fields

Each evaluated bet or slip MUST record:

- `evaluationId`
- `betId`
- `userId`
- `timestamp`
- `sport`
- `marketType`
- `betType`
- `legs`
- `stake`
- `oddsSnapshot`
- `bestBook`
- `edgeScore`
- `confidenceScore`
- `fragilityScore`
- `stabilityScore`
- `dnaMode`
- `triggeredProtocols`
- `recommendationType`
- `recommendationDetails`
- `userAction`
- `finalResult`
- `legsWon`
- `legsLost`
- `settlementTimestamp`
- `modelVersion`
- `protocolLibraryVersion`
- `calibrationVersion`
- `recommendationVersion`

### 7.3 Optional But Valuable Fields

- closing line
- injury or news changes after evaluation
- odds drift after evaluation
- whether user modified bet after suggestion
- alert interaction history
- whether recommendation was accepted or ignored

### 7.4 Requirements

- logs MUST be immutable after settlement except for append-only enrichment fields
- logs MUST be timestamped
- logs MUST be version-linked
- logs MUST be queryable by sport, market, protocol, and user segment

---

## 8. Layer 2: Calibration Learning

### 8.1 Purpose

Improve how honest the scores are.

### 8.2 Key Question

When the system says `78` confidence, does reality support that level of confidence?

### 8.3 Inputs

- evaluation logs
- settlement outcomes
- confidence buckets
- sport and market breakdowns

### 8.4 Outputs

- calibration curves
- bucket correction tables
- overconfidence alerts
- underconfidence alerts
- proposed confidence mapping updates

### 8.5 Allowed Actions

- generate new calibration tables
- propose score remapping
- propose sport-specific confidence adjustment ranges

### 8.6 Forbidden Actions

- altering the raw DNA formula directly
- rewriting explanation language without review

### 8.7 Promotion Rule

Calibration updates require:

- minimum sample threshold
- holdout evaluation
- approval in admin workflow

---

## 9. Layer 3: Protocol Weight Tuning

### 9.1 Purpose

Improve the impact estimates of protocols over time.

### 9.2 Key Question

How much should each protocol affect:

- fragility
- stability
- edge
- recommendation severity

### 9.3 Learnable Fields

- protocol `riskWeight`
- confidence thresholds
- fragility contribution
- stability penalty
- recommendation severity multiplier
- sport-specific tuning
- market-specific tuning

### 9.4 Constraints

Every tunable field MUST have:

- current value
- allowed range
- minimum step size
- max change per promotion
- sample threshold

### 9.5 Forbidden Actions

- redefining what a protocol is
- changing trigger logic without separate protocol review
- auto-promoting protocol impact to production without approval

### 9.6 Promotion Rule

Protocol tuning proposals require:

- statistical evidence
- holdout validation
- no material calibration damage
- no explanation incoherence
- review approval

---

## 10. Layer 4: Personalization Learning

### 10.1 Purpose

Improve the system’s fit to each user without altering core scoring integrity.

### 10.2 Learnable Areas

- user risk identity
- preferred explanation density
- preferred markets and sports
- protocol sensitivity preferences
- alert timing
- favorite workflows
- response to recommendation types

### 10.3 Allowed Outputs

- explanation style selection
- alert ranking
- protocol default settings
- suggestion ordering
- pick feed prioritization
- bankroll guidance display style

### 10.4 Forbidden Outputs

- score inflation to match user preference
- suppressing valid warnings because the user dislikes them
- more aggressive advice to boost action rate

### 10.5 User Control

Users MUST be allowed to:

- opt out of personalization
- reset their profile
- override inferred preferences

---

## 11. Layer 5: Strategy Discovery

### 11.1 Purpose

Detect recurring useful patterns that may justify new protocols, bundles, or heuristics.

### 11.2 Allowed Outputs

- candidate protocol proposals
- candidate protocol bundle proposals
- candidate risk segmentation ideas
- research notes for analyst or admin review

### 11.3 Forbidden Outputs

- direct auto-creation of production protocols
- direct activation of new strategy logic
- user-facing behavior changes without promotion

### 11.4 Rule

This layer produces research proposals, not production logic.

---

## 12. Learning Targets

The system SHOULD optimize for these priorities in order:

1. calibration honesty
2. fragility detection quality
3. recommendation usefulness
4. protocol relevance
5. user-specific fit

The system MUST NOT prioritize raw pick hit rate without context.

---

## 13. Data Contracts

### 13.1 Evaluation Log Contract

```json
{
  "evaluationId": "eval_123",
  "betId": "bet_456",
  "userId": "user_789",
  "timestamp": "2026-03-08T13:20:00-05:00",
  "sport": "NBA",
  "marketType": "parlay",
  "legs": 4,
  "confidenceScore": 74,
  "fragilityScore": 58,
  "stabilityScore": 69,
  "edgeScore": 3.2,
  "dnaMode": "CORE_PLUS_PROTOCOLS",
  "triggeredProtocols": [
    "fatigue_b2b_v1",
    "pace_mismatch_v1"
  ],
  "recommendationType": "consider_simplifying",
  "userAction": "paper_placed",
  "result": "loss",
  "legsWon": 3,
  "legsLost": 1,
  "modelVersion": "dna_v1.2.0",
  "protocolLibraryVersion": "pl_v1.0.0",
  "calibrationVersion": "cal_v1.0.1",
  "recommendationVersion": "rec_v1.0.0"
}
```

### 13.2 Learning Proposal Contract

```json
{
  "proposalId": "prop_001",
  "proposalType": "protocol_tuning",
  "createdAt": "2026-03-08T15:00:00-05:00",
  "status": "pending_review",
  "target": {
    "entityType": "protocol",
    "entityId": "fatigue_b2b_v1",
    "field": "stabilityPenalty"
  },
  "currentValue": -8,
  "proposedValue": -10,
  "reason": "Observed underestimation of performance degradation in qualifying games.",
  "evidence": {
    "sampleSize": 4231,
    "holdoutImprovement": 0.04,
    "calibrationImpact": "neutral"
  },
  "allowedRange": [-12, -4],
  "modelScope": ["NBA"],
  "review": {
    "required": true,
    "reviewedBy": null,
    "reviewedAt": null,
    "decision": null
  }
}
```

### 13.3 Promotion Record Contract

```json
{
  "promotionId": "prom_101",
  "proposalId": "prop_001",
  "promotedAt": "2026-03-10T09:30:00-05:00",
  "approvedBy": "admin_user_1",
  "oldVersion": "pl_v1.0.0",
  "newVersion": "pl_v1.0.1",
  "rollbackVersion": "pl_v1.0.0",
  "notes": "Approved after holdout validation and QA review."
}
```

---

## 14. Versioning

All learning-affecting systems MUST be versioned.

### 14.1 Required Versions

- `dnaModelVersion`
- `protocolLibraryVersion`
- `calibrationVersion`
- `recommendationVersion`
- `personalizationModelVersion`
- `alertRankingVersion`

### 14.2 Requirements

Every evaluation log MUST store the exact versions used at evaluation time.

### 14.3 Why This Matters

Versioning must allow the system to answer:

- why did this score happen?
- what logic was live then?
- what changed later?
- was a trust drop tied to a promoted learning change?

---

## 15. Guardrails

### 15.1 Hard Guardrails

These are absolute:

- no silent production mutation
- no changes without versioning
- no direct learning writes to production config
- no deployment without rollback target
- no production tuning from sub-threshold samples
- no confidence inflation to drive action
- no removal of truthful warnings for engagement reasons
- no legal or compliance copy mutation by the learning system
- no direct rewrite of core scoring equation structure

### 15.2 Soft Guardrails

These require review thresholds:

- recommendation severity changes
- protocol impact adjustments
- personalization tuning
- alert relevance ranking
- explanation ordering changes

### 15.3 Minimum Sample Thresholds

Suggested baseline thresholds:

- calibration changes: `>= 1000` settled evaluations per relevant segment
- protocol tuning: `>= 500` triggered protocol events per segment
- personalization changes: `>= 50` meaningful interactions per user pattern cluster
- strategy discovery proposals: `>= 300` relevant observed cases

These values MAY be revised, but only through explicit review.

---

## 16. Holdout And Validation Rules

Every proposal that affects production logic MUST be evaluated on:

- training set
- validation set
- holdout set

### 16.1 Proposal Acceptance Criteria

A proposal may be approved only if it:

- improves the target metric
- does not materially harm calibration
- does not reduce explanation integrity
- does not increase overconfidence rate
- stays within approved ranges
- passes regression checks

### 16.2 Regression Checks

Regression checks MUST ensure no unacceptable impact on:

- other sports
- other markets
- recommendation consistency
- admin interpretability

---

## 17. Admin Review Workflow

### 17.1 States

- `draft`
- `pending_review`
- `approved`
- `rejected`
- `promoted`
- `rolled_back`

### 17.2 Required Review Fields

- proposal summary
- affected entity
- current value
- proposed value
- supporting evidence
- sample size
- holdout results
- expected user impact
- risk notes
- reviewer decision
- reviewer notes

### 17.3 Reviewer Powers

Reviewer MAY:

- approve
- reject
- request more evidence
- narrow scope
- cap magnitude of change
- stage for limited rollout

---

## 18. Rollout Modes

### 18.1 Mode 1: Offline Analysis Only

Generate proposals but do not expose changes.

### 18.2 Mode 2: Staged Rollout

Expose changes to a limited environment or small internal cohort.

### 18.3 Mode 3: Production Rollout

Approved config becomes live.

### 18.4 Mode 4: Rollback

Immediate reversion to the prior version.

### 18.5 Recommendation

Mode 1 and Mode 2 SHOULD be used heavily in early system maturity.

---

## 19. Learning Services Architecture

Recommended services or modules:

- `evaluation_logger`
- `outcome_resolver`
- `calibration_analyzer`
- `protocol_tuner`
- `recommendation_ranker`
- `personalization_profiler`
- `strategy_discovery_engine`
- `proposal_registry`
- `promotion_auditor`
- `model_registry`
- `rollback_manager`

### 19.1 Separation Rule

Production scoring reads only from approved versioned configs.

Learning jobs write only to proposal or staging storage.

This separation is mandatory.

---

## 20. Metrics

### 20.1 Integrity Metrics

- calibration error
- overconfidence rate
- underconfidence rate
- fragility detection precision
- fragility detection recall
- explanation consistency score

### 20.2 Product Value Metrics

- evaluation usage rate
- repeat evaluation rate
- recommendation acceptance rate
- protocol interaction rate
- alert click or open rate
- daily return rate

### 20.3 Safety And Trust Metrics

- stale-data incident rate
- recommendation regret indicator
- unexplained score variance rate
- post-promotion trust drop
- rollback frequency

---

## 21. Compliance And Risk Posture

The system is an analysis platform, not a direct wagering advisor.

### 21.1 Allowed

- explain signals
- rank risk
- suggest simplification
- suggest alternative structures
- surface contextual warnings

### 21.2 Not Allowed

- guaranteed language
- coercive urgency
- manipulative framing
- hidden optimization toward higher user betting volume
- advice language implying certainty

### 21.3 Policy Rule

All learning outputs MUST preserve the line between:

- risk analysis
- betting advice

---

## 22. Allowed vs Forbidden Self-Modification

### 22.1 Allowed To Auto-Update

These MAY be auto-updated without review if explicitly configured and low-risk:

- alert send timing
- recommendation display order
- non-critical UI ranking
- personalization display density
- feed ordering preferences

### 22.2 Requires Review Before Promotion

- calibration tables
- protocol weights
- recommendation severity thresholds
- bankroll suggestion parameters
- protocol-specific confidence thresholds
- user risk identity model behavior

### 22.3 Forbidden From Self-Modifying

- legal language
- odds parsing
- settlement logic
- core scoring equation structure
- supported market definitions
- production protocol definitions
- feature access controls
- age or compliance gating

---

## 23. V1 Roadmap

### 23.1 Phase 1

- evaluation logging
- settlement and outcome joining
- version registry
- calibration reports
- admin proposal storage

### 23.2 Phase 2

- protocol tuning proposals
- recommendation ranking proposals
- personalization profiling
- review dashboard

### 23.3 Phase 3

- limited staged rollout
- strategy discovery proposals
- alert relevance tuning
- rollback tooling

### 23.4 Phase 4

- richer segmentation by sport, market, and user type
- replay diagnostics
- confidence lineage inspection
- protocol bundle discovery

---

## 24. Success Criteria

Learning System v1 is successful if:

1. confidence buckets become more honest over time
2. protocol weights become better calibrated without destabilizing trust
3. recommendations become more relevant
4. personalization improves UX without corrupting scores
5. every meaningful change is explainable, reviewable, and reversible

If the system becomes less explainable while appearing smarter, that is failure.

---

## 25. Canonical Operating Rule

The Learning System may:

- propose
- rank
- tune
- personalize

It may not silently rewrite the truth.

---

## 26. Invariants

```
INVARIANT: No production-affecting learning change may occur without proposal, review, versioning, and rollback path.
INVARIANT: Production scoring MUST read only approved versioned configs.
INVARIANT: Learning jobs MUST write only to proposal or staging storage.
INVARIANT: Confidence honesty is a higher priority than engagement optimization.
INVARIANT: The learning system MUST NOT silently rewrite the core scoring equation structure.
INVARIANT: The learning system MUST preserve the line between analysis and betting advice.
```
