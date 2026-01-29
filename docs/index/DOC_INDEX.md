# DOC_INDEX.md
# Documentation Index

**Last Updated:** 2026-01-29

---

## Anti-Drift Rule

```
RULE: No implementation ticket may proceed unless it cites
      the contract sections it touches.

ENFORCEMENT:
1. PR description MUST list affected contract sections
2. Code changes MUST NOT contradict cited contracts
3. If contract change needed, update contract FIRST
```

---

## Contract Documents

| Document | Status | Purpose | When to Consult |
|----------|--------|---------|-----------------|
| `docs/contracts/SYSTEM_CONTRACT_SDS.md` | CANONICAL | Sherlock–DNA dataflow | Before any Sherlock ↔ DNA integration |
| `docs/contracts/SCH_SDK_CONTRACT.md` | CANONICAL | Sherlock library interface | Before calling Sherlock, before modifying Sherlock |
| `docs/contracts/DNA_PRIMITIVES_CONTRACT.md` | CANONICAL | 7 Frozen Primitives schemas | Before persisting any state, before querying DNA |
| `docs/contracts/ENDPOINT_CONTRACT.md` | CANONICAL | HTTP endpoint definitions | Before adding/modifying API routes |
| `docs/contracts/INTERFACE_CONTRACT.md` | CANONICAL | Data interface schemas | Before changing request/response shapes |

---

## Mapping Documents

| Document | Status | Purpose | When to Consult |
|----------|--------|---------|-----------------|
| `docs/mappings/MAP_SHERLOCK_TO_DNA.md` | CANONICAL | Sherlock → DNA translation | Before writing DNA persistence code |

---

## Governance Documents

| Document | Status | Purpose | When to Consult |
|----------|--------|---------|-----------------|
| `docs/RALPH_LOOP.md` | LOCKED | Feature governance loop | Before proposing new features |
| `docs/SPRINT_PLAN.md` | LOCKED | Sprint definitions | Before starting any work |
| `docs/SPRINT_1_LOCK.md` | LOCKED | Sprint 1 scope lock | When questioning Sprint 1 scope |
| `docs/GOVERNANCE.md` | CANONICAL | General governance rules | When unclear about process |

---

## Specification Documents

| Document | Status | Purpose | When to Consult |
|----------|--------|---------|-----------------|
| `docs/UI_SPEC.md` | CANONICAL | UI specification | Before modifying UI |
| `docs/ENV_VARIABLES.md` | CANONICAL | Environment variables | Before adding env vars |
| `docs/deploy.md` | CANONICAL | Deployment process | Before deploying |

---

## Verification Documents

| Document | Status | Purpose | When to Consult |
|----------|--------|---------|-----------------|
| `docs/VERIFY_DEPLOYMENT.md` | CANONICAL | Deployment verification | After every deploy |

---

## Index Documents

| Document | Status | Purpose | When to Consult |
|----------|--------|---------|-----------------|
| `docs/index/DOC_INDEX.md` | CANONICAL | This index | When looking for docs |
| `docs/index/DECISION_LOG.md` | APPEND-ONLY | Architectural decisions | Before major decisions |

---

## Status Definitions

| Status | Meaning | Modification Rules |
|--------|---------|-------------------|
| CANONICAL | Authoritative source of truth | Update only via PR with review |
| LOCKED | Frozen, no changes allowed | No modifications without explicit unlock |
| DRAFT | Work in progress | May change freely |
| APPEND-ONLY | Can add, cannot modify/delete | New entries only |
| DEPRECATED | Being phased out | Do not use for new work |

---

## Citation Format

When citing contracts in PRs/tickets:

```
Affects: docs/contracts/SCH_SDK_CONTRACT.md#section-4-finalreport-schema
Affects: docs/contracts/DNA_PRIMITIVES_CONTRACT.md#section-2-3-conflict
```

---

## Document Ownership

| Category | Owner | Review Required By |
|----------|-------|-------------------|
| Contracts | Architecture | Any contract change requires arch review |
| Governance | Product | Product sign-off on governance changes |
| Specs | Engineering | Engineering lead review |
| Index | Anyone | Self-service, keep accurate |
