# UI Test Plan - Components & Workflows

## Test Structure
- **Component Tests**: Individual UI elements
- **Workflow Tests**: End-to-end user journeys
- **Edge Cases**: Error states, boundaries

---

# PART 1: COMPONENT TESTS

## C1: Navigation Bar
**Component**: Fixed bottom navigation
**Location**: All authenticated pages

| Test ID | Test Case | Steps | Expected Result | Status |
|---------|-----------|-------|-----------------|--------|
| NAV-001 | Home icon active | 1. Load dashboard | Home icon highlighted | ⬜ |
| NAV-002 | Home click | 1. Click Home | Navigate to dashboard | ⬜ |
| NAV-003 | Search click | 1. Click Search | Navigate to browse | ⬜ |
| NAV-004 | Build click | 1. Click Build | Navigate to builder | ⬜ |
| NAV-005 | My Bets click | 1. Click My Bets | Navigate to history | ⬜ |
| NAV-006 | Active indicator | 1. Navigate to each page | Correct icon highlighted | ⬜ |
| NAV-007 | Icon tap target | 1. DevTools → check size | Min 44x44px | ⬜ |

---

## C2: Auth Form
**Component**: Login/Register form
**Location**: `/app?screen=auth`

| Test ID | Test Case | Steps | Expected Result | Status |
|---------|-----------|-------|-----------------|--------|
| AUTH-001 | Email empty | 1. Leave email empty<br>2. Click Login | Error: "Email required" | ⬜ |
| AUTH-002 | Email invalid | 1. Type "bad"<br>2. Click Login | Error: "Invalid email" | ⬜ |
| AUTH-003 | Password empty | 1. Valid email<br>2. Empty password<br>3. Click Login | Error: "Password required" | ⬜ |
| AUTH-004 | Password short | 1. Type "123"<br>2. Click Login | Error: "Password too short" | ⬜ |
| AUTH-005 | Wrong credentials | 1. Valid format email<br>2. Wrong password<br>3. Click Login | Error: "Invalid credentials" | ⬜ |
| AUTH-006 | Valid login | 1. Valid email<br>2. Valid password<br>3. Click Login | Redirect to dashboard | ⬜ |
| AUTH-007 | Loading state | 1. Click Login | Button shows spinner/disabled | ⬜ |
| AUTH-008 | Token stored | 1. Login successfully | localStorage has access_token | ⬜ |
| AUTH-009 | Register link | 1. Click Register | Navigate to register page | ⬜ |
| AUTH-010 | Enter key submit | 1. Fill form<br>2. Press Enter | Form submits | ⬜ |

---

## C3: Game Card
**Component**: Game listing card
**Location**: Dashboard, Browse

| Test ID | Test Case | Steps | Expected Result | Status |
|---------|-----------|-------|-----------------|--------|
| CARD-001 | Display teams | 1. Load dashboard | Home and away teams shown | ⬜ |
| CARD-002 | Display time | 1. Load dashboard | Start time shown | ⬜ |
| CARD-003 | Display spread | 1. Load dashboard | Spread line visible | ⬜ |
| CARD-004 | Display total | 1. Load dashboard | Total line visible | ⬜ |
| CARD-005 | Display ML | 1. Load dashboard | Moneyline odds visible | ⬜ |
| CARD-006 | Card clickable | 1. Click card | Navigate to builder | ⬜ |
| CARD-007 | Build button | 1. Click Build Parlay | Navigate to builder | ⬜ |
| CARD-008 | Live indicator | 1. Live game | "LIVE" badge shown | ⬜ |
| CARD-009 | Score display | 1. Live game | Current score shown | ⬜ |

---

## C4: Market Tabs
**Component**: Segmented control for markets
**Location**: Builder page

| Test ID | Test Case | Steps | Expected Result | Status |
|---------|-----------|-------|-----------------|--------|
| TAB-001 | Main Lines active | 1. Load builder | MAIN LINES selected | ⬜ |
| TAB-002 | Tab click Props | 1. Click PLAYER PROPS | Props content shown | ⬜ |
| TAB-003 | Tab click Quarters | 1. Click QUARTERS | Quarters content shown | ⬜ |
| TAB-004 | Tab click Halves | 1. Click HALVES | Halves content shown | ⬜ |
| TAB-005 | Active indicator | 1. Click each tab | Red underline on active | ⬜ |
| TAB-006 | No console errors | 1. Click each tab | No errors in console | ⬜ |
| TAB-007 | Tab persistence | 1. Click QUARTERS<br>2. Add leg<br>3. Click MAIN<br>4. Click QUARTERS | Previous selection still highlighted | ⬜ |

