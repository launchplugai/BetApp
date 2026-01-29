# UI SPECIFICATION v1

> **Status**: LOCKED
> **Last Updated**: 2026-01-29
> **Reference Device**: iPhone Safari

---

## 1. Route Map

| Method | Route | Purpose |
|--------|-------|---------|
| GET | `/v1` | Landing page. Links to Builder and History. |
| GET | `/v1/build` | Parlay builder with structured team/bet selection. |
| POST | `/v1/build/add` | Add a leg to parlay. Redirects back to builder. |
| POST | `/v1/evaluate` | Accepts parlay form. Returns server-rendered debrief HTML. |
| GET | `/v1/history` | Server-rendered list of recent evaluations. Not login-gated. |
| GET | `/v1/account` | Placeholder. May show "Login not enabled" safely. |

**No other routes.** No `/app`. No `/ui2`. No client-side routing.

---

## 2. Builder Flow (Structured Selection)

### No Text Input
Users select from structured dropdowns/radios instead of typing free text.

### Selection Flow
1. **Select Team** - Dropdown grouped by league (NBA/NFL/MLB/NHL)
2. **Select Bet Type** - Radio buttons (Spread, ML, Total, Team Total)
3. **Enter Line** - Text input for spread/total value (e.g., "5.5")
4. **Select Direction** - Dropdown (Minus/Under or Plus/Over)
5. **Add Leg** - Form POST adds leg, redirects back to builder
6. **Repeat** - Add more legs as needed
7. **Select Tier** - Radio buttons (GOOD/BETTER/BEST)
8. **Evaluate** - Form POST returns debrief page

### Data Source
- 4 leagues: NBA, NFL, MLB, NHL
- ~122 teams total
- Bet types: spread, ml, total, team_total

---

## 3. Debrief Page Wireframe

```
┌─────────────────────────────────────────┐
│ DNA BET ENGINE               [Account]  │
├─────────────────────────────────────────┤
│ ← Back to Builder                       │
├─────────────────────────────────────────┤
│ YOUR PARLAY                             │
│ ┌─────────────────────────────────────┐ │
│ │ 1  LA Lakers -5.5                   │ │
│ │ 2  Boston Celtics ML                │ │
│ │ 3  Denver Nuggets o220.5            │ │
│ └─────────────────────────────────────┘ │
├─────────────────────────────────────────┤
│ VERDICT                                 │
│ ┌─────────────────────────────────────┐ │
│ │ [YELLOW]                            │ │
│ └─────────────────────────────────────┘ │
├─────────────────────────────────────────┤
│ EXPLANATION                             │
│ ┌─────────────────────────────────────┐ │
│ │ This parlay carries elevated risk   │ │
│ │ due to correlated outcomes...       │ │
│ └─────────────────────────────────────┘ │
├─────────────────────────────────────────┤
│ METRICS                    [GOOD tier]  │
│ ┌─────────────────────────────────────┐ │
│ │ Raw Fragility:     0.42             │ │
│ │ Final Fragility:   0.58             │ │
│ │ Leg Penalty:       0.15             │ │
│ │ Correlation:       0.08             │ │
│ └─────────────────────────────────────┘ │
├─────────────────────────────────────────┤
│ ERRORS                                  │
│ ┌─────────────────────────────────────┐ │
│ │ (reserved space - empty on success) │ │
│ └─────────────────────────────────────┘ │
├─────────────────────────────────────────┤
│ [Build Another]       [View History]    │
└─────────────────────────────────────────┘
```

### Section Order (Fixed)
1. Header (App name + Account link)
2. Back to Builder link
3. INPUT ECHO (numbered list of legs)
4. VERDICT (inductor level badge)
5. EXPLANATION TEXT
6. METRICS (tier-gated display)
7. ERRORS BOX (always present, empty on success)
8. Actions: Build Another / View History

---

## 4. No-JS Contract

The following **MUST** work with JavaScript disabled:

| Action | Implementation | JS Required? |
|--------|----------------|--------------|
| Navigate between pages | `<a href="/v1/...">` | No |
| Select team | `<select>` with `<optgroup>` | No |
| Select bet type | `<input type="radio">` | No |
| Enter line | `<input type="text">` | No |
| Add leg to parlay | `<form method="POST" action="/v1/build/add">` | No |
| Select tier | `<input type="radio">` | No |
| Evaluate parlay | `<form method="POST" action="/v1/evaluate">` | No |
| Receive debrief | Server returns full HTML page | No |
| View history | `<a href="/v1/history">` | No |

