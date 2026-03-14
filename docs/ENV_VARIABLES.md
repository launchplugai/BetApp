# Environment Variables Reference

**Status:** CANONICAL
**Last Updated:** 2026-01-29

Complete list of key environment variables used by BetApp.

---

## Required for Production

| Variable | Example | Description |
|----------|---------|-------------|
| `LEADING_LIGHT_ENABLED` | `true` | Enable evaluation API |
| `OPENAI_API_KEY` | `sk-...` | OpenAI API key for vision/TTS |
| `RAILWAY_ENVIRONMENT` | `production` | Environment name |

---

## Deploy Identification

| Variable | Default | Source | Description |
|----------|---------|--------|-------------|
| `RAILWAY_GIT_COMMIT_SHA` | - | Railway auto | Git commit SHA |
| `GIT_SHA` | `unknown` | Manual | Fallback if Railway var missing |
| `BUILD_TIME_UTC` | startup time | railway.json | ISO8601 build timestamp |
| `RAILWAY_ENVIRONMENT` | `development` | Railway auto | Environment name |
| `ENV` | - | Manual | Alternative env indicator |

---

## Feature Flags

| Variable | Default | Description |
|----------|---------|-------------|
| `LEADING_LIGHT_ENABLED` | `false` | Enable Leading Light evaluation API |
| `LEADING_LIGHT_DEMO_OVERRIDE` | `false` | Allow demo endpoints for non-BEST tiers |
| `VOICE_ENABLED` | `false` | Enable text-to-speech narration |
| `VOICE_OVERRIDE` | `false` | Override voice feature checks |
| `IMAGE_EVAL_ENABLED` | `true` | Enable image evaluation |

---

## API Keys & Secrets

| Variable | Required | Description |
|----------|----------|-------------|
| `OPENAI_API_KEY` | Yes* | OpenAI API key (*required for vision/voice features) |
| `JWT_SECRET_KEY` | Yes in production | JWT signing secret for auth tokens |
| `AUTH_JWT_SECRET` | No | Legacy alias for `JWT_SECRET_KEY` |
| `JWT_ALGORITHM` | No | JWT algorithm override, defaults to `HS256` |
| `ADMIN_EMAILS` | No | Comma-separated admin email allowlist for internal surfaces like `/api/admin` and `/debug`. Users with `BEST` tier also pass this gating. |
| `STRIPE_SECRET_KEY` | No | Stripe secret key (billing) |
| `STRIPE_WEBHOOK_SECRET` | No | Stripe webhook signing secret |

---

## Stripe / Billing

| Variable | Default | Description |
|----------|---------|-------------|
| `STRIPE_BEST_PRICE_ID` | hardcoded | Price ID for BEST tier subscription |
| `STRIPE_TEST_MODE` | `true` | Use Stripe test mode |

---

## Database / Persistence

| Variable | Default | Description |
|----------|---------|-------------|
| `APP_DATABASE_URL` | `sqlite:///./dna_bets.db` | Primary application database URL. For Postgres/Supabase use `postgresql+psycopg://...` so SQLAlchemy uses the declared psycopg driver. |
| `NBA_DATABASE_URL` | `sqlite:///./data/nba_analytics.db` | NBA analytics database URL |
| `DNA_DB_PATH` | `data/dna.db` | SQLite database file path |
| `DNA_PERSISTENCE` | `true` | Enable alert persistence to SQLite |

## Auth Configuration

| Variable | Default | Description |
|----------|---------|-------------|
| `JWT_SECRET_KEY` | development fallback only | Required in production. Signs and validates access tokens. |
| `AUTH_JWT_SECRET` | - | Backward-compatible alias for `JWT_SECRET_KEY` |
| `JWT_ALGORITHM` | `HS256` | Access token signing algorithm |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | `15` | Access token lifetime in minutes |
| `REFRESH_TOKEN_EXPIRE_DAYS` | `30` | Refresh token lifetime in days |

---

## Rate Limiting

