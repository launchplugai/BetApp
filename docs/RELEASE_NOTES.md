# RELEASE NOTES

---

## Sprint 1 — Parlay Builder + Evaluation Flow

**Lock Date:** 2026-01-26
**Branch:** `claude/lock-sprints-chat-package-QXI7T`
**Commit:** `4900d4a`

### What Shipped

- **Discover / Evaluate / Builder / History tabs** — Four-tab UI at `/app` for end-to-end parlay workflow
- **Parlay Builder** — Manual leg construction (basketball only), bet slip import via image OCR, builder-as-fix-mode from evaluation results
- **Evaluation flow** — Text and image-based evaluation against the live engine; tier-gated results (GOOD / BETTER / BEST)
- **Structured results** — Primary failure highlight, fastest fix recommendation, delta preview, signal-level breakdown
- **Tier gating** — GOOD tier shows overall grade + verdict; BETTER/BEST unlock deeper insights. Locked sections visible but blurred for upsell
- **History** — Evaluation history storage and retrieval (`GET /history`, `GET /history/{id}`), evaluationId-based contract
- **Bet slip import** — Image upload extracts parlay legs via OCR, populates builder automatically
- **Builder improvement workbench** — Removed manual parlay typing; builder entered via fix CTA or slip import
- **Deployment stamp** — `/build` endpoint and UI footer showing commit hash, build time, environment
- **Developer panel** — `/panel` route for internal testing (text + image evaluation)
- **Voice narration** — `/voice/*` endpoints for TTS narration of evaluation results
- **Rate limiting + input validation** — Airlock module sanitizes all input; rate limiter prevents abuse

### Known Constraints

- **No sportsbook execution** — DNA evaluates parlays but does not place bets
- **No live odds** — Odds are user-supplied, not fetched from a live feed
- **No live injury/lineup data** — Context ingestion is Sprint 3
- **No alerts** — Proactive signals are Sprint 4
- **No authentication/billing** — Auth and payment modules are scaffolded but dormant
- **No persistent storage** — History is in-memory only; persistence module is scaffolded but not active
- **Basketball only** — Sport selector is constrained to NBA for Sprint 1

### Out-of-Scope Modules (Present but Dormant)

- `alerts/` — Sprint 4
- `context/` — Sprint 3
- `auth/` — Future
- `billing/` — Sprint 5
- `persistence/` — Future
