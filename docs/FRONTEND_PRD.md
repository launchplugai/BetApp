# DNA Bet Engine - Frontend PRD (Comprehensive)
## S15: Messaging-Style UI Architecture

**Version:** 0.3.0  
**Last Updated:** 2026-02-08  
**Status:** In Development

---

## 1. EXECUTIVE SUMMARY

### 1.1 Product Vision
A single-screen bet analysis interface that feels like texting a knowledgeable friend. Users paste, snap, or speak their bets and get instant, jargon-free analysis.

### 1.2 Core User Flow
```
User lands on page
    ↓
Sees friendly chat interface (🎯 "What are you betting on?")
    ↓
INPUT PATH (3 options):
  ├─ Type bet text directly
  ├─ Tap sport chip → select suggestion
  └─ Tap camera → upload screenshot
    ↓
Tap Analyze (dark red button)
    ↓
System processes (spinner/loading state)
    ↓
Results display (verdict, confidence, breakdown)
```

---

## 2. FUNCTIONAL ARCHITECTURE

### 2.1 Function Inventory

| Function ID | Name | Purpose | Called By |
|-------------|------|---------|-----------|
| F1 | `initializeUI()` | Setup event listeners, check session | Page load |
| F2 | `handleTextInput()` | Capture and validate text input | User typing |
| F3 | `handleVoiceInput()` | Web Speech API integration | Voice button |
| F4 | `handleImageSelect()` | File picker and preview | Camera button |
| F5 | `submitOCR()` | Send image to OCR endpoint | Image selected |
| F6 | `handleSportSelect()` | Sport chip selection | Sport chip tap |
| F7 | `showSportSuggestions()` | Render sport-specific templates | F6 |
| F8 | `applySuggestion()` | Populate text from template | Suggestion tap |
| F9 | `submitAnalysis()` | Send text to evaluate endpoint | Analyze button |
| F10 | `displayResults()` | Render evaluation response | F9 success |
| F11 | `displayError()` | Show error toast | Any failure |
| F12 | `updateSession()` | Track evaluation count | After analysis |

### 2.2 Function Dependency Graph
```
F1 (initialize)
  ├─> F2 (text input) ──> F9 (submit) ──> F10 (results)
  │                                          └─> F12 (session)
  ├─> F3 (voice) ───────> F2
  ├─> F4 (image) ───────> F5 (OCR) ────> F2
  └─> F6 (sport) ───────> F7 (suggestions)
                            └─> F8 ─────> F2

F9, F5 ──[error]──> F11 (error display)
```

---

## 3. UI ARTIFACT TO FUNCTION MAPPING

### 3.1 Component: Chat Header

**UI Artifact:**
```html
<div class="chat-header">
    <div class="chat-avatar">🎯</div>
    <div class="chat-title">
        <h2>Analyze Bet</h2>
        <span class="chat-subtitle">What are you betting on?</span>
    </div>
</div>
```

**Associated Functions:** None (static display)

**Purpose:** Branding and context setting

---

### 3.2 Component: Text Input Bubble

**UI Artifact:**
```html
<div class="chat-bubble-input">
    <textarea 
        class="chat-text-field" 
        id="chat-text-field"
        placeholder="Paste your bet slip...">
    </textarea>
</div>
```

**Associated Functions:**
| Event | Function | Description |
|-------|----------|-------------|
| `input` | `F2: handleTextInput()` | Capture text, enable/disable Analyze button |
| `keydown` (Enter) | `F9: submitAnalysis()` | Submit if text present |
| `focus` | Internal | Visual focus state |

**State Changes:**
- Empty → Placeholder visible, Analyze disabled
- Has text → Placeholder hidden, Analyze enabled
- Typing → Debounce validation (optional)

---

### 3.3 Component: Toolbar Buttons

**UI Artifact:**
```html
<div class="chat-toolbar">
    <button class="chat-tool-btn" id="chat-voice-btn">🎙️</button>
    <button class="chat-tool-btn" id="chat-camera-btn">📷</button>
    <button class="chat-tool-btn" id="chat-keyboard-btn">⌨️</button>
    <button class="chat-send-btn" id="chat-send-btn">Analyze</button>
</div>
```

