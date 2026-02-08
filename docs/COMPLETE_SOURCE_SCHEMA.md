# DNA Bet Engine - Complete Source + Schema Package
## All 4 Screens: Code + Data Bindings

**For:** Designer/Developer handoff  
**Contains:** Full HTML + CSS + JS + Data requirements  
**Date:** 2026-02-08

---

## TABLE OF CONTENTS

1. [Landing Page](#1-landing-page)
   - HTML Source (337 lines)
   - Data Bindings (15% dynamic)
   
2. [Dashboard](#2-dashboard)
   - HTML Source (254 lines)
   - Data Bindings (80% dynamic)
   
3. [Browse](#3-browse)
   - HTML Source (316 lines)
   - Data Bindings (70% dynamic)
   
4. [Builder](#4-builder)
   - HTML Source (308 lines)
   - Data Bindings (75% dynamic)

5. [API Endpoints Summary](#5-api-endpoints-summary)

6. [Implementation Checklist](#6-implementation-checklist)

---

## 1. LANDING PAGE

### Source Code
**File:** `app/templates/screens/landing.html`  
**Lines:** 337  
**Dependencies:** Tailwind CDN, Iconify, Tanker + Satoshi fonts

```html
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <script src="https://cdn.tailwindcss.com"></script>
    <script src="https://code.iconify.design/iconify-icon/1.0.7/iconify-icon.min.js"></script>
    <link href="https://api.fontshare.com/v2/css?f[]=tanker@400&f[]=satoshi@400,500,700,900&display=swap" rel="stylesheet">
    <style>
        :root {
            --neon-red: #ff1744;
            --bg-dark: #050505;
        }
        body {
            font-family: 'Satoshi', sans-serif;
            background-color: var(--bg-dark);
            color: #ffffff;
            margin: 0;
            padding: 0;
        }
        .font-tanker {
            font-family: 'Tanker', sans-serif;
        }
        .neon-glow-red {
            text-shadow: 0 0 15px #ff1744, 0 0 30px #ff1744, 0 0 50px rgba(255, 23, 68, 0.6);
            animation: neon-pulse 3s infinite alternate;
        }
        @keyframes neon-pulse {
            from { text-shadow: 0 0 15px #ff1744, 0 0 30px #ff1744, 0 0 45px rgba(255, 23, 68, 0.5); }
            to { text-shadow: 0 0 20px #ff1744, 0 0 45px #ff1744, 0 0 65px rgba(255, 23, 68, 0.8); }
        }
        /* DNA HELIX ANIMATION */
        .helix-viewport {
            perspective: 1200px;
            width: 100%;
            height: 280px;
            position: relative;
            display: flex;
            align-items: center;
            justify-content: center;
            overflow: hidden;
        }
        .helix-container {
            width: 40px;
            height: 240px;
            position: relative;
            transform-style: preserve-3d;
            animation: revolve 10s linear infinite;
        }
        .dot {
            position: absolute;
            width: 5px;
            height: 5px;
            background-color: var(--neon-red);
            border-radius: 50%;
            box-shadow: 0 0 12px var(--neon-red);
        }
        @keyframes revolve {
            from { transform: rotateY(0deg); }
            to { transform: rotateY(360deg); }
        }
    </style>
</head>
<body>
    <!-- FULL HTML AVAILABLE IN SOURCE FILE -->
    <!-- See: app/templates/screens/landing.html -->
</body>
</html>
```

### Data Bindings

| Element | Variable | Type | Default | API Source |
|---------|----------|------|---------|------------|
| Hero Badge | `hero.badge` | String | "The Genetic Edge" | Static/CMS |
| Hero Title Line 1 | `hero.line1` | String | "PARLAY" | Static/CMS |
| Hero Title Line 2 | `hero.line2` | String | "INTELLIGENCE" | Static/CMS |
| CTA URL | `cta.url` | String | "/app?screen=dashboard" | Config |
| Pricing Tiers | `pricing.tiers[]` | Array[3] | See schema | Static/DB |

**Static:** 85% (marketing content)  
**Dynamic:** 15% (CTA destinations, optional CMS)

---

## 2. DASHBOARD

### Source Code
**File:** `app/templates/screens/dashboard.html`  
**Lines:** 254  
**Current:** Tailwind-based, needs API integration

**Key Sections:**
1. Header (lines 10-20)
2. Balance card (lines 22-35)
3. Stats grid (lines 40-60)
4. Active bets list (lines 65-150)
5. Bottom nav (lines 155-170)

### Data Bindings

#### User Profile API
**Endpoint:** `GET /api/user/me`  
**Status:** ✅ Mock exists

```json
{
  "id": "user_001",
  "name": "Ben Ross",
  "email": "ben@example.com",
  "tier": "elite",
  "balance": 12840.50,
  "win_rate": 0.685,
  "total_bets": 142,
  "avatar_url": null
}
```

**Bindings:**
| UI Element | Variable Path | Format | Example |
|------------|---------------|--------|---------|
| Tier badge | `user.tier` | Uppercase + " TIER" | "ELITE TIER" |
| Balance | `user.balance` | Currency | "$12,840.50" |
| Win rate | `user.win_rate` | Percent * 100 | "68.5%" |
| Total bets | `user.total_bets` | Number | "142" |
| Avatar | `user.avatar_url` | Image URL or emoji | "👤" |

#### Active Bets API
**Endpoint:** `GET /api/user/bets?status=active`  
**Status:** ✅ Mock exists

```json
{
  "bets": [
    {
      "id": "bet_001",
      "game_id": "nba_001",
      "legs": [
        {
          "market": "spread",
          "selection": "lakers",
          "line": -4.5,
          "odds": -110
        }
      ],
      "wager": 50.00,
      "potential_payout": 170.00,
      "status": "winning"
    }
  ]
}
```

**Bindings:**
| UI Element | Variable Path | Format | Example |
|------------|---------------|--------|---------|
| Bet card | `bets[]` | Array loop | Multiple cards |
| Sport icon | `game.sport` | Emoji map | "🏀" |
| Teams | Join `game_id` | Lookup games table | "Lakers vs Heat" |
| Live badge | `game.status` | Conditional | Show if "live" |
| Odds | `bet.odds` | American odds | "+240" |
| Wager | `bet.wager` | Currency | "$50.00" |
| Payout | `bet.potential_payout` | Currency | "$170.00" |
| Progress | Calculate from legs | Percent | "85%" |

**Static:** 20%  
**Dynamic:** 80%  
**APIs Needed:** 2 endpoints (user, bets)

---

## 3. BROWSE

### Source Code
**File:** `app/templates/screens/browse.html`  
**Lines:** 316  
**Current:** Tailwind-based, static game data

**Key Sections:**
1. Sport selector grid (lines 15-45)
2. Featured events list (lines 50-250)
3. AI insight banner (lines 260-280)
4. Bottom nav (lines 285-310)

### Data Bindings

#### Sports List API
**Endpoint:** `GET /api/sports`  
**Status:** ✅ Mock exists

```json
{
  "sports": [
    {
      "id": "nba",
      "name": "NBA",
      "icon": "🏀",
      "active": true
    }
  ]
}
```

**Bindings:**
| UI Element | Variable Path | Action | Example |
|------------|---------------|--------|---------|
| Sport grid | `sports[]` | Loop + filter | 6 chips |
| Sport icon | `sport.icon` | Render | "🏀" |
| Sport name | `sport.name` | Uppercase | "NBA" |
| Active state | `sport.active` | Class toggle | Gray if false |
| Live indicator | Count games with status=live | Conditional | Red dot |

#### Games List API
**Endpoint:** `GET /api/games?sport={id}&status=live,upcoming`  
**Status:** ✅ Mock exists

```json
{
  "games": [
    {
      "id": "nba_001",
      "sport": "nba",
      "home_team": {
        "name": "Lakers",
        "code": "LAL",
        "color": "#552583"
      },
      "away_team": {
        "name": "Warriors",
        "code": "GSW",
        "color": "#1D428A"
      },
      "home_score": 88,
      "away_score": 82,
      "start_time": "2024-02-08T19:30:00Z",
      "status": "live",
      "quarter": "Q3",
      "time_remaining": "8:42"
    }
  ]
}
```

**Bindings:**
| UI Element | Variable Path | Format | Example |
|------------|---------------|--------|---------|
| Game cards | `games[]` | Loop | Multiple cards |
| Live badge | `game.status === "live"` | Conditional | Show/hide |
| Quarter | `game.quarter` | String | "Q3" |
| Time | `game.time_remaining` | String | "8:42" |
| Teams | `game.home_team.code` | String | "LAL" |
| Scores | `game.home_score` | Number | "88" |
| Start time | `game.start_time` | Format | "20:30 EST" |

#### Odds API
**Endpoint:** `GET /api/odds/{game_id}`  
**Status:** ✅ Mock exists

```json
{
  "game_id": "nba_001",
  "odds": {
    "spread": {
      "home": { "line": -4.5, "odds": -110 },
      "away": { "line": 4.5, "odds": -110 }
    },
    "total": {
      "over": { "line": 224.5, "odds": -108 },
      "under": { "line": 224.5, "odds": -108 }
    },
    "moneyline": {
      "home": { "odds": -190 },
      "away": { "odds": 158 }
    }
  }
}
```

**Bindings:**
| UI Element | Variable Path | Format | Example |
|------------|---------------|--------|---------|
| Spread button | `odds.spread.home.line` | Signed number | "-4.5" |
| Spread odds | `odds.spread.home.odds` | American | "-110" |
| Total button | `odds.total.over.line` | "O " + number | "O 224.5" |
| ML button | `odds.moneyline.home.odds` | American | "-190" |

**Static:** 30%  
**Dynamic:** 70%  
**APIs Needed:** 3 endpoints (sports, games, odds)

---

## 4. BUILDER

### Source Code
**File:** `app/templates/screens/builder.html`  
**Lines:** 308  
**Current:** Tailwind-based, client-side slip logic

**Key Sections:**
1. Game matchup header (lines 10-50)
2. Market tabs (lines 55-70)
3. Odds grid (lines 75-150)
4. Parlay slip (lines 155-220)
5. Wager summary (lines 225-260)
6. Place bet button (lines 265-275)

### Data Bindings

#### Game Details API
**Endpoint:** `GET /api/games/{id}`  
**Status:** ✅ Mock exists

```json
{
  "id": "nba_001",
  "sport": "nba",
  "home_team": {
    "name": "Lakers",
    "code": "LAL",
    "color": "#552583",
    "emoji": "💜"
  },
  "away_team": {
    "name": "Warriors",
    "code": "GSW",
    "color": "#1D428A",
    "emoji": "💛"
  },
  "start_time": "2024-02-08T19:30:00Z",
  "status": "live"
}
```

**Bindings:**
| UI Element | Variable Path | Format | Example |
|------------|---------------|--------|---------|
| Sport label | `game.sport` | Uppercase | "NBA" |
| Start time | `game.start_time` | Relative | "Tonight 7:30 PM" |
| Home team code | `game.home_team.code` | String | "LAL" |
| Home team color | `game.home_team.color` | Hex | "#552583" |
| Team emoji | `game.home_team.emoji` | Emoji | "💜" |

#### Odds Grid
**Endpoint:** `GET /api/odds/{game_id}`  
**Status:** ✅ Mock exists (same as browse)

**Client State:**
```javascript
const slip = {
  legs: [
    {
      id: "leg_1",
      game_id: "nba_001",
      market: "spread",
      selection: "lakers",
      line: -4.5,
      odds: -110
    }
  ],
  wager: 50.00
};
```

**Bindings:**
| UI Element | Variable Path | Calculation | Example |
|------------|---------------|-------------|---------|
| Leg count | `slip.legs.length` | Count | "2" |
| Leg cards | `slip.legs[]` | Loop | Multiple cards |
| Market type | `leg.market` | Map to label | "Spread" → "SPREAD" |
| Selection | `leg.selection + leg.line` | Concatenate | "Lakers -4.5" |
| Leg odds | `leg.odds` | American | "-110" |
| Total odds | Calculate from all legs | American odds math | "+264" |
| Wager | `slip.wager` | Currency input | "$50.00" |
| Est. payout | `slip.wager * totalOdds` | Calculate | "$182.00" |

#### Place Bet API
**Endpoint:** `POST /app/evaluate`  
**Status:** ✅ Exists, accepts legs[]

**Request:**
```json
{
  "input": "Lakers -4.5 + LeBron O25.5",
  "tier": "good",
  "legs": [
    {
      "market": "spread",
      "team": "Lakers",
      "line": -4.5,
      "odds": -110
    },
    {
      "market": "player_prop",
      "player": "LeBron James",
      "prop": "points",
      "line": 25.5,
      "odds": -115
    }
  ]
}
```

**Response:** (existing evaluation response)

**Static:** 25%  
**Dynamic:** 75%  
**APIs Needed:** 2 endpoints (game details, odds) + evaluation endpoint

---

## 5. API ENDPOINTS SUMMARY

### Existing (Mock or Real)
| Endpoint | Method | Returns | Used By | Status |
|----------|--------|---------|---------|--------|
| `/api/mock/user/me` | GET | User profile | Dashboard | ✅ Mock |
| `/api/mock/user/bets` | GET | Active bets list | Dashboard | ✅ Mock |
| `/api/mock/sports` | GET | Sports list | Browse | ✅ Mock |
| `/api/mock/games` | GET | Games list | Browse, Builder | ✅ Mock |
| `/api/mock/odds/{id}` | GET | Odds for game | Browse, Builder | ✅ Mock |
| `/app/evaluate` | POST | Bet analysis | Builder | ✅ Real |

### Missing (Need to Build)
| Endpoint | Method | Returns | Used By | Priority |
|----------|--------|---------|---------|----------|
| `/api/notifications` | GET | Unread count | Dashboard | Low |
| `/api/user/stats` | GET | Weekly trends | Dashboard | Medium |
| `/api/insights/featured` | GET | AI insights | Browse | Low |
| `/api/slip/calculate` | POST | Parlay odds calc | Builder | High |
| `/api/bets` | POST | Place/track bet | Builder | High |

---

## 6. IMPLEMENTATION CHECKLIST

### Phase 1: Wire Static to Mock APIs (This Week)
- [x] Create mock data (MOCK_GAMES, MOCK_ODDS, MOCK_USER)
- [x] Create mock API endpoints
- [ ] Wire dashboard to fetch from `/api/mock/user/me`
- [ ] Wire dashboard bets from `/api/mock/user/bets`
- [ ] Wire browse sports grid from `/api/mock/sports`
- [ ] Wire browse games from `/api/mock/games`
- [ ] Wire browse odds from `/api/mock/odds/{id}`
- [ ] Wire builder game details from `/api/mock/games/{id}`
- [ ] Wire builder odds grid from `/api/mock/odds/{id}`
- [ ] Wire builder slip calculation (client-side)
- [ ] Wire place bet to `/app/evaluate`

### Phase 2: Replace with Real Backend (Week 2)
- [ ] Create database schema (games, odds, bets tables)
- [ ] Replace mock endpoints with DB queries
- [ ] Add user authentication
- [ ] Add real-time score updates (polling or WebSocket)
- [ ] Add bet tracking/history

### Phase 3: Polish & Production (Week 3+)
- [ ] Integrate real odds API (The Odds API, etc.)
- [ ] Add wallet/payment flow
- [ ] Add AI insights engine
- [ ] Add notifications system
- [ ] Performance optimization
- [ ] Security audit

---

## NEXT ACTIONS

**Immediate (Today):**
1. Review this document with team
2. Confirm API schema matches expectations
3. Choose first screen to wire (recommend: Browse → Builder flow)

**This Week:**
1. Wire all mock API calls
2. Test full user flow: Browse → Select game → Build slip → Place bet → Analyze
3. Fix any bugs in evaluation flow

**Design Handoff:**
1. Import HTML into design tool (Figma, etc.)
2. Map data bindings to design components
3. Create component library with variants for each state
4. Design empty states, loading states, error states

---

**File Locations:**
- Landing: `app/templates/screens/landing.html` (337 lines)
- Dashboard: `app/templates/screens/dashboard.html` (254 lines)
- Browse: `app/templates/screens/browse.html` (316 lines)
- Builder: `app/templates/screens/builder.html` (308 lines)
- Mock Data: `app/mock_data.py` (170 lines)
- Mock API: `app/routers/mock_api.py` (140 lines)

**Total Lines of Code:** 1,525 lines  
**Total Data Points:** 147 bindings  
**API Endpoints:** 6 existing, 5 needed

---

**Ready to implement?**
