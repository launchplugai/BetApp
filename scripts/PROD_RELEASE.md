# Production Release — Step by Step

## Step 1: Fix Railway Config (YOU DO THIS)

Go to: https://railway.com/project/YOUR_PROJECT/variables

### SET these variables:
```
ODDS_PROVIDER=mock
```

### REMOVE (or blank out):
```
THE_ODDS_API_KEY
```

### VERIFY:
- Only `ODDS_PROVIDER=mock` should remain for odds config
- This forces MockOddsProvider (no live API calls)

---

## Step 2: Deploy (YOU DO THIS)

### Option A: Auto-deploy (if production branch)
```bash
cd /var/lib/openbot/workdir/target
git checkout production/main  # or your prod branch
git merge main
git push origin production/main
```

### Option B: Manual deploy (Railway dashboard)
1. Go to Railway dashboard
2. Click "Deploy" on the DNA service
3. Wait for build to complete

---

## Step 3: Run Smoke Test (SCRIPT PROVIDED)

### From local machine or EC2:
```bash
# Download script
curl -O https://raw.githubusercontent.com/launchplugai/DNA/main/scripts/prod_smoke_test.sh
chmod +x prod_smoke_test.sh

# Run it
./prod_smoke_test.sh
```

### Or test manually with curl:
```bash
PROD_URL="https://dna-production-cb47.up.railway.app"

# Test 1: Landing
curl -s "$PROD_URL/" | head -5

# Test 2: Games API
curl -s "$PROD_URL/api/games?sport=NBA" | python3 -m json.tool | head -20

# Test 3: Odds API (critical — was 500 before)
curl -s "$PROD_URL/api/odds/nba-lal-gsw-2026-02-09" | python3 -m json.tool | head -40
```

---

## Expected Results

### ✅ PASS means:
- Landing: HTTP 200
- Games: Returns array with LAL, GSW games
- Odds: Returns markets (spread, total, moneyline, player_prop)
- Provider: Shows "provider": "mock" in response
- No 500 errors

### ❌ FAIL means:
- Check Railway logs: `railway logs`
- Likely causes:
  - ODDS_PROVIDER not set → defaults to wrong provider
  - THE_ODDS_API_KEY still present → tries oddsapi with bad IDs
  - Build failure → check Railway build logs

---

## Step 4: Report Back

Send me the smoke test output. If all ✅, we move to Settlement sprint.

If any ❌, we fix that one thing only.
