# Router Surface Map

**Last Updated:** 2026-03-08

This document maps the active FastAPI router surface so cleanup work can distinguish live code from legacy baggage.

## Active Routers

These routers are imported and included in [app/main.py](../../app/main.py).

| Router | Primary Role | Notes |
|--------|--------------|-------|
| `app/routers/web.py` | Canonical web UI routes | Main HTML surface at `/`, `/app`, and `/app/evaluate` |
| `app/routers/mock_api.py` | Mock/provider development routes | Active in runtime |
| `app/routers/live_api.py` | Live/provider-backed routes | Active in runtime |
| `app/routers/dashboard_stubs.py` | Dashboard and command-center stub APIs | Active, but partially feature-flagged and partly placeholder |
| `app/protocol/router.py` | Protocol CRUD and related protocol flows | Active |
| `app/protocol/recommendation_router.py` | Recommendation flows | Active |
| `app/routers/auth.py` | Authentication routes | Active |
| `app/routers/dashboard.py` | Dashboard routes | Active |
| `app/routers/bets.py` | Bet-related APIs | Active |
| `app/routers/odds.py` | Odds and evaluation-related APIs | Active |
| `app/nba/router.py` | NBA data routes | Active |
| `app/admin/router.py` | Admin routes | Active |
| `app/voice/router.py` | Voice routes | Active |
| `app/routers/preferences.py` | User preference routes | Active |
| `app/routers/notifications.py` | Notification routes | Active |
| `app/routers/leading_light.py` | OCR / image-parsing adjacent routes | Active behind config/features |
| `app/routers/panel.py` | Panel UI or admin-adjacent routes | Active |
| `app/routers/history.py` | History routes | Active |
| `app/routers/v1_ui.py` | Server-rendered v1 UI | Active, but separate from canonical `/app` flow |
| `app/routers/metrics.py` | Metrics/observability routes | Active |
| `app/routers/debug.py` | Debug and governance introspection | Active; included later in `main.py` |

## Legacy Or Non-Routed Routers

These files exist in the repo but are not currently included in [app/main.py](../../app/main.py).

| Router | Status | Notes |
|--------|--------|-------|
| `app/routers/web_old.py` | Legacy, non-routed | Large previous UI/router implementation retained for reference |
| `app/routers/_deprecated_web_legacy.py` | Deprecated, non-routed | Older legacy web surface retained in repo only |

## Current Truth

- `app/routers/web.py` is the canonical web surface.
- `/app?screen=*` is the canonical screen-routing pattern for the active web UI.
- `/ui2` and `/new` in `app/routers/web.py` are compatibility redirects only, not active product architecture.
- `app/routers/v1_ui.py` is still live, so cleanup must treat it as active until explicitly retired.
- `app/routers/dashboard_stubs.py` is active even though parts of it are stub or feature-flagged.
- Legacy router files should not be deleted casually until route parity and import safety are reviewed.

## Cleanup Rule

Before deleting or reorganizing router files:

1. confirm whether the router is imported in `app/main.py`
2. confirm whether tests still import it directly
3. confirm whether templates/assets still depend on its output shape
4. update this document when router status changes
