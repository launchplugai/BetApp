# Airlock Route Gap Audit

**Status:** CANONICAL  
**Last Updated:** 2026-03-14

This document is the Sprint B route-by-route audit for restoring Airlock as a membrane.

## 1. Purpose

Identify which current routes already align with the Airlock membrane contract and which still need restoration work.

## 2. Current Route Status

| Surface | Route | Inbound Airlock | Outbound Airlock | Status | Notes |
|---------|-------|-----------------|------------------|--------|-------|
| Text Evaluate | `POST /app/evaluate` | yes | yes, minimum viable | `PARTIAL` | Inbound validation is active; outbound shaping and explicit builder handoff are now routed through Airlock |
| OCR Review | `POST /api/ocr/review` | partial | partial | `PARTIAL` | Contract is already frontend-safe, but route does not yet call a shared Airlock membrane helper |
| Image Evaluate | `POST /app/evaluate/image` | mixed | mixed | `GAP` | Still legacy-compatible and not the canonical frontend OCR path |
| Builder handoff | derived from evaluate response | yes, via evaluate response | yes, minimum viable | `PARTIAL` | Explicit `builderHandoff` payload now exists, but no dedicated route exists yet |
| Bet create | `POST /api/bets/` | no | no | `GAP` | Safe enough for milestone use, but not yet routed through explicit Airlock helpers |
| Bet history | `GET /api/bets/history` | n/a | no | `GAP` | Stable contract for first slice, but not yet owned by Airlock shaping |
| History replay detail | `GET /history/{item_id}` | n/a | no | `GAP` | Useful for replay/edit, but not yet aligned to the membrane contract |

## 3. Milestone Decision

For the first sprint milestone, minimum viable Airlock restoration means:

- `POST /app/evaluate` must use Airlock for both ingest and frontend-safe output shaping
- OCR trust gate must remain on the dedicated `POST /api/ocr/review` contract
- Builder handoff must be explicit in the evaluation response

That milestone is now reached.

## 4. Next Restoration Targets

1. pull OCR review shaping into explicit shared Airlock helpers
2. define a dedicated builder handoff contract or route if needed
3. normalize bet and history outputs through Airlock
4. retire reliance on history-template-specific replay payloads

## 5. Guardrail

No new frontend surface should depend on:

- backend-private fields
- ad hoc route-specific compatibility data
- direct DNA or Sherlock internals

Frontend-facing surfaces should target Airlock-shaped contracts only.
