# Manual UI Verification Checklist

## Purpose
Walk through every interactive element manually. No assumptions. No "tests passed = working."

---

## Environment Setup
- [ ] Server running locally: `python -m uvicorn app.main:app --reload`
- [ ] Browser: Chrome/Firefox DevTools open (F12)
- [ ] Network tab visible to verify API calls
- [ ] Console tab visible to catch errors

---

## Page 1: Auth (`/app?screen=auth`)

### Visual Elements
- [ ] Page loads without console errors
- [ ] Email input field visible and clickable
- [ ] Password input field visible and clickable
- [ ] Login button visible
- [ ] Register link visible
- [ ] Error messages appear below inputs (if invalid)

### Functional Tests
- [ ] **Empty submit**: Click Login with empty fields → shows validation error
- [ ] **Invalid email**: Type "bad" in email, submit → shows format error
- [ ] **Wrong credentials**: Valid email format, wrong password → shows auth error
- [ ] **Valid login**: Correct credentials → redirects to dashboard
- [ ] **Session persistence**: Refresh page after login → still logged in

### API Verification (Network tab)
- [ ] POST `/api/auth/login` sent on submit
- [ ] 200 response with access_token
- [ ] Token stored in localStorage/sessionStorage

---

## Page 2: Dashboard (`/app?screen=dashboard`)

### Visual Elements
- [ ] Welcome message shows username
- [ ] Navigation bar: Home, Search, Build, My Bets
- [ ] Active games list loads
- [ ] Each game card shows: teams, time, spread/total/moneyline
- [ ] "Build Parlay" button on each game card
- [ ] Empty state if no games (should show message)

### Functional Tests
- [ ] **Game cards clickable** → goes to builder with game pre-selected
- [ ] **Build Parlay button** → goes to builder with game pre-selected
- [ ] **Navigation links work**:
  - [ ] Home → dashboard (refresh)
  - [ ] Search → browse page
  - [ ] Build → builder (may show "select game" state)
  - [ ] My Bets → history page
- [ ] **Back button** in browser works
- [ ] **Refresh** maintains logged-in state

### API Verification
- [ ] GET `/api/games` returns game list
- [ ] Response has: id, home, away, start_time, odds

---

## Page 3: Builder (`/app?screen=builder`)

### Visual Elements
- [ ] Header with back arrow and "BUILD PARLAY" title
- [ ] Four tabs: MAIN LINES, PLAYER PROPS, QUARTERS, HALVES
- [ ] Game info: teams, score (if live), time
- [ ] MAIN LINES shows: spread, total, moneyline buttons
- [ ] PLAYER PROPS shows: player stats (if available)
- [ ] QUARTERS shows: Q1, Q2, Q3, Q4 lines
- [ ] HALVES shows: 1st Half, 2nd Half lines
- [ ] Parlay slip visible (or accessible)
- [ ] Wager input field
- [ ] Potential payout display
- [ ] Analyze with DNA button
- [ ] Submit Bet button

### Functional Tests - Tab Switching
- [ ] Click MAIN LINES → shows spread/total/moneyline
- [ ] Click PLAYER PROPS → shows player markets
- [ ] Click QUARTERS → shows Q1-Q4
- [ ] Click HALVES → shows 1H/2H
- [ ] **No console errors when switching tabs**

### Functional Tests - Adding Legs
- [ ] **Spread**: Click spread line → leg appears in slip
- [ ] **Total**: Click Over/Under → leg appears in slip
- [ ] **Moneyline**: Click ML odds → leg appears in slip
- [ ] **Quarter spread**: Click Q1 spread → leg appears
- [ ] **Quarter total**: Click Q1 total → leg appears
- [ ] **Half spread**: Click 1H spread → leg appears
- [ ] **Half total**: Click 1H total → leg appears
- [ ] **Half moneyline**: Click 1H ML → leg appears

