# Deployment Verification Guide

**Purpose:** Verify that Railway is running the expected commit from main.

---

## Quick Check (PowerShell)

### 1. Get Deployed Git SHA

```powershell
# Fetch health endpoint and extract git_sha
$response = Invoke-RestMethod -Uri "https://dna-production-cb47.up.railway.app/health"
$response.git_sha
```

**Expected output:** A 40-character git commit SHA (e.g., `a1b2c3d4e5f6...`) or `unknown` if not set.

### 2. Get Full Health Response

```powershell
# View all deployment metadata
Invoke-RestMethod -Uri "https://dna-production-cb47.up.railway.app/health" | ConvertTo-Json
```

**Expected output:**
```json
{
  "status": "healthy",
  "service": "dna-matrix",
  "version": "0.1.0",
  "environment": "production",
  "git_sha": "a1b2c3d4e5f6...",
  "build_time_utc": "2026-01-28T12:00:00Z",
  "started_at": "2026-01-28T12:00:05+00:00"
}
```

### 3. Compare with GitHub Main HEAD

```powershell
# Store deployed SHA
$deployed = (Invoke-RestMethod -Uri "https://dna-production-cb47.up.railway.app/health").git_sha

# Display for manual comparison with GitHub
Write-Host "Deployed SHA: $deployed"
Write-Host "Compare with: https://github.com/launchplugai/DNA/commits/main"
```

**To verify:**
1. Run the command above to get deployed SHA
2. Go to https://github.com/launchplugai/DNA/commits/main
3. Check if the deployed SHA matches the latest commit on main

---

## Interpreting Results

### Match (Deployment is current)
- Deployed `git_sha` matches GitHub main HEAD
- `build_time_utc` is recent (within expected deploy window)

### Mismatch (Deployment is stale)
- Deployed `git_sha` does NOT match GitHub main HEAD

**Actions if mismatched:**
1. Check Railway dashboard for failed deploys
2. Verify main branch has been pushed
3. Trigger manual redeploy in Railway if needed
4. Check Railway build logs for errors

### Unknown SHA
- `git_sha` shows `unknown`

**Causes:**
- Environment variable `RAILWAY_GIT_COMMIT_SHA` not set
- Running locally without `GIT_SHA` env var

---

## Environment Variables

Railway automatically provides:
- `RAILWAY_GIT_COMMIT_SHA` — Git commit SHA of deployed code
- `RAILWAY_ENVIRONMENT` — Environment name (production/staging)

The app also accepts:
- `GIT_SHA` — Fallback if Railway variable not available
- `BUILD_TIME_UTC` — Set in railway.json start command

---

## Curl Alternative (Linux/Mac/Git Bash)

```bash
# Get deployed SHA
curl -s https://dna-production-cb47.up.railway.app/health | jq -r '.git_sha'

# Full health response
curl -s https://dna-production-cb47.up.railway.app/health | jq

# Compare with local main
DEPLOYED=$(curl -s https://dna-production-cb47.up.railway.app/health | jq -r '.git_sha')
LOCAL=$(git rev-parse main)
echo "Deployed: $DEPLOYED"
echo "Local main: $LOCAL"
if [ "$DEPLOYED" = "$LOCAL" ]; then echo "MATCH"; else echo "MISMATCH"; fi
```

---

## Troubleshooting

| Symptom | Likely Cause | Fix |
|---------|--------------|-----|
| `git_sha` is `unknown` | Env var not set | Check Railway variables |
| SHA doesn't match main | Deploy not triggered | Push to main or manual redeploy |
| `build_time_utc` is old | Container restarted, not rebuilt | Redeploy to get fresh build time |
| 503/timeout | Service down | Check Railway logs |