**Associated Functions:**
| Button ID | Function | Trigger | Description |
|-----------|----------|---------|-------------|
| `chat-voice-btn` | `F3: handleVoiceInput()` | Click | Initiates Web Speech API |
| `chat-camera-btn` | `F4: handleImageSelect()` | Click | Opens file picker |
| `chat-keyboard-btn` | Internal | Click | Focuses `#chat-text-field` |
| `chat-send-btn` | `F9: submitAnalysis()` | Click | Validates and submits |

**Function Details:**

**F3: handleVoiceInput()**
```javascript
function handleVoiceInput() {
    // Check browser support
    if (!('webkitSpeechRecognition' in window)) {
        F11('Voice not supported');
        return;
    }
    
    // Initialize recognition
    const recognition = new webkitSpeechRecognition();
    recognition.onresult = (e) => {
        const text = e.results[0][0].transcript;
        document.getElementById('chat-text-field').value = text;
        F2(); // Trigger input handler
    };
    
    recognition.start();
    showToast('Listening...');
}
```

**F4: handleImageSelect()**
```javascript
function handleImageSelect() {
    const input = document.getElementById('chat-file-input');
    input.click(); // Trigger hidden file input
}
```

**F9: submitAnalysis()**
```javascript
async function submitAnalysis() {
    const text = document.getElementById('chat-text-field').value.trim();
    
    // Validation
    if (!text) {
        F11('Enter your bet first');
        return;
    }
    
    // Loading state
    const btn = document.getElementById('chat-send-btn');
    btn.disabled = true;
    btn.textContent = 'Analyzing...';
    
    try {
        const response = await fetch('/app/evaluate', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                input: text,
                tier: 'good',
                legs: null
            })
        });
        
        if (!response.ok) throw new Error(`HTTP ${response.status}`);
        
        const data = await response.json();
        F10(data); // Display results
        F12(); // Update session
        
    } catch (err) {
        F11(err.message || 'Failed to analyze');
    } finally {
        btn.disabled = false;
        btn.textContent = 'Analyze';
    }
}
```

---

### 3.4 Component: Sport Chips

**UI Artifact:**
```html
<div class="sport-chips">
    <button class="sport-chip" data-sport="nfl">🏈 NFL</button>
    <button class="sport-chip" data-sport="nba">🏀 NBA</button>
    <button class="sport-chip" data-sport="mlb">⚾ MLB</button>
    <button class="sport-chip" data-sport="nhl">🏒 NHL</button>
</div>
<div class="sport-suggestions" id="sport-suggestions"></div>
```

**Associated Functions:**
| Event | Function | Description |
|-------|----------|-------------|
| Click sport chip | `F6: handleSportSelect(sport)` | Sets active sport |
| F6 calls | `F7: showSportSuggestions(sport)` | Renders templates |
| Click suggestion | `F8: applySuggestion(text)` | Populates input |

**Function Details:**

**F6: handleSportSelect(sport)**
```javascript
function handleSportSelect(sport) {
    // Clear all active states
    document.querySelectorAll('.sport-chip').forEach(c => {
        c.classList.remove('active');
    });
    
    // Set active on clicked
    const chip = document.querySelector(`[data-sport="${sport}"]`);
    chip.classList.add('active');
    
    // Show suggestions
    F7(sport);
}
```

