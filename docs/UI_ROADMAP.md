# DNA Bet Engine - UI Architecture Roadmap
## Target State: Neon Dark Theme Interface

**Date:** 2026-02-08  
**Current Version:** v0.2.1 (S15 Messaging UI)  
**Target Version:** v1.0 (Full Parlay Intelligence Platform)

---

## TARGET STATE OVERVIEW

The 4 HTML mockups represent the complete user journey:

```
┌─────────────────┐     ┌─────────────────┐     ┌─────────────────┐     ┌─────────────────┐
│   1. LANDING    │────▶│  2. DASHBOARD   │────▶│ 3. BET PLACEMENT│────▶│ 4. PARLAY BUILD │
│  (Marketing)    │     │  (Home/Hub)     │     │ (Game Browser)  │     │  (Leg Builder)  │
└─────────────────┘     └─────────────────┘     └─────────────────┘     └─────────────────┘
                                                                               │
                                                                               ▼
                                                                        ┌─────────────────┐
                                                                        │  ANALYSIS/EVAL  │
                                                                        │  (Existing)     │
                                                                        └─────────────────┘
```

### Screen 1: Landing Page
**Purpose:** Marketing, pricing, signup
**Key Elements:**
- DNA helix animation (brand identity)
- "Parlay Intelligence" hero
- Pricing tiers: Recruit ($49), Elite ($99), Exome ($249)
- "Get Started" CTA → Dashboard

### Screen 2: Dashboard
**Purpose:** User hub, quick stats, active bets
**Key Elements:**
- Balance display ($12,840.50)
- Win rate (68.5%), Total parlays (142)
- Active protocols (live bets with progress)
- Bottom navigation (Home, Browse, Activity, Profile)
- "Start New Bet Protocol" CTA → Bet Placement

### Screen 3: Bet Placement
**Purpose:** Browse games, quick bets
**Key Elements:**
- Sport selector grid (NBA, NFL, MLB, NHL, Soccer, MMA)
- Featured events list
- Live game cards with scores
- Quick odds buttons (Spread, Total, Moneyline)
- "Select Event Target" → Parlay Builder

### Screen 4: Parlay Builder
**Purpose:** Build multi-leg parlays
**Key Elements:**
- Game matchup header
- Market tabs (Main Lines, Player Props, Quarters, Halves)
- Odds grid (Spread/Total/Moneyline per team)
- Parlay slip (add/remove legs)
- Wager input, total odds, est. payout
- "Place Bet" → Analysis → Results

---

## CURRENT STATE vs TARGET

| Component | Current (S15) | Target | Gap |
|-----------|---------------|--------|-----|
| **Theme** | Light iOS messaging | Dark neon cyber | CSS overhaul |
| **Input** | Chat text field | Visual parlay builder | New UI paradigm |
| **Data** | Text-only | Structured games/odds | Database + APIs |
| **Navigation** | Single screen | 4-screen flow | Routing + state |
| **Analysis** | Working | Working (keep) | ✅ No change needed |

---

## DATA ARCHITECTURE (Target)

### Core Entities

```
┌─────────────┐     ┌─────────────┐     ┌─────────────┐     ┌─────────────┐
│    SPORT    │────▶│    GAME     │────▶│    ODDS     │────▶│     BET     │
│   (League)  │     │   (Matchup) │     │  (Markets)  │     │  (Parlay)   │
└─────────────┘     └─────────────┘     └─────────────┘     └─────────────┘
       │                   │                   │                   │
       ▼                   ▼                   ▼                   ▼
   name: NBA          game_id: 12345     market: spread       user_id: 789
   icon: 🏀           home: Lakers       line: -4.5          legs: [leg1, leg2]
                     away: Warriors     odds: -110           wager: 50.00
                     time: 7:30 PM                          status: active
                     status: live                           payout: 182.00
```

