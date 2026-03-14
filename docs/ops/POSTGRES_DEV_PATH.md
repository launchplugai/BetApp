# Postgres Dev Path

**Status:** CANONICAL  
**Last Updated:** 2026-03-08

This document defines the practical path for running BetApp against Postgres or Supabase-backed Postgres during the control-plane cutover.

## 1. Purpose

Use this path when you want to validate:

- Alembic migrations on Postgres instead of SQLite
- governance/control-plane tables on the target database family
- `APP_DATABASE_URL` wiring before a broader Supabase migration

This is not a full production cutover guide. It is the safe developer path.

## 2. Driver

BetApp uses SQLAlchemy 2.x with:

```text
psycopg[binary]
```

Use connection URLs in this form:

```bash
postgresql+psycopg://USER:PASSWORD@HOST:PORT/DBNAME
```

Examples:

```bash
# Local Postgres
export APP_DATABASE_URL=postgresql+psycopg://postgres:password@127.0.0.1:5432/betapp

# Supabase pooler
export APP_DATABASE_URL='postgresql+psycopg://postgres.PROJECT_REF:PASSWORD@aws-0-us-east-1.pooler.supabase.com:6543/postgres?sslmode=require'
```

## 3. Local Validation Flow

### One-command disposable validation

If Homebrew `postgresql@16` and `.venv312` are available, run:

```bash
bash scripts/postgres_control_plane_smoke.sh
```

This starts a disposable local Postgres instance, applies Alembic migrations, verifies the governance tables/revision, exercises the governed service layer, runs the startup schema guard, and shuts the server back down.

### Install dependencies

```bash
uv venv --python 3.12 .venv
source .venv/bin/activate
pip install -r requirements.txt
```

### Set core env vars

```bash
export JWT_SECRET_KEY=dev-local-change-me
export APP_DATABASE_URL=postgresql+psycopg://postgres:password@127.0.0.1:5432/betapp
```

### Apply migrations

```bash
PYTHONPATH=.:./dna-matrix:$PYTHONPATH alembic upgrade head
```

### Start the app

```bash
PYTHONPATH=.:./dna-matrix:$PYTHONPATH uvicorn app.main:app --reload --port 8000
```

Startup now verifies that:

- required governance tables exist
- `alembic_version` exists
- the DB is at revision `20260308_0002` or later head

If not, the app fails clearly and tells you to run `alembic upgrade head`.

## 4. What To Validate First

When moving from SQLite to Postgres, validate these first:

1. `alembic upgrade head` succeeds cleanly
2. `/health` returns healthy or degraded for config only, not schema failure
3. `/debug/governance` returns registry and evaluation log summaries
4. a sample evaluation writes to `evaluation_logs`
5. admin/provider/debug surfaces still render

## 5. Recommended Scope

For the first Postgres-backed iteration, treat these as the primary target tables:

- `model_registry`
- `evaluation_logs`
- `learning_proposals`
- `promotion_audit`

Those tables are the governed control-plane and the safest first slice for Postgres validation.

## 6. Current Non-Goal

Do not treat this as a mandate to move all persistence at once.

Specifically, this document does not require immediate migration of:

- NBA analytics DB
- every legacy SQLite-backed feature
- auth/session rewrite
- protocol/business logic rewrite

## 7. Supabase Notes

Supabase is currently recommended as:

- managed Postgres
- versioned control-plane storage
- audit/log/proposal/promotion backbone

It is not currently recommended as:

- a FastAPI replacement
- a scoring engine replacement
- a forced Edge Functions rewrite

## 8. Failure Modes

If Postgres validation fails, check in this order:

1. `APP_DATABASE_URL` format
2. network reachability / credentials
3. `psycopg[binary]` installed in the active venv
4. `alembic current`
5. `alembic upgrade head`

## 9. Canonical Rule

For Postgres/Supabase work, migrations are applied through Alembic and runtime reads the same `APP_DATABASE_URL`.

Do not add new one-off migration scripts for Postgres-specific schema work unless blocked.