### Explicit Rules
- **No text parsing required.** All input is structured.
- **Parlay state in URL.** Legs stored as JSON in query param.
- **All navigation uses anchor tags.**
- **All submissions use form POST.**
- **Redirects use 303 See Other.**

---

## 5. Mobile Constraints

| Constraint | Requirement |
|------------|-------------|
| Reference device | iPhone Safari |
| Touch targets | Minimum 44px height/width |
| Horizontal scroll | None allowed |
| Viewport meta | `<meta name="viewport" content="width=device-width, initial-scale=1">` |
| Hover states | Not relied upon for functionality |
| Font size | Minimum 16px for inputs (prevents iOS zoom) |
| Select dropdowns | Native iOS picker used |

---

## 6. Non-Goals for v1

Explicitly **NOT** included in this version:

- No SPA (Single Page Application)
- No client-side routing
- No global JavaScript event handlers
- No debrief IDs or persistence guarantees
- No authentication gating required
- No real-time updates
- No WebSocket connections
- No localStorage/sessionStorage requirements
- No service workers
- No text parsing / NLP
- No player props (team-level bets only in v1)

---

## 7. Supported Leagues and Teams

### NBA (30 teams)
ATL, BOS, BKN, CHA, CHI, CLE, DAL, DEN, DET, GSW, HOU, IND, LAC, LAL, MEM, MIA, MIL, MIN, NOP, NYK, OKC, ORL, PHI, PHX, POR, SAC, SAS, TOR, UTA, WAS

### NFL (32 teams)
ARI, ATL, BAL, BUF, CAR, CHI, CIN, CLE, DAL, DEN, DET, GB, HOU, IND, JAX, KC, LV, LAC, LAR, MIA, MIN, NE, NO, NYG, NYJ, PHI, PIT, SF, SEA, TB, TEN, WAS

### MLB (30 teams)
ARI, ATL, BAL, BOS, CHC, CHW, CIN, CLE, COL, DET, HOU, KC, LAA, LAD, MIA, MIL, MIN, NYM, NYY, OAK, PHI, PIT, SD, SF, SEA, STL, TB, TEX, TOR, WAS

### NHL (32 teams)
ANA, ARI, BOS, BUF, CGY, CAR, CHI, COL, CBJ, DAL, DET, EDM, FLA, LA, MIN, MTL, NSH, NJ, NYI, NYR, OTT, PHI, PIT, SJ, SEA, STL, TB, TOR, VAN, VGK, WAS, WPG

---

## 8. Bet Types

| Type | Code | Needs Line | Needs Direction | Example |
|------|------|------------|-----------------|---------|
| Spread | `spread` | Yes | Yes (-/+) | "LA Lakers -5.5" |
| Moneyline | `ml` | No | No | "LA Lakers ML" |
| Total | `total` | Yes | Yes (o/u) | "LA Lakers o220.5" |
| Team Total | `team_total` | Yes | Yes (o/u) | "LA Lakers TT o112.5" |

---

## 9. Error States

All error states render as full HTML pages (not JSON):

| Error | Display |
|-------|---------|
| No legs added | Debrief page with ERRORS box: "No legs in parlay" |
| Invalid team | Redirect back to builder (no error shown) |
| Rate limited | Debrief page with ERRORS box + retry guidance |
| Server error | Debrief page with ERRORS box + generic message |

The user should **never** see raw JSON or a blank page.

---

## 10. File Structure

```
app/
├── data/
│   ├── __init__.py
│   └── leagues.py          # League/team data (122 teams)
├── routers/
│   └── v1_ui.py            # All v1 routes
```

---

## Approval Checklist

- [x] Route map defined (6 routes)
- [x] Structured selection flow (no text input)
- [x] Debrief wireframe with all sections
- [x] No-JS contract explicit
- [x] Mobile constraints documented
- [x] Non-goals listed
- [x] All 4 leagues with teams
- [x] Bet types documented
- [x] Error states defined
- [x] File structure defined

**This spec is LOCKED. Proceed to testing.**