### Functional Tests - Selection Highlighting
- [ ] Click any button → button gets **RED BORDER** (leg-selected class)
- [ ] Click same button again → leg removed, red border gone
- [ ] Switch tabs → previously selected legs stay highlighted
- [ ] Add multiple legs from different tabs → all show red border

### Functional Tests - Parlay Slip
- [ ] Each added leg shows: selection text, odds, remove button
- [ ] Click remove (X) → leg removed, highlight cleared
- [ ] "Clear All" button removes all legs
- [ ] Leg counter updates: "2 LEG PARLAY"
- [ ] Odds multiplier updates with each leg added

### Functional Tests - Wager & Payout
- [ ] Enter wager amount → potential payout calculates
- [ ] Wager = $10, odds = +200 → payout shows $30
- [ ] Wager = $0 or empty → payout shows $0 or "—"

### Functional Tests - Analyze
- [ ] **No legs** → Analyze button **DISABLED**
- [ ] **Add 1+ legs** → Analyze button **ENABLED**
- [ ] Click Analyze → loading state shown
- [ ] Analyze returns → results displayed (confidence, summary)
- [ ] Analyze with 2+ legs → correlation warnings if applicable

### Functional Tests - Submit
- [ ] **No legs** → Submit button **DISABLED**
- [ ] **Add legs** → Submit **ENABLED**
- [ ] Click Submit → success message or confirmation
- [ ] Submitted bet appears in History

### API Verification
- [ ] GET `/api/odds/{gameId}` on page load
- [ ] POST `/app/evaluate` on Analyze
- [ ] POST `/api/bets` on Submit

### Error States
- [ ] **Markets fail to load**: Shows error message + retry button
- [ ] **Analyze fails**: Shows error, keeps legs
- [ ] **Submit fails**: Shows error, doesn't clear slip

---

## Page 4: History (`/app?screen=history`)

### Visual Elements
- [ ] Header: "MY BETS"
- [ ] List of previous bets (or empty state)
- [ ] Each bet card shows: date, teams, legs, result, amount
- [ ] Status badges: PENDING, WON, LOST

### Functional Tests
- [ ] **Empty state**: Shows "No bets yet" + CTA to build
- [ ] **Bet cards**: Clickable to view details
- [ ] **Pagination/Load more**: If many bets
- [ ] **Refresh**: Maintains list

### API Verification
- [ ] GET `/api/bets/history` returns bet list
- [ ] Each bet has: id, input_text, legs, wager, status

---

## Page 5: Browse/Search (`/app?screen=browse`)

### Visual Elements
- [ ] Search input field
- [ ] Sport/league filters
- [ ] Game list matching filters

### Functional Tests
- [ ] **Search by team**: Type "Lakers" → shows LAL games
- [ ] **Filter by sport**: Click NBA → shows only NBA
- [ ] **Clear filters**: Shows all games again
- [ ] **Click game** → goes to builder

---

## Cross-Cutting Checks

### Mobile Responsiveness
- [ ] Test on mobile viewport (DevTools → Responsive)
- [ ] All buttons tappable (min 44px)
- [ ] No horizontal scroll
- [ ] Text readable (no tiny fonts)

### Performance
- [ ] Page load < 3 seconds
- [ ] Tab switch < 500ms
- [ ] No spinner/freeze when adding legs

### Accessibility
- [ ] Tab key navigates through interactive elements
- [ ] Enter/Space activates buttons
- [ ] Error messages announced (screen reader)

### Session Handling
- [ ] **Token expiry**: Wait 15 min, refresh → redirects to auth
- [ ] **Logout**: Click logout → clears session, redirects to auth
- [ ] **Unauthorized API call**: Returns 401, redirects to auth

---

## Sign-Off

| Page | Verified By | Date | Issues Found |
|------|-------------|------|--------------|
| Auth | | | |
| Dashboard | | | |
| Builder | | | |
| History | | | |
| Browse | | | |

**Overall Status**: ⬜ NOT READY / ⬜ READY WITH ISSUES / ⬜ READY

**Blockers**:
1. 
2. 
3. 
