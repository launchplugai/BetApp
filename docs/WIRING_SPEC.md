# BetApp Wiring Spec v1.0

> **North Star.** Every Claude/Codex session building on this repo starts here.
> "We are not building a random stack of features. Every bet, every filter, every parlay, and every preference must map to a clear, tested, traceable function. No magic, no surprises."

---

## 0. Product Promise

The user should never feel like they're playing roulette.

If the user:
- picks a protocol (strategy),
- builds a parlay (execution),
- evaluates it (analysis),
- saves it (memory),
- revisits it (history),
- filters it (search),
- and gets surfaced bets (protocol feed),

...then the system must behave **deterministically and consistently**.

---

## 1. Core Loop

### 1.1 User Journey (Happy Path)

1. **Landing** - User sees what the product is, CTA to login.
2. **Auth** - User logs in. Tokens stored consistently.
3. **Dashboard** - User sees: recent evaluations, saved bets, protocol alerts/feed summary, quick entry points (Browse, Builder, Protocols).
4. **Browse** - User selects sport/game and optionally a protocol lens.
5. **Builder** - User builds a parlay using markets/legs.
6. **Evaluate** - User hits Evaluate. System returns: per-leg analysis, overall grade, reasoning, protocol alignment tags.
7. **Save** - User can save evaluation as a bet record (persisted).
8. **History** - User can search/filter past evaluations and saved bets.
9. **Protocols** - User picks/creates protocols (filters + heuristics). Protocols generate feeds of matching opportunities + alerts.

### 1.2 User Expectations

- Every action produces an explainable output
- Every saved record is: indexable, searchable, actionable
- Every protocol selection changes what the user sees in a predictable way

---

## 2. System Spine: The Four Contracts

This system lives or dies on contracts. No contract, no feature.

### 2.1 Screen Contract

For every screen, define:
- route
- auth required
- data dependencies (API calls)
- states: loading, empty, error, populated
- outputs (what user can do next)

### 2.2 API Contract

Every endpoint must have:
- stable request + response shape
- versioning policy
- error format
- auth behavior
- logging correlation (sessionId, evaluationId)

### 2.3 Data Contract (Persistence)

Anything saved must be:
- normalized enough to query
- tagged enough to filter
- linked enough to trace

### 2.4 Protocol Contract (Strategy -> Feed -> Alerts)

A Protocol is not a vibe. It is a machine-readable filter/strategy definition that:
- defines matching rules
- produces a feed of candidates
- annotates evaluations with alignment + rationale

---

## 3. UI Surfaces (Single System Rule)

### 3.1 One UI System

**Rule:** One UI surface serves users. No parallel UIs.

- `/app?screen=<name>` is the only entry point
- No `/v1/*` HTML-string UI
- No raw file read bypassing templating
- No duplicate bottom nav per screen
- No token logic duplicated per screen

**Outcome:** One shared shell + consistent auth + consistent navigation.

**Status:** DONE (commits `412d9b0`, `c4d01b4`, `f1d8fb7`). Enforced by `tests/contracts/test_wiring_contracts.py` (15 tests).

---

## 4. Screens: Required Wiring

### 4.1 Screen Map

| Screen | Route | Auth | Purpose | API |
|--------|-------|------|---------|-----|
| landing | `/app?screen=landing` | No | Entry + CTA | none |
| auth | `/app?screen=auth` | No | Login | `POST /api/auth/login` |
| dashboard | `/app?screen=dashboard` | Yes | Hub | `GET /api/bets/history`, `GET /api/notifications`, `GET/PUT /api/preferences`, `GET /api/protocols` |
| browse | `/app?screen=browse` | Yes | Select game context | `GET /api/sports`, `GET /api/games?sport=`, `GET /api/odds/{gameId}` |
| builder | `/app?screen=builder` | Yes | Build parlay | `GET /api/odds/{gameId}` (optional) |
| evaluate | (action) | Yes | Run analysis | `POST /api/evaluate` |
| history | `/app?screen=history` | Yes | Search records | `GET /api/bets/history?filters...` |
| protocol | `/app?screen=protocol&id=...` | Yes | Protocol deep dive | `GET /api/protocols/{id}`, `GET /api/protocols/{id}/snapshot-v2` |
| notifications | `/app?screen=notifications` | Yes | Alerts | `GET /api/notifications` |
| onboarding | `/app?screen=onboarding` | Yes | Configure settings | `GET/PUT /api/preferences` |

