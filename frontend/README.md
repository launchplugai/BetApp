# Frontend Split Scaffold

This directory is the additive frontend scaffold described in the canonical separation docs.

Current scope:

- `POST /app/evaluate`
- `POST /api/ocr/review`

Current runtime note:

- `npm start` and `npm run dev` use a zero-dependency fallback server in `dev-server.mjs`
- the Next.js scaffold remains in `src/` and is still the planned destination once local package install is healthy
- fallback routes currently available:
  - `/` for Evaluate text input
  - `/review` for OCR review upload and payload inspection
  - `/builder` for Builder handoff persistence and re-evaluation
  - `/history` for persisted bet history plus dev replay history

Next scaffold progress:

- `src/app/evaluate/page.tsx`
- `src/app/evaluate/review/page.tsx`
- `src/app/builder/page.tsx`
- `src/app/history/page.tsx`

Rules for parallel work:

- frontend code should consume frozen contracts from `src/lib/contracts/`
- backend changes should stay additive unless the canonical contract docs are updated first
- Builder, bets, and history routes should be added behind the same typed client pattern
