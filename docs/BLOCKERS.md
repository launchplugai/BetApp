# Remaining Blockers & Path Forward

**Last Updated:** 2026-02-14

## ✅ Recently Completed
- Builder blank page fix (protocol validation + error handling)
- Real odds API integration (NHL working)
- OCR API fix (newlines in key)
- Audio transcription working
- S21 User Preferences/DNA system

---

## 🚧 Active Blockers

### 1. Protocol System Enhancement
**Status:** Core loop works, needs intelligence layer

**Current:**
- Protocol loads game context
- User can build parlays
- Basic constraint checking

**Missing:**
- [ ] Related bet suggestions ("Players like this also...")
- [ ] Live edge notifications ("Line moved +3%")
- [ ] Smart protocol linking (team → all their games)
- [ ] Cross-game correlation detection

**Effort:** 2-3 days
**Priority:** HIGH (core UX promise)

---

### 2. Analysis Tier System
**Status:** Debug data exists, needs natural language layer

**Current:**
- Debug panel shows raw data points
- Tiered features stubbed

**Missing:**
- [ ] Natural language generation from data points
- [ ] Tier-based feature gating (BASIC/GOOD/BETTER/BEST)
- [ ] Live data injection into analysis
- [ ] Heuristic scoring for higher tiers

**Effort:** 3-4 days
**Priority:** HIGH (differentiator)

---

### 3. Sherlock → DNA Integration
**Status:** Not started

**What is Sherlock?**
External intelligence source for bet analysis

**Needed:**
- [ ] Sherlock client/service
- [ ] Data transformation to DNA format
- [ ] Cache layer for Sherlock responses
- [ ] Fallback when Sherlock unavailable

**Effort:** 2-3 days
**Priority:** MEDIUM (depends on Sherlock availability)

---

### 4. NBA Player Props Fix
**Status:** Parser regex broken

**Issue:** Player prop abbreviations not parsing correctly

**Fix needed:**
- [ ] Update regex in `_detect_leg_markets()`
- [ ] Handle: pts, reb, ast, blk, stl, to, 3pm
- [ ] O/U patterns: O27.5, U10.5

**Effort:** 1 day
**Priority:** LOW (NBA All-Star break, no games)

---

### 5. UI Polish
**Status:** Builder functional, needs refinement

**Issues:**
- [ ] Basketball icons for NHL games
- [ ] Player Props tab empty (no props API yet)
- [ ] Mobile scrolling issues

**Effort:** 1-2 days
**Priority:** MEDIUM

---

## 🎯 Recommended Path

### Phase 1: Intelligence Layer (Week 1)
1. **Protocol Suggestions** (2 days)
   - Related bets algorithm
   - "Explore suggestions" button
   - Basic heuristic matching

2. **Analysis Tiers - BASIC** (2 days)
   - Natural language from data points
   - Tier feature gating
   - BASIC tier analysis display

### Phase 2: Integration (Week 2)
3. **Sherlock Integration** (2-3 days)
   - Client implementation
   - Data transformation
   - Cache layer

4. **Analysis Tiers - Premium** (2 days)
   - GOOD/BETTER/BEST tiers
   - Live data injection
   - Heuristic scoring

### Phase 3: Polish (Week 3)
5. **NBA Parser Fix** (1 day)
6. **UI Polish** (2 days)
7. **Testing & Hardening** (2 days)

---

## 🔧 Immediate Next Steps

**What should we tackle first?**

A) Protocol suggestions + related bets
B) Analysis natural language (BASIC tier)
C) Sherlock integration
D) Something else?

**Current Production Status:**
- ✅ Dashboard loads
- ✅ Builder works with NHL
- ✅ Real odds displaying
- ✅ User login functional
- ⚠️ Player Props empty (no API source)
- ⚠️ Analysis shows debug data only