**F7: showSportSuggestions(sport)**
```javascript
const SUGGESTIONS = {
    nfl: [
        { label: 'Spread', text: 'Chiefs -3.5' },
        { label: 'Total', text: 'Over 47.5' },
        { label: 'Mahomes', text: 'Mahomes O280 passing yards' },
        { label: 'Any TD', text: 'Kelley anytime TD' }
    ],
    nba: [
        { label: 'Spread', text: 'Lakers -5.5' },
        { label: 'LeBron', text: 'LeBron O27.5 pts' },
        { label: 'Total', text: 'Over 220.5' },
        { label: 'Rebounds', text: 'AD O10.5 reb' }
    ],
    mlb: [
        { label: 'ML', text: 'Yankees ML' },
        { label: 'Total', text: 'Over 8.5' },
        { label: 'Strikeouts', text: 'Cole O6.5 Ks' },
        { label: 'Hits', text: 'Judge O1.5 hits' }
    ],
    nhl: [
        { label: 'Puck Line', text: 'Rangers -1.5' },
        { label: 'Total', text: 'Over 5.5' },
        { label: 'Shots', text: 'Ovechkin O3.5 shots' },
        { label: 'Saves', text: 'Shesterkin O28.5 saves' }
    ]
};

function showSportSuggestions(sport) {
    const container = document.getElementById('sport-suggestions');
    const suggestions = SUGGESTIONS[sport] || [];
    
    container.innerHTML = suggestions.map(s => 
        `<button class="suggestion-chip" data-text="${s.text}">${s.label}</button>`
    ).join('');
    
    // Add click handlers
    container.querySelectorAll('.suggestion-chip').forEach(btn => {
        btn.addEventListener('click', () => F8(btn.dataset.text));
    });
    
    container.classList.remove('hidden');
}
```

**F8: applySuggestion(text)**
```javascript
function applySuggestion(text) {
    const input = document.getElementById('chat-text-field');
    input.value = text;
    input.focus();
    F2(); // Trigger validation
}
```

---

### 3.5 Component: Image Upload Flow

**UI Artifacts:**
```html
<input type="file" id="chat-file-input" accept="image/*" class="hidden">
<div class="chat-photo-preview hidden" id="chat-photo-preview">
    <img id="chat-preview-img">
    <button id="chat-remove-photo">×</button>
</div>
```

**Associated Functions:**
| Event | Function | Description |
|-------|----------|-------------|
| Camera button click | `F4: handleImageSelect()` | Opens file picker |
| File selected | `F5: submitOCR(file)` | Uploads to OCR endpoint |
| Remove click | `removePhoto()` | Clears preview and input |

**Function Details:**

**F5: submitOCR(file)**
```javascript
async function submitOCR(file) {
    // Validation
    const validTypes = ['image/png', 'image/jpeg', 'image/jpg', 'image/webp'];
    if (!validTypes.includes(file.type)) {
        F11('Please upload PNG, JPG, or WebP');
        return;
    }
    if (file.size > 5 * 1024 * 1024) {
        F11('Image must be under 5MB');
        return;
    }
    
    // Show preview
    const reader = new FileReader();
    reader.onload = (e) => {
        document.getElementById('chat-preview-img').src = e.target.result;
        document.getElementById('chat-photo-preview').classList.remove('hidden');
    };
    reader.readAsDataURL(file);
    
    // Submit to OCR
    const btn = document.getElementById('chat-send-btn');
    btn.disabled = true;
    btn.textContent = 'Reading...';
    
    try {
        const formData = new FormData();
        formData.append('image', file);      // CORRECT field name
        formData.append('plan', 'free');      // REQUIRED parameter
        
        const response = await fetch('/evaluate/image', {  // CORRECT endpoint
            method: 'POST',
            body: formData
        });
        
        if (!response.ok) throw new Error(`OCR failed: ${response.status}`);
        
        const data = await response.json();
        
        if (data.extractedText) {
            document.getElementById('chat-text-field').value = data.extractedText;
            F2(); // Validate
            showToast('Text extracted! Tap Analyze');
        } else {
            F11('Could not read text from image');
        }
        
    } catch (err) {
        console.error('OCR error:', err);
        F11('OCR failed. Try typing instead.');
    } finally {
        btn.disabled = false;
        btn.textContent = 'Analyze';
    }
}
```

---

### 3.6 Component: Results Display

