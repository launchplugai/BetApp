# CLAUDE CHAT PACKAGE — DNA BET ENGINE

> **Version:** 2.0 | **Updated:** 2026-01-26 | **Purpose:** Full context transfer for any new Claude session

---

## 1. ROLE & IDENTITY

You are Claude acting as a focused **frontend / integration engineer** on a sports parlay evaluation product called **DNA Matrix** (aka the DNA Bet Engine).

**Repo:** `launchplugai/DNA`
**Production:** `https://dna-production-b681.up.railway.app`
**Runtime:** Python 3.12 | FastAPI | Uvicorn
**Deployment:** Railway (Nixpacks auto-build on push to `main`)

---

## 2. PROJECT STATE (SNAPSHOT)

| Component | Status |
|-----------|--------|
| Core evaluation engine | **COMPLETE AND LIVE** |
| API endpoints | **STABLE** |
| Tier gating (GOOD / BETTER / BEST) | **ENFORCED SERVER-SIDE** |
| Web UI (`/app`) | **LIVE** (4-tab: Discover / Evaluate / Builder / History) |
| Voice/TTS narration | **LIVE** |
| Breaking changes to core logic | **PROHIBITED** |

---

## 3. SPRINT STATUS

| Sprint | Focus | Status |
|--------|-------|--------|
| 1 | Parlay Builder + Evaluation Flow | **LOCKED** (all 5 DoD gates PASS) |
| 2 | Explainability + Trust | **Pending** |
| 3 | Context Ingestion | Pending |
| 4 | Live Signals + Alerts | Pending |
| 5 | Harden + Monetize | Pending |

**Sprint 1 Lock:** `docs/sprints/SPRINT_1_LOCK.md`
**Sprint Plan:** `docs/SPRINT_PLAN.md` (LOCKED 2026-01-16)

### Sprint 1 Delivered Tickets

| # | Title |
|---|-------|
| 1 | UI Flow Lock |
| 2 | Core Loop Reinforcement |
| 3 | GOOD Tier Structured Evaluation Output |
| 4 | primaryFailure + deltaPreview |
| 6 | History MVP |
| 6B | Canonical /history endpoints + evaluationId contract |
| 7A | Fix default tab to Discover |
| 8 | Bet Slip-First Evaluate UX |
| 9 | Builder Improvement Workbench (No Manual Parlay Typing) |
| 10 | Deployment Stamp |
| 11 | Lock Sprint 1 + Governance Snapshot |
| 12 | Split web.py into maintainable parts |

### Sprint 2 Scope (NEXT — NOT STARTED)

**Goal:** User understands WHY the engine said what it said.

**Deliverables:**
- Visual sections mapped to engine stages: Structural Risk, Correlation, Fragility, Context Snapshot (static)
- Tier behavior: GOOD = headlines only, BETTER = summaries, BEST = full breakdown + narration

**Prerequisite:** Product Owner must approve Sprint 2 ticket set before work begins.

---

## 4. RALPH LOOP — GOVERNANCE SYSTEM

**Source:** `docs/RALPH_LOOP.md`

### The Loop
```
Build -> Validate -> Explain -> Observe -> Adjust -> Lock
```

Each phase must complete before advancing. No shortcuts.

### Sprint Advancement Gates
- [ ] Working endpoint
- [ ] Visible UI proof
- [ ] Clear explanation mapping
- [ ] All tests passing

### Feature Qualification Test

> "What user decision does this improve?"

- **PASS:** "Shows correlation risk so user knows if legs are too dependent"
- **FAIL:** "Makes the architecture more elegant"
- **FAIL:** "Prepares for future features"

### Refactor Policy

**No refactors unless something is broken.** "Clean code" is not justification. "It works" is the standard.

### Module Scope Gate (HARD RULE)

Any ticket that introduces a new folder or module beyond the current sprint scope must be **BLOCKED** unless explicitly approved by the Product Owner.

This includes:
- Creating new top-level directories
- Adding imports from out-of-scope modules (`alerts/`, `context/`, `auth/`, `billing/`, `persistence/`)
- Activating scaffolded-but-dormant code from future sprints
- Adding dependencies that serve future sprint features

**Violations are rolled back. No exceptions.**

### Sprint Lock Step Checklist

Before proceeding to the next sprint, ALL of the following must be complete:

- [ ] Lock document exists in `docs/sprints/SPRINT_N_LOCK.md`
- [ ] Definition of Done checklist shows all items PASS
- [ ] Full test suite passes with zero regressions
- [ ] Release notes updated in `docs/RELEASE_NOTES.md`
- [ ] Out-of-scope modules verified as dormant
- [ ] No uncommitted or unreviewed changes remain
- [ ] Product Owner has approved next sprint ticket set
- [ ] New sprint ticket set documented before any work begins

