# S14: JARVIS INPUT OVERHAUL + NEW UI NEXUS
**Branch:** claude/s14-jarvis-nexus (already created)
**Mission:** Replace clunky menu-heavy builder with Jarvis-like "Nexus" experience

## CONSTRAINTS (CRITICAL)
- DO NOT modify scoring/math engines
- DO NOT add probability/win-rate claims
- DO NOT touch production workflows
- DO NOT break API contracts

## IMPLEMENTATION ORDER

### S14-A: Create Nexus Input Panel
**Goal:** New default landing/entry section

**Requirements:**
1. Create "Nexus Input Panel" at top of evaluate tab:
   - Title: "Drop your slip"
   - Subtitle: "Paste it, snap it, or say it."

2. Three input actions (all visible):
   **A) BIG TEXT AREA (default focus)**
   - placeholder: "LeBron O27.5 pts + AD O10.5 reb + Lakers ML…"
   - CTA button: "Analyze"
   
   **B) IMAGE UPLOAD (OCR)**
   - Button: "Upload screenshot"
   - Connects to existing OCR endpoint (do NOT modify OCR logic)
   
   **C) MANUAL BUILDER (Advanced)**
   - Collapsed by default
   - Button: "Build manually (advanced)"
   - Current builder UI reused inside collapse

3. Old menu-driven builder NOT default path
4. Mobile-first: one-thumb usable

**Files to modify:**
- `app/web_assets/templates/app.html`
- `app/web_assets/static/app.css`
- `app/web_assets/static/app.js`

**Commit:** `S14-A: Create Nexus Input Panel - Jarvis-style default entry`

---

### S14-B: Parsing Confirmation + Quick Fix Loop
**Goal:** Show detected legs, allow inline edits

**Requirements:**
1. Add "Detected Legs" section after analysis:
   - Each leg as pill/card
   - Show detected market type (ML/Spread/Total/Prop)

2. Lightweight inline edit actions:
   - Edit leg text
   - Remove leg
   - Add leg (simple text input)

3. Re-run analysis after edits (use existing evaluation pipeline)

**Constraints:**
- DO NOT build new data model
- Keep as "text → parse → evaluate" loop

**Commit:** `S14-B: Add detected legs display and inline edit loop`

---

### S14-C: Reality-Anchored Output (Tier 0)
**Goal:** Make output sound connected to sports reality WITHOUT live data

**Allowed patterns:**
- "player prop heavy"
- "depends on one game"
- "volume outcomes vs binary outcomes"
- "late-game variance"
- "injury-sensitive legs" (ONLY if implied by leg type)

**NOT ALLOWED:**
- Current stats, injuries, averages
- "LeBron has scored over this in X of Y"
- Any API calls to live sports data

**Implementation:**
- Update narrative copy in results to use sports language
- Ground in slip content + structural signals (snapshot, grounding, correlation)

**Files to modify:**
- `app/web_assets/templates/app.html` (copy changes)
- `app/web_assets/static/app.js` (if generating narrative dynamically)

**Commit:** `S14-C: Reality-anchored Tier-0 output with sports language`

---

### S14-D: Builder Relegation
**Goal:** Keep builder available but not required

**Requirements:**
- Manual builder becomes "Advanced mode"
- Builder UI can remain as-is
- Should not block users
- Reduce required fields/steps if possible

**Commit:** `S14-D: Relegate builder to advanced mode`

---

## TESTING
After each section:
```bash
.venv/bin/python -m pytest app/tests -k "test_web" -x --tb=short
```

If tests fail and can't fix in <30 min → STOP and report

## FINAL STEPS
1. Push branch to origin:
   ```bash
   git push origin claude/s14-jarvis-nexus
   ```

2. Create receipt at `docs/sprints/S14-report.md`:
   - What changed (user-visible)
   - What stayed same (truth/scoring)
   - What is now possible (next sprint)
   - Optional: request visual direction examples

## VISUAL DIRECTION (if needed)
If you need mockups/examples, ask Product Owner for:
- 1-2 screenshots of desired "Jarvis" style
- Example apps to emulate (dark/light, cards, tone)
- Preferred input hierarchy (text vs image vs builder)
