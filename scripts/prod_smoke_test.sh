#!/bin/bash
# Production Smoke Test — DNA Bet Engine
# Run this after Railway deploy to verify critical path

set -e

BASE_URL="${PROD_URL:-https://dna-production-cb47.up.railway.app}"
GAME_ID="nba-lal-gsw-2026-02-09"

echo "=== DNA Production Smoke Test ==="
echo "Target: $BASE_URL"
echo ""

# 1) Landing loads
echo -n "1. Landing page (/): "
curl -s -o /dev/null -w "%{http_code}" "$BASE_URL/" | grep -q "200" && echo "✅ PASS" || echo "❌ FAIL"

# 2) Launch app
echo -n "2. App loads (/app): "
curl -s -o /dev/null -w "%{http_code}" "$BASE_URL/app" | grep -q "200" && echo "✅ PASS" || echo "❌ FAIL"

# 3) Browse games
echo -n "3. Games API (/api/games?sport=NBA): "
GAMES_RESP=$(curl -s "$BASE_URL/api/games?sport=NBA")
echo "$GAMES_RESP" | grep -q "LAL" && echo "✅ PASS (found LAL)" || echo "❌ FAIL"

# 4) Builder markets
echo -n "4. Odds API (/api/odds/$GAME_ID): "
ODDS_RESP=$(curl -s "$BASE_URL/api/odds/$GAME_ID")
echo "$ODDS_RESP" | grep -q "spread" && echo "✅ PASS (has spread)" || echo "❌ FAIL"

# 5) Check provider diagnostics
echo -n "5. Provider diagnostics: "
echo "$ODDS_RESP" | grep -q "provider.*mock" && echo "✅ PASS (using mock)" || echo "⚠️  WARN (check provider)"

# 6) Player props
echo -n "6. Player props present: "
echo "$ODDS_RESP" | grep -q "player_prop" && echo "✅ PASS" || echo "❌ FAIL"

# 7) Quarters/Halves (via markets check)
echo -n "7. Main lines present: "
(echo "$ODDS_RESP" | grep -q "spread" && echo "$ODDS_RESP" | grep -q "total" && echo "$ODDS_RESP" | grep -q "moneyline") && echo "✅ PASS" || echo "❌ FAIL"

echo ""
echo "=== Smoke Test Complete ==="
echo "If any ❌ FAIL, check Railway logs: railway logs"
