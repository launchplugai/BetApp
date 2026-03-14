# Documentation Index

**Last Updated:** 2026-03-14

This index is for the active BetApp application. If a document conflicts with running code, treat code as the source of truth and update the docs.

## Start Here

Read these first when joining the project:

| Document | Status | Purpose |
|----------|--------|---------|
| `README.md` | CANONICAL | Product framing, repo reality, and entry points |
| `docs/architecture/SYSTEM_RESTORATION_BLUEPRINT.md` | CANONICAL | Canonical architecture pivot and current module model |
| `docs/contracts/AIRLOCK_MEMBRANE_CONTRACT.md` | CANONICAL | Restored boundary rules for frontend-safe system interaction |
| `docs/contracts/SHERLOCK_DNA_INTERACTION_CONTRACT.md` | CANONICAL | Canonical bounded interaction between Sherlock and DNA |
| `docs/ops/ARCHITECTURE_RESTORATION_SPRINT_MAP.md` | CANONICAL | Sprint order and guardrails for the architecture restoration refactor |
| `docs/contracts/DNA_SCORING_MODEL.md` | CANONICAL | Canonical scoring outputs, pipeline, and explanation contract |
| `docs/contracts/PROTOCOL_LIBRARY_V1.md` | CANONICAL | Protocol definitions, launch tiers, and modifier rules |
| `docs/contracts/LEARNING_SYSTEM_V1.md` | CANONICAL | Governed learning model, proposals, review, promotion, rollback |
| `docs/ENV_VARIABLES.md` | CANONICAL | Required runtime configuration |
| `docs/deploy.md` | CANONICAL | Deployment process |

## Core Contracts

| Document | Status | Purpose | When to Consult |
|----------|--------|---------|-----------------|
| `docs/contracts/DNA_SCORING_MODEL.md` | CANONICAL | Bet scoring, fragility, stability, edge, confidence | Before changing evaluation scoring or score presentation |
| `docs/contracts/PROTOCOL_LIBRARY_V1.md` | CANONICAL | Protocol definitions, trigger rules, and score impacts | Before adding or changing protocol logic |
| `docs/contracts/PROTOCOL_DNA_REQUIREMENT_MAP_V1.md` | CANONICAL | First protocol-to-DNA fragment requirement map for active Tier 1 protocols | Before refactoring protocol data retrieval |
| `docs/contracts/LEARNING_SYSTEM_V1.md` | CANONICAL | Governed learning, proposals, promotion, rollback, and versioning | Before building adaptive behavior |
| `docs/contracts/MODEL_REGISTRY_CONTRACT.md` | CANONICAL | Version registry for production-affecting models and configs | Before storing or promoting model/config versions |
| `docs/contracts/EVALUATION_LOG_CONTRACT.md` | CANONICAL | Canonical evaluation event logging for learning and auditability | Before building evaluation logging or outcome joins |
| `docs/contracts/LEARNING_PROPOSAL_CONTRACT.md` | CANONICAL | Proposal record for governed adaptive changes | Before generating or reviewing learning proposals |
| `docs/contracts/PROMOTION_AUDIT_CONTRACT.md` | CANONICAL | Promotion and rollback audit records for governed changes | Before promoting learning-driven changes |
| `docs/contracts/SYSTEM_CONTRACT_SDS.md` | CANONICAL | Sherlock-DNA system dataflow | Before changing Sherlock-DNA integration boundaries |
| `docs/contracts/AIRLOCK_MEMBRANE_CONTRACT.md` | CANONICAL | Restored Airlock boundary rules for inbound and outbound contracts | Before changing frontend-facing contracts or Airlock responsibilities |
| `docs/contracts/SHERLOCK_DNA_INTERACTION_CONTRACT.md` | CANONICAL | Bounded interaction model between Sherlock synthesis and DNA structured state | Before changing protocol retrieval, Sherlock requests, or DNA exposure shape |
| `docs/contracts/SCH_SDK_CONTRACT.md` | CANONICAL | Sherlock library interface | Before changing Sherlock integration code |
| `docs/contracts/DNA_PRIMITIVES_CONTRACT.md` | CANONICAL | DNA primitive schemas and persistence assumptions | Before changing low-level DNA state modeling |
| `docs/contracts/MODULE_BOUNDARY_CONTRACT.md` | CANONICAL | Module boundaries and separation rules | Before moving responsibilities across subsystems |
| `docs/contracts/BET_HISTORY_API.md` | CANONICAL | Bet history API contract | Before changing bet history request/response shape |
| `docs/contracts/FRONTEND_SPLIT_CONTRACT_FREEZE_CHECKLIST.md` | CANONICAL | First frontend-facing contract map and freeze checklist for the web/API split | Before scaffolding the dedicated frontend |

