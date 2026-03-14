# Active Frontend Ownership Map

**Status:** CANONICAL  
**Last Updated:** 2026-03-14

This document identifies which frontend surfaces are actively mounted, which are compatibility bridges, and which are currently parallel or legacy implementation paths.

## 1. Purpose

BetApp frontend work has drifted across multiple templates and JS entrypoints.

Before more frontend changes land, contributors need one honest answer to:

```text
Which frontend files actually own the live product flow right now?
```

## 2. Current Ownership Summary

| Surface | Current Owner | Status | Notes |
|---------|---------------|--------|-------|
| `/app` default experience | `app/templates/screens/dashboard.html` | `ACTIVE` | Current default mounted screen in `app/routers/web.py` |
| `/app?screen=builder` | `app/templates/screens/builder.html` + `app/web_assets/static/js/builder.js` | `ACTIVE` | Builder flow is actively mounted and should route via `/app?screen=*` |
| `/app?screen=browse` | `app/templates/screens/browse.html` | `ACTIVE` | Active browse flow |
| `/app/evaluate` API | `app/routers/web.py` + Airlock shaping | `ACTIVE` | Current frontend-safe Evaluate boundary |
| OCR review contract | `app/routers/ocr.py` | `ACTIVE` | Canonical OCR trust-gate API contract |
| `app/templates/app/index.html` + `/static/js/app.js` | Evaluate workbench prototype path | `PARALLEL_NON_MOUNTED` | Rich Evaluate/OCR workbench exists but is not the default mounted `/app` surface today |
| `app/web_assets/templates/app.html` + `/static/app.js` | Older workbench path | `LEGACY_PARALLEL` | Separate builder workbench implementation, not the canonical mounted app |
| `/ui2` | redirect in `app/routers/web.py` | `COMPATIBILITY_ONLY` | Bridge only, not architecture truth |
| `/new` | redirect in `app/routers/web.py` | `COMPATIBILITY_ONLY` | Bridge only, not architecture truth |
| `app/routers/web_old.py` | historical router | `LEGACY_NON_ROUTED` | Retained for reference only |
| `app/routers/_deprecated_web_legacy.py` | historical router | `LEGACY_NON_ROUTED` | Deprecated, non-routed |

## 3. Canonical Truth

Today, the active mounted app is not one single rich Evaluate workbench template.

It is a screen-routed app under:

```text
/app?screen=*
```

owned primarily by:

- `app/templates/screens/dashboard.html`
- `app/templates/screens/builder.html`
- `app/templates/screens/browse.html`
- related active screen templates

The canonical API boundary for evaluation is:

- `POST /app/evaluate`
- `POST /api/ocr/review`

## 4. Important Clarification

The following files are real and useful, but they are not the current mounted source of truth for `/app`:

- `app/templates/app/index.html`
- `app/web_assets/static/js/app.js`

These should be treated as a parallel Evaluate/OCR workbench implementation path.

That means:

- they are not fake
- they are not deleted yet
- they are not the current mounted default

## 5. Working Rule

Before editing frontend behavior:

1. confirm whether the target file is in the `ACTIVE`, `PARALLEL_NON_MOUNTED`, or `LEGACY_PARALLEL` category
2. prefer active mounted screens for user-facing behavior changes
3. do not treat parallel workbench files as canonical without an explicit activation decision

## 6. Immediate Cleanup Implications

The next frontend cleanup work should:

- keep `/app?screen=*` as the active routing truth
- stop active flows from linking through deprecated `/new` paths
- treat `app/templates/app/index.html` + `/static/js/app.js` as a refactor target, not assumed live behavior
- avoid building new UX simultaneously in both the active screen templates and the parallel workbench path

## 7. Relationship To Other Docs

Read with:

- `docs/architecture/ROUTER_SURFACE_MAP.md`
- `docs/ui/FRONTEND_IMPLEMENTATION_SPEC.md`
- `docs/ui/LIVE_UX_GAP_REPORT.md`
- `docs/ops/ARCHITECTURE_RESTORATION_SPRINT_MAP.md`
