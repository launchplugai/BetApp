# BetApp Wiring Spec v1

> One UI system. One auth pattern. One evaluation contract. One shared layout.
> This is the source of truth for how screens connect to APIs.

---

## Current State (the mess)

Three parallel UI systems:
1. **Neon screens** (`/app?screen=X`) — Tailwind, raw HTML, no Jinja2
2. **v1 UI** (`/v1/*`) — Python f-string HTML, inline CSS
3. **app/index.html** (`/app` old) — Custom CSS, chat-style

Three evaluation routes returning different shapes:
- `/app/evaluate` — camelCase (web.py)
- `/v1/evaluate` — snake_case (v1_ui.py)
- `/leading-light/evaluate/text` — snake_case with different wrapper

Auth is inconsistent:
- Some screens use `AUTH.fetch()` utility
- Some read tokens directly from storage
- Some skip auth entirely
- Token key names vary

No shared layout — every screen imports CDN links separately.

---

## Target State

### Decision 1: ONE UI SYSTEM

**Keep: Neon screens** (`/app?screen=X`)
**Kill: v1 UI** (`/v1/*`) — absorb its evaluate logic into the neon pipeline
**Kill: app/index.html** — legacy chat interface, superseded by builder

**Reason:** The neon screens are the most complete, have the right UX flow
(landing → auth → onboarding → dashboard → browse → builder → history),
and use a modern stack (Tailwind).

### Decision 2: ONE SHARED LAYOUT

Create `templates/base.html` as a Jinja2 layout. All screens extend it.

```
base.html provides:
- <head>: viewport, Tailwind CDN, Fontshare fonts, Iconify CDN
- <body>: dark bg, screen content slot
- Bottom nav (shared, with active state from variable)
- Auth check script (shared)
- Feature flag script (nav-protocols.js)
```

Switch `web.py` from `template_path.read_text()` to proper
`templates.TemplateResponse()` with Jinja2 inheritance.

### Decision 3: ONE AUTH PATTERN

**Standard:** `auth.js` (`AUTH` utility) is the only way to manage tokens.

Every authenticated screen:
1. Loads `<script src="/static/js/auth.js"></script>` from base.html
2. Calls `AUTH.requireAuth()` on load (redirects to `/app?screen=auth` if no token)
3. Uses `AUTH.fetch(url, options)` for all API calls (handles 401 + refresh)
4. Uses `AUTH.logout()` for logout

**Token storage keys** (canonical, no alternatives):
- `dna_auth_token` — access token
- `dna_refresh_token` — refresh token
- `dna_user` — user object
- `dna_remember_me` — persistence flag

**Public screens** (no auth required): landing, auth
**Authenticated screens**: dashboard, browse, builder, protocol, history, notifications, onboarding, admin

### Decision 4: ONE EVALUATION CONTRACT

All evaluation goes through one endpoint: `POST /api/evaluate`

**Request:**
```json
{
  "legs": [
    {
      "entity": "Lakers",
      "market": "spread",
      "value": "-5.5",
      "raw": "Lakers -5.5"
    }
  ],
  "tier": "GOOD"
}
```

**Response** (camelCase for JS consumption):
```json
{
  "parlayId": "uuid",
  "tier": "GOOD",
  "legCount": 3,
  "verdict": {
    "level": "GREEN",
    "explanation": "Low fragility parlay with independent legs."
  },
  "metrics": {
    "rawFragility": 0.23,
    "finalFragility": 0.31,
    "legPenalty": 0.05,
    "correlationPenalty": 0.03
  },
  "recommendation": {
    "action": "accept",
    "reason": "Legs are independent with manageable risk."
  },
  "notableLegs": [],
  "humanSummary": "...",
  "structure": { ... },
  "meta": {
    "elapsedMs": 142,
    "requestId": "abc-123"
  }
}
```

The old routes (`/v1/evaluate`, `/leading-light/evaluate/text`) become thin
redirects to `POST /api/evaluate` for backwards compatibility, then get removed.

### Decision 5: SCREEN → API WIRING MAP

This is the canonical map. Each screen lists exactly what it fetches and
what shape it expects back.

