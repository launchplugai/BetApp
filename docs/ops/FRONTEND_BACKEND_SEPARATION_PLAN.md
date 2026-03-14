# Frontend / Backend Separation Plan

**Status:** CANONICAL  
**Last Updated:** 2026-03-14

This document defines the recommended plan for separating BetApp frontend and backend development.

It is not a rewrite proposal.

This document should now be read through the restored architecture lens:

- one repo
- frontend module
- Airlock membrane
- Sherlock synthesis
- DNA structured state

If this document conflicts with `docs/architecture/SYSTEM_RESTORATION_BLUEPRINT.md`, the restoration blueprint wins.

It is a staged separation plan designed to:

- preserve product momentum
- reduce frontend/backend coupling
- make the Evaluate loop easier to redesign
- keep the scoring/protocol/governance backend intact

## 1. Decision

BetApp should separate frontend and backend development.

### Recommended architecture

```text
/apps
  /api     FastAPI backend
  /web     dedicated frontend app

/packages
  /contracts   shared API contracts / schemas / generated types
```

### Keep

- FastAPI runtime
- Python scoring pipeline
- protocol engine
- OCR backend endpoints
- governance/control-plane services
- Alembic/Postgres migration path

### Change

- stop treating server templates as the long-term app frontend
- move active product UX into a dedicated frontend app
- make the frontend consume explicit backend APIs

## 2. Why This Makes Sense

The current repo already shows the pressure points:

- mixed server templates and frontend JS
- overlapping or partially duplicated Evaluate flows
- UI state coupled to backend-rendered assumptions
- UX redesign work blocked by unclear frontend ownership

A dedicated frontend helps because it:

- gives the Evaluate / OCR / Builder loop one clear home
- lets frontend move without entangling runtime/server-template debt
- forces stronger API contracts
- makes screen-level redesign practical
- allows backend to focus on scoring, protocols, OCR, auth, and governance

## 3. What Not To Do

Do not:

- rewrite everything in one pass
- replatform the backend away from FastAPI first
- keep stacking major UX work forever onto the mixed template/JS app
- split frontend/backend without freezing the core API contracts first

## 4. Target Responsibilities

## 4.1 Backend Responsibilities

The backend owns:

- authentication and session APIs
- evaluation APIs
- OCR/image ingest APIs
- protocol/scoring logic
- bets/history APIs
- governance APIs
- calibration/outcome enrichment
- persistence and migrations

### Backend must become explicit about

- request/response contracts
- error contracts
- evaluation payload shapes
- OCR review payload shapes
- builder handoff payload shapes

## 4.2 Frontend Responsibilities

The frontend owns:

- page flow
- screen hierarchy
- OCR trust gate experience
- Evaluate result hierarchy
- Builder refinement UX
- History replay UX
- Dashboard routing UX
- client state and navigation

The frontend should not own scoring logic.

## 5. Target Repo Shape

Recommended end state:

```text
betapp/
  apps/
    api/
      app/
      alembic/
      requirements.txt
      pyproject.toml
    web/
      src/
      public/
      package.json
      tsconfig.json
  packages/
    contracts/
      openapi/
      generated-types/
      schemas/
  docs/
```

### Transitional shape

Because the repo is already live, the first transition can be:

```text
app-src/
  app/              # stays as backend
  frontend/         # new dedicated web app
```

This is the least disruptive starting point.

## 6. Suggested Frontend Stack

Recommended stack:

- React
- Next.js or Vite + React Router
- TypeScript
- TanStack Query for API state
- Zod for client-side schema validation

### Recommendation

If you want server rendering and deployment simplicity:

```text
Next.js
```

If you want a thinner client-only app with fewer framework opinions:

```text
Vite + React
```

My recommendation for this project is:

```text
Next.js + TypeScript
```

Because:

- Evaluate and Builder benefit from structured routing
- marketing/auth/app surfaces can live cleanly in one web app
- server components are optional, not required
- deployment and frontend organization stay simple

## 7. API Contract Freeze Before Separation

Before building the new frontend, freeze these backend contracts:

### 7.1 Evaluate

- text evaluation request
- image evaluation request
- evaluation result payload
- guided fix payload
- builder handoff payload

### 7.2 OCR Review

