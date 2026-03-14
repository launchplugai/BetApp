# Airlock Membrane Contract

**Version:** 1.0.0  
**Status:** CANONICAL  
**Last Updated:** 2026-03-14

## 1. Purpose

This contract restores Airlock as the membrane between major BetApp layers.

Airlock is not merely input validation.

Airlock is responsible for governing what is allowed to pass between:

- frontend and backend
- protocol intent and reasoning
- reasoning and frontend-safe output

## 2. Responsibilities

Airlock must own:

- input sanitization
- schema validation
- canonical normalization
- boundary authorization
- output shaping
- safe-field filtering
- boundary audit metadata

Airlock must not own:

- scoring logic
- protocol scoring weights
- entity truth storage
- Sherlock reasoning
- DNA persistence internals

## 3. Inbound Flow

Inbound requests may come from:

- text evaluate
- OCR review
- image evaluate
- builder refinement
- bet placement
- history replay/edit

Inbound Airlock duties:

1. validate schema
2. sanitize free text
3. normalize shape
4. resolve canonical tier/mode names
5. canonicalize detected legs when present
6. reject malformed or unauthorized cross-layer fields

## 4. Outbound Flow

Outbound results may include:

- evaluation result
- OCR review result
- builder handoff payload
- protocol trigger payload
- history replay payload

Outbound Airlock duties:

1. shape result into frontend-safe contract
2. suppress backend-private internals
3. preserve required identifiers
4. expose uncertainty explicitly
5. preserve auditability without leaking implementation guts

## 5. Allowed Cross-Layer Objects

Allowed objects through Airlock:

- normalized user input
- canonical detected legs
- evaluation identifiers
- score payloads
- protocol trigger payloads
- builder handoff payloads
- user-visible explanation payloads

Forbidden direct pass-through:

- ORM models
- raw database rows
- backend-private governance state
- Sherlock internal iteration artifacts
- DNA persistence internals
- undeclared experimental fields

## 6. Authorization Rules

Airlock must reject:

- unknown privileged flags from frontend
- backend-only override fields
- attempts to set protected model versions
- attempts to inject protocol trigger state directly
- attempts to provide trusted OCR output without review path

## 7. Frontend Rule

The frontend may depend only on:

- frozen Airlock contracts
- additive documented fields

The frontend must not depend on:

- template-only assumptions
- backend-private compatibility fields
- undocumented output structure

## 8. Sherlock Rule

Sherlock must receive only normalized, authorized asks.

Sherlock must return only:

- reasoned conclusions
- evidence and counterevidence
- confidence and uncertainty
- requested structured result fields

Any Sherlock-internal audit or mutation artifacts are not frontend-safe by default.

Airlock decides what becomes publishable.

## 9. DNA Rule

DNA must not be exposed directly to the frontend.

DNA fragments may be requested by Sherlock and shaped back through Airlock, but raw ontology structures are not implicitly frontend-facing.

## 10. Guardrails

Hard guardrails:

- No layer may bypass Airlock for frontend-facing contracts.
- Airlock changes require contract review.
- New frontend surfaces must map to explicit Airlock contracts before implementation.
- No silent passthrough of new fields from backend internals to frontend.

Soft guardrails:

- prefer additive contract evolution
- prefer normalized IDs and naming
- keep legacy compatibility fields only during migration windows

## 11. Minimum Enforcement Targets

The following surfaces must be routed through explicit Airlock contracts:

- `POST /app/evaluate`
- `POST /api/ocr/review`
- builder handoff payload
- `POST /api/bets/`
- `GET /api/bets/history`
- history replay/detail payloads

## 12. Relationship To Existing Code

Current implementation entrypoint:

- `app/airlock.py`

Current implementation is partial.

This contract is the target state that future refactors must restore.