### Data Flow (Target)

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                              DATA SOURCES                                    │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐        │
│  │ Odds API    │  │ Live Scores │  │ User History│  │ DNA Engine  │        │
│  │ (Provider)  │  │ (Sports API)│  │ (Database)  │  │ (Internal)  │        │
│  └──────┬──────┘  └──────┬──────┘  └──────┬──────┘  └──────┬──────┘        │
│         │                │                │                │                │
│         └────────────────┴────────────────┴────────────────┘                │
│                                    │                                         │
│                                    ▼                                         │
│                         ┌─────────────────┐                                  │
│                         │  DNA Backend    │                                  │
│                         │  (FastAPI)      │                                  │
│                         └────────┬────────┘                                  │
│                                  │                                          │
│                    ┌─────────────┼─────────────┐                            │
│                    ▼             ▼             ▼                            │
│              ┌──────────┐ ┌──────────┐ ┌──────────┐                        │
│              │  Games   │ │  Odds    │ │  Bets    │                        │
│              │  API     │ │  API     │ │  API     │                        │
│              └────┬─────┘ └────┬─────┘ └────┬─────┘                        │
│                   └─────────────┴─────────────┘                             │
│                                 │                                           │
│                                 ▼                                           │
│                         ┌─────────────────┐                                 │
│                         │   Frontend UI   │                                 │
│                         │  (4 Screens)    │                                 │
│                         └─────────────────┘                                 │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## IMPLEMENTATION ROADMAP

### Phase 1: Foundation (Week 1-2)
**Goal:** Static UI shell with routing

**Tasks:**
- [ ] Convert 4 HTML mockups to Jinja2 templates
- [ ] Implement CSS design system (neon theme, fonts, animations)
- [ ] Add client-side routing (or server-side tab switching)
- [ ] DNA helix animation (landing page)
- [ ] Bottom navigation component

**Result:** Clickable UI prototype with no live data

---

### Phase 2: Data Layer (Week 3-4)
**Goal:** Games and odds infrastructure

**Database:**
```sql
-- Sports table
CREATE TABLE sports (
    id SERIAL PRIMARY KEY,
    name VARCHAR(50),        -- 'NBA', 'NFL', etc.
    icon VARCHAR(10),        -- emoji or icon name
    active BOOLEAN DEFAULT true
);

-- Games table
CREATE TABLE games (
    id SERIAL PRIMARY KEY,
    sport_id INTEGER REFERENCES sports(id),
    home_team VARCHAR(100),
    away_team VARCHAR(100),
    home_score INTEGER DEFAULT 0,
    away_score INTEGER DEFAULT 0,
    start_time TIMESTAMP,
    status VARCHAR(20),      -- 'upcoming', 'live', 'finished'
    created_at TIMESTAMP DEFAULT NOW()
);

-- Odds table (versioned)
CREATE TABLE odds (
    id SERIAL PRIMARY KEY,
    game_id INTEGER REFERENCES games(id),
    market VARCHAR(50),      -- 'spread', 'total', 'moneyline', 'player_prop'
    selection VARCHAR(100),  -- 'lakers', 'over', 'lebron_points'
    line DECIMAL(10,2),      -- -4.5, 220.5, etc.
    odds INTEGER,            -- -110, +150, etc.
    timestamp TIMESTAMP DEFAULT NOW()
);
```

**API Endpoints:**
- `GET /api/sports` — List sports
- `GET /api/games?sport={id}&status={status}` — List games
- `GET /api/odds/{game_id}` — Get odds for game
- `POST /api/slip/calculate` — Calculate parlay odds

**Data Sources:**
- Option A: Mock data (hardcoded games/odds)
- Option B: Odds API integration (The Odds API, etc.)
- Option C: Manual admin entry

**Result:** Working game browser with real or mock data

---

### Phase 3: Parlay Builder (Week 5-6)
**Goal:** Functional leg builder

**Frontend:**
- [ ] Market selection grid (spread/total/moneyline)
- [ ] Add to slip functionality
- [ ] Slip panel with delete buttons
- [ ] Real-time odds calculation
- [ ] Wager input with payout preview

**Backend:**
- [ ] Parlay odds calculation logic
- [ ] Leg validation (no conflicting bets)

**Integration:**
- [ ] "Place Bet" → `/app/evaluate` with legs array

**Result:** Users can build and analyze parlays visually

---

### Phase 4: Dashboard & User State (Week 7-8)
**Goal:** Personalized experience

**Features:**
- [ ] User authentication
- [ ] Balance/wallet system
- [ ] Active bets tracking
- [ ] Bet history
- [ ] Win rate calculation