### 4.2 Global UI Rules

- Auth gating is not "sometimes" - if `require_auth=true`, screen must redirect to auth or show login prompt on 401
- Every screen uses one API wrapper for tokens + headers (`AUTH.fetch()`)
- Every screen is accountable to its API contract

---

## 5. Evaluation: Single Source of Truth

### 5.1 Why this matters

This is the heart of the product. If the evaluation output isn't stable and interpretable, Protocol can't work, History can't be searchable, Dashboard becomes noise.

### 5.2 Endpoint

`POST /api/evaluate`

**Request:**
```json
{
  "sessionId": "uuid",
  "userId": "optional-if-derived-from-token",
  "sport": "nba",
  "gameId": "game_123",
  "protocolId": "proto_default",
  "legs": [
    {
      "marketKey": "player_points",
      "selection": "Over",
      "line": 24.5,
      "price": -110,
      "meta": { "playerId": "..." }
    }
  ],
  "stake": 10
}
```

**Response:**
```json
{
  "sessionId": "uuid",
  "evaluationId": "eval_456",
  "createdAt": "ISO-8601",
  "summary": {
    "grade": "B",
    "edge": 0.041,
    "risk": 0.62,
    "confidence": 0.71
  },
  "legs": [
    {
      "index": 0,
      "grade": "B-",
      "riskDrivers": ["volatility", "correlation"],
      "tags": ["injuryRisk", "paceShock"],
      "notes": "..."
    }
  ],
  "protocol": {
    "id": "proto_default",
    "alignmentScore": 0.78,
    "badges": ["SAFE", "NO-CHASE"],
    "matchedRules": ["avoid_injury_star", "playoff_hunt_bias"]
  },
  "explain": {
    "sherlock": [
      {
        "title": "Why risk is elevated",
        "bullets": ["...", "..."]
      }
    ]
  },
  "persist": {
    "canSave": true,
    "saveTarget": "/api/bets"
  },
  "errors": []
}
```

### 5.3 Error Contract (Standard)

All endpoints must return:
```json
{
  "error": {
    "code": "ODDS_PROVIDER_DOWN",
    "message": "Human readable",
    "details": {}
  }
}
```

---

## 6. Persistence: Saved Bets Must Be Queryable

### 6.1 Saved Record Types

- **Evaluation**: raw analysis output, reproducible summary.
- **BetRecord**: user action "I saved/placed this", links to evaluation.

### 6.2 Required Stored Fields (Minimum)

Every saved evaluation/bet must include:
- `evaluationId`
- `userId`
- `sessionId`
- `sport`
- `gameIds` (array)
- `legs` (normalized representation)
- `summary.grade`, `summary.risk`, `summary.confidence`
- `protocolId`
- `protocol.badges`
- `tags[]` (global tags, derived from heuristics)
- `createdAt`

### 6.3 Indexing (Search/Filter)

History must support filtering by:
- date range
- sport
- grade
- risk range
- protocolId
- tags (injuryRisk, tanking, playoffHunt, etc.)
- free text (optional, via notes/explain titles)

If it can't be filtered, it's basically dead weight storage.

---

## 7. Protocols: Strategy Engine Spec

### 7.1 What Protocol Is

A Protocol is a named strategy filter that produces:
1. A feed of opportunities that match
2. An annotation layer on evaluations ("this parlay matches protocol X because...")

