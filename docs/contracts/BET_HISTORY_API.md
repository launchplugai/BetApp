# API Contract: Bet History (S18-D)

## Overview

Sprint S18-D adds bet history persistence and retrieval endpoints. Users can view their past bets with pagination, filtering, and detailed information.

**Version:** 1.0.0  
**Status:** Active  
**Date:** 2026-02-09

---

## Endpoints

### 1. GET `/api/bets/history`

Retrieve paginated bet history for authenticated user.

**Authentication:** Required (Bearer token)

**Query Parameters:**

| Parameter | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|
| `status` | string | No | - | Filter by status: `pending`, `won`, `lost`, `void` |
| `page` | integer | No | 1 | Page number (min: 1) |
| `per_page` | integer | No | 10 | Items per page (min: 1, max: 50) |

**Response Schema:**

```json
{
  "bets": [
    {
      "id": "bet_abc123",
      "input_text": "Lakers ML + Warriors -5.5",
      "legs": [
        {
          "entity": "Lakers",
          "market": "moneyline",
          "value": null,
          "odds": -150
        },
        {
          "entity": "Warriors",
          "market": "spread",
          "value": "-5.5",
          "odds": -110
        }
      ],
      "wager": 10000,
      "total_odds": 275,
      "potential_payout": 27500,
      "status": "pending",
      "actual_payout": null,
      "verdict": "PROCEED WITH CAUTION",
      "confidence": 65,
      "created_at": "2026-02-09T06:00:00Z",
      "settled_at": null
    }
  ],
  "total": 42,
  "page": 1,
  "per_page": 10
}
```

**Status Codes:**

- `200` - Success
- `401` - Unauthorized (invalid/expired token)
- `422` - Validation error (invalid params)

**Example Requests:**

```bash
# Get all bets (page 1)
curl -H "Authorization: Bearer TOKEN" \
  https://dna-production-cb47.up.railway.app/api/bets/history

# Filter by won bets
curl -H "Authorization: Bearer TOKEN" \
  https://dna-production-cb47.up.railway.app/api/bets/history?status=won

# Pagination
curl -H "Authorization: Bearer TOKEN" \
  https://dna-production-cb47.up.railway.app/api/bets/history?page=2&per_page=20
```

---

### 2. GET `/api/bets/{bet_id}`

Get detailed information for a single bet.

**Authentication:** Required (Bearer token)

**Path Parameters:**

| Parameter | Type | Description |
|-----------|------|-------------|
| `bet_id` | string | Bet identifier (e.g., `bet_abc123`) |

**Response Schema:**

```json
{
  "id": "bet_abc123",
  "user_id": "user_xyz789",
  "input_text": "Lakers ML + Warriors -5.5",
  "legs": [...],
  "wager": 10000,
  "total_odds": 275,
  "potential_payout": 27500,
  "status": "won",
  "actual_payout": 27500,
  "verdict": "PROCEED WITH CAUTION",
  "confidence": 65,
  "fragility": 42,
  "created_at": "2026-02-09T06:00:00Z",
  "settled_at": "2026-02-09T08:30:00Z"
}
```

**Status Codes:**

- `200` - Success
- `401` - Unauthorized
- `404` - Bet not found (or doesn't belong to user)

**Example Request:**

```bash
curl -H "Authorization: Bearer TOKEN" \
  https://dna-production-cb47.up.railway.app/api/bets/bet_abc123
```

---

## Data Types

### BetLeg

Represents a single leg in a parlay.

| Field | Type | Description |
|-------|------|-------------|
| `entity` | string | Team or player name |
| `market` | string | Market type: `moneyline`, `spread`, `total`, `player_prop` |
| `value` | string? | Line value (e.g., `-5.5`, `over 220`) |
| `odds` | integer? | American odds (e.g., -110, +150) |

### BetStatus

| Value | Description |
|-------|-------------|
| `pending` | Bet is active, outcome pending |
| `won` | User won the bet |
| `lost` | User lost the bet |
| `void` | Bet was cancelled/voided |

### Currency Representation

All monetary values are stored as **cents (integers)**.

| Field | Type | Example | Display |
|-------|------|---------|---------|
| `wager` | integer | 10000 | $100.00 |
| `potential_payout` | integer | 27500 | $275.00 |
| `actual_payout` | integer | 27500 | $275.00 |

**JavaScript conversion:**

```javascript
function formatCurrency(cents) {
  return new Intl.NumberFormat('en-US', {
    style: 'currency',
    currency: 'USD'
  }).format(cents / 100);
}
```

---

## Pagination

Pagination follows standard REST patterns:

- `page`: 1-indexed page number
- `per_page`: Items per page (default: 10, max: 50)
- `total`: Total number of items matching filter

**Example Response:**

```json
{
  "bets": [...],
  "total": 127,
  "page": 2,
  "per_page": 10
}
```

**Calculating total pages:**

```javascript
const totalPages = Math.ceil(data.total / data.per_page);
```

---

## Frontend Integration

### History Screen

**Route:** `/app?screen=history`

**Features:**
- Loading state (spinner)
- Empty state (no bets yet)
- Error state (network failure)
- Filter tabs (All, Active, Won, Lost)
- Pagination controls
- Click to view bet detail (future)

**Session Storage:**

```javascript
const token = sessionStorage.getItem('dna_auth_token');
const user = JSON.parse(sessionStorage.getItem('dna_user'));
```

**Fetch Example:**

```javascript
async function loadHistory() {
  const response = await fetch('/api/bets/history?status=pending', {
    headers: {
      'Authorization': `Bearer ${token}`
    }
  });

  if (response.status === 401) {
    // Token expired, redirect to auth
    sessionStorage.clear();
    window.location.href = '/app?screen=auth';
    return;
  }

  const data = await response.json();
  renderBets(data.bets);
}
```

---

## Security

- **Authentication:** All endpoints require valid JWT token
- **Authorization:** Users can only access their own bets
- **Rate Limiting:** Standard rate limits apply (10 req/min per IP)
- **Token Expiry:** JWT tokens expire after 7 days

---

## Testing

Run unit tests:

```bash
pytest app/tests/test_bets_api.py -v
```

**Coverage:**
- ✅ Authentication requirement
- ✅ Empty results for new users
- ✅ Pagination logic
- ✅ Status filtering
- ✅ Bet detail endpoint
- ✅ 404 for non-existent bets
- ✅ Response schema validation

---

## Migration Notes

**Database Schema:**

The `bets` table uses:
- SQLite for development/testing
- Same schema can migrate to PostgreSQL for production

**Existing Data:**

If migrating from a system without stored bets:
- History starts empty
- Users build history going forward
- No backfill needed

---

## Future Enhancements

- [ ] Bulk export (CSV/JSON)
- [ ] Advanced filters (date range, confidence threshold)
- [ ] Bet detail modal/screen
- [ ] Update bet status (admin only)
- [ ] Analytics aggregations

---

## Support

**API Issues:** Check `/api/docs` for OpenAPI spec  
**Frontend Issues:** Inspect browser console, check auth token  
**Testing:** See `app/tests/test_bets_api.py` for examples

**Status Check:**

```bash
curl https://dna-production-cb47.up.railway.app/health
```