**Database:**
```sql
-- Users table
CREATE TABLE users (
    id SERIAL PRIMARY KEY,
    email VARCHAR(255) UNIQUE,
    password_hash VARCHAR(255),
    balance DECIMAL(10,2) DEFAULT 0,
    created_at TIMESTAMP DEFAULT NOW()
);

-- Bets table
CREATE TABLE bets (
    id SERIAL PRIMARY KEY,
    user_id INTEGER REFERENCES users(id),
    legs JSONB,              -- Array of leg objects
    wager DECIMAL(10,2),
    total_odds INTEGER,
    potential_payout DECIMAL(10,2),
    status VARCHAR(20),      -- 'pending', 'won', 'lost', 'active'
    created_at TIMESTAMP DEFAULT NOW(),
    settled_at TIMESTAMP
);
```

**Result:** Full user accounts with history

---

### Phase 5: Polish & Real-time (Week 9-10)
**Goal:** Production-ready experience

**Features:**
- [ ] Live score updates (WebSocket or polling)
- [ ] Odds movement indicators
- [ ] Push notifications for bet outcomes
- [ ] Responsive design refinement
- [ ] Loading states and error handling
- [ ] Onboarding flow

**Result:** v1.0 release

---

## CURRENT SYSTEM INTEGRATION

### What Stays (No Changes)
- ✅ DNA evaluation engine (`/app/evaluate`)
- ✅ OCR image processing (`/evaluate/image`)
- ✅ Analysis algorithms
- ✅ Session tracking

### What Gets Wrapped
```
Current: Text → Evaluate → Results
          ↓
Target:  Builder → Legs Array → Evaluate → Results
                 ↓
         Visual selection replaces text input
         (But same backend!)
```

### API Compatibility
The existing `/app/evaluate` endpoint already accepts a `legs` parameter:

```python
# Current request (text)
{ "input": "Lakers -4.5 + LeBron O25.5", "tier": "good" }

# Target request (structured)
{
  "input": "Lakers -4.5 + LeBron O25.5",
  "tier": "good",
  "legs": [
    { "market": "spread", "team": "Lakers", "line": -4.5 },
    { "market": "player_prop", "player": "LeBron James", "prop": "points", "line": 25.5 }
  ]
}
```

**Key insight:** We can build the visual UI NOW and wire it to the existing backend. The structured legs array is already supported.

---

## PRIORITY DECISIONS NEEDED

### 1. Data Source for Games/Odds
| Option | Pros | Cons | Recommendation |
|--------|------|------|----------------|
| **A. Mock data** | Fast, free, controlled | Not real, stale quickly | ✅ Start here |
| **B. The Odds API** | Real odds, multiple sports | Paid ($29-499/mo), rate limits | Scale to this |
| **C. Manual entry** | Exact control | Time intensive | Niche use |

**Decision:** Start with Option A (mock), migrate to B when ready.

---

### 2. User Accounts
| Option | Pros | Cons | Recommendation |
|--------|------|------|----------------|
| **A. Skip for now** | Faster to market | No personalization, no history | ⚠️ Limit testing |
| **B. Simple auth** | User state, history | More complexity | ✅ Do this |
| **C. Full wallet** | Real betting flow | Regulatory, payment complexity | Later phase |

**Decision:** Option B (simple auth + history tracking, no real money)

---

### 3. Real-time Updates
| Option | Pros | Cons | Recommendation |
|--------|------|------|----------------|
| **A. Static** | Simple, cacheable | Stale data | ✅ MVP |
| **B. Polling** | Near real-time | API load, battery drain | Phase 2 |
| **C. WebSocket** | Instant, efficient | Complex infra | Scale |

**Decision:** Option A for MVP, B for v1.1

---

## SUCCESS CRITERIA

The target UI is successful when:

1. **User can:** Browse games by sport
2. **User can:** View live scores and odds
3. **User can:** Build parlays by clicking (not typing)
4. **User can:** See payout calculation in real-time
5. **User can:** Submit for DNA analysis
6. **User can:** View bet history and stats
7. **System:** Maintains current analysis quality
8. **System:** Supports the design aesthetic (neon dark)

---

## NEXT ACTIONS

**Immediate (Today):**
1. Confirm priority decisions (data source, auth, real-time)
2. Create git branch for new UI
3. Set up CSS design system

**This Week:**
1. Convert HTML mockups to templates
2. Implement routing between screens
3. Create mock data for games/odds

**Next Week:**
1. Wire parlay builder to existing `/app/evaluate`
2. Test end-to-end flow
3. Iterate on UX

---

**Document Status:** Living document — update as decisions are made and progress happens.
