# SUPABASE_MIGRATION_PLAN.md
# Supabase / Postgres Migration Plan

**Status:** DRAFT
**Date:** 2026-03-08
**Owner:** Engineering

---

## 1. Decision

BetApp / DNA Matrix will adopt Supabase as the managed Postgres and governance backbone for the next phase of the product.

### Adopt

- Supabase Postgres
- versioned application data
- learning-system storage
- proposal / promotion audit storage
- protocol / recommendation / notification persistence

### Do Not Adopt Yet

- full Supabase app rewrite
- Edge Functions as primary backend runtime
- Supabase Auth migration in phase 1
- replacement of the Python evaluation engine

### Rationale

The current repo’s biggest scaling problem is persistence and governance, not lack of frameworks.

The product now depends on:

- versioned scoring
- protocol tuning
- calibration logs
- reviewable learning proposals
- durable audit trails

SQLite is too limiting for where this system is headed.

---

## 2. Migration Goals

This migration should achieve:

1. move durable state off SQLite
2. create a proper control plane for learning and governance
3. support analytics, calibration, and protocol tuning workflows
4. preserve the current FastAPI application runtime
5. avoid a risky multi-system rewrite

---

## 3. Current Persistence State

The repo currently persists across multiple local SQLite-oriented paths:

### Core App Persistence

- [app/models/__init__.py](/Users/benaiahross/development/projects/betapp/app-src/app/models/__init__.py)
  - `users`
  - `bets`
  - `transactions`
  - `refresh_tokens`
  - `token_blacklist`

### User / Notification Extensions

- [app/models/user_preferences.py](/Users/benaiahross/development/projects/betapp/app-src/app/models/user_preferences.py)
  - `user_preferences`
- [app/models/user_dna_snapshot.py](/Users/benaiahross/development/projects/betapp/app-src/app/models/user_dna_snapshot.py)
  - `user_dna_snapshots`
- [app/models/notification_event.py](/Users/benaiahross/development/projects/betapp/app-src/app/models/notification_event.py)
  - `notification_events`
- plus additional notification-related models in [app/models](/Users/benaiahross/development/projects/betapp/app-src/app/models)

### Protocol System

- [app/protocol/models.py](/Users/benaiahross/development/projects/betapp/app-src/app/protocol/models.py)
  - `protocols`
  - `protocol_targets`
  - `protocol_items`

### Recommendation Layer

- [app/protocol/recommendation_models.py](/Users/benaiahross/development/projects/betapp/app-src/app/protocol/recommendation_models.py)
  - `recommendations`
  - `parlays`

### NBA Analytics

- separate SQLite path in [app/nba/database.py](/Users/benaiahross/development/projects/betapp/app-src/app/nba/database.py)
  - analytics / ingestion data
  - rest context
  - injuries
  - derived heuristics inputs

---

## 4. Architectural Position

### 4.1 FastAPI Remains Primary Runtime

The application backend stays in Python / FastAPI.

Supabase becomes:

- managed Postgres
- admin and audit data backbone
- optional future storage/auth layer

### 4.2 Production Scoring Stays In Python

The scoring engine, protocol evaluation, and learning analyzers remain in application-controlled Python services.

### 4.3 Learning Writes Stay Segregated

Production scoring reads approved versioned config only.

Learning jobs write proposal / staging records only.

This separation is mandatory.

---

## 5. Recommended Data Domains

The system should be split into these persistent domains:

### Domain A: Identity & Access

- users
- sessions / refresh tokens
- token blacklist
- optional future auth linkage

### Domain B: Betting Core

- bets
- transactions
- bet DNA receipts / snapshots
- settlement results

### Domain C: Protocols & Recommendations

- protocols
- protocol_targets
- protocol_items
- recommendations
- parlays

### Domain D: User Profile & Preferences

- user_preferences
- user_dna_snapshots
- personalization profile tables

### Domain E: Notifications

- notification_events
- notification_receipts
- notification_preferences
- user_devices
- eligible_opportunities

### Domain F: Learning & Governance

- evaluation_logs
- outcome_enrichment
- model_registry
- calibration_versions
- protocol_library_versions
- recommendation_versions
- learning_proposals
- promotion_records
- rollback_records
- admin_review_events

### Domain G: Analytics / Sports Context

- nba analytics tables
- rest context
- injury context
- matchup context
- derived heuristics inputs

---

## 6. Migration Strategy

The migration should happen in phases, not as a big-bang cutover.

### Phase 0: Cleanup And Reorg

Do first:

- centralize SQLAlchemy engine/session configuration
- stop hard-coding SQLite URLs in multiple places
- define explicit config env vars for:
  - `APP_DATABASE_URL`
  - `NBA_DATABASE_URL`
  - `SUPABASE_DB_URL`
- isolate runtime persistence concerns behind service boundaries
- identify stale / duplicate routes and legacy files before data migration

### Phase 1: Introduce Postgres For New Governed Systems

Build in Supabase first:

- `model_registry`
- `evaluation_logs`
- `learning_proposals`
- `promotion_records`
- `admin_review_events`

Reason:

