# ALEMBIC_MIGRATION_WORKFLOW.md
# Alembic Migration Workflow

**Status:** ACTIVE
**Date:** 2026-03-08

---

## 1. Purpose

This repo now standardizes schema migration work around Alembic instead of accumulating one-off migration scripts.

The goal is:

- one migration workflow
- reproducible schema changes
- clearer review history
- easier SQLite -> Postgres transition

---

## 2. Current Position

Alembic is now scaffolded and wired to the shared app DB path via `APP_DATABASE_URL`.

Files:

- [alembic.ini](/Users/benaiahross/development/projects/betapp/app-src/alembic.ini)
- [alembic/env.py](/Users/benaiahross/development/projects/betapp/app-src/alembic/env.py)
- [alembic/script.py.mako](/Users/benaiahross/development/projects/betapp/app-src/alembic/script.py.mako)
- [alembic/versions/20260308_0001_baseline.py](/Users/benaiahross/development/projects/betapp/app-src/alembic/versions/20260308_0001_baseline.py)
- [alembic/versions/20260308_0002_governance_control_plane.py](/Users/benaiahross/development/projects/betapp/app-src/alembic/versions/20260308_0002_governance_control_plane.py)

`20260308_0001` is a reviewed stamp-only baseline.
`20260308_0002` is the first real forward Alembic revision and creates the governed control-plane tables.

---

## 3. Canonical Commands

Stamp an existing validated database to the reviewed baseline:

```bash
alembic stamp 20260308_0001
```

Apply the first real control-plane schema after stamping:

```bash
alembic upgrade head
```

Create a revision:

```bash
alembic revision -m "describe_change"
```

Autogenerate a revision:

```bash
alembic revision --autogenerate -m "describe_change"
```

Apply latest migrations:

```bash
alembic upgrade head
```

Check current revision:

```bash
alembic current
```

Show migration history:

```bash
alembic history
```

---

## 4. Rules

- new schema changes SHOULD go through Alembic
- direct ad hoc migration scripts SHOULD stop being the default
- autogenerate output MUST be reviewed manually before merge
- destructive downgrades require explicit review

---

## 5. Transition Guidance

There are still legacy one-off migration scripts under [migrations](/Users/benaiahross/development/projects/betapp/app-src/migrations).

During transition:

- do not delete them blindly
- do not create more unless blocked
- prefer Alembic for all new schema changes
- treat `20260308_0001` as the reviewed baseline for existing databases

The next cleanup step should be deciding whether to:

1. create a baseline Alembic revision from the current authoritative schema, or
2. hand-convert the legacy migration history into reviewed Alembic revisions

Recommendation:

- baseline now exists as a stamp-only starting point
- future work should build forward from that revision
- the first real forward Alembic schema now covers governance/control-plane tables
- only create a full bootstrap revision later if we decide to support full empty-db bootstrap purely through Alembic

---

## 6. Environment

Alembic reads the application DB URL through the shared DB layer:

- `APP_DATABASE_URL` when set
- fallback: `sqlite:///./dna_bets.db`

This means the same migration path can be used for:

- local SQLite
- future Supabase/Postgres cutover

## 7. Startup Enforcement

Application startup now assumes governed control-plane tables are Alembic-managed.

Boot paths in:

- [railway.json](/Users/benaiahross/development/projects/betapp/app-src/railway.json)
- [Procfile](/Users/benaiahross/development/projects/betapp/app-src/Procfile)
- [start-dna.sh](/Users/benaiahross/development/projects/betapp/app-src/start-dna.sh)

run `alembic upgrade head` before `uvicorn`.

The app also performs a startup guard for governance schema readiness and fails clearly when:

- required governance tables are missing
- `alembic_version` is missing
- the governance revision is behind `20260308_0002`

The guard is skipped for test/CI-style environments and can be bypassed explicitly with:

- `SKIP_STARTUP_SCHEMA_CHECK=true`