---

## C5: Bet Buttons (Market Lines)
**Component**: Individual line selection buttons
**Location**: Builder, all tabs

| Test ID | Test Case | Steps | Expected Result | Status |
|---------|-----------|-------|-----------------|--------|
| BTN-001 | Button display | 1. Load builder | Line and odds visible | ⬜ |
| BTN-002 | Click add leg | 1. Click spread button | Leg added to slip | ⬜ |
| BTN-003 | Highlight on select | 1. Click button | Red border appears | ⬜ |
| BTN-004 | Toggle off | 1. Click selected button | Leg removed, border gone | ⬜ |
| BTN-005 | Quarters highlight | 1. Click Q1 spread | Red border appears | ⬜ |
| BTN-006 | Halves highlight | 1. Click 1H spread | Red border appears | ⬜ |
| BTN-007 | Multiple select | 1. Click 3 different buttons | All 3 have red borders | ⬜ |
| BTN-008 | Across tabs | 1. Add MAIN spread<br>2. Add Q1 spread | Both highlighted when viewing | ⬜ |
| BTN-009 | Hover state | 1. Hover button | Visual feedback (opacity/bg) | ⬜ |
| BTN-010 | Disabled state | 1. Markets loading | Buttons disabled | ⬜ |

---

## C6: Parlay Slip
**Component**: Selected legs container
**Location**: Builder page

| Test ID | Test Case | Steps | Expected Result | Status |
|---------|-----------|-------|-----------------|--------|
| SLIP-001 | Empty state | 1. No legs selected | Shows "Add legs" message | ⬜ |
| SLIP-002 | Leg display | 1. Add spread leg | Leg text shown correctly | ⬜ |
| SLIP-003 | Leg count | 1. Add 2 legs | "2 LEG PARLAY" shown | ⬜ |
| SLIP-004 | Remove leg | 1. Click X on leg | Leg removed, count updates | ⬜ |
| SLIP-005 | Clear all | 1. Click Clear All | All legs removed | ⬜ |
| SLIP-006 | Odds display | 1. Add +200 leg | Odds shown: +200 | ⬜ |
| SLIP-007 | Combined odds | 1. Add +200, +150 | Shows combined multiplier | ⬜ |
| SLIP-008 | Leg persistence | 1. Add legs<br>2. Switch tabs<br>3. Return | Legs still in slip | ⬜ |

---

## C7: Wager Input
**Component**: Bet amount input
**Location**: Builder page

| Test ID | Test Case | Steps | Expected Result | Status |
|---------|-----------|-------|-----------------|--------|
| WAGER-001 | Default value | 1. Load builder | Shows placeholder or $0 | ⬜ |
| WAGER-002 | Enter amount | 1. Type "50" | Displays "$50" or "50" | ⬜ |
| WAGER-003 | Minimum | 1. Type "0"<br>2. Blur | Shows error or resets to min | ⬜ |
| WAGER-004 | Maximum | 1. Type "999999"<br>2. Blur | Capped or error shown | ⬜ |
| WAGER-005 | Decimal | 1. Type "50.50" | Accepted or rounded | ⬜ |
| WAGER-006 | Non-numeric | 1. Type "abc" | Rejected or ignored | ⬜ |
| WAGER-007 | Negative | 1. Type "-50" | Rejected or abs value | ⬜ |

---

## C8: Payout Display
**Component**: Potential winnings calculation
**Location**: Builder page

| Test ID | Test Case | Steps | Expected Result | Status |
|---------|-----------|-------|-----------------|--------|
| PAY-001 | No wager | 1. No wager entered | Shows "$0" or "—" | ⬜ |
| PAY-002 | No legs | 1. Enter wager<br>2. No legs | Shows "$0" or "—" | ⬜ |
| PAY-003 | Single leg | 1. Wager: $10<br>2. Leg: +200 | Payout: $30 | ⬜ |
| PAY-004 | Multiple legs | 1. Wager: $10<br>2. Legs: +200, +150 | Payout: $75 | ⬜ |
| PAY-005 | Update on leg add | 1. Wager: $10<br>2. Add leg | Payout updates | ⬜ |
| PAY-006 | Update on leg remove | 1. 2 legs, $10<br>2. Remove 1 | Payout recalculates | ⬜ |
| PAY-007 | Large wager | 1. Wager: $10000<br>2. 3 legs | Shows formatted payout | ⬜ |

