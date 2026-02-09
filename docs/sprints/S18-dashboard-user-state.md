# Sprint S18: Dashboard + User State

**Date:** 2026-02-09  
**Goal:** Complete user authentication + dashboard + bet history  
**Estimate:** 4-6 hours  
**Constraint:** NO changes to scoring/evaluation logic

---

## Tickets

### S18-A: Create Database Models ⏳
**Priority:** P0 (blocker)  
**Est:** 30 min

**Problem:** `app/models.py` doesn't exist but is imported by:
- `app/services/auth.py`
- `app/services/stats.py`
- `app/routers/dashboard.py`

**Tasks:**
- [ ] Create `app/models.py` with SQLAlchemy models:
  - User (id, email, password_hash, name, tier, balance, created_at, last_login)
  - Bet (id, user_id, input_text, legs, wager, total_odds, potential_payout, verdict, confidence, fragility, status, actual_payout, created_at, settled_at)
- [ ] Add `get_session()` function for DB access
- [ ] Initialize database tables

**Files:**
- CREATE: `app/models.py`

---

### S18-B: Wire Auth Router to Main App
**Priority:** P0  
**Est:** 20 min

**Tasks:**
- [ ] Include auth router in main.py
- [ ] Include dashboard router in main.py
- [ ] Add `/new?screen=auth` route

**Files:**
- EDIT: `app/main.py`
- EDIT: `app/routers/web.py`

---

### S18-C: Dashboard Data Integration
**Priority:** P1  
**Est:** 45 min

**Tasks:**
- [ ] Wire dashboard.html to fetch from `/api/dashboard`
- [ ] Display real user data (name, tier, stats)
- [ ] Show recent bets from history
- [ ] Handle loading/error states

**Files:**
- EDIT: `app/templates/screens/dashboard.html`

---

### S18-D: Bet History Persistence
**Priority:** P1  
**Est:** 45 min

**Tasks:**
- [ ] After DNA analysis, save bet to user's history
- [ ] Add history endpoint `/api/bets`
- [ ] Create history screen or add to dashboard

**Files:**
- EDIT: `app/routers/web.py` or new `app/routers/bets.py`
- EDIT: DNA results handling in builder

---

### S18-E: Auth Flow Polish
**Priority:** P2  
**Est:** 30 min

**Tasks:**
- [ ] Add auth token header to API requests
- [ ] Redirect to auth if not logged in (on protected screens)
- [ ] Logout functionality
- [ ] Session persistence across refreshes

**Files:**
- EDIT: `app/templates/screens/*.html` (add auth helpers)

---

### S18-F: Test E2E Flow
**Priority:** P0  
**Est:** 30 min

**Tasks:**
- [ ] Register → Dashboard → Browse → Builder → Analyze → History
- [ ] Verify bet saved to database
- [ ] Test login after logout
- [ ] Check stats calculation

---

## Success Criteria

1. ✅ User can register/login
2. ✅ Dashboard shows real user data
3. ✅ Bets are saved to history
4. ✅ Win rate / stats calculate correctly
5. ✅ No regressions to DNA analysis

---

## Notes

- Database: SQLite at `data/dna.db`
- Auth: JWT tokens stored in sessionStorage
- Tier gating: Deferred (BETTER/BEST features not implemented yet)
