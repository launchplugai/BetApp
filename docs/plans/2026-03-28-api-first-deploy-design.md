# BetApp v1 — API-First Deploy Design

**Date:** 2026-03-28
**Status:** Approved
**Approach:** API-First (backend deploy, then frontend)

## Decisions

- **Auth:** None for v1 — public access, add auth later
- **Frontend:** Use existing Next.js app in `app-src/frontend/`, wire shells to real API
- **Backend:** Docker container on Hostinger VPS via existing Traefik stack
- **Deployment:** Vercel (frontend) + Hostinger VPS (backend)
- **Rejected:** Full-stack vertical slice (too many moving parts in one sprint), Frontend-first with mocks (fake progress, double work)

## Environment & Secrets

Single `.env.example` at repo root — source of truth for all required config. Actual secrets:
- VPS: `.env` on server (never committed)
- Vercel: Dashboard environment variables
- Local: `.env` copied from `.env.example`

## Sprint 1: Backend Deploy to VPS

**Goal:** FastAPI container running on Hostinger, protocol endpoints live, health check passing.

### What ships:
- Strip auth middleware from protocol routes (public access)
- Update docker-compose.yml for Hostinger Traefik stack
- Consolidated .env.example with every required key documented
- Deploy container, verify /health and /api/protocols respond

### Endpoints live:
| Endpoint | Purpose |
|---|---|
| GET /health | Container health |
| POST /api/protocols | Create protocol |
| GET /api/protocols | List protocols |
| GET /api/protocols/{id} | Protocol detail |
| GET /api/protocols/{id}/recommendations | Get recommendations |
| POST /api/protocols/{id}/build-parlay | Build parlay |
| POST /app/evaluate | DNA engine evaluation |

### Verification:
- curl health check
- curl protocol CRUD
- browse skill to verify API responses

## Sprint 2: Frontend on Vercel

**Goal:** Next.js app on Vercel hitting the live VPS API. User visits URL, creates protocol, sees recommendations.

### What ships:
- Wire existing Next.js page shells to real API (protocol CRUD, recommendations)
- NEXT_PUBLIC_API_URL env var pointing to VPS
- Vercel deploy config
- browse/playwright QA on each page

## Iteration Model

After sprints 1+2, every feature is a thin vertical slice:
- Build parlay UI > evaluate UI > history UI
- Each ships independently, each gets browse/playwright QA
- Auth added when needed, not before

## Success Criteria

- /health returns 200 from VPS URL
- Can create a protocol via API and get recommendations
- Next.js app loads on Vercel URL
- Full protocol flow works end-to-end in browser
