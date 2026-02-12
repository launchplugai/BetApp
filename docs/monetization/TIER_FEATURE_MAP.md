# Tier Feature Map - S-PROT-4G

Capability gating for Good/Better/Best tiers.

> **Note:** Pricing not exposed — this document maps capabilities only.

---

## Feature Matrix

| Tier | Feature | Endpoint/Location | Category |
|------|---------|-------------------|----------|
| GOOD | protocol_basic | `/api/protocols` (all) | Core |
| GOOD | snapshot_v2 | `/api/protocols/{id}/snapshot-v2` | Data |
| GOOD | narrative_v1 | Snapshot `conclusion.narrative` | Intelligence |
| GOOD | basic_risk_profile | `/api/risk-profile` | Risk |
| GOOD | dashboard_basic | Dashboard home | UI |
| GOOD | history_tracking | `/api/history` | Core |
| BETTER | *all GOOD features* | - | - |
| BETTER | fragility_scoring | Snapshot `structuredConfidence.fragility` | Intelligence |
| BETTER | edge_feed | `/api/edge-feed` | Intelligence |
| BETTER | advanced_confidence | Snapshot `structuredConfidence` (v3) | Intelligence |
| BETTER | kelly_criterion | Risk sizing recommendations | Risk |
| BETTER | correlation_detection | Multi-leg bet analysis | Risk |
| BETTER | dashboard_advanced | Advanced dashboard panels | UI |
| BEST | *all BETTER features* | - | - |
| BEST | micro_signals | Edge feed sub-signals | Intelligence |
| BEST | live_mutation | Real-time protocol updates | Data |
| BEST | priority_updates | Priority data refresh | Data |
| BEST | api_access | API key management | Pro |
| BEST | custom_alerts | User-defined alerts | Pro |
| BEST | export_data | CSV/JSON export | Pro |
| BEST | dashboard_pro | Custom layouts | UI |

---

## Endpoint Tier Requirements

| Endpoint | Required Tier | Feature Flag Check |
|----------|--------------|-------------------|
| `GET /api/protocols` | GOOD | `protocol_basic` |
| `POST /api/protocols` | GOOD | `protocol_basic` |
| `GET /api/protocols/{id}` | GOOD | `protocol_basic` |
| `GET /api/protocols/{id}/snapshot-v2` | GOOD | `snapshot_v2` |
| `GET /api/edge-feed` | BETTER | `edge_feed` |
| `GET /api/edge-feed/protocol/{id}` | BETTER | `edge_feed` |
| `GET /api/risk-profile` | GOOD | `basic_risk_profile` |
| `POST /api/risk-profile` | GOOD | `basic_risk_profile` |
| `GET /api/system-health` | GOOD | `dashboard_basic` |

---

## Feature Flag Implementation

```python
# app/services/feature_flags.py

def check_feature_access(user_tier: str, feature: str) -> bool:
    """
    Check if user tier has access to feature.
    
    Args:
        user_tier: GOOD | BETTER | BEST
        feature: Feature name from tier maps above
        
    Returns:
        bool: True if access granted
    """
    tier_features = {
        "GOOD": GOOD_FEATURES,
        "BETTER": BETTER_FEATURES,
        "BEST": BEST_FEATURES
    }
    
    features = tier_features.get(user_tier.upper(), GOOD_FEATURES)
    return feature in features
```

### Usage in Routers

```python
from app.services.feature_flags import has_feature

@router.get("/api/edge-feed")
async def get_edge_feed(user: User = Depends(get_current_user)):
    if not has_feature(user.tier, "edge_feed"):
        raise HTTPException(
            status_code=403,
            detail="Edge feed requires BETTER tier"
        )
    # ... endpoint logic
```

---

## Upgrade Paths

### GOOD → BETTER
Unlocks:
- Edge feed (real-time signals)
- Fragility scoring
- Advanced confidence (v3)
- Kelly criterion
- Correlation detection

### BETTER → BEST
Unlocks:
- Micro-signals
- Live mutation tracking
- Priority updates
- API access
- Custom alerts
- Data export
- Custom dashboard layouts

---

## Future Additions

Planned features (not yet implemented):
- `sentiment_analysis` - Market sentiment tracking
- `advanced_correlation` - ML correlation models
- `priority_support` - Fast-track support

---

## Related Documents

- `app/services/feature_flags.py` - Implementation
- `app/routers/edge_feed.py` - Example usage
- Sprint: S-PROT-4G (Monetization Prep)