## Mapping And Architecture Docs

| Document | Status | Purpose | When to Consult |
|----------|--------|---------|-----------------|
| `docs/mappings/MAP_SHERLOCK_TO_DNA.md` | CANONICAL | Sherlock to DNA translation map | Before wiring Sherlock output into DNA persistence |
| `docs/architecture/DNA-SHERLOCK-division.md` | CANONICAL | Responsibility split between systems | Before reshaping analysis boundaries |
| `docs/architecture/SYSTEM_RESTORATION_BLUEPRINT.md` | CANONICAL | Current architecture pivot: frontend, Airlock, protocols, Sherlock, DNA, governance | Before refactor, module boundary, or frontend separation work |
| `docs/architecture/SHERLOCK_DNA_TOUCHPOINT_AUDIT.md` | CANONICAL | Code-backed audit of current Sherlock, DNA, and protocol touchpoints | Before implementing the first Sherlock ↔ DNA adapter seam |
| `docs/architecture/NBA_DATA_ARCHITECTURE.md` | CANONICAL | NBA ingestion and data architecture | Before changing NBA data flows |
| `docs/architecture/ROUTER_SURFACE_MAP.md` | CANONICAL | Active versus legacy router map | Before router cleanup or route reorganization |
| `docs/architecture/USER_FLOW_MAP.md` | CANONICAL | Intended end-user journey from intake through evaluation, refinement, placement, and learning | Before changing major user flow or UX seams |

## Product And UX Docs

| Document | Status | Purpose | When to Consult |
|----------|--------|---------|-----------------|
| `docs/UI_SPEC.md` | CANONICAL | UI specification | Before modifying the primary interface |
| `docs/architecture/USER_FLOW_MAP.md` | CANONICAL | Canonical user journey and UX seam priorities | Before changing entry flow, Evaluate, Builder, or protocol visibility |
| `docs/ui/ACTIVE_FRONTEND_OWNERSHIP_MAP.md` | CANONICAL | Honest map of active, parallel, and legacy frontend ownership | Before editing templates or frontend JS ownership |
| `docs/ui/SCREEN_COMPONENT_SPEC.md` | CANONICAL | Screen-by-screen responsibilities, component priorities, and UX rules | Before changing active screen structure or component hierarchy |
| `docs/ui/LIVE_UX_GAP_REPORT.md` | DRAFT | Ranked comparison of live UX against the canonical flow and screen model | Before deciding the next UX implementation pass |
| `docs/ui/FRONTEND_IMPLEMENTATION_SPEC.md` | DRAFT | Build plan, state contracts, and acceptance criteria for the next frontend passes | Before implementing the next UX/frontend slice |
| `docs/FRONTEND_PRD.md` | DRAFT | Product framing for frontend direction | When evaluating UI/product direction |
| `docs/UI_ROADMAP.md` | DRAFT | UI roadmap | When planning UI work |
| `docs/UI_WIRING_DIAGRAM.md` | DRAFT | UI flow wiring | When tracing page behavior |
| `docs/ui/pages/builder.md` | DRAFT | Builder page notes | Before touching builder UX |
| `docs/ui/TEST_PLAN.md` | DRAFT | UI test planning | Before adding UI verification |
| `docs/ui/MANUAL_VERIFICATION_CHECKLIST.md` | DRAFT | Manual UI checks | Before or after UI releases |

## Operations