---

## C9: Analyze Button
**Component**: DNA analysis trigger
**Location**: Builder page

| Test ID | Test Case | Steps | Expected Result | Status |
|---------|-----------|-------|-----------------|--------|
| ANZ-001 | Disabled no legs | 1. No legs selected | Button disabled | ⬜ |
| ANZ-002 | Enabled with legs | 1. Add 1+ legs | Button enabled | ⬜ |
| ANZ-003 | Loading state | 1. Click Analyze | Shows loading/spinner | ⬜ |
| ANZ-004 | Success result | 1. Click Analyze<br>2. Wait | Shows confidence + summary | ⬜ |
| ANZ-005 | Error state | 1. Disconnect network<br>2. Click Analyze | Shows error message | ⬜ |
| ANZ-006 | Retry | 1. Error shown<br>2. Click Retry | Retries analysis | ⬜ |

---

## C10: Submit Button
**Component**: Save bet to history
**Location**: Builder page

| Test ID | Test Case | Steps | Expected Result | Status |
|---------|-----------|-------|-----------------|--------|
| SUB-001 | Disabled no legs | 1. No legs | Button disabled | ⬜ |
| SUB-002 | Enabled with legs | 1. Add legs | Button enabled | ⬜ |
| SUB-003 | Click submit | 1. Click Submit | Shows confirmation/success | ⬜ |
| SUB-004 | Appears in history | 1. Submit bet<br>2. Go to History | Bet appears in list | ⬜ |
| SUB-005 | Auth required | 1. Log out<br>2. Click Submit | Redirects to auth | ⬜ |

---

# PART 2: WORKFLOW TESTS

## W1: New User Registration
**Workflow**: First-time user signup

| Step | Action | Expected Result | Status |
|------|--------|-----------------|--------|
| 1 | Navigate to `/app?screen=auth` | Auth page loads | ⬜ |
| 2 | Click Register | Register form shown | ⬜ |
| 3 | Enter email | Email accepted | ⬜ |
| 4 | Enter password | Password masked | ⬜ |
| 5 | Confirm password | Match validation | ⬜ |
| 6 | Click Create Account | Account created | ⬜ |
| 7 | Redirect | To dashboard | ⬜ |
| 8 | Welcome | First-time message shown | ⬜ |

---

## W2: Login Flow
**Workflow**: Existing user login

| Step | Action | Expected Result | Status |
|------|--------|-----------------|--------|
| 1 | Navigate to auth | Login form shown | ⬜ |
| 2 | Enter valid email | Accepted | ⬜ |
| 3 | Enter valid password | Masked | ⬜ |
| 4 | Click Login | Loading state | ⬜ |
| 5 | Success | Redirect to dashboard | ⬜ |
| 6 | Token stored | Can refresh without re-login | ⬜ |

---

## W3: Build Simple Parlay
**Workflow**: Select game, add legs, analyze

| Step | Action | Expected Result | Status |
|------|--------|-----------------|--------|
| 1 | Dashboard load | Games displayed | ⬜ |
| 2 | Click game | Navigate to builder | ⬜ |
| 3 | Verify MAIN LINES active | Spread/Total/ML visible | ⬜ |
| 4 | Click spread | Leg added, highlighted | ⬜ |
| 5 | Click QUARTERS tab | Q1-Q4 visible | ⬜ |
| 6 | Click Q1 spread | Leg added, highlighted | ⬜ |
| 7 | Click HALVES tab | 1H/2H visible | ⬜ |
| 8 | Click 1H total | Leg added, highlighted | ⬜ |
| 9 | Verify slip | 3 legs shown | ⬜ |
| 10 | Enter wager | Payout calculated | ⬜ |
| 11 | Click Analyze | Loading, then results | ⬜ |
| 12 | Review analysis | Confidence, summary shown | ⬜ |

---

## W4: Submit Bet to History
**Workflow**: Complete bet lifecycle

