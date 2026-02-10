# Deployment Notes - DNA Bet Engine

## Current Issue: Production API 500 Error
**URL:** https://dna-production-cb47.up.railway.app/api/odds/nba-lal-gsw-2026-02-09
**Error:** 500 Internal Server Error
**Cause:** Production has THE_ODDS_API_KEY set → uses real OddsApiProvider → game ID not found

## Solution Options

### Option 1: Remove API Key from Railway Dashboard (Fastest)
1. Go to https://railway.app/project/dna-production-cb47
2. Click on "dna-production-cb47" service
3. Go to "Variables" tab
4. Delete or comment out: THE_ODDS_API_KEY
5. Redeploy happens automatically

### Option 2: Code Fix - Force Mock Provider
Modify `app/routers/odds.py`:
```python
def get_odds_provider() -> any:
    """Force mock provider until real API integration ready."""
    return MockOddsProvider()  # Ignore API key for now
```
Commit, push, auto-deploy via GitHub integration.

### Option 3: Fix Real API Integration
Update code to fetch from real API and match game IDs properly.
Requires: proper game ID format matching The Odds API.

## Railway CLI Authentication Issue

### Problem
Tokens provided don't work with Railway CLI v4.29.0 in non-interactive mode:
- Token format: `81176125-5c55-487c-922a-81a66e51cb40` (project ID?)
- Token format: `ed5e5b7f-393f-48ed-aa94-05b1ee243bda` (token - unauthorized)
- Token format: `7dcd3b83-b10d-4052-b323-a9b4418649bb` (token - unauthorized)  
- Token format: `2ebb7350-1c3d-4ae8-a4eb-8531e41494ce` (fresh from dashboard - invalid)

All fail with: "Invalid RAILWAY_TOKEN" or "Unauthorized"

### Root Cause
Railway CLI requires initial interactive login before API tokens work:
```bash
railway login  # Opens browser, creates ~/.railway/config.json
# THEN tokens work for subsequent commands
```

### Working Deployment Flow
1. SSH to EC2: `ssh launchplugai@100.75.246.47`
2. Login once: `railway login` (browser opens, click authorize)
3. Deploy: `railway up` (works now and forever)

### Alternative: GitHub Actions
```yaml
# .github/workflows/deploy.yml
name: Deploy to Railway
on:
  push:
    branches: [main]
jobs:
  deploy:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - uses: railway/cli@v4
        with:
          railway_token: ${{ secrets.RAILWAY_TOKEN }}
      - run: railway up
```

## Current Code Status

### Ready to Deploy (10 commits on main)
- `eb81e18` debug: Player props logging
- `2ba177e` feat: Money tracking per account
- `33cf679` fix: Player props working
- `b17cac5` fix: My Bets nav link
- `76b8891` fix: Landing ↔ App navigation
- `ee72c34` fix: Landing page at /
- `b49bd51` feat: Quick bet shortcuts
- `9585801` debug: Mock provider logging

### Production Status
- Last successful deploy: ~4 hours ago
- Git SHA: `2ba177e` (money tracking, no player props fix)
- Issue: API 500 errors blocking functionality

## Action Required

### Immediate (Fix 500 Error)
1. Remove THE_ODDS_API_KEY from Railway dashboard, OR
2. Push code that forces MockOddsProvider

### Long-term (Enable CLI Deploys)
1. SSH to EC2 and run `railway login` once, OR
2. Set up GitHub Actions auto-deploy

---
Last Updated: 2026-02-10