| Variable | Default | Description |
|----------|---------|-------------|
| `DNA_RATE_LIMIT_MODE` | `prod` | Rate limit mode (`prod` or `bypass`) |
| `DNA_RATE_LIMIT_BYPASS_UNTIL` | - | ISO8601 timestamp for time-bomb bypass expiry |

**Safety:** Bypass NEVER activates when `ENV=production` or `RAILWAY_ENVIRONMENT=production`.

---

## External Services

| Variable | Default | Description |
|----------|---------|-------------|
| `NBA_AVAILABILITY_LIVE` | `false` | Use live NBA availability data |
| `NBA_AVAILABILITY_TIMEOUT` | `10` | NBA API timeout in seconds |

---

## OpenAI Configuration

| Variable | Default | Description |
|----------|---------|-------------|
| `OPENAI_API_KEY` | - | API key (required) |
| `IMAGE_EVAL_MODEL` | `gpt-4o-mini` | Model for image evaluation |
| `OPENAI_TTS_MODEL` | `tts-1` | Model for text-to-speech |
| `OPENAI_TTS_VOICE` | `alloy` | Voice for text-to-speech |

---

## Server Configuration

| Variable | Default | Description |
|----------|---------|-------------|
| `MAX_REQUEST_SIZE_BYTES` | `1048576` | Max request body size (1MB) |
| `PORT` | `8000` | Server port (Railway sets automatically) |

---

## Railway Auto-Provided

These are automatically set by Railway (do not configure manually):

| Variable | Description |
|----------|-------------|
| `RAILWAY_GIT_COMMIT_SHA` | Current deploy commit SHA |
| `RAILWAY_ENVIRONMENT` | Environment name |
| `RAILWAY_PRIVATE_DOMAIN` | Internal DNS |
| `RAILWAY_PROJECT_ID` | Project identifier |
| `RAILWAY_SERVICE_ID` | Service identifier |
| `RAILWAY_REPLICA_ID` | Replica identifier |
| `PORT` | Assigned port |

---

## Configuration Tiers

### Minimal (Development)
```
# SQLite default
JWT_SECRET_KEY=dev-local-change-me

# Or Postgres/Supabase
APP_DATABASE_URL=postgresql+psycopg://postgres:password@127.0.0.1:5432/betapp
```

### Minimal (Production)
```
LEADING_LIGHT_ENABLED=true
OPENAI_API_KEY=sk-...
```

### Full Production
```
LEADING_LIGHT_ENABLED=true
OPENAI_API_KEY=sk-...
VOICE_ENABLED=true
DNA_PERSISTENCE=true
STRIPE_SECRET_KEY=sk_live_...
STRIPE_WEBHOOK_SECRET=whsec_...
STRIPE_TEST_MODE=false
```

---

## File Locations

Variables are read in these files:

| File | Variables |
|------|-----------|
| `app/config.py` | Core config, feature flags, deploy ID |
| `app/rate_limiter.py` | Rate limiting |
| `app/routers/leading_light.py` | Leading Light feature flag |
| `app/voice/tts_client.py` | Voice/TTS config |
| `app/image_eval/config.py` | Image eval config |
| `billing/stripe_client.py` | Stripe config |
| `persistence/db.py` | Database path |
| `alerts/service.py` | Persistence flag |
| `context/providers/nba_availability.py` | NBA data config |

---

## Validation

Check current config at startup in logs:
```
[STARTUP] service=dna-matrix version=0.1.0 environment=production git_sha=abc123...
```

Check deployed config via API:
```bash
curl https://dna-production-cb47.up.railway.app/health
```

## Postgres Notes

When targeting Postgres or Supabase, prefer URL forms like:

```bash
APP_DATABASE_URL=postgresql+psycopg://postgres:password@127.0.0.1:5432/betapp
APP_DATABASE_URL=postgresql+psycopg://postgres.project-ref:password@aws-0-us-east-1.pooler.supabase.com:6543/postgres?sslmode=require
```

This repo now declares `psycopg[binary]` as the Postgres driver for SQLAlchemy 2.x.