**If any item fails, sprint is not locked and advancement is blocked.**

---

## 5. HARD CONSTRAINTS

| Constraint | Reason |
|------------|--------|
| Do NOT redesign the engine | Already works, is live |
| Do NOT introduce speculative AI behavior | Must be deterministic |
| Do NOT remove explainability | Core product differentiator |
| All logic must be auditable | User trust requirement |
| Do NOT modify `dna-matrix/core/evaluation.py` logic | Engine is frozen |
| Do NOT bypass tier gating from the client | Server is source of truth |
| Do NOT activate dormant modules | Scope gate enforced |

---

## 6. ARCHITECTURE

### Directory Structure

```
DNA/
+-- app/                           # FastAPI application (ACTIVE)
|   +-- main.py                    # Entrypoint (middleware, routes, /health, /build)
|   +-- airlock.py                 # Input validation gateway (ONLY entry point)
|   +-- pipeline.py                # Evaluation facade (Airlock -> Engine -> Response)
|   +-- config.py                  # Centralized config + env var loading
|   +-- tiering.py                 # Tier gating logic
|   +-- correlation.py             # Request correlation IDs
|   +-- rate_limiter.py            # Token-bucket rate limiting
|   +-- history_store.py           # In-memory evaluation history
|   +-- build_info.py              # Deployment metadata
|   +-- routers/
|   |   +-- web.py                 # Web UI router (HTML + forms, 2652 lines)
|   |   +-- leading_light.py       # Leading Light API (JSON evaluation)
|   |   +-- panel.py               # Developer panel
|   |   +-- history.py             # History endpoints
|   +-- schemas/
|   |   +-- leading_light.py       # Request/response schemas
|   +-- image_eval/
|   |   +-- extractor.py           # OCR/image processing for bet slips
|   +-- voice/
|   |   +-- router.py              # Voice/TTS endpoints
|   |   +-- narration.py           # Narration generation
|   |   +-- tts_client.py          # OpenAI TTS client
|   +-- web_assets/
|   |   +-- static/                # CSS, JS
|   |   +-- templates/             # HTML templates
|   +-- tests/                     # 14 test files
|
+-- dna-matrix/                    # Core evaluation engine (DO NOT MODIFY LOGIC)
|   +-- core/
|   |   +-- evaluation.py          # Main orchestrator (evaluate_parlay)
|   |   +-- parlay_reducer.py      # Parlay state + correlations
|   |   +-- correlation_engine.py  # Correlation detection
|   |   +-- risk_inductor.py       # Risk level computation
|   |   +-- dna_enforcement.py     # DNA profile constraints
|   |   +-- fragility_engine.py    # Fragility calculation
|   |   +-- suggestion_engine.py   # Fix suggestions
|   |   +-- alert_engine.py        # Alert generation
|   |   +-- context_adapters.py    # Context integration
|   |   +-- builder_contract.py    # Builder protocol
|   |   +-- models/
|   |   |   +-- leading_light.py   # Core data types (679 lines)
|   |   |   +-- claim.py
|   |   |   +-- common.py
|   |   |   +-- organism.py
|   +-- tests/core/                # 4 core test files
|
+-- docs/                          # Project documentation
|   +-- SPRINT_PLAN.md             # Locked sprint definitions
|   +-- RALPH_LOOP.md              # Governance rules
|   +-- RELEASE_NOTES.md           # Sprint 1 changelog
|   +-- deploy.md                  # Deployment verification guide
|   +-- FUTURE_EXTRACTIONS.md      # Code to port from closed PR #4
|   +-- sprints/
|       +-- SPRINT_1_LOCK.md       # Sprint 1 completion record
|
+-- alerts/                        # Sprint 4 (DORMANT)
+-- context/                       # Sprint 3 (DORMANT)
+-- auth/                          # Future (DORMANT)
+-- billing/                       # Sprint 5 (DORMANT)
+-- persistence/                   # Future (DORMANT)
+-- data/                          # Data storage
|
+-- CLAUDE.md                      # THIS FILE
+-- README.md                      # Project overview
+-- CHANGELOG.md                   # Version history
+-- progress.txt                   # Task tracking log
+-- requirements.txt               # Python dependencies
+-- pyproject.toml                 # Project config + pytest + linting
+-- railway.json                   # Railway deployment config
+-- Procfile                       # Process definition
+-- runtime.txt                    # Python 3.12
```

### Request Flow

```
Browser -> /app/evaluate (POST)
           |
           v
       Airlock (validate + normalize input)
           |
           v
       Pipeline (run_evaluation)
           |
           v
       dna-matrix/core/evaluation.py (evaluate_parlay)
           |
           v
       Tier filtering (GOOD / BETTER / BEST)
           |
           v
       HTML or JSON response
```

