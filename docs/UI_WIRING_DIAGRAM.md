# DNA Bet Engine - UI to Backend Wiring Diagram
## S16: Data Requirements by Screen

**Date:** 2026-02-08  
**Status:** Frontend complete, backend wiring in progress

---

## SCREEN 1: LANDING PAGE
**URL:** `/app?screen=landing`  
**File:** `landing.html` (337 lines)

### Static Content (No API needed)
| Element | Type | Content | Status |
|---------|------|---------|--------|
| Header logo | Static | DNA icon + "DNA BET" | ✅ Hardcoded |
| Hero title | Static | "PARLAY INTELLIGENCE" | ✅ Hardcoded |
| Hero subtitle | Static | Marketing copy | ✅ Hardcoded |
| DNA Helix | CSS Animation | 3D rotating helix | ✅ CSS only |
| How It Works | Static | 3 steps | ✅ Hardcoded |
| Core Protocols | Static | 4 feature cards | ✅ Hardcoded |
| Pricing Tiers | Static | Recruit/Elite/Exome | ✅ Hardcoded |
| Footer | Static | Links, social | ✅ Hardcoded |

### CTA Actions
| Button | Action | Destination |
|--------|--------|-------------|
| "Get Started" | Navigation | `/app?screen=dashboard` |
| "Select Tier" | Navigation | (Future: Stripe checkout) |
| Menu button | Navigation | (Future: Mobile menu) |

**Backend Needs:** NONE (fully static)

---

## SCREEN 2: DASHBOARD
**URL:** `/app?screen=dashboard`  
**File:** `dashboard.html` (254 lines)

### Data Requirements

#### 1. Header Section
```
┌─────────────────────────────────────┐
│ DNA Engine        🔔 👤            │
│ DASHBOARD                           │
└─────────────────────────────────────┘
```
| Element | Data Field | API Endpoint | Mock Status |
|---------|-----------|--------------|-------------|
| Notification bell | unread_count | `GET /api/notifications` | ❌ Not in mock |
| User avatar | avatar_url | `GET /api/user/me` | ❌ Static emoji |

#### 2. Balance Card
```
┌─────────────────────────────────────┐
│ Total Balance    [Pro Tier]         │
│ $12,840.50         📈 +12.4%        │
│                    this week        │
└─────────────────────────────────────┘
```
| Element | Data Field | API Endpoint | Mock Status |
|---------|-----------|--------------|-------------|
| Balance amount | balance | `GET /api/user/me` | ✅ MOCK_USER.balance |
| User tier | tier | `GET /api/user/me` | ✅ MOCK_USER.tier |
| Weekly change | weekly_change_pct | `GET /api/user/stats` | ❌ Hardcoded +12.4% |

#### 3. Quick Stats Grid
```
┌──────────────┐ ┌──────────────┐
│ Win Rate     │ │ Total Parlays│
│ 68.5%        │ │ 142 Lifetime │
└──────────────┘ └──────────────┘
```
| Element | Data Field | API Endpoint | Mock Status |
|---------|-----------|--------------|-------------|
| Win rate | win_rate | `GET /api/user/me` | ✅ MOCK_USER.win_rate |
| Total bets | total_bets | `GET /api/user/me` | ✅ MOCK_USER.total_bets |

#### 4. Active Protocols (Bets List)
```
┌─────────────────────────────────────┐
│ 🔴 ACTIVE PROTOCOLS    View All     │
├─────────────────────────────────────┤
│ 🏀 Lakers vs Heat     [LIVE]  +240  │
│    NBA • 4th Quarter                │
│ ─────────────────────────────────── │
│ Wager: $50.00    Est: $170.00       │
│ Progress bar [████████░░] 85%       │
├─────────────────────────────────────┤
│ 🏈 Chiefs vs Bills           -110   │
│    NFL • Starts in 2h               │
│ ─────────────────────────────────── │
│ [Total Points O 48.5]    Wager $100 │
└─────────────────────────────────────┘
```
| Element | Data Field | API Endpoint | Mock Status |
|---------|-----------|--------------|-------------|
| Bet cards array | bets[] | `GET /api/user/bets?status=active` | ✅ MOCK_USER.active_bets |
| Sport icon | sport | Join with games table | ❌ Hardcoded emoji |
| Teams | home_team, away_team | `GET /api/games/{id}` | ❌ game_id only |
| Live status | status | `GET /api/games/{id}/status` | ❌ Hardcoded |
| Odds | odds | From bet or odds table | ✅ In bet object |
| Wager | wager | From bet object | ✅ In bet object |
| Payout | potential_payout | From bet object | ✅ In bet object |
| Progress bar | completion_pct | Calculated from legs | ❌ Hardcoded 85% |

#### 5. Bottom Navigation
```
┌────────┬────────┬────────┬────────┐
│  🏠    │   🔍   │   📊   │   👤   │
│ Home   │ Browse │Activity│Profile │
└────────┴────────┴────────┴────────┘
```
| Element | Action | Route |
|---------|--------|-------|
| Home | Navigate | `/app?screen=dashboard` (active) |
| Browse | Navigate | `/app?screen=browse` |
| Activity | Navigate | (Future: `/app?screen=activity`) |
| Profile | Navigate | (Future: `/app?screen=profile`) |