**UI Artifact (to be implemented):**
```html
<div class="results-panel hidden" id="results-panel">
    <div class="verdict-badge" id="verdict-badge">GOOD</div>
    <div class="confidence-score" id="confidence-score">75%</div>
    <div class="summary-text" id="summary-text">...</div>
    <div class="legs-breakdown" id="legs-breakdown">...</div>
</div>
```

**Associated Functions:**
| Function | Description |
|----------|-------------|
| `F10: displayResults(data)` | Renders evaluation response |

**Function Details:**

**F10: displayResults(data)**
```javascript
function displayResults(data) {
    const panel = document.getElementById('results-panel');
    
    // Verdict
    const verdict = data.overallAssessment?.verdict || 'UNKNOWN';
    document.getElementById('verdict-badge').textContent = verdict;
    document.getElementById('verdict-badge').className = `verdict-badge verdict-${verdict.toLowerCase()}`;
    
    // Confidence
    const confidence = Math.round((data.overallAssessment?.confidenceScore || 0) * 100);
    document.getElementById('confidence-score').textContent = `${confidence}%`;
    
    // Summary
    document.getElementById('summary-text').textContent = 
        data.overallAssessment?.summary || 'Analysis complete.';
    
    // Legs breakdown
    const legsContainer = document.getElementById('legs-breakdown');
    legsContainer.innerHTML = (data.legs || []).map(leg => `
        <div class="leg-item">
            <span class="leg-text">${leg.player || leg.team} ${leg.market || ''}</span>
            <span class="leg-signal">${leg.signal || ''}</span>
        </div>
    `).join('');
    
    // Show panel
    panel.classList.remove('hidden');
    panel.scrollIntoView({ behavior: 'smooth' });
}
```

---

### 3.7 Component: Error Display

**UI Artifact:**
```javascript
// Toast notification (dynamically created)
<div id="chat-toast" style="...">Error message</div>
```

**Associated Functions:**
| Function | Description |
|----------|-------------|
| `F11: displayError(message)` | Shows error toast |

**Function Details:**

**F11: displayError(message)**
```javascript
function displayError(message) {
    let toast = document.getElementById('chat-toast');
    
    if (!toast) {
        toast = document.createElement('div');
        toast.id = 'chat-toast';
        toast.style.cssText = `
            position: fixed;
            bottom: 100px;
            left: 50%;
            transform: translateX(-50%);
            background: rgba(139, 0, 0, 0.9);
            color: white;
            padding: 12px 24px;
            border-radius: 20px;
            font-size: 14px;
            z-index: 9999;
            max-width: 80%;
            text-align: center;
        `;
        document.body.appendChild(toast);
    }
    
    toast.textContent = message;
    toast.style.display = 'block';
    
    setTimeout(() => {
        toast.style.display = 'none';
    }, 4000);
}
```

---

### 3.8 Component: Session Tracking

**UI Artifact:**
```html
<div class="session-bar" id="session-bar">
    <span class="session-label">Session:</span>
    <input type="text" id="session-name" placeholder="Name this session">
    <span class="session-history" id="session-history">5 evaluations</span>
</div>
```

**Associated Functions:**
| Function | Description |
|----------|-------------|
| `F12: updateSession()` | Increments evaluation count |

**Function Details:**

**F12: updateSession()**
```javascript
function updateSession() {
    // Get current count
    const historyEl = document.getElementById('session-history');
    const match = historyEl.textContent.match(/(\d+)/);
    const count = match ? parseInt(match[1]) + 1 : 1;
    
    // Update display
    historyEl.textContent = `${count} evaluation${count !== 1 ? 's' : ''}`;
    
    // Optionally persist to localStorage
    localStorage.setItem('dna_eval_count', count.toString());
}
```

---

## 4. API SPECIFICATION

### 4.1 Endpoint: Text Evaluation

**URL:** `POST /app/evaluate`

**Request Schema:**
```typescript
interface EvaluateRequest {
    input: string;           // Required: bet text
    tier?: string;           // Optional: "good" | "better" | "best"
    legs?: CanonicalLeg[];   // Optional: structured legs
}

interface CanonicalLeg {
    id: string;
    player?: string;
    team?: string;
    market: string;
    line?: number;
    side?: string;
}
```

