# 09 — UI Schematics

> Single source of truth for the DNA Bet Engine UI wiring.
> Machine-checkable contracts live in `09-ui-schematics.contracts.json`.

---

## Non-Negotiables

1. **One UI surface** — `/app?screen={name}` is the only entry point. No `/v1/`, no `/new/`, no parallel systems.
2. **One routing pattern** — `SCREENS` dict in `web.py` is the registry. If it's not in `SCREENS`, it doesn't exist.
3. **One auth pattern** — `AUTH.*` utility from `auth.js`. No raw `sessionStorage.getItem('dna_auth_token')`.
4. **One evaluation contract** — `POST /api/evaluate` (canonical) aliased at `/app/evaluate`. Response is camelCase.

---

## Screen Map

| Screen | Route | Auth | Purpose | Primary API Calls |
|--------|-------|------|---------|-------------------|
| `landing` | `/app?screen=landing` | No | Marketing / pricing | None |
| `auth` | `/app?screen=auth` | No | Login / Register | `POST /api/auth/login`, `POST /api/auth/register` |
| `onboarding` | `/app?screen=onboarding` | Yes | Sport selection | `POST /api/preferences` |
| `dashboard` | `/app?screen=dashboard` | Yes | Home — stats, recent, streak | `GET /api/dashboard/stats`, `GET /api/bets/recent` |
| `browse` | `/app?screen=browse` | Yes | Sport grid, live games, protocols | `GET /api/odds/games`, `GET /api/protocols` |
| `builder` | `/app?screen=builder` | Yes | Build & evaluate parlays | `POST /api/evaluate` |
| `history` | `/app?screen=history` | Yes | Past evaluations | `GET /api/bets/history` |
| `protocol` | `/app?screen=protocol` | Yes | Protocol detail view | `GET /api/protocols/{id}` |
| `notifications` | `/app?screen=notifications` | Yes | Notification preferences | `GET/PUT /api/notifications/preferences` |

### Also Served (non-screen routes)

| Route | Purpose |
|-------|---------|
| `/` | Landing page (same template as `?screen=landing`) |
| `/admin` | Admin dashboard (separate template) |
| `/health` | Health check (JSON) |
| `/build` | Build info (JSON) |

---

## Template Architecture

```
base.html                          ← Single layout: Tailwind, fonts, nav, auth gate
├── screens/landing.html           ← {% extends "base.html" %}, nav hidden
├── screens/auth.html              ← {% extends "base.html" %}, nav hidden
├── screens/onboarding.html        ← Standalone (different design system)
├── screens/dashboard.html         ← {% extends "base.html" %}
├── screens/browse.html            ← {% extends "base.html" %}
├── screens/builder.html           ← {% extends "base.html" %}
├── screens/history.html           ← {% extends "base.html" %}
├── screens/protocol.html          ← {% extends "base.html" %}
└── screens/notifications.html     ← {% extends "base.html" %}
```

### base.html Provides

- Tailwind CDN, Iconify, Fontshare (Tanker, Satoshi)
- CSS variables (`--accent: #ff1744`, dark theme)
- Bottom nav (hidden for `landing`, `auth`)
- `auth.js` auto-included on every page
- Auth gate: calls `AUTH.requireAuth()` when `require_auth` is true
- `nav-protocols.js` auto-included
- Blocks: `title`, `extra_head`, `nav`, `body`, `scripts`

### Template Context (always passed)

| Variable | Type | Source |
|----------|------|--------|
| `request` | `Request` | FastAPI |
| `active_screen` | `str` | URL `?screen=` param |
| `require_auth` | `bool` | `SCREENS` dict |
| `git_sha` | `str` | Config (first 8 chars) |

---

## Auth Contract

### Token Storage (via `AUTH.*` in `auth.js`)

| Key | Storage | Purpose |
|-----|---------|---------|
| `dna_auth_token` | sessionStorage (or localStorage if remember) | JWT access token |
| `dna_refresh_token` | sessionStorage (or localStorage if remember) | Refresh token |
| `dna_user` | sessionStorage | User profile JSON |
| `dna_remember_me` | localStorage | Persistence flag |

### AUTH API Surface

| Method | Purpose |
|--------|---------|
| `AUTH.getAccessToken()` | Get current JWT |
| `AUTH.setTokens(access, refresh, remember)` | Store tokens |
| `AUTH.clearTokens()` | Wipe all auth state |
| `AUTH.isAuthenticated()` | Check if token exists |
| `AUTH.getAuthHeaders()` | `{Authorization: "Bearer ..."}` |
| `AUTH.refreshAccessToken()` | Exchange refresh for new access |
| `AUTH.logout()` | Clear tokens, redirect to auth |
| `AUTH.requireAuth()` | Redirect to auth if not authenticated |
| `AUTH.fetch(url, options)` | Fetch with auto-auth headers + 401 handling |

### Rules

- Authenticated screens MUST use `AUTH.fetch()` for all API calls
- On 401 response: call `AUTH.logout()` (redirects to `/app?screen=auth`)
- Login/register MUST use `AUTH.setTokens()`, not raw `sessionStorage.setItem()`
- Auth check on page load: `AUTH.requireAuth()` (injected by base.html when `require_auth` is true)

