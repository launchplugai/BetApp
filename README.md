# BetApp

BetApp is a bettor intelligence platform focused on two jobs:

- evaluate existing slips and expose hidden fragility
- help users discover better legs and protocols with explainable analytics

The product is not a picks oracle. It is a decision-support system that scores structural quality, surfaces contextual risk, and explains why a bet looks stronger or weaker.

## Product Focus

Current product priorities:

- parlay evaluation first
- fragility reduction over pure hit-rate theater
- protocol-driven risk detection
- clear, explainable reasoning
- bettor education over blind recommendation

Primary users today are serious hobbyist bettors, with NBA and NFL as the main sports in scope.

## Repo Reality

This repository contains the active FastAPI application, UI routes, scoring pipeline, protocol logic, governance substrate, and the nested `dna-matrix` engine package.

Treat these as the main starting points:

- [app/main.py](app/main.py): FastAPI entry point and app wiring
- [app/pipeline.py](app/pipeline.py): DNA evaluation pipeline
- [app/routers](app/routers): web and API routes
- [app/services](app/services): auth, scoring, protocols, governance services
- [app/models](app/models): SQLAlchemy models
- [docs/index/DOC_INDEX.md](docs/index/DOC_INDEX.md): current documentation index

Important note: the top-level `dna-matrix` folder is part of the repo, but the root app is the active product surface.

## Current Architecture

- Runtime: FastAPI
- Persistence today: app DB plus separate NBA analytics DB
- Scoring: DNA scoring model plus protocol modifiers
- Learning: governed proposal/review/promotion model
- Deployment: Python app with deployment docs and VPS/Railway artifacts in repo

The project is moving toward a managed Postgres control plane while keeping the Python runtime and evaluation stack intact.

## Source Of Truth

Code is the primary source of truth.

When you need product and system contracts, start here:

- [docs/contracts/DNA_SCORING_MODEL.md](docs/contracts/DNA_SCORING_MODEL.md)
- [docs/contracts/PROTOCOL_LIBRARY_V1.md](docs/contracts/PROTOCOL_LIBRARY_V1.md)
- [docs/contracts/LEARNING_SYSTEM_V1.md](docs/contracts/LEARNING_SYSTEM_V1.md)
- [docs/contracts/MODEL_REGISTRY_CONTRACT.md](docs/contracts/MODEL_REGISTRY_CONTRACT.md)
- [docs/contracts/EVALUATION_LOG_CONTRACT.md](docs/contracts/EVALUATION_LOG_CONTRACT.md)
- [docs/contracts/LEARNING_PROPOSAL_CONTRACT.md](docs/contracts/LEARNING_PROPOSAL_CONTRACT.md)
- [docs/contracts/PROMOTION_AUDIT_CONTRACT.md](docs/contracts/PROMOTION_AUDIT_CONTRACT.md)

Operational docs:

- [docs/ENV_VARIABLES.md](docs/ENV_VARIABLES.md)
- [docs/deploy.md](docs/deploy.md)
- [docs/ops/SUPABASE_MIGRATION_PLAN.md](docs/ops/SUPABASE_MIGRATION_PLAN.md)
- [docs/ops/ALEMBIC_MIGRATION_WORKFLOW.md](docs/ops/ALEMBIC_MIGRATION_WORKFLOW.md)

## Developer Notes

- `requirements.txt` is currently the reliable dependency source
- Alembic is the forward migration path
- existing legacy docs and legacy route files still exist; do not assume every file in the repo is active without checking imports and router registration

## Local Setup

```bash
uv venv --python 3.12 .venv
source .venv/bin/activate
python -m ensurepip --upgrade
pip install -r requirements.txt
```

Use Python 3.12 for local work. The repo declares `python-3.12` in `runtime.txt`, and parts of the nested engine use Python 3.10+ features that fail under 3.9.

Set environment variables from [docs/ENV_VARIABLES.md](docs/ENV_VARIABLES.md). At minimum for auth-capable local work, set:

```bash
export JWT_SECRET_KEY=dev-local-change-me
```

The shell environment may not be populated automatically after reopening the editor.

Before starting the app, apply the governed schema:

```bash
PYTHONPATH=.:./dna-matrix:$PYTHONPATH alembic upgrade head
PYTHONPATH=.:./dna-matrix:$PYTHONPATH uvicorn app.main:app --reload --port 8000
```

The app now fails startup clearly if the governance/control-plane schema is missing or not tracked by Alembic.

For a disposable Postgres control-plane smoke test, use:

```bash
bash scripts/postgres_control_plane_smoke.sh
```
