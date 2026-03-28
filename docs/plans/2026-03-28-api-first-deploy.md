# API-First Deploy Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Get the BetApp FastAPI backend running on Hostinger VPS behind Traefik, then wire the Next.js frontend to it on Vercel — protocol flow working end-to-end.

**Architecture:** Strip auth from protocol routes (hardcode demo user), deploy Docker container to VPS with Traefik TLS, then deploy Next.js to Vercel pointing at the live API.

**Tech Stack:** Python 3.12, FastAPI, SQLAlchemy, Docker, Traefik v3, Next.js 15, React 19, Vercel

---

## Task 1: Strip Auth from Protocol Routes

**Files:**
- Modify: `app/protocol/router.py` (lines 16-17, 24-119)
- Modify: `app/protocol/service.py` (lines 56-75)

**Step 1: Write test verifying public protocol creation**

```python
# tests/test_protocol_public.py
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)

def test_create_protocol_no_auth():
    """Protocol creation works without auth token."""
    resp = client.post("/api/protocols", json={
        "sport": "nba",
        "title": "Test Protocol",
        "context": {},
    })
    assert resp.status_code == 200
    data = resp.json()
    assert data["sport"] == "nba"
    assert data["title"] == "Test Protocol"
    assert "id" in data

def test_list_protocols_no_auth():
    """Protocol listing works without auth token."""
    resp = client.get("/api/protocols")
    assert resp.status_code == 200
    assert isinstance(resp.json(), list)
```

**Step 2: Run test to verify it fails (auth blocks it)**

Run: `cd app-src && python -m pytest tests/test_protocol_public.py -v`
Expected: FAIL — 401 Unauthorized

**Step 3: Remove auth from protocol router**

In `app/protocol/router.py`:
- Remove `from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials` (line 16)
- Remove `security = HTTPBearer()` (line 17)
- Remove `credentials: HTTPAuthorizationCredentials = Depends(security)` from all 5 endpoint signatures
- Remove `user = get_current_user_from_token(credentials.credentials)` + the `if not user` check from each endpoint
- Replace `user.id` with `"demo_user"` in all service calls

In `app/protocol/service.py`:
- In `create_stats_snapshot()` (lines 56-75), remove the `if protocol.user_id != user_id: raise PermissionError` check

**Step 4: Run test to verify it passes**

Run: `cd app-src && python -m pytest tests/test_protocol_public.py -v`
Expected: PASS

**Step 5: Commit**

```bash
cd app-src && git add app/protocol/router.py app/protocol/service.py tests/test_protocol_public.py
git commit -m "feat: strip auth from protocol routes for public v1 access"
```

---

## Task 2: Consolidate .env.example

**Files:**
- Modify: `.env.example` (root)

**Step 1: Create comprehensive .env.example**

```env
# === BetApp Environment ===

# Server
PORT=19801
ENVIRONMENT=production
GIT_SHA=

# Database
DATABASE_URL=sqlite:///./dna_bets.db

# Domain (used by Traefik for TLS)
BETAPP_DOMAIN=betapp.yourdomain.com
ACME_EMAIL=you@example.com

# Sports Data
ODDS_API_KEY=
NBA_API_ENABLED=true

# AI / TTS (optional)
OPENAI_API_KEY=

# Frontend
NEXT_PUBLIC_API_BASE_URL=https://betapp.yourdomain.com

# CORS (comma-separated origins, or * for all)
CORS_ORIGINS=*
```

**Step 2: Commit**

```bash
git add .env.example
git commit -m "docs: consolidate all env vars into .env.example"
```

---

## Task 3: Update Dockerfile for Clean Build

**Files:**
- Modify: `Dockerfile`
- Modify: `entrypoint.sh`

**Step 1: Update Dockerfile to use local code instead of git clone**

```dockerfile
FROM python:3.12-slim

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends curl && rm -rf /var/lib/apt/lists/*

COPY app-src/requirements.txt ./requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

COPY app-src/ ./
COPY entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh

ENV PYTHONPATH=/app:/app/dna-matrix:/app/dna-matrix/src
EXPOSE 19801

HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD curl -f http://localhost:19801/health || exit 1

ENTRYPOINT ["/entrypoint.sh"]
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "19801"]
```

**Step 2: Verify entrypoint.sh sets up persistence correctly**

Review `entrypoint.sh` — ensure it symlinks databases from `/app/persist/` and then exec's the CMD.

**Step 3: Test Docker build locally**

Run: `docker build -t betapp:test .`
Expected: Build succeeds

**Step 4: Test container starts and health check passes**

Run: `docker run --rm -p 19801:19801 betapp:test &`
Run: `sleep 5 && curl -s http://localhost:19801/health | python -m json.tool`
Expected: JSON with `"status": "ok"` or similar