---

## Evaluate Contract

### Request

```
POST /api/evaluate
Content-Type: application/json
Authorization: Bearer <token>

{
  "input": "Lakers ML + Celtics -5.5",
  "tier": "GOOD" | "BETTER" | "BEST",
  "legs": [                              // optional structured legs
    {
      "entity": "Lakers",
      "market": "moneyline",
      "value": null,
      "raw": "Lakers ML"
    }
  ]
}
```

### Response (camelCase)

Top-level keys (all camelCase, converted from PipelineResponse):

| Key | Type | Always Present |
|-----|------|----------------|
| `evaluation` | object | Yes |
| `evaluation.parlayId` | string (UUID) | Yes |
| `evaluation.inductor` | `{level, explanation}` | Yes |
| `evaluation.metrics` | `{rawFragility, finalFragility, legPenalty, correlationPenalty, correlationMultiplier}` | Yes |
| `evaluation.correlations` | array | Yes |
| `evaluation.dna` | `{violations, baseStakeCap, recommendedStake, maxLegs, fragilityTolerance}` | Yes |
| `evaluation.recommendation` | `{action, reason}` | Yes |
| `interpretation` | object | Yes |
| `explain` | object | Yes |
| `tier` | string | Yes |
| `context` | object | No |
| `nbaHeuristics` | object | No |
| `primaryFailure` | object | No |
| `deltaPreview` | object | No |
| `signalInfo` | object | No |
| `entities` | object | No |
| `secondaryFactors` | array | No |
| `humanSummary` | string | No |
| `evaluatedParlay` | object | No |
| `notableLegs` | array | No |
| `finalVerdict` | object | No |
| `gentleGuidance` | object | No |
| `nextAction` | object | No |
| `confidenceTrend` | object | No |
| `groundingWarnings` | array | No |
| `sherlockResult` | object | No |
| `debugExplainability` | object | No |
| `proofSummary` | object | No |
| `structure` | object | No |
| `delta` | object | No |
| `groundingScore` | object | No |
| `input` | `{betText, tier}` | Yes (added by proxy) |
| `_meta` | `{elapsedMs}` | Yes (added by proxy) |

---

## SessionStorage Contracts

| Key | Written By | Read By | Shape |
|-----|-----------|---------|-------|
| `dna_auth_token` | auth screen | AUTH.* | string (JWT) |
| `dna_refresh_token` | auth screen | AUTH.* | string |
| `dna_user` | auth screen | dashboard, nav | `{name, email, id}` |
| `dna_remember_me` | auth screen | AUTH.* | `"true"` / `"false"` |
| `dna_protocol_context` | browse | builder | `{protocolId, sport, ...}` |

---

## Component Inventory

| Component | Location | Used By |
|-----------|----------|---------|
| Bottom Nav | base.html | All screens except landing, auth |
| Auth Gate | base.html script | All `require_auth: true` screens |
| Toast | Per-screen | notifications, builder |
| Game Card | browse.html | browse |
| Sport Chip Grid | browse.html | browse |
| Parlay Slip | builder.html | builder |
| DNA Results Panel | builder.html | builder |
| Stat Cards | dashboard.html | dashboard |
| History Table | history.html | history |

---

## API Route Inventory

| Method | Path | Router | Purpose |
|--------|------|--------|---------|
| POST | `/api/evaluate` | web.py | Evaluate parlay (canonical) |
| POST | `/app/evaluate` | web.py | Evaluate parlay (alias) |
| POST | `/api/auth/login` | auth.py | Login |
| POST | `/api/auth/register` | auth.py | Register |
| POST | `/api/auth/refresh` | auth.py | Refresh token |
| GET | `/api/dashboard/stats` | dashboard.py | Dashboard stats |
| GET | `/api/bets/recent` | bets.py | Recent bets |
| GET | `/api/bets/history` | bets.py | Bet history |
| GET | `/api/odds/games` | odds.py | Live games/odds |
| GET | `/api/protocols` | protocol | List protocols |
| GET | `/api/protocols/{id}` | protocol | Protocol detail |
| GET/PUT | `/api/notifications/preferences` | notifications.py | Notification prefs |
| POST | `/api/preferences` | preferences.py | User preferences |

---

## Enforcement

The companion file `09-ui-schematics.contracts.json` is machine-checkable.
`tests/test_wiring_contracts.py` loads it and validates:

1. Every screen in `SCREENS` dict matches the contract
2. Every screen template file exists
3. Auth requirements match
4. Route aliases resolve
5. Templates extend `base.html` (except onboarding)
6. No raw `sessionStorage.getItem('dna_auth_token')` in authenticated screens
7. All authenticated screens use `AUTH.fetch()` or `AUTH.requireAuth()`

If a screen is added without updating the contract, tests fail.
If auth is bypassed, tests fail.
If a template doesn't extend base.html, tests fail.

**"WORKING" is provable.**