### Live Routes

| Route | Method | Description |
|-------|--------|-------------|
| `/app` | GET | Main UI (4-tab: Discover / Evaluate / Builder / History) |
| `/app/evaluate` | POST | Evaluation submission |
| `/health` | GET | Health check + service metadata |
| `/build` | GET | Build info (commit hash, build time, env) |
| `/history` | GET | Evaluation history list |
| `/history/{id}` | GET | Single evaluation by ID |
| `/leading-light/evaluate/text` | POST | Core text evaluation API (JSON) |
| `/leading-light/evaluate/image` | POST | Image evaluation API (bet slip OCR) |
| `/voice/*` | * | Voice narration endpoints |
| `/panel` | GET | Developer testing panel |

---

## 7. CORE ENGINE INTERNALS (READ-ONLY REFERENCE)

### evaluate_parlay() Response Shape

```python
EvaluationResponse (frozen):
  parlay_id: UUID
  inductor: InductorInfo
    level: RiskInductor (STABLE / LOADED / TENSE / CRITICAL)
    explanation: str
  metrics: MetricsInfo
    raw_fragility, final_fragility, leg_penalty,
    correlation_penalty, correlation_multiplier
  correlations: tuple[Correlation, ...]
  dna: DNAInfo
    violations, base_stake_cap, recommended_stake,
    max_legs, fragility_tolerance
  recommendation: Recommendation
    action: ACCEPT / REDUCE / AVOID
    reason: str
  suggestions: Optional[tuple[SuggestedBlock, ...]]
```

### Recommendation Rules
- STABLE => ACCEPT
- LOADED => ACCEPT
- TENSE => REDUCE
- CRITICAL => AVOID
- DNA enforcement can only **downgrade** (ACCEPT -> REDUCE -> AVOID), never upgrade

### Signal System (Pipeline)
```python
SIGNAL_MAP = {
    "blue":   {"label": "Strong",  "css": "signal-blue"},
    "green":  {"label": "Solid",   "css": "signal-green"},
    "yellow": {"label": "Fixable", "css": "signal-yellow"},
    "red":    {"label": "Fragile", "css": "signal-red"},
}
```

### Tier Enum (Canonical via Airlock)
```python
class Tier(str, Enum):
    GOOD = "good"       # Free tier. "free" is aliased to "good"
    BETTER = "better"
    BEST = "best"
```

### Tier Display Behavior
- **GOOD:** Overall grade + short verdict. Locked sections visible but blurred/disabled
- **BETTER:** Summary insights unlocked
- **BEST:** Full explanation + narration flag + all breakdowns

### System Invariants
- Fragility never decreases due to context
- Context signals never generate bets
- All context deltas must be >= 0
- effectiveFragility >= baseFragility
- finalFragility clamped [0, 100]
- correlationMultiplier must be one of [1.0, 1.15, 1.3, 1.5]

---

## 8. ENVIRONMENT & CONFIGURATION

### Environment Variables (Railway)

| Variable | Purpose | Default |
|----------|---------|---------|
| `PORT` | Server port | `8000` |
| `RAILWAY_ENVIRONMENT` | Environment name | `"development"` |
| `RAILWAY_GIT_COMMIT_SHA` | Deploy commit hash | (auto-set by Railway) |
| `GIT_SHA` | Fallback commit hash | (manual) |
| `MAX_REQUEST_SIZE_BYTES` | Max request body | `1048576` (1MB) |
| `LEADING_LIGHT_ENABLED` | Enable evaluation API | `true` |
| `VOICE_ENABLED` | Enable voice/TTS | `true` |
| `OPENAI_API_KEY` | OpenAI API key for TTS | (secret, presence-checked only) |

### Security Config
- Sensitive substrings never logged: `key`, `token`, `secret`, `password`, `credential`, `auth`
- Config snapshot at startup logs structure but **never actual secret values**
- Only boolean `openai_api_key_present` is stored/logged

### Rate Limiting
- 10 requests/min per IP
- Burst allowance: 3
- Token bucket algorithm

### Input Validation (Airlock)
- Max input: 10,000 characters
- Min input: 1 character
- All input passes through `airlock_ingest()` (single entry point)
- No raw input in logs

---

## 9. DEPLOYMENT (RAILWAY)

### How to Deploy
```bash
git push origin main
```
Railway auto-deploys on push. Nixpacks auto-detects Python and installs from `requirements.txt`.

### Verify Deployment
```bash
# Health check
curl -sS https://dna-production-b681.up.railway.app/health | python -m json.tool

# Verify deployed commit matches
curl -sS https://dna-production-b681.up.railway.app/health | python -m json.tool | grep git_sha
git rev-parse HEAD
```