**Step 5: Commit**

```bash
git add Dockerfile entrypoint.sh
git commit -m "fix: Dockerfile uses local code, clean build"
```

---

## Task 4: Update docker-compose.yml for Traefik

**Files:**
- Modify: `docker-compose.yml`

**Step 1: Update compose for Traefik routing with env-based domain**

```yaml
services:
  betapp:
    build:
      context: .
      dockerfile: Dockerfile
    container_name: betapp
    restart: unless-stopped
    env_file: .env
    volumes:
      - betapp_persist:/app/persist
    networks:
      - traefik_public
    labels:
      - "traefik.enable=true"
      - "traefik.http.routers.betapp.rule=Host(`${BETAPP_DOMAIN}`)"
      - "traefik.http.routers.betapp.entrypoints=websecure"
      - "traefik.http.routers.betapp.tls.certresolver=letsencrypt"
      - "traefik.http.services.betapp.loadbalancer.server.port=19801"
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:19801/health"]
      interval: 30s
      timeout: 5s
      retries: 3
      start_period: 10s

volumes:
  betapp_persist:

networks:
  traefik_public:
    external: true
```

**Step 2: Verify Traefik network exists on VPS**

Run (on VPS): `docker network ls | grep traefik_public`
If missing: `docker network create traefik_public`

**Step 3: Commit**

```bash
git add docker-compose.yml
git commit -m "feat: docker-compose with Traefik TLS routing"
```

---

## Task 5: Deploy Backend to VPS

**Step 1: Push code to VPS**

```bash
git push origin main
```

Then on VPS:
```bash
cd /path/to/betapp
git pull origin main
```

**Step 2: Create .env on VPS from .env.example**

```bash
cp .env.example .env
# Edit .env with real values: BETAPP_DOMAIN, ACME_EMAIL, ODDS_API_KEY, etc.
```

**Step 3: Build and start container**

```bash
docker compose up -d --build
```

**Step 4: Verify health check**

Run: `curl -s https://${BETAPP_DOMAIN}/health | python -m json.tool`
Expected: 200 OK with health JSON

**Step 5: Verify protocol endpoint**

```bash
curl -s -X POST https://${BETAPP_DOMAIN}/api/protocols \
  -H "Content-Type: application/json" \
  -d '{"sport":"nba","title":"Test","context":{}}' | python -m json.tool
```
Expected: 200 with protocol object

---

## Task 6: Wire Frontend API to VPS Backend

**Files:**
- Create: `app-src/frontend/.env.production`
- Verify: `app-src/frontend/src/lib/api/http.ts` (already reads NEXT_PUBLIC_API_BASE_URL)

**Step 1: Create production env for frontend**

```env
NEXT_PUBLIC_API_BASE_URL=https://betapp.yourdomain.com
```

**Step 2: Verify frontend builds with API URL**

Run: `cd app-src/frontend && npm run build`
Expected: Build succeeds

**Step 3: Commit**

```bash
cd app-src && git add frontend/.env.production
git commit -m "feat: frontend production env pointing to VPS API"
```

---

## Task 7: Deploy Frontend to Vercel

**Step 1: Create vercel.json**

```json
{
  "framework": "nextjs",
  "buildCommand": "npm run build",
  "outputDirectory": ".next",
  "installCommand": "npm install",
  "devCommand": "npm run dev"
}
```

Save to: `app-src/frontend/vercel.json`

**Step 2: Connect to Vercel**

```bash
cd app-src/frontend
npx vercel --yes
```

Set `NEXT_PUBLIC_API_BASE_URL` in Vercel dashboard environment variables.

**Step 3: Deploy**

```bash
npx vercel --prod
```

**Step 4: Verify — browse the live URL**

Use browse/playwright to:
1. Navigate to Vercel URL
2. Verify landing page loads
3. Navigate to protocol creation
4. Verify API calls hit VPS backend (check network tab / console)

**Step 5: Commit**

```bash
git add frontend/vercel.json
git commit -m "feat: Vercel deployment config for frontend"
```

---

## Task 8: End-to-End Smoke Test

**Step 1: Use browse skill to verify the full flow**

1. Open Vercel URL in browser
2. Navigate to protocol creation page
3. Create a protocol (sport: NBA, title: "Test")
4. Verify protocol appears in list
5. Check recommendations endpoint responds
6. Screenshot each step

**Step 2: Verify API health from frontend context**

Open browser dev tools, confirm:
- API calls go to VPS URL (not localhost)
- No CORS errors
- Responses return valid JSON

**Step 3: Document the live URLs**

Update README or create a DEPLOY.md with:
- Frontend URL (Vercel)
- Backend URL (VPS)
- Health check endpoint
- How to redeploy each
