# Knowledge Digest

*Ralph's understanding of the DNA/BetApp project*

## Status: Active — Phase 2 Ready

### Current State

**Phase 0 (Infra Stability):** ✅ COMPLETE
- Railway deployment stable at `https://dna-production-cb47.up.railway.app`
- Health checks passing (`/health` → 200)
- Gateway operational post-reboot
- Auto-deploy from main working

**Phase 1 (Data Intelligence):** ✅ COMPLETE
- `analytics/` module live with NBA/NFL stat enrichment
- NBA: pace, offensive/defensive/net rating from stats.nba.com
- NFL: plays/game, points/game from ESPN
- TTL cache (1 hour) with LRU eviction
- Degraded mode: returns 200 with `is_enriched: false` on API failure
- `/context/{sport}/{game_id}` endpoint operational

**Phase 2 (Heuristic Engine):** 🎯 NEXT
- Goal: Signal detection (pace shock, rest asymmetry, injury leverage)
- Foundation ready, implementation pending

### Active Agents
- **Ralph** (Scrum Master): Sprint coordination
- **Ira** (Infra Agent): Deployment monitoring, runbooks
- **Tess** (Test Agent): pytest, coverage, regression detection

### Technical Constraints
- `dna-matrix/` — FROZEN (never modify)
- `sherlock/` — DORMANT (audit module, modify with care)
- External APIs: stats.nba.com, ESPN (no keys required)

### No Blockers
Production stable. Ready for Phase 2 heuristic implementation.

---

*Last updated: 2026-02-21*