| Step | Action | Expected Result | Status |
|------|--------|-----------------|--------|
| 1 | Complete W3 | 3-leg parlay ready | ⬜ |
| 2 | Enter $50 wager | Payout shows | ⬜ |
| 3 | Click Submit | Success message | ⬜ |
| 4 | Navigate to History | New bet in list | ⬜ |
| 5 | Verify details | Teams, legs, amount correct | ⬜ |
| 6 | Status badge | Shows "PENDING" | ⬜ |

---

## W5: Browse and Search
**Workflow**: Find specific game

| Step | Action | Expected Result | Status |
|------|--------|-----------------|--------|
| 1 | Click Search | Browse page loads | ⬜ |
| 2 | Type "Lakers" | Lakers games filtered | ⬜ |
| 3 | Clear search | All games shown | ⬜ |
| 4 | Click NBA filter | Only NBA games | ⬜ |
| 5 | Click game | Navigate to builder | ⬜ |

---

## W6: Session Expiry
**Workflow**: Token expiration handling

| Step | Action | Expected Result | Status |
|------|--------|-----------------|--------|
| 1 | Login | Token stored | ⬜ |
| 2 | Use app normally | Works for 15 min | ⬜ |
| 3 | Wait 15+ min | Token expires | ⬜ |
| 4 | Click any action | API returns 401 | ⬜ |
| 5 | App behavior | Redirect to login | ⬜ |
| 6 | Login again | Back to previous page | ⬜ |

---

## W7: Error Recovery
**Workflow**: Handle failures gracefully

| Step | Action | Expected Result | Status |
|------|--------|-----------------|--------|
| 1 | Disconnect network | WiFi off | ⬜ |
| 2 | Load dashboard | Shows error/empty state | ⬜ |
| 3 | Click retry | Attempts reload | ⬜ |
| 4 | Reconnect network | Data loads | ⬜ |
| 5 | Builder: markets fail | Error message shown | ⬜ |
| 6 | Builder: retry | Markets reload | ⬜ |
| 7 | Analyze fails | Error shown, legs preserved | ⬜ |
| 8 | Retry analyze | Second attempt | ⬜ |

---

## W8: Mobile Complete Flow
**Workflow**: Full flow on mobile viewport

| Step | Action | Expected Result | Status |
|------|--------|-----------------|--------|
| 1 | DevTools → iPhone 12 | Mobile viewport | ⬜ |
| 2 | Login | Form usable, no zoom | ⬜ |
| 3 | Dashboard | Cards scrollable | ⬜ |
| 4 | Click game | Navigate | ⬜ |
| 5 | Builder tabs | Swipe/tap works | ⬜ |
| 6 | Add 3 legs | All tappable | ⬜ |
| 7 | Enter wager | Keyboard numeric | ⬜ |
| 8 | Analyze | Results visible | ⬜ |
| 9 | Submit | Success | ⬜ |
| 10 | History | Bet visible | ⬜ |

---

# PART 3: TEST EXECUTION LOG

## Date: ___________
## Tester: ___________
## Environment: ___________

### Component Results
| Category | Pass | Fail | Blocked | Notes |
|----------|------|------|---------|-------|
| Navigation | | | | |
| Auth | | | | |
| Game Cards | | | | |
| Market Tabs | | | | |
| Bet Buttons | | | | |
| Parlay Slip | | | | |
| Wager Input | | | | |
| Payout Display | | | | |
| Analyze | | | | |
| Submit | | | | |

### Workflow Results
| Workflow | Status | Issues |
|----------|--------|--------|
| W1: Registration | ⬜ | |
| W2: Login | ⬜ | |
| W3: Build Parlay | ⬜ | |
| W4: Submit Bet | ⬜ | |
| W5: Browse/Search | ⬜ | |
| W6: Session Expiry | ⬜ | |
| W7: Error Recovery | ⬜ | |
| W8: Mobile Flow | ⬜ | |

### Critical Issues Found
1. 
2. 
3. 

### Recommendation
⬜ ALL TESTS PASS - Ready for production  
⬜ MINOR ISSUES - Fix then release  
⬜ MAJOR ISSUES - Block release

---

## Quick Reference: Test URLs
```
Local: http://localhost:8000/app?screen=auth
Staging: https://staging.example.com/app?screen=auth
Prod: https://dna-production-cb47.up.railway.app/app?screen=auth
```

## Console Error Check
```javascript
// Run in console to check for errors
console.clear();
// Perform action
// Check: console.errors.length === 0
```

## Network Check
```
DevTools → Network → XHR
- Look for 200/201 responses
- No 500 errors
- Response times < 2s
```
