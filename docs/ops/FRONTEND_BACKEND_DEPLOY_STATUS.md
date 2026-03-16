# Frontend/Backend Deploy Status

Last updated: 2026-03-15

## Purpose

This memo captures the current deploy-review state of the frontend/backend separation work so the team can evaluate the split in deployment without confusing that goal with the still-incomplete frontend runtime migration.

## Status

### Green

- `POST /app/evaluate` is a stable frontend-facing contract for the Evaluate-first slice.
- `POST /api/ocr/review` is separated from evaluation and can be used by the new frontend review flow.
- `GET /api/bets/history` is the canonical persisted history list base for the first split.
- `GET /api/bets/{bet_id}` now safely exposes additive replay context without requiring evaluation-log enrichment to be available.
- The additive frontend under `frontend/` exercises the separated flow end to end through the fallback runtime.

### Yellow

- Builder handoff is still a frontend-state contract rather than a dedicated backend API contract.
- Persisted History replay is usable, but not always canonical. When replay is derived from stored bet data instead of an evaluation log, the payload is explicitly marked as fallback-derived.
- The Next scaffold under `frontend/src/` is materially migrated, but it is not yet the active runtime.

### Red

- The final Next runtime/toolchain is still blocked by package-install behavior in this environment.
- Legacy replay support under `/app/history` still exists during the migration and has not been fully retired.

## What A Deploy Review Should Answer

- Does the new frontend consume the frozen contracts without needing backend internals?
- Does the backend continue to support the first slice without frontend-specific branching?
- Does persisted History provide enough replay context to support Builder continuation?
- Are any remaining problems separation problems, or are they frontend runtime/tooling problems?

## Deploy Verification Checklist

1. Deploy the current FastAPI backend changes.
2. Verify `POST /app/evaluate` returns a stable top-level `evaluationId`.
3. Verify `POST /api/ocr/review` returns review data without evaluating automatically.
4. Verify authenticated `GET /api/bets/history` responds successfully.
5. Verify authenticated `GET /api/bets/{bet_id}` responds successfully even if evaluation-log enrichment is unavailable.
6. Run the fallback frontend from `frontend/dev-server.mjs`.
7. Walk the user flow:
   - `/` Evaluate
   - `/review` OCR review
   - `/builder` Builder handoff
   - `/history` persisted History and replay
8. On History, confirm a persisted bet detail can be loaded and replay can be sent to Builder.
9. Treat any failure isolated to the Next runtime as a tooling/platform issue, not evidence that the contract split failed.

## Bottom Line

The current codebase is ready for a deployment-based review of the frontend/backend separation for the first slice.

The main incomplete work is not the backend boundary. It is the final frontend runtime migration from the fallback server to the intended Next runtime.
