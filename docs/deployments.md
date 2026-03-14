# Deployment Environments

## Production

| Field | Value |
|-------|-------|
| **Base URL** | https://dna-production-b681.up.railway.app |
| **Platform** | Railway |
| **Region** | us-east4 |
| **Health Endpoint** | GET /health |
| **Build Info** | GET /build |

### Health Check Commands

```bash
# Quick reachability test
curl -I -m 5 https://dna-production-b681.up.railway.app

# Health status
curl -sS -m 5 https://dna-production-b681.up.railway.app/health

# Build/version info
curl -sS -m 5 https://dna-production-b681.up.railway.app/build
```

### Troubleshooting

If health checks fail:
1. Check Railway dashboard for service status
2. Look for `x-railway-fallback: true` header (indicates app not running)
3. Review deploy logs for startup errors
4. Verify environment variables (PORT, DATABASE_URL, etc.)

---

## Staging

| Field | Value |
|-------|-------|
| **Base URL** | *(Not configured)* |
| **Platform** | *(Not configured)* |

*Add staging URL here when created.*

---

## Local Development

```bash
# Apply schema first
PYTHONPATH=.:./dna-matrix:$PYTHONPATH alembic upgrade head

# Run locally
PYTHONPATH=.:./dna-matrix:$PYTHONPATH uvicorn app.main:app --reload --port 8000

# Health check locally
curl http://localhost:8000/health
```

If the governed control-plane schema is missing, app startup now fails clearly and instructs you to run `alembic upgrade head`.

---

*Last updated: 2026-02-20*