**Response Schema:**
```typescript
interface EvaluateResponse {
    overallAssessment: {
        verdict: string;           // "GOOD" | "BETTER" | "BEST" | "RISKY"
        confidenceScore: number;   // 0.0 - 1.0
        summary: string;           // Human-readable summary
    };
    legs: LegResult[];
    structureSnapshot: StructureSnapshot;
    tiers: TierBreakdown;
    input: {
        betText: string;
        tier: string;
    };
    _meta: {
        elapsedMs: number;
    };
}

interface LegResult {
    id: string;
    player?: string;
    team?: string;
    market: string;
    line?: number;
    signal?: string;
    confidence?: number;
}
```

**Error Responses:**
| Status | Code | Message |
|--------|------|---------|
| 400 | INVALID_INPUT | Cannot parse bet text |
| 429 | RATE_LIMITED | Too many requests |
| 500 | INTERNAL_ERROR | Server error |

---

### 4.2 Endpoint: Image OCR

**URL:** `POST /evaluate/image`

**Request:** `multipart/form-data`

**Fields:**
| Field | Type | Required | Description |
|-------|------|----------|-------------|
| image | File | Yes | Image file (PNG, JPG, WebP) |
| plan | string | Yes | Plan tier ("free", "pro", etc.) |
| session_id | string | No | Session identifier |

**Response Schema:**
```typescript
interface OCRResponse {
    extractedText: string;     // Raw text from image
    confidence: number;        // OCR confidence (0-1)
    evaluation?: EvaluateResponse;  // If auto-evaluated
}
```

**Error Responses:**
| Status | Code | Message |
|--------|------|---------|
| 400 | INVALID_FILE_TYPE | Not an image |
| 413 | FILE_TOO_LARGE | > 5MB |
| 422 | OCR_FAILED | Could not extract text |
| 503 | FEATURE_DISABLED | OCR not available |

---

## 5. STATE MACHINE

### 5.1 Application States

```
┌─────────────┐
│   INITIAL   │ ← Page load
└──────┬──────┘
       │
       ▼
┌─────────────┐
│   READY     │ ← F1 complete, waiting for input
└──────┬──────┘
       │
       ├── Input detected ──► ┌─────────────┐
       │                      │   TYPING    │
       │                      └──────┬──────┘
       │                             │
       ├── Sport selected ──► ┌─────────────┐
       │                      │ SPORT_MENU  │
       │                      └──────┬──────┘
       │                             │
       ├── Image selected ──► ┌─────────────┐
       │                      │   PREVIEW   │
       │                      └──────┬──────┘
       │                             │
       ▼                             ▼
┌─────────────┐              ┌─────────────┐
│  SUBMITTED  │ ◄─────────── │   LOADING   │
└──────┬──────┘              └─────────────┘
       │
       ├── Success ──► ┌─────────────┐
       │               │   RESULTS   │
       │               └──────┬──────┘
       │                      │
       │                      ▼
       │               ┌─────────────┐
       │               │   READY     │ ◄── Can analyze again
       │               └─────────────┘
       │
       └── Error ──► ┌─────────────┐
                     │    ERROR    │
                     └──────┬──────┘
                            │
                            ▼
                     ┌─────────────┐
                     │   READY     │
                     └─────────────┘
```

---

## 6. ERROR HANDLING MATRIX

| Function | Error Type | User Message | Recovery |
|----------|------------|--------------|----------|
| F3 (voice) | Not supported | "Voice not supported on this browser" | Hide/disable button |
| F4/F5 (image) | Invalid type | "Please upload PNG, JPG, or WebP" | Clear selection |
| F4/F5 (image) | Too large | "Image must be under 5MB" | Clear selection |
| F5 (OCR) | Extraction failed | "Could not read image. Try typing." | Focus text field |
| F9 (analyze) | Empty input | "Enter your bet first" | Focus text field |
| F9 (analyze) | Network error | "Check connection" | Retry button |
| F9 (analyze) | Rate limited | "Slow down" | Wait 10s |
| F9 (analyze) | Server error | "Analysis failed. Try again." | Retry button |
| F10 (display) | Missing data | "Results incomplete" | Show partial |