- this is mostly additive
- low migration risk
- highest strategic value for the new learning system

### Phase 2: Migrate Core App Persistence

Move:

- users
- bets
- transactions
- refresh_tokens
- token_blacklist
- user_preferences
- user_dna_snapshots

Requirements:

- compatibility layer for current auth/session services
- migration scripts for SQLite -> Postgres
- dual-read validation during transition if needed

### Phase 3: Migrate Protocol / Recommendation System

Move:

- protocols
- protocol_targets
- protocol_items
- recommendations
- parlays

Reason:

- protocol data is strategic
- recommendations need better auditability and analytics

### Phase 4: Migrate Notifications

Move:

- notification_events
- notification_receipts
- notification preferences
- user devices
- eligible opportunities

Reason:

- notification systems need durable delivery history and analytics

### Phase 5: Revisit NBA Analytics Placement

Decide whether NBA analytics should:

- remain in a separate Postgres schema / database
- move selectively to Supabase
- keep heavy ETL / warehouse-style tables separate from app OLTP tables

Recommendation:

- do not rush this phase
- move the app-critical context tables first
- keep bulk ingest / heavy sports analytics isolated if query patterns diverge

---

## 7. What Should Move First

### Highest-Value First Tables

Create these in Supabase immediately:

1. `model_registry`
2. `evaluation_logs`
3. `learning_proposals`
4. `promotion_records`
5. `admin_review_events`

### Next

6. `protocols`
7. `protocol_targets`
8. `protocol_items`
9. `recommendations`
10. `parlays`

### Then

11. `bets`
12. `transactions`
13. `user_preferences`
14. `user_dna_snapshots`
15. `notification_events`

---

## 8. Auth Recommendation

Do not migrate auth to Supabase Auth in phase 1.

### Why

- current auth already exists in Python and needs cleanup regardless
- auth rewrites create high breakage risk
- the strategic bottleneck is data/governance, not authentication vendor choice

### Revisit Later When

- session model is cleaned up
- JWT secret handling is fixed
- user model is stabilized
- product access/tier logic is explicit

---

## 9. Schema Design Guidance

### 9.1 Use Postgres-Native Types

Prefer:

- `uuid` where appropriate
- `jsonb` for flexible structured payloads
- indexed timestamp columns
- enum-like checked values where stability matters

### 9.2 Add Version Columns Explicitly

Learning-sensitive tables should include explicit version references:

- `dna_model_version`
- `protocol_library_version`
- `calibration_version`
- `recommendation_version`

### 9.3 Separate Config From Observations

Do not mix:

- live configuration
- logged evaluations
- proposal records
- promotion history

These need different mutability and audit behavior.

### 9.4 Prefer Append-Only Audit Tables

For:

- proposals
- promotions
- rollbacks
- review actions
- evaluation logs

Append-only behavior is preferred wherever practical.

---

## 10. Service Refactor Targets

Before or during migration, create or normalize these service boundaries:

### Required

- `db/session_manager`
- `model_registry`
- `evaluation_logger`
- `proposal_registry`
- `promotion_auditor`
- `rollback_manager`

### Strongly Recommended

- `bet_repository`
- `protocol_repository`
- `notification_repository`
- `user_profile_repository`

This reduces direct model coupling and makes database migration tractable.

---

## 11. Operational Plan

### Step 1

Introduce a Postgres connection path locally and in non-prod.

### Step 2

Create the new governed-learning tables first.

### Step 3

Write migration scripts from current SQLite tables to Postgres for core entities.

### Step 4

Switch write path for new governed systems to Postgres.

### Step 5

Migrate existing core user/bet/protocol data.

### Step 6

Cut application reads to Postgres.

### Step 7

Decommission SQLite usage table-by-table, not all at once.

---

## 12. Risks

### Main Risks

- data shape drift between current SQLite models and target Postgres schema
- auth/session regressions during core persistence move
- over-coupled code paths with direct session/model assumptions
- premature migration of NBA analytics bulk data
- partial migrations with no authoritative source of truth

### Risk Reduction

- move additive governed systems first
- keep rollback path
- version migration scripts
- use shadow validation for critical paths
- avoid auth rewrite in the same phase

---

## 13. Success Criteria

This migration is successful if:

1. governed learning tables are live in Postgres
2. evaluation and proposal history become durable and queryable
3. protocol/recommendation data is no longer trapped in SQLite
4. production scoring remains stable during migration
5. rollback and audit history become first-class

---

## 14. Immediate Next Artifacts

The next engineering artifacts should be:

1. `MODEL_REGISTRY_CONTRACT.md`
2. `EVALUATION_LOG_CONTRACT.md`
3. `LEARNING_PROPOSAL_CONTRACT.md`
4. `PROMOTION_AUDIT_CONTRACT.md`
5. first SQLAlchemy/Postgres config refactor

---

## 15. Canonical Recommendation

Adopt Supabase as:

- managed Postgres
- governance backbone
- learning-system persistence layer
- long-term control-plane foundation

Do not adopt Supabase as:

- a replacement for FastAPI
- a forced Edge Functions runtime
- a phase-1 auth rewrite
- a full product rewrite target
