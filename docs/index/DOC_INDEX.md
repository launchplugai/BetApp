# Documentation Index

**Last Updated:** 2026-03-16

This index is for the active BetApp application. If a document conflicts with running code, treat code as the source of truth and update the docs.

## Start Here

Read these first when joining the project:

| Document | Status | Purpose |
|----------|--------|---------|
| `README.md` | CANONICAL | Product framing, repo reality, and entry points |
| `CONTEXT.md` | CANONICAL | Single-file wake-up entry point for fresh chats, reconnects, and external workers | First stop when the goal is rapid repo-memory wake-up |
| `docs/ops/BOOTSTRAP_PROTOCOL.md` | CANONICAL | Required bootstrap order for any new chat, reconnect, or agent |
| `docs/ops/CURRENT_EXECUTION_STATE.md` | ACTIVE | Current implementation state, latest validation, and exact next step |
| `docs/architecture/SYSTEM_RESTORATION_BLUEPRINT.md` | CANONICAL | Canonical architecture pivot and current module model |
| `docs/contracts/AIRLOCK_MEMBRANE_CONTRACT.md` | CANONICAL | Restored boundary rules for frontend-safe system interaction |
| `docs/contracts/SHERLOCK_DNA_INTERACTION_CONTRACT.md` | CANONICAL | Canonical bounded interaction between Sherlock and DNA |
| `docs/contracts/SHERLOCK_DNA_REQUEST_CONTRACT.md` | CANONICAL | First Sherlock-facing request/response shape over runtime DNA fragments |
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
| `docs/contracts/SHERLOCK_DNA_REQUEST_CONTRACT.md` | CANONICAL | First request/response contract for Sherlock-facing DNA fragment retrieval | Before expanding live Sherlock fragment access |
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
| `docs/ops/FRONTEND_BACKEND_DEPLOY_STATUS.md` | DRAFT | Green/yellow/red deploy-review status and verification checklist for the current frontend/backend split | Before deployment review or separation status meetings |
| `docs/ops/FRONTEND_PARALLEL_WORKFLOW.md` | DRAFT | Practical workflow for parallel frontend/backend development against frozen contracts | Before adding new frontend slices on top of the phase-one scaffold |
| `docs/ops/FRONTEND_BACKEND_VISUAL_STATUS_MAP.md` | DRAFT | Visual map of current frontend/backend boundaries, canonical paths, and transitional seams | When sanity-checking whether the separation work still serves the overall goal |
| `docs/ops/FRONTEND_DEV_BOOTSTRAP.md` | ACTIVE | Fast bootstrap path for frontend-dev continuation, agents, and VPS workers | First stop when resuming the frontend-dev stream |
| `docs/ops/FRONTEND_DEV_BUILD_TRACKER.md` | ACTIVE | Working definition of usable frontend-dev progress, blockers, and next milestone | Before picking the next frontend-dev build slice |
| `docs/ops/FRONTEND_DEV_CONTEXT_LOG.md` | ACTIVE | Compact continuity log for frontend-dev work across compaction, handoff, or agent swaps | When recovering frontend-dev state quickly |
| `docs/ops/CHAT_SIDE_WORKFLOW_CANON.md` | CANONICAL | Canonical chat-side collaboration workflow for heartbeat, continuity, escalation, and small process improvements | Before relying on thread memory or changing the collaboration workflow |
| `docs/ops/STARTUP_HEARTBEAT_TEMPLATE.md` | ACTIVE | Reusable startup proof/checksum + heartbeat template for fresh chats and reconnects | When booting a new chat or testing wake-up reliability |
| `docs/ops/MEMORY_HEARTBEAT_PROTOCOL.md` | ACTIVE | Freshness cadence, shared heartbeat fields, and checker workflow for active memory surfaces | Before trusting wake-up docs after drift or long gaps |
| `docs/ops/ENVIRONMENT_BOOTSTRAP_CHAT_WORKFLOW.md` | ACTIVE | Bootstrap path for the collaboration environment itself, including heartbeat and recovery expectations | First stop when recovering the chat-side operating model |
| `docs/ops/BULLETPROOF_CHAT_INITIALIZATION_LOOP.md` | CANONICAL | Hardened new-chat and reconnect initialization loop with five explicit reliability passes | Before starting implementation after a fresh chat, reconnect, or continuity wobble |
| `docs/ops/SOUL.md` | CANONICAL | Enduring agent core for this environment, including chosen traits and anti-drift orientation | Early in bootstrap when restoring core memory and operating posture |
| `docs/ops/BRAIN_STEM_MODULE.md` | CANONICAL | Packaged autonomic foundation for continuity, startup, recovery, heartbeat, and reflexive conflict handling | Before extending the workflow system with higher-order routing, memory, or orchestration layers |
| `docs/ops/BRAIN_STEM_PACKAGING_CHECKLIST.md` | ACTIVE | Portable checklist for recreating the brain stem module in new chats, clones, or worker contexts | When porting or validating the continuity foundation elsewhere |
| `docs/ops/WHOLE_SYSTEM_PLAN.md` | CANONICAL | Modular roadmap for the full chat-side operating system from brain stem through planning and orchestration | When deciding what cognitive/continuity layer should be built next |
| `docs/ops/WORKING_MEMORY_MODULE.md` | DRAFT | Next-layer spec for preserving the immediate active thought across chat boundaries | Before implementing working-memory relay or "new chat, same thought" continuity |
| `docs/ops/WORKING_MEMORY_HANDOFF_CONTRACT.md` | DRAFT | Minimal record for carrying the last unresolved thought and expected response into a fresh chat | Before testing or implementing working-memory handoff behavior |
| `docs/ops/NEW_CHAT_CARRYOVER_PROTOCOL.md` | DRAFT | Step-by-step protocol for using working-memory handoff after brain-stem initialization | Before testing "new chat, same thought" continuity |
| `docs/ops/WORKING_MEMORY_STORAGE_AND_INJECTION.md` | DRAFT | File-backed storage and manual injection path for the first working-memory carry-over milestone | Before attempting explicit fresh-chat carry-over |
| `docs/ops/ACTIVE_WORKING_MEMORY_HANDOFF.yaml` | ACTIVE | Current active working-memory relay record for explicit fresh-chat carry-over | When waking up a fresh chat from the latest unresolved thought |
| `docs/ops/ACTIVE_WAKEUP_TARGET.md` | ACTIVE | Focused current-work target for fresh-chat wake-up when the goal is to point immediately at the real next task | When the next chat needs the shortest path from wake-up to current work |
| `docs/ops/NEW_CHAT_WAKEUP_PROMPT_TEMPLATE.md` | DRAFT | Prompt template for booting a fresh chat from repo memory and active working-memory handoff | When testing or using explicit fresh-chat carry-over |
| `docs/ops/SYSTEM_MEMORY_ARCHITECTURE.md` | CANONICAL | Memory-layer map for identity, workflow, active state, working memory, and entry routing | Before extending the chat-side operating system memory model |
| `docs/ops/SYSTEM_DESIGN_JOURNAL.md` | ACTIVE | Running design journal for the chat-side operating system and its modular evolution | When continuing to build or revisit the system architecture |
| `docs/ui/EVALUATION_ENVELOPE_BLUEPRINT.md` | DRAFT | Normalized frontend envelope blueprint, 5-zone UI structure, and adapter coverage map | Before wiring new UI work directly to backend route payloads |
| `docs/ops/BOOTSTRAP_PROTOCOL.md` | CANONICAL | Required bootstrap order for reconnecting, new chats, or agent handoff | First stop before resuming work |
| `docs/ops/CONTEXT_LOCK_PROTOCOL.md` | CANONICAL | Required process for locking sprint and handoff state into the repo | Before sprint closeout, context compaction, or chat handoff |
| `docs/ops/CURRENT_EXECUTION_STATE.md` | ACTIVE | Current implementation state, latest validation, and exact next step | First stop after bootstrap when reconnecting or resuming work |
| `docs/ops/deployment-hardening.md` | DRAFT | Deployment hardening notes | When improving operational safety |

## Governance And Planning

| Document | Status | Purpose | When to Consult |
|----------|--------|---------|-----------------|
| `docs/GOVERNANCE.md` | CANONICAL | General governance rules | When unclear about process |
| `docs/RALPH_LOOP.md` | LOCKED | Feature governance loop | Before proposing major new features |
| `docs/MASTER_ROADMAP.md` | DRAFT | Product and engineering roadmap | When planning medium-term work |
| `docs/SPRINT_PLAN.md` | HISTORICAL | Early sprint framing | Historical reference only |
| `docs/adr/ADR-2026-03-14-restored-layered-architecture.md` | CANONICAL | ADR locking the restored layered architecture | Before reopening frontend/backend or Airlock boundary debates |
| `docs/adr/ADR-2026-03-14-governed-adaptation-after-boundary-restoration.md` | CANONICAL | ADR locking the order of adaptation work after boundary restoration | Before proposing self-improving research behavior |
| `docs/SPRINT_1_LOCK.md` | HISTORICAL | Early sprint scope lock | Historical reference only |
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
