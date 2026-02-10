# DNA Bet Engine - Known Issues Tracker

## Critical Issues (Blocking)

### 1. Player Props Don't Work
**Status:** ❌ Broken
**Evidence:** PLAYER PROPS tab shows "No player props available" or empty
**Root Cause:** Mock provider doesn't generate player props data
**Fix Needed:** Add player props to mock data + transform in builder.js

### 2. Money Simulation Not Accurate
**Status:** ❌ Broken  
**Evidence:** Balance shows $0.00, wagers don't deduct, payouts don't add
**Root Cause:** No actual balance update logic in bet submission
**Fix Needed:** Update user balance on bet submit/settle

### 3. No Money Tracking Per Account
**Status:** ❌ Missing
**Evidence:** User balance always resets, no transaction history
**Root Cause:** Balance stored but never updated
**Fix Needed:** Balance mutation on bet submit + win/loss settlement

### 4. Team Logos Missing
**Status:** ❌ Missing
**Evidence:** No team logos in game cards or builder
**Root Cause:** No logo URLs in mock data or templates
**Fix Needed:** Add logo mapping + display in UI

### 5. Right Players Not Selectable
**Status:** ❌ Broken
**Evidence:** Player prop buttons don't add legs correctly
**Root Cause:** Player prop selection matching logic broken
**Fix Needed:** Fix isLegSelected() for player_prop market

### 6. No Suggested Parlays
**Status:** ❌ Missing
**Evidence:** No "Suggested" or "Popular" parlays section
**Root Cause:** Feature not implemented
**Fix Needed:** Add suggested parlays based on trends/correlations

### 7. Analytics Too Dry
**Status:** ❌ Needs Improvement
**Evidence:** Just "+120" and "This parlay has moderate confidence"
**Root Cause:** Minimal explain data being shown
**Fix Needed:** Rich analysis with truth + emotion (per S2-FND philosophy)

### 8. Can't Navigate to Landing Page
**Status:** ❌ Broken
**Evidence:** Clicking DNA Engine logo doesn't go to /
**Root Cause:** May be auth guard blocking or link not working
**Fix Needed:** Verify navigation works

---

## Fix Priority Order

1. **Landing Page Navigation** (Quick win)
2. **Player Props** (Core feature)
3. **Team Logos** (Visual polish)
4. **Player Selection Fix** (Core feature)
5. **Rich Analytics** (Experience)
6. **Money Tracking** (Core feature)
7. **Suggested Parlays** (Enhancement)

---

## Implementation Notes

### Player Props Fix
```javascript
// In mock provider, add player props
_get_nba_player_props() {
  return [
    { player: "LeBron James", prop: "points", line: 27.5, over_odds: -110, under_odds: -110 },
    { player: "Stephen Curry", prop: "3pm", line: 4.5, over_odds: -120, under_odds: +100 },
    // ... more players
  ];
}
```

### Money Tracking Fix
```python
# In bets.py create_bet()
user.balance -= request.wager  # Deduct wager

# In settle_bet() or outcome tracking
user.balance += payout  # Add payout on win
```

### Rich Analytics Fix
```javascript
// Show multiple signals:
- Confidence score with visual meter
- Risk assessment (low/medium/high)
- Key insights (3-4 bullet points)
- Suggested improvements
- Emotional framing ("This parlay tells a story...")
```

---

Last Updated: 2026-02-10
