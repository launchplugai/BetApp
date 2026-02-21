# INCIDENT REPORT — DNA Prod Health Check Failure
**Date:** 2026-02-20 22:04 EST  
**Reporter:** OpenBot (Marvin)  
**Status:** 🔴 **P0 — Application Down**

---

## Symptom
Production health endpoints (`/health`, `/build`) returning 404 with "Application not found" error.

---

## Evidence

```bash
$ curl -I -m 5 https://dna-production-b681.up.railway.app
HTTP/2 404 
content-type: application/json
server: railway-edge
x-railway-fallback: true          <-- CRITICAL
x-railway-request-id: 5qSKcbG2SUCpGMuOezItjw

$ curl -sS -m 5 https://dna-production-b681.up.railway.app/health
{"status":"error","code":404,"message":"Application not found","request_id":"967baPvfRZW-ZM4ic9o55Q"}

$ curl -sS -m 5 https://dna-production-b681.up.railway.app/build
{"status":"error","code":404,"message":"Application not found","request_id":"6DBQYmVnQuqpg3zEezItjw"}
```

---

## Classification: Deploy Crash

| Indicator | Value | Meaning |
|-----------|-------|---------|
| HTTP Status | 404 | Not application-level — Railway edge responding |
| `x-railway-fallback: true` | Present | Railway serving fallback page — **app not running** |
| Response body | JSON error | Railway's standard "app not found" response |
| DNS | Working | `dna-production-b681.up.railway.app` resolves |
| Network | Reachable | Response time <100ms |

**Conclusion:** Railway infrastructure is up. The application container is **not running** (crashed, failed deploy, or scaled to zero).

---

## Likely Causes (Ranked)

1. **Failed Deploy** — Last push crashed on startup (missing env var, import error, port binding issue)
2. **Container Crash** — App started then crashed (runtime error, health check timeout)
3. **Scaled to Zero** — Railway suspended service (check dashboard settings)
4. **DB Connection Failure** — App crashing on startup due to DB unreachable

---

## Next Action Steps

### Immediate (You Do This Now)

1. **Open Railway Dashboard** → https://railway.app/dashboard
2. **Find project:** `dna-production` (or search for `dna-production-b681`)
3. **Check Deploy Status:**
   - Last deploy timestamp
   - Deploy logs (look for Python traceback on startup)
   - Service status (Running / Crashed / Sleeping)
4. **Check Environment Variables:**
   - Verify `PORT=8000` (or whatever FastAPI expects)
   - Verify `DATABASE_URL` or other required vars
5. **Check Logs:**
   - Look for: `ModuleNotFoundError`, `KeyError`, `Connection refused`, `bind: address already in use`

### If Deploy Failed

```bash
# Common fixes to check:
- Missing requirements in requirements.txt
- Procfile syntax error
- Wrong port (Railway sets PORT env var)
- Database migration not run
```

### If You Need Help

Send me:
- Screenshot of Railway service status
- Last 50 lines of deploy logs
- Last 50 lines of runtime logs

---

## Canonical URLs (For Future Reference)

- **Production:** https://dna-production-b681.up.railway.app
- **Health:** https://dna-production-b681.up.railway.app/health
- **Build:** https://dna-production-b681.up.railway.app/build

---

**Stop Condition Met:** Cannot proceed with feature work until prod is healthy. Waiting for Railway dashboard info.