- OCR extraction payload
- parsed slip payload
- confidence / uncertainty fields
- review-required signals

### 7.3 Bets / History

- create bet
- create bet with `evaluation_id`
- history item
- history detail / replay payload

### 7.4 Protocols

- embedded protocol trigger payload
- protocol detail payload
- saved protocol workflow payload if added

### 7.5 Auth

- login
- signup
- current user/session
- admin/debug gating behavior

## 8. Migration Strategy

### Phase 0: Stabilize Backend Contracts

Goal:

- freeze API shapes needed by the new frontend

Deliverables:

- contract docs updated
- OpenAPI or equivalent generated
- explicit error envelopes where needed

### Phase 1: Create Dedicated Frontend App

Goal:

- spin up a new web app without cutting over existing users

Deliverables:

- `frontend/` app scaffold
- auth/session integration
- API client layer
- shared type generation or manual typed contracts

### Phase 2: Migrate Evaluate First

Goal:

- move the product home first

Why:

- Evaluate is the core identity
- OCR trust gate work belongs here
- current Evaluate implementation is the most fragmented

Deliverables:

- Evaluate screen
- OCR upload
- parsed slip confirmation
- evaluation results
- guided fix CTA

### Phase 3: Migrate Builder

Goal:

- preserve the refinement loop

Deliverables:

- Builder screen
- Builder state hydration from Evaluate
- before/after delta
- re-evaluation loop
- bet placement with `evaluation_id`

### Phase 4: Migrate History

Goal:

- bring over the learning replay surface

Deliverables:

- history list
- history detail
- re-evaluate from history
- edit/refine from history

### Phase 5: Migrate Dashboard / Browse / Protocols

Goal:

- complete the user-facing shell

Deliverables:

- Dashboard as action hub
- Browse as research surface
- Protocols as secondary destination

### Phase 6: Retire Old Frontend

Goal:

- remove or freeze the mixed server-template app UI

Deliverables:

- old templates marked legacy or removed
- backend serves APIs primarily, not app UI
- deployment updated to support separated web + api services

## 9. Deployment Model

## 9.1 Short-Term

Keep the current backend deploy path.

Add a separate frontend deploy target.

Example:

```text
betapp-api.example.com
betapp-web.example.com
```

or:

```text
api.example.com
app.example.com
```

## 9.2 Preferred Production Shape

```text
app.example.com   -> frontend
api.example.com   -> FastAPI backend
```

### Backend concerns

- CORS
- auth token strategy
- cookie or bearer-token policy
- environment separation

## 10. Shared Contracts Layer

The separation is much easier if the project introduces a contract package.

At minimum, share:

- OpenAPI schema
- generated TS types
- canonical response envelopes
- frontend-facing domain models

Without this, frontend/backend separation will still drift even if the repos are physically separate.

## 11. Frontend Cutover Rules

### Cut over Evaluate first if:

- evaluation APIs are stable
- OCR flow contract is explicit
- Builder handoff payload is stable

### Do not cut over Builder until:

- Evaluate can hand context cleanly
- `evaluation_id` flow is confirmed end-to-end

### Do not retire old templates until:

- new frontend has parity for core loop
- auth works
- history replay works
- placement/save flows work

## 12. Risks

### Risk 1: Contract drift

Mitigation:

- freeze contracts first
- use generated types if possible

### Risk 2: Two frontends living too long

Mitigation:

- migrate in a strict order
- name the old app legacy once the new one exists

### Risk 3: OCR and Evaluate logic split badly

Mitigation:

- keep OCR parsing and evaluation on backend
- let frontend own trust gate UX only

### Risk 4: Frontend rewrite before product priorities are settled

Mitigation:

- use the canonical UX docs already created

## 13. Recommended Immediate Actions

1. Create the separation branch/plan and commit the docs.
2. Freeze the Evaluate, OCR, Builder handoff, bets, and history contracts.
3. Scaffold `frontend/` with the chosen stack.
4. Build Evaluate first.
5. Keep backend templates only as legacy fallback during migration.

## 14. Executive Recommendation

Do this separation.

But do it as:

```text
backend contract stabilization
→ dedicated frontend scaffold
→ Evaluate migration
→ Builder migration
→ History migration
→ broader shell migration
```

That is the right balance between product momentum and architectural cleanup.