**Backend Needs Summary:**
- ✅ User profile endpoint (exists)
- ✅ User bets endpoint (exists)
- ❌ Notifications endpoint (not in mock)
- ❌ Real-time game status updates
- ❌ Weekly stats calculation

---

## SCREEN 3: BROWSE (Bet Placement)
**URL:** `/app?screen=browse`  
**File:** `browse.html` (316 lines)

### Data Requirements

#### 1. Sport Selector Grid
```
┌────────┬────────┬────────┐
│   🏀   │   🏈   │   ⚾   │
│  NBA   │  NFL   │  MLB  │
├────────┼────────┼────────┤
│   🏒   │   ⚽   │   🥊   │
│  NHL   │ SOCCER │  MMA  │
└────────┴────────┴────────┘
```
| Element | Data Field | API Endpoint | Mock Status |
|---------|-----------|--------------|-------------|
| Sport list | sports[] | `GET /api/sports` | ✅ SPORTS array |
| Icon | icon | In sports table | ✅ Hardcoded emoji |
| Active state | active | In sports table | ✅ In SPORTS array |
| Selection | onClick | Filter games | ✅ Client-side |

#### 2. Featured Events
```
┌─────────────────────────────────────┐
│ FEATURED TARGETS          View All >│
├─────────────────────────────────────┤
│ 🏀 Regular Season  [LIVE] Q3 8:42   │
│                                     │
│    LAKERS        VS      WARRIORS   │
│    88                      82       │
│                                     │
│ [Spread -4.5] [Total O224] [-190]   │
│                                     │
│ [SELECT EVENT TARGET →]             │
├─────────────────────────────────────┤
│ 🏀 NBA • Tomorrow         20:30 EST │
│    CELTICS       VS         HEAT    │
│                                     │
│ [Spread -2.5] [Total O212] [-145]   │
│                                     │
│ [VIEW MARKETS]                      │
└─────────────────────────────────────┘
```
| Element | Data Field | API Endpoint | Mock Status |
|---------|-----------|--------------|-------------|
| Game cards | games[] | `GET /api/games?status=live,upcoming` | ✅ MOCK_GAMES |
| Sport | sport | In game object | ✅ In game object |
| Home team | home_team | In game object | ✅ In game object |
| Away team | away_team | In game object | ✅ In game object |
| Scores | home_score, away_score | In game object | ✅ In game object |
| Time/Quarter | time_remaining, quarter | In game object | ✅ In game object |
| Odds buttons | spread, total, ml | `GET /api/odds/{game_id}` | ✅ MOCK_ODDS |
| Quick select | onClick | Add to slip | ✅ Client-side |

#### 3. AI Insight Banner
```
┌─────────────────────────────────────┐
│ AI INSIGHT                          │
│ Lakers spread has 82% probability   │
│                          [⚡]        │
└─────────────────────────────────────┘
```
| Element | Data Field | API Endpoint | Mock Status |
|---------|-----------|--------------|-------------|
| Insight text | insight | `GET /api/insights/featured` | ❌ Hardcoded |
| Probability | confidence_pct | In insight object | ❌ Hardcoded 82% |

**Backend Needs Summary:**
- ✅ Sports list endpoint (exists)
- ✅ Games endpoint (exists)
- ✅ Odds endpoint (exists)
- ❌ AI insights endpoint (not in mock)
- ❌ Real-time score updates

---

## SCREEN 4: BUILDER (Parlay Builder)
**URL:** `/app?screen=builder`  
**File:** `builder.html` (308 lines)

### Data Requirements

#### 1. Game Matchup Header
```
┌─────────────────────────────────────┐
│ ← BUILD PARLAY            ⋯         │
├─────────────────────────────────────┤
│ NBA • Tonight 7:30 PM  [Live Odds]  │
│                                     │
│    💜 LAL              💛 GSW       │
│    Lakers             Warriors      │
└─────────────────────────────────────┘
```
| Element | Data Field | API Endpoint | Mock Status |
|---------|-----------|--------------|-------------|
| Back button | onClick | Navigate back | ✅ Client-side |
| Game info | sport, start_time | `GET /api/games/{id}` | ✅ In mock |
| Teams | home_team, away_team | `GET /api/games/{id}` | ✅ In mock |
| Live indicator | status | `GET /api/games/{id}` | ✅ In mock |

#### 2. Market Tabs
```
[MAIN LINES] [PLAYER PROPS] [QUARTERS] [HALVES]
```
| Element | Data Field | API Endpoint | Mock Status |
|---------|-----------|--------------|-------------|
| Tab list | markets[] | Static config | ✅ Hardcoded |
| Active tab | selected_market | Client state | ✅ Client-side |

