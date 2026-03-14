#!/bin/bash
set -euo pipefail

# Disposable Postgres control-plane validation for BetApp.
#
# What it does:
# - starts a temporary local Postgres 16 instance
# - creates a scratch betapp database
# - runs Alembic governance migrations
# - verifies the expected tables and revision
# - exercises governed persistence services against Postgres
# - runs the startup governance guard against Postgres
# - shuts the temporary server down

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"
VENV_BIN="${VENV_BIN:-$PROJECT_DIR/.venv312/bin}"
PG_BIN_DIR="${PG_BIN_DIR:-/usr/local/opt/postgresql@16/bin}"
TMP_ROOT="${TMP_ROOT:-$PROJECT_DIR/.tmp/postgres-smoke}"
PORT="${PORT:-54329}"
DB_NAME="${DB_NAME:-betapp}"
DB_USER="${DB_USER:-$(whoami)}"
SOCKET_DIR="$TMP_ROOT/socket"
PGDATA_DIR="$TMP_ROOT/pgdata"
LOG_FILE="$TMP_ROOT/postgres.log"
APP_DATABASE_URL="postgresql+psycopg://${DB_USER}@/${DB_NAME}?host=${SOCKET_DIR}&port=${PORT}"

require_bin() {
  if [[ ! -x "$1" ]]; then
    echo "Missing executable: $1" >&2
    exit 1
  fi
}

cleanup() {
  if [[ -f "$PGDATA_DIR/postmaster.pid" ]]; then
    "$PG_BIN_DIR/pg_ctl" -D "$PGDATA_DIR" stop >/dev/null 2>&1 || true
  fi
}

trap cleanup EXIT

require_bin "$PG_BIN_DIR/initdb"
require_bin "$PG_BIN_DIR/pg_ctl"
require_bin "$PG_BIN_DIR/createdb"
require_bin "$PG_BIN_DIR/psql"
require_bin "$PG_BIN_DIR/pg_isready"
require_bin "$VENV_BIN/alembic"
require_bin "$VENV_BIN/python"

mkdir -p "$TMP_ROOT" "$SOCKET_DIR"

if [[ -d "$PGDATA_DIR" ]]; then
  mv "$PGDATA_DIR" "${PGDATA_DIR}.old.$(date +%s)"
fi

echo "==> Initializing disposable Postgres cluster"
"$PG_BIN_DIR/initdb" -D "$PGDATA_DIR" >/dev/null

echo "==> Starting Postgres on port $PORT"
"$PG_BIN_DIR/pg_ctl" \
  -D "$PGDATA_DIR" \
  -l "$LOG_FILE" \
  -o "-p $PORT -k $SOCKET_DIR" \
  start >/dev/null

echo "==> Waiting for Postgres readiness"
"$PG_BIN_DIR/pg_isready" -h "$SOCKET_DIR" -p "$PORT" >/dev/null

echo "==> Creating scratch database: $DB_NAME"
"$PG_BIN_DIR/createdb" -h "$SOCKET_DIR" -p "$PORT" "$DB_NAME"

echo "==> Applying Alembic migrations"
(
  cd "$PROJECT_DIR"
  APP_DATABASE_URL="$APP_DATABASE_URL" "$VENV_BIN/alembic" upgrade head >/dev/null
)

echo "==> Verifying governance tables"
TABLES=$("$PG_BIN_DIR/psql" -h "$SOCKET_DIR" -p "$PORT" -d "$DB_NAME" -Atqc \
  "SELECT tablename FROM pg_tables WHERE schemaname = 'public' ORDER BY tablename;")
for required_table in alembic_version evaluation_logs learning_proposals model_registry promotion_audit; do
  if ! printf '%s\n' "$TABLES" | grep -qx "$required_table"; then
    echo "Missing required table after migration: $required_table" >&2
    exit 1
  fi
done

echo "==> Verifying Alembic revision"
REVISION=$("$PG_BIN_DIR/psql" -h "$SOCKET_DIR" -p "$PORT" -d "$DB_NAME" -Atqc \
  "SELECT version_num FROM alembic_version;")
if [[ "$REVISION" != "20260308_0002" ]]; then
  echo "Unexpected Alembic revision: $REVISION" >&2
  exit 1
fi

echo "==> Running startup governance guard"
(
  cd "$PROJECT_DIR"
  APP_DATABASE_URL="$APP_DATABASE_URL" "$VENV_BIN/python" - <<'PY'
from app.startup import ensure_governance_schema_ready

ensure_governance_schema_ready()
print("startup_guard_ok")
PY
)

echo "==> Exercising governance services on Postgres"
(
  cd "$PROJECT_DIR"
  APP_DATABASE_URL="$APP_DATABASE_URL" "$VENV_BIN/python" - <<'PY'
from types import SimpleNamespace

from app.db import reset_engine
from app.services.evaluation_logger import get_evaluation_log_summary, log_evaluation_event
from app.services.governance_registry import get_learning_control_summary
from app.services.model_registry import get_active_model_versions, get_governance_summary

reset_engine()

versions = get_active_model_versions()
assert versions["dna_model_version"] == "dna_v1.0.0"

normalized = SimpleNamespace(
    tier=SimpleNamespace(value="better"),
    input_text="Celtics ML + over 227.5",
    has_canonical_legs=True,
)
evaluation = SimpleNamespace(parlay_id="pg_smoke_eval_001")
dna_scoring = {
    "scores": {
        "confidence": 72,
        "fragility": 54,
        "edge": 4,
        "stability": 68,
    },
    "recommendation": "consider_simplifying",
    "explanation": {"summary": "Reasonable structure with moderate fragility."},
}
triggered_protocols = [{"id": "fatigue_b2b_v1"}, {"id": "pace_mismatch_v1"}]
entities = {"sport_guess": "nba", "markets_detected": ["moneyline", "total"]}

log_evaluation_event(
    normalized=normalized,
    evaluation=evaluation,
    leg_count=2,
    dna_scoring=dna_scoring,
    triggered_protocols=triggered_protocols,
    entities=entities,
    primary_failure={"reason": "leg_count_risk"},
)

governance = get_governance_summary()
evaluation_logs = get_evaluation_log_summary()
learning_control = get_learning_control_summary()

assert governance["production_entries"] >= 4
assert evaluation_logs["total_logs"] == 1
assert evaluation_logs["recent_evaluations"][0]["evaluation_id"] == "pg_smoke_eval_001"
assert learning_control["promotion_count"] == 0

print("service_layer_ok")
PY
)

echo "==> Postgres control-plane smoke passed"
