# Sprint: How It Works - Feature Implementation

## Sprint Goal
Implement the 3 core features described in the "How It Works" landing page section.

---

## Feature 1: Input DNA Data
**User Story:** As a user, I want to input my betting history and preferences so the engine can learn my style.

**Current State:** ❌ Not Implemented
**Priority:** HIGH

### Acceptance Criteria
- [ ] User can input past bets (manual entry or import)
- [ ] Preference vectors (risk tolerance, sport preferences, bet types)
- [ ] Betting history stored per user account
- [ ] Data feeds into recommendation engine

### Technical Tasks
- [ ] Create `user_preferences` table or extend User model
- [ ] Build betting history import UI
- [ ] Create preference onboarding flow
- [ ] Store preference vectors (JSON: risk_level, preferred_sports, max_legs, etc.)

### UI/UX
- Onboarding wizard after first login
- Settings page to adjust preferences
- Import from CSV or manual entry

---

## Feature 2: Evolutionary Search
**User Story:** As a user, I want the system to analyze millions of outcomes to find optimal strategies for me.

**Current State:** ⚠️ Partial (Basic analysis exists)
**Priority:** HIGH

### Acceptance Criteria
- [ ] Parlay analysis generates multiple scenarios
- [ ] Correlation detection between legs
- [ ] Risk assessment based on user profile
- [ ] Strategy suggestions based on user's "DNA"

### Technical Tasks
- [ ] Extend DNA analysis with more signals
- [ ] Monte Carlo simulation for parlay outcomes
- [ ] Machine learning model for user preferences
- [ ] Correlation matrix for common bet combinations

### UI/UX
- Rich analysis display (not just 1 number)
- Confidence meter with visual
- Risk breakdown (low/medium/high)
- Suggested improvements section

---

## Feature 3: Optimal Execution
**User Story:** As a user, I want real-time alerts for bets that match my success profile.

**Current State:** ❌ Not Implemented
**Priority:** MEDIUM

### Acceptance Criteria
- [ ] Push notifications for recommended bets
- [ ] Alert when odds shift favorably
- [ ] Daily/weekly digest of opportunities
- [ ] Smart timing suggestions (best time to place)

### Technical Tasks
- [ ] Push notification service (web push or email)
- [ ] Background job to scan for opportunities
- [ ] Odds change detection
- [ ] Alert preferences (frequency, channels)

### UI/UX
- Notification settings page
- Alert history
- One-tap bet from alert
- Notification center in app

---

## Feature 4: CORE PROTOCOLS (Visible on landing)
**User Story:** As a user, I want to see available betting protocols/strategies.

**Current State:** ❌ Not Implemented
**Priority:** MEDIUM

### Acceptance Criteria
- [ ] Display available protocols on landing page
- [ ] Each protocol has description and example
- [ ] Protocol selection in builder
- [ ] Protocol-specific analytics

### Technical Tasks
- [ ] Define protocol schema (parlay types, strategies)
- [ ] Create protocol database table
- [ ] Protocol recommendation engine
- [ ] Protocol performance tracking

### UI/UX
- Protocol cards on landing page
- Protocol selector in browse
- Protocol badges on active bets
- Protocol performance dashboard

---

## Additional Missing Features (From Previous Feedback)

### Suggested Parlays
**Status:** ❌ Not Implemented
**Priority:** MEDIUM
- Show "Popular Parlays" or "Trending" in builder
- Based on other users or correlation data

### Team Logos
**Status:** ❌ Not Implemented
**Priority:** LOW
- Add team logo URLs to mock provider
- Display logos in game cards

### Rich Analytics (Truth + Emotion)
**Status:** ⚠️ Partial
**Priority:** HIGH
- Current: Just confidence number
- Needed: Multiple insights, risk assessment, emotional framing
- Reference S2-FND philosophy

### Money Simulation Accuracy
**Status:** ⚠️ Partial (Balance tracking added, settlement needed)
**Priority:** HIGH
- Bet creation deducts balance ✅
- Win/loss settlement adds payout ⏳
- Transaction history ⏳

---

## Sprint Planning

### Sprint Duration: 2 weeks
### Team Size: 1 (you + me)

### Week 1 Focus
1. **Input DNA Data** - Preference storage + onboarding
2. **Rich Analytics** - Better analysis display
3. **Money Settlement** - Win/loss payout logic

### Week 2 Focus
4. **Evolutionary Search** - ML/correlation improvements
5. **Optimal Execution** - Notification framework
6. **Core Protocols** - Landing page content + selection

---

## Definition of Done
- [ ] All 3 "How It Works" features functional
- [ ] Landing page accurately reflects implemented features
- [ ] Each feature has basic UI and backend
- [ ] Tests passing
- [ ] Deployed to production

---

Last Updated: 2026-02-10