---

## 7. TESTING SCENARIOS

### 7.1 Unit Tests (Functions)

| Test ID | Function | Scenario | Expected |
|---------|----------|----------|----------|
| T1 | F2 | Empty input → Analyze click | Error: "Enter your bet first" |
| T2 | F2 | Valid input entered | Analyze button enabled |
| T3 | F6 | NFL chip clicked | NFL suggestions shown, chip highlighted |
| T4 | F7 | NBA selected | 4 NBA suggestions rendered |
| T5 | F8 | "Spread" suggestion clicked | Text field: "Lakers -5.5" |
| T6 | F5 | 10MB image selected | Error: "Image must be under 5MB" |
| T7 | F9 | Valid text submitted | POST to /app/evaluate, loading state |
| T8 | F10 | Response received | Results panel visible |
| T9 | F11 | Any error | Toast visible 4 seconds |
| T10 | F12 | After analysis | Counter increments |

### 7.2 Integration Tests (Flows)

| Test ID | Flow | Steps | Expected |
|---------|------|-------|----------|
| I1 | Full text flow | Type → Analyze → Results | Complete in < 3s |
| I2 | Sport → suggestion | NFL → Spread → Analyze | Chiefs -3.5 analyzed |
| I3 | Image → OCR | Camera → Select → Extract | Text populated |
| I4 | Image → Analyze | Upload → Auto-analyze | Results shown |
| I5 | Error recovery | Disconnect → Analyze → Error → Retry | Success on retry |

### 7.3 E2E Tests (User Journeys)

| Test ID | Journey | Steps |
|---------|---------|-------|
| E1 | First-time user | Land → Read subtitle → Type bet → Analyze → Read results |
| E2 | Sport picker | Land → Tap NBA → Tap LeBron → Edit → Analyze |
| E3 | Screenshot user | Land → Tap camera → Upload slip → Review extracted → Analyze |
| E4 | Voice user | Land → Tap mic → Speak bet → Review → Analyze |
| E5 | Multi-bet session | Analyze 1 → Analyze 2 → Check counter shows "2 evaluations" |

---

## 8. PERFORMANCE REQUIREMENTS

| Metric | Target | Maximum |
|--------|--------|---------|
| Time to Interactive | < 1s | 2s |
| Text analysis | < 2s | 5s |
| Image OCR | < 5s | 10s |
| First Contentful Paint | < 0.5s | 1s |
| Bundle size | < 200KB | 500KB |
| Lighthouse score | > 90 | > 70 |

---

## 9. ACCESSIBILITY

### 9.1 Requirements
- Keyboard navigation (Tab, Enter, Space)
- Screen reader labels on all interactive elements
- Focus indicators visible
- Color contrast > 4.5:1
- Touch targets > 44x44px

### 9.2 Implementation
```html
<button aria-label="Voice input" id="chat-voice-btn">🎙️</button>
<button aria-label="Upload image" id="chat-camera-btn">📷</button>
<button aria-label="Focus text field" id="chat-keyboard-btn">⌨️</button>
<button aria-label="Analyze bet" id="chat-send-btn">Analyze</button>
```

---

## 10. CHANGE LOG

| Version | Date | Changes |
|---------|------|---------|
| 0.1.0 | 2026-02-07 | Initial S14 Nexus UI |
| 0.2.0 | 2026-02-07 | S15 messaging-style redesign |
| 0.3.0 | 2026-02-08 | Sport chips, dark red theme, PRD |
| 0.3.1 | TBD | Image OCR fixes, results display |

---

**Document Owner:** Claude (Marvin)  
**Review Cycle:** Weekly during active development  
**Next Review:** 2026-02-15
