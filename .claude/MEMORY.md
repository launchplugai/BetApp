# DNA Bet Engine - Claude Memory

This file contains persistent context for Claude Code sessions on the DNA project.

## Project Identity

- **Name:** DNA Bet Engine (DNA Matrix)
- **Production:** https://dna-production-cb47.up.railway.app
- **Repo:** launchplugai/DNA
- **Runtime:** Python 3.12 | FastAPI | Uvicorn
- **Deployment:** Railway (Nixpacks auto-build on push to `main`)

## Current Sprint Status

- **Sprint 1:** LOCKED (all tickets complete)
- **Sprint 2:** Pending PO approval

## Key Files

| File | Purpose |
|------|---------|
| `app/routers/web.py` | Main UI (HTML + JavaScript) |
| `app/pipeline.py` | Evaluation pipeline facade |
| `app/airlock.py` | Input validation gateway |
| `dna-matrix/core/evaluation.py` | Core engine (DO NOT MODIFY) |
| `docs/SPRINT_PLAN.md` | Sprint definitions |
| `docs/RALPH_LOOP.md` | Governance rules |

## Hard Rules

1. **DO NOT** modify `dna-matrix/core/evaluation.py` logic
2. **DO NOT** add ML, live odds, or stats feeds
3. **DO NOT** activate dormant modules (alerts/, context/, auth/, billing/)
4. All tests must pass before push
5. iPhone Safari compatibility required
6. Commit messages must include ticket numbers

## CLI Commands

```bash
# Run all tests
pytest

# Run specific test file
pytest app/tests/test_web.py -v

# Start local server
PYTHONPATH=dna-matrix:$PYTHONPATH uvicorn app.main:app --reload

# Health check (production)
curl https://dna-production-cb47.up.railway.app/health

# Lint
ruff check .
```

## Recent Tickets Completed

- Ticket 34: OCR → Builder Precision
- Ticket 35: Inline Refine Loop
- Ticket 36: OCR Regression Repair
- Ticket 37: Deterministic leg_id
- Ticket 37B: SHA-256 hash upgrade
- Ticket 38: Notable Legs v2
- Ticket 38A: OCR error rendering fix

## Test Counts

- `app/tests/test_web.py`: 183 tests
- `app/tests/test_pipeline.py`: 43 tests (including Ticket 38 notable legs tests)
