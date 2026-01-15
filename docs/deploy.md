# Deploy Verification

## Production

**URL:** https://dna-production-b681.up.railway.app

## Health Check

```bash
curl -sS https://dna-production-b681.up.railway.app/health | python -m json.tool
```

## Expected Response Fields

| Field | Description |
|-------|-------------|
| `status` | `"healthy"` |
| `service` | `"dna-matrix"` |
| `version` | Current version (e.g., `"0.1.0"`) |
| `environment` | From `RAILWAY_ENVIRONMENT` env var |
| `started_at` | ISO 8601 timestamp of service start |
| `git_sha` | From `RAILWAY_GIT_COMMIT_SHA` - use to verify deployed commit |

## Verifying a Deploy

1. Get the expected commit SHA from the branch:
   ```bash
   git rev-parse HEAD
   ```

2. Hit the health endpoint and check `git_sha` matches:
   ```bash
   curl -sS https://dna-production-b681.up.railway.app/health | python -m json.tool | grep git_sha
   ```

3. If `git_sha` is missing, check Railway environment variables:
   - `RAILWAY_GIT_COMMIT_SHA` should be set automatically by Railway
   - `GIT_SHA` can be set manually as a fallback

## Railway Configuration

- Config file: `railway.json`
- Health check path: `/health`
- Builder: Nixpacks