### Railway Config (`railway.json`)
```json
{
  "build": { "builder": "NIXPACKS" },
  "deploy": {
    "startCommand": "PYTHONPATH=/app/dna-matrix:$PYTHONPATH uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000}",
    "healthcheckPath": "/health",
    "healthcheckTimeout": 30,
    "restartPolicyType": "ON_FAILURE",
    "restartPolicyMaxRetries": 3
  }
}
```

### No CI/CD Pipeline
No `.github/workflows` exist. Deployment is push-to-Railway only. Tests must be run locally before push.

---

## 10. CLI COMMANDS

```bash
# Run all tests
pytest

# Run tests verbose
pytest -v

# Run specific test file
pytest app/tests/test_web.py

# Start local server
uvicorn app.main:app --reload

# Start with PYTHONPATH (matches Railway)
PYTHONPATH=dna-matrix:$PYTHONPATH uvicorn app.main:app --reload

# Health check (production)
curl https://dna-production-b681.up.railway.app/health

# Health check (local)
curl http://localhost:8000/health

# Build info
curl https://dna-production-b681.up.railway.app/build

# Lint
ruff check .

# Format
black .

# Type check
mypy .
```

---

## 11. GIT & BRANCHING

### Branch Convention
- Feature branches: `claude/<description>-<session-id>`
- Main branch: `main`
- Push with: `git push -u origin <branch-name>`

### Recent Commit History (as of 2026-01-26)
```
2240b5a Ticket 12: Split web.py into maintainable parts (no behavior change)
8805a95 Ticket 11: Lock Sprint 1 + Governance Snapshot (docs only)
4900d4a Ticket 10: Deployment stamp - build visibility for UI and API
fea4b19 Ticket 9: Builder Improvement Workbench (No Manual Parlay Typing)
14fc0f2 Ticket 8: Bet Slip-First Evaluate UX
```

---

## 12. DEPENDENCIES (`requirements.txt`)

```
pytest>=8.0.0,<10.0.0
fastapi>=0.115.0
uvicorn>=0.30.0
python-multipart>=0.0.7
black>=24.0.0
mypy>=1.8.0
ruff>=0.5.0
httpx>=0.27.0
openai>=1.0.0
bcrypt>=4.1.0
stripe>=7.0.0
```

**Note:** `bcrypt` and `stripe` are installed but their modules (`auth/`, `billing/`) are **dormant** until their designated sprints.

---

## 13. TESTING

### Framework
- **pytest** with config in `pyproject.toml`
- Test paths: `dna-matrix/tests`, `auth/tests`, `persistence/tests`, `alerts/tests`, `context/tests`, `billing/tests`, `app/tests`
- Python path includes: `.` and `dna-matrix`
- Options: `-v --tb=short`

### Test Count
- ~173 tests passing at Sprint 1 lock
- 14 app test files + 4 core test files + framework tests for dormant modules

### Run Before Every Push
```bash
pytest
```
Zero regressions required. No push if tests fail.

---

## 14. DORMANT MODULES (DO NOT ACTIVATE)

| Module | Path | Sprint | Notes |
|--------|------|--------|-------|
| Alerts | `alerts/` | Sprint 4 | Proactive signals |
| Context | `context/` | Sprint 3 | Injury/weather/trade data |
| Auth | `auth/` | Future | JWT authentication |
| Billing | `billing/` | Sprint 5 | Stripe payments |
| Persistence | `persistence/` | Future | Database storage |

These are scaffolded. Do not import, activate, or depend on them until their sprint is approved and started.

---

## 15. FUTURE EXTRACTIONS (from closed PR #4)

Documented in `docs/FUTURE_EXTRACTIONS.md`. Code to port from branch `claude/audit-dependencies-mk44qyna6tfaezq4-dCbHr`:

1. **User Profiling System** (Sprint 2-3): `BettingPersonality`, trait-based evaluation
2. **Enhanced Airlock Validation** (Sprint 5): 7-chromosome pipeline, quarantine system
3. **Coherence Analysis** (Sprint 3): Detects conflicting user traits

---

## 16. SESSION START PROTOCOL

1. Read this file (CLAUDE.md)
2. Check `docs/SPRINT_PLAN.md` for current sprint status
3. Check `docs/RALPH_LOOP.md` for governance constraints
4. Acknowledge sprint scope and constraints
5. Verify which sprint is active (Sprint 1 is LOCKED; Sprint 2 is PENDING PO approval)
6. Begin work only on approved items

**Do NOT start Sprint 2 work without Product Owner approval and a documented ticket set.**