### 7.2 Protocol Definition

**Protocol:**
- `id`
- `name`
- `description`
- `rules[]` (machine-readable)
- `enabled` (bool)
- `visibility` (private/public)
- `createdBy`
- `createdAt`

**Rule Types:**
- game context rules (playoff hunt, tanking)
- team state rules (injured star, back-to-back, travel)
- market rules (avoid alt lines, prefer certain bet types)
- risk posture rules (max risk, min confidence, etc.)

### 7.3 Protocol Feed

`GET /api/protocols/{id}/feed`

Returns a list of candidates with:
- why it matched
- what markets/legs are suggested
- a "build in builder" action payload

### 7.4 Protocol Snapshot

`GET /api/protocols/{id}/snapshot-v2`

Returns:
- last N matches
- performance summary
- rule hit rates
- top drivers

---

## 8. Preferences & Modifiers: No Ghost Settings

### 8.1 Rule

If a preference exists in UI, it must map to behavior in:
- evaluation
- filtering
- protocol feed generation
- or display

### 8.2 Examples

- "risk tolerance" must affect evaluation thresholds
- "hide high variance markets" must filter odds/markets in builder/browse
- "default protocol" must load protocol context automatically

No more settings that are just decorative UI confetti.

---

## 9. Observability: Trace Everything

### 9.1 Correlation IDs

Every request should carry:
- `sessionId`
- `evaluationId` (after evaluation)
- `userId` from token

### 9.2 Logs

For Evaluate:
- inputs summary (not sensitive)
- provider health (odds availability)
- protocol rule matches
- persistence result

If it can't be debugged, it can't be trusted.

---

## 10. Acceptance Criteria (Definition of "Wired")

### Core Loop
- Landing -> Auth -> Dashboard -> Browse -> Builder -> Evaluate -> Save -> History works end-to-end.
- The same parlay evaluated twice produces consistent structure and comparable scoring.

### Protocol Loop
- A protocol is selectable.
- When selected: it changes what appears in feed/browse/builder suggestions; evaluations return protocol alignment + matched rules.
- Protocol feed is populated by deterministic rules, not randomness.

### Data
- Saved records can be filtered by protocolId, tags, risk, confidence.
- History shows data that matches what was saved.

### No Roulette
- No screen uses a different token key.
- No screen bypasses the API wrapper.
- No duplicate evaluation endpoint shapes in production paths.

---

## Implementation Status

### Phase 0: Single UI System
**STATUS: COMPLETE**
- One UI surface (`/app?screen=name`) - DONE
- Shared base.html layout - DONE
- Unified auth (AUTH.*) - DONE
- Machine-checkable contracts (15 tests) - DONE
- Dead code removed (v1_ui, web_old, deprecated) - DONE

### Phase 1: Evaluate Contract Alignment
**STATUS: IN PROGRESS**
- Current evaluate accepts: `{input, tier, legs[]}` (text-based)
- Target evaluate accepts: `{sessionId, sport, gameId, protocolId, legs[], stake}`
- Gap: request/response shapes need bridging

### Phase 2: Protocol Engine
**STATUS: PENDING**
- Protocol model with rules[] exists partially
- Feed endpoint (`/api/protocols/{id}/feed`) - MISSING
- Snapshot v2 (`/api/protocols/{id}/snapshot-v2`) - EXISTS (partial)
- Protocol alignment in evaluate response - MISSING

### Phase 3: Persistence & History
**STATUS: PENDING**
- Bet saving exists but fields incomplete
- History filtering by tags/protocolId/risk - MISSING
- evaluationId linkage - MISSING

### Phase 4: Preferences -> Behavior Mapping
**STATUS: PENDING**
- Preferences stored but not wired to evaluation/filtering

### Phase 5: Observability
**STATUS: PARTIAL**
- X-Request-Id correlation exists
- sessionId/evaluationId correlation in evaluate - MISSING