| Document | Status | Purpose | When to Consult |
|----------|--------|---------|-----------------|
| `docs/ENV_VARIABLES.md` | CANONICAL | Environment variables | Before adding env vars or changing config |
| `docs/deploy.md` | CANONICAL | Deployment process | Before deploying |
| `docs/VERIFY_DEPLOYMENT.md` | CANONICAL | Deployment verification | After every deploy |
| `docs/ops/SUPABASE_MIGRATION_PLAN.md` | CANONICAL | Managed Postgres migration plan | Before Postgres or Supabase cutover work |
| `docs/ops/ALEMBIC_MIGRATION_WORKFLOW.md` | CANONICAL | Forward schema migration workflow | Before new schema changes |
| `docs/ops/POSTGRES_DEV_PATH.md` | CANONICAL | Local and Supabase-backed Postgres validation path | Before validating `APP_DATABASE_URL` on Postgres |
| `docs/ops/FRONTEND_BACKEND_SEPARATION_PLAN.md` | CANONICAL | Staged plan for splitting the web app from the FastAPI backend | Before starting frontend extraction or API-first migration work |
| `docs/ops/ARCHITECTURE_RESTORATION_SPRINT_MAP.md` | CANONICAL | Sprint order and guardrails for restoring the Airlock-centered layered architecture | Before starting the next refactor or frontend module work |
| `docs/ops/AIRLOCK_ROUTE_GAP_AUDIT.md` | CANONICAL | Route-by-route audit of current Airlock membrane coverage | Before implementing Sprint B boundary restoration work |
| `docs/ops/FRONTEND_BACKEND_CONTRACT_FREEZE_PHASE1.md` | CANONICAL | Phase 1 contract-freeze checklist, route audit, and frontend scaffold recommendation | Before scaffolding the new frontend or freezing Evaluate/OCR/History contracts |
| `docs/ops/CONTEXT_LOCK_PROTOCOL.md` | CANONICAL | Required process for locking sprint and handoff state into the repo | Before sprint closeout, context compaction, or chat handoff |
| `docs/ops/CURRENT_EXECUTION_STATE.md` | ACTIVE | Current implementation state, latest validation, and exact next step | First stop when reconnecting or resuming work |
| `docs/ops/deployment-hardening.md` | DRAFT | Deployment hardening notes | When improving operational safety |

## Governance And Planning

| Document | Status | Purpose | When to Consult |
|----------|--------|---------|-----------------|
| `docs/GOVERNANCE.md` | CANONICAL | General governance rules | When unclear about process |
| `docs/RALPH_LOOP.md` | LOCKED | Feature governance loop | Before proposing major new features |
| `docs/MASTER_ROADMAP.md` | DRAFT | Product and engineering roadmap | When planning medium-term work |
| `docs/SPRINT_PLAN.md` | LOCKED | Sprint definitions | When reading historical sprint framing |
| `docs/adr/ADR-2026-03-14-restored-layered-architecture.md` | CANONICAL | ADR locking the restored layered architecture | Before reopening frontend/backend or Airlock boundary debates |
| `docs/adr/ADR-2026-03-14-governed-adaptation-after-boundary-restoration.md` | CANONICAL | ADR locking the order of adaptation work after boundary restoration | Before proposing self-improving research behavior |
| `docs/SPRINT_1_LOCK.md` | LOCKED | Early sprint scope lock | Historical reference only |
| `docs/index/DECISION_LOG.md` | APPEND-ONLY | Architectural decisions | Before major decisions or reversals |

## Historical And Investigative Docs

These are useful context, not default source of truth:

| Document | Status | Purpose |
|----------|--------|---------|
| `docs/DEPLOY_NOTES.md` | HISTORICAL | Deployment notes from prior work |
| `docs/INCIDENT_2026-02-20_PROD_DOWN.md` | HISTORICAL | Production incident record |
| `docs/SESSION_REPORT_2026-02-10.md` | HISTORICAL | Historical session report |
| `docs/deployment-error-analysis.md` | HISTORICAL | Deployment troubleshooting notes |
| `docs/deployments.md` | HISTORICAL | Prior deployment notes |
| `docs/NBA_PROCESS_IMPROVEMENT.md` | HISTORICAL | Prior NBA process ideas |
| `docs/UI_ISSUES.md` | HISTORICAL | Issue list for UI cleanup |

## Status Definitions

| Status | Meaning |
|--------|---------|
| `CANONICAL` | Current authoritative source of truth |
| `DRAFT` | Useful but still evolving |
| `LOCKED` | Historical or process-bound document that should not drift casually |
| `APPEND-ONLY` | Add to it, do not rewrite history |
| `HISTORICAL` | Useful context but not primary truth |

## Anti-Drift Rule

Before making implementation changes:

1. identify the contract or source doc that governs the change
2. update the contract first if the implementation must change the rule
3. do not treat stale historical docs as current architecture