#### 3. Odds Grid
```
┌─────────────────────────────────────┐
│ Team    Spread    Total    Money    │
├─────────────────────────────────────┤
│ LAKERS  [-4.5     [O 224    [-190   │
│         -110]      ]              ]  │
├─────────────────────────────────────┤
│WARRIORS [+4.5     [U 224    [+158   │
│         -110]      ]              ]  │
└─────────────────────────────────────┘
```
| Element | Data Field | API Endpoint | Mock Status |
|---------|-----------|--------------|-------------|
| Spread odds | spread.home, spread.away | `GET /api/odds/{game_id}` | ✅ MOCK_ODDS |
| Total odds | total.over, total.under | `GET /api/odds/{game_id}` | ✅ MOCK_ODDS |
| Moneyline | ml.home, ml.away | `GET /api/odds/{game_id}` | ✅ MOCK_ODDS |
| Player props | player_props[] | `GET /api/odds/{game_id}` | ✅ MOCK_ODDS |
| Selection | onClick | Add to slip | ✅ Client-side |

#### 4. Parlay Slip
```
┌─────────────────────────────────────┐
│ PARLAY SLIP [2]          Clear All  │
├─────────────────────────────────────┤
│ │ Spread │ Lakers vs Warriors   ✕  │
│ │          Lakers -4.5             │
│ │          Main Lines        -110  │
├─────────────────────────────────────┤
│ │Player P│ Lakers vs Warriors   ✕  │
│ │          L. James O 25.5         │
│ │          Player Props      -115  │
└─────────────────────────────────────┘
```
| Element | Data Field | Source | Mock Status |
|---------|-----------|--------|-------------|
| Leg count | legs.length | Client state | ✅ Client-side |
| Leg items | legs[] | Client state | ✅ Client-side |
| Market type | market | From selection | ✅ Client-side |
| Selection details | selection, line | From selection | ✅ Client-side |
| Odds | odds | From selection | ✅ Client-side |
| Remove leg | onClick | Remove from state | ✅ Client-side |
| Clear all | onClick | Clear state | ✅ Client-side |

#### 5. Wager Summary
```
┌─────────────────────────────────────┐
│ Total Odds                 +264     │
├─────────────────────────────────────┤
│ WAGER AMOUNT              [MAX]     │
│ $ 50.00                             │
├─────────────────────────────────────┤
│ Est. Payout            $182.00      │
│                        Incl. Wager  │
└─────────────────────────────────────┘
```
| Element | Data Field | Calculation | Mock Status |
|---------|-----------|-------------|-------------|
| Total odds | total_odds | Calculate from legs | ✅ Client-side |
| Wager input | wager | User input | ✅ Client-side |
| Max button | max_wager | User balance | ❌ Not wired |
| Est. payout | payout | wager × odds | ✅ Client-side |

#### 6. Place Bet Button
```
┌─────────────────────────────────────┐
│     [PLACE BET →]                   │
└─────────────────────────────────────┘
```
| Element | Action | API Endpoint | Mock Status |
|---------|--------|--------------|-------------|
| Place bet | POST | `/app/evaluate` | ✅ Works with text |
| With structured legs | POST | `/app/evaluate` with legs[] | ⚠️ Needs testing |

**Backend Needs Summary:**
- ✅ Game details endpoint (exists)
- ✅ Odds endpoint (exists)
- ⚠️ Evaluate endpoint accepts legs (exists, needs testing)
- ❌ SGP (Same Game Parlay) detection logic
- ❌ Max wager validation
- ❌ Bet placement/tracking

---

## DATA SCHEMA GAPS

### What Exists (Mock Data)
```
✅ SPORTS[]          - Static sport list
✅ MOCK_GAMES{}      - Games by sport
✅ MOCK_ODDS{}       - Odds by game_id
✅ MOCK_USER{}       - User profile & bets
```

### What's Missing (Need Real Backend)
```
❌ NOTIFICATIONS     - Unread count, messages
❌ REAL-TIME SCORES  - Live game updates (WebSocket/polling)
❌ AI INSIGHTS       - Probability calculations
❌ WEEKLY STATS      - Time-series aggregations
❌ BET HISTORY       - Completed/settled bets
❌ WALLET/BALANCE    - Real financial tracking
❌ USER AUTH         - Login/signup flow
❌ SGP LOGIC         - Same-game parlay detection
❌ BET PLACEMENT     - Record bets to database
❌ ODDS PROVIDER     - Integration with real odds API
```

---

## PRIORITY WIRING ORDER

### Phase 1: Browse → Builder Flow (This Week)
1. Wire sport selector to filter games
2. Wire game cards to show real mock data
3. Wire odds grid to fetch from `/api/mock/odds/{game_id}`
4. Wire add-to-slip functionality
5. Wire parlay calculation
6. Test place bet → evaluation flow

### Phase 2: Dashboard Live Data (Next Week)
1. Wire balance from user endpoint
2. Wire active bets list
3. Add real-time score polling
4. Add bet progress tracking

### Phase 3: Real Backend (Future)
1. Replace mock data with database
2. Add user authentication
3. Integrate real odds API
4. Add wallet/payment flow
5. Add AI insights engine

---

## NEXT ACTIONS

**Choose one:**

**A)** Wire browse screen to fetch live games/odds from mock API
**B)** Wire builder slip to calculate parlays and submit to `/app/evaluate`
**C)** Add real-time updates to dashboard (polling)
**D)** Something else?