```
SCREEN          ROUTE                     AUTH    FETCHES
──────          ─────                     ────    ───────
landing         /app?screen=landing       no      nothing (static)

auth            /app?screen=auth          no      POST /api/auth/login
                                                  POST /api/auth/register
                                                  → { success, user, access_token, refresh_token }

onboarding      /app?screen=onboarding    yes     GET  /api/preferences
                                                  POST /api/preferences
                                                  → { risk_profile, bet_style, constraints, bankroll_policy }

dashboard       /app?screen=dashboard     yes     GET  /api/preferences
                                                  GET  /api/notifications?page=1&per_page=1
                                                  GET  /api/bets/history?status=pending&limit=5
                                                  → preferences shape, notification count, active bets

browse          /app?screen=browse        yes     GET  /api/sports
                                                  GET  /api/games?sport={sport}
                                                  GET  /api/odds/{gameId}  (enrichment, optional)
                                                  GET  /api/live/logos/all-leagues
                                                  → sports[], games[], market odds, logo urls

builder         /app?screen=builder       yes     reads sessionStorage.dna_protocol_context (set by browse)
                                                  GET  /api/odds/{gameId}
                                                  POST /api/evaluate
                                                  → market selections, evaluation result

protocol        /app?screen=protocol      yes     GET  /api/protocols/{id}
                                                  GET  /api/protocols/{id}/snapshot-v2/latest
                                                  POST /api/protocols/{id}/snapshot-v2
                                                  → protocol detail, intelligence snapshot

history         /app?screen=history       yes     GET  /api/bets/history?page=N&per_page=10&status=X
                                                  → { bets[], total, page, per_page }

notifications   /app?screen=notifications yes     GET  /api/notifications
                                                  PUT  /api/preferences/notifications
                                                  → notification list, settings

admin           /admin                    yes*    GET  /api/admin/report/super
                                                  POST /api/admin/config/update
                                                  POST /api/admin/nba/*
                                                  → admin report, config state
```

*admin uses a separate auth check (tier=BEST or IP whitelist)

### Decision 6: SESSIONSSTORAGE CONTRACT (browse → builder handoff)

Browse sets `dna_protocol_context` in sessionStorage when user picks a game:

```json
{
  "gameId": "nba-lal-at-gsw-2026-03-05",
  "protocolId": "nba-lal-at-gsw-2026-03-05",
  "league": "NBA",
  "homeTeam": "GSW",
  "awayTeam": "LAL",
  "homeTeamFull": "Golden State Warriors",
  "awayTeamFull": "Los Angeles Lakers",
  "startTime": "2026-03-05T19:30:00Z",
  "status": "SCHEDULED"
}
```

Builder reads this on load. If missing, shows "Select a game first" with link to browse.

### Decision 7: API RESPONSE CONVENTIONS

All API endpoints follow these rules:
1. Response keys are **snake_case** (Python/Pydantic standard)
2. The **web.py evaluate proxy** converts to camelCase for JS
3. All other endpoints stay snake_case — JS screens handle it
4. Error responses: `{ "error": "message", "code": "ERROR_CODE" }`
5. List responses: `{ "items": [...], "total": N, "page": N, "per_page": N }`
6. Timestamps: ISO 8601 strings

**Exception:** `/api/evaluate` returns camelCase because the builder JS
expects it and it's the highest-traffic endpoint.

---

## Implementation Order

### Phase 1: Shared Layout (no behavior change)
1. Create `templates/base.html` with Tailwind/fonts/nav
2. Convert each screen to `{% extends "base.html" %}` + `{% block content %}`
3. Switch `web.py` to use `templates.TemplateResponse()` with context vars
4. Remove duplicate CDN imports from every screen

### Phase 2: Unified Auth
1. Add `<script src="/static/js/auth.js">` to base.html
2. Add auth guard to each authenticated screen (replace inline checks)
3. Standardize token key usage across all screens
4. Remove direct localStorage/sessionStorage reads

### Phase 3: Single Evaluation Contract
1. Create `POST /api/evaluate` that wraps pipeline
2. Update builder.js to call `/api/evaluate` instead of `/app/evaluate`
3. Deprecate `/v1/evaluate` and `/leading-light/evaluate/text`
4. Remove v1_ui.py entirely

### Phase 4: Kill Dead Code
1. Remove `v1_ui.py` (entire file)
2. Remove `app/templates/app/index.html` (old chat UI)
3. Remove `web_old.py`, `_deprecated_web_legacy.py` if they exist
4. Remove `dashboard_stubs.py` if fully replaced
5. Clean up unused imports in `main.py`

---

## Verification

After each phase, verify:
- `GET /` → landing page renders
- `GET /app` → dashboard (or auth redirect)
- `GET /app?screen=browse` → browse renders
- `GET /app?screen=builder` → builder renders
- `POST /api/evaluate` → returns evaluation JSON
- `GET /api/bets/history` → returns bet history
- `GET /health` → healthy

Run: `python -m pytest tests/ -v`
