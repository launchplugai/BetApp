        // State
        let selectedTier = 'good';
        let debugMode = new URLSearchParams(window.location.search).get('debug') === '1';
        let lastResponse = null;
        let currentMode = 'builder';
        let builderLegs = [];
        let hasOcrLegs = false; // Ticket 34: Track if legs came from OCR
        let pendingEvaluation = null; // Ticket 34: For soft gate flow
        let lockedLegIds = new Set(); // Ticket 37: Track locked legs by deterministic ID (was lockedLegIndices)
        let resultsLegs = []; // Ticket 35: Current legs in results view (for inline edits)
        let isReEvaluation = false; // Ticket 36: Track if current evaluation is a re-evaluation

        // ============================================================
        // S5-A: Copy Debug Info
        // ============================================================

        function copyDebugInfo() {
            const version = 'v0.2.1';
            const commit = '{git_sha}';
            const timestamp = new Date().toISOString();
            const debugText = `DNA Bet Engine ${version}\\nCommit: ${commit}\\nTimestamp: ${timestamp}`;
            
            navigator.clipboard.writeText(debugText).then(() => {
                const btn = event.target;
                const originalText = btn.textContent;
                btn.textContent = 'Copied!';
                btn.style.color = 'var(--green)';
                setTimeout(() => {
                    btn.textContent = originalText;
                    btn.style.color = '';
                }, 2000);
            }).catch(err => {
                console.error('Copy failed:', err);
            });
        }

        // ============================================================
        // Ticket 37: Deterministic Leg ID Generation
        // ============================================================

        /**
         * Ticket 37B: Get canonical string for leg hashing.
         */
        function getCanonicalLegString(leg) {
            return [
                (leg.entity || '').toLowerCase().trim(),
                (leg.market || '').toLowerCase().trim(),
                (leg.value || '').toString().toLowerCase().trim(),
                (leg.sport || '').toLowerCase().trim()
            ].join('|');
        }

        /**
         * Ticket 37B: djb2 hash algorithm (sync fallback).
         */
        function hashDjb2(str) {
            let hash = 5381;
            for (let i = 0; i < str.length; i++) {
                hash = ((hash << 5) + hash) + str.charCodeAt(i);
                hash = hash & hash;
            }
            return 'leg_' + (hash >>> 0).toString(16).padStart(8, '0');
        }

        /**
         * Ticket 37B: Generate leg_id using SHA-256 (WebCrypto) with djb2 fallback.
         * Uses first 16 hex chars of SHA-256 for 64 bits of entropy.
         */
        async function generateLegId(leg) {
            const canonical = getCanonicalLegString(leg);

            // Try WebCrypto SHA-256 first
            if (typeof crypto !== 'undefined' && crypto.subtle) {
                try {
                    const encoder = new TextEncoder();
                    const data = encoder.encode(canonical);
                    const hashBuffer = await crypto.subtle.digest('SHA-256', data);
                    const hashArray = Array.from(new Uint8Array(hashBuffer));
                    const hashHex = hashArray.map(b => b.toString(16).padStart(2, '0')).join('');
                    return 'leg_' + hashHex.substring(0, 16);
                } catch (e) {
                    // WebCrypto failed, fall through to djb2
                }
            }

            // Fallback to djb2 if WebCrypto unavailable
            return hashDjb2(canonical);
        }

        /**
         * Ticket 37B: Synchronous leg_id generation (djb2 only).
         * Use async generateLegId() when possible for SHA-256.
         */
        function generateLegIdSync(leg) {
            return hashDjb2(getCanonicalLegString(leg));
        }

        // Elements
        const betInput = document.getElementById('bet-input');
        const submitBtn = document.getElementById('submit-btn');
        const loading = document.getElementById('loading');
        const errorPanel = document.getElementById('error-panel');
        const results = document.getElementById('results');
        const resetBtn = document.getElementById('reset-btn');
        const inputSection = document.getElementById('input-section');
        const builderSection = document.getElementById('builder-section');
        const pasteSection = document.getElementById('paste-section');
        const legsList = document.getElementById('legs-list');
        const legsEmpty = document.getElementById('legs-empty');
        const builderWarning = document.getElementById('builder-warning');

        // Ticket 32 Part A: Image Upload Elements
        const imageInput = document.getElementById('image-input');
        const imageStatus = document.getElementById('image-status');
        const ocrResult = document.getElementById('ocr-result');
        const ocrText = document.getElementById('ocr-text');
        const useOcrBtn = document.getElementById('use-ocr-text');

        // Ticket 34: OCR Info Box and Review Gate Elements
        const ocrInfoBox = document.getElementById('ocr-info-box');
        const ocrReviewGate = document.getElementById('ocr-review-gate');
        const gateReviewBtn = document.getElementById('gate-review-btn');
        const gateProceedBtn = document.getElementById('gate-proceed-btn');

        // ============================================================
        // Ticket 34 Part A: OCR → Canonical Leg Parsing
        // ============================================================

        /**
         * Parse OCR text into canonical leg objects.
         * Each line is treated as a potential leg.
         */
        function parseOcrToLegs(text) {
            const lines = text.split('\\n').map(l => l.trim()).filter(l => l.length > 0);
            const legs = [];

            for (const line of lines) {
                const leg = parseOcrLine(line);
                if (leg) {
                    legs.push(leg);
                }
            }

            return legs;
        }

        /**
         * Parse a single OCR line into a canonical leg object.
         */
        function parseOcrLine(line) {
            const raw = line;
            let entity = '';
            let market = 'unknown';
            let value = null;
            let sport = null;

            // Normalize line for parsing
            const normalized = line.toLowerCase();

            // Detect sport (optional)
            if (/\b(nba|basketball)\b/i.test(line)) sport = 'NBA';
            else if (/\b(nfl|football)\b/i.test(line)) sport = 'NFL';
            else if (/\b(mlb|baseball)\b/i.test(line)) sport = 'MLB';
            else if (/\b(ncaa|college)\b/i.test(line)) sport = 'NCAA';

            // Detect market type and extract components
            // Moneyline patterns: "Lakers ML", "Lakers to win", "Lakers moneyline"
            if (/\b(ml|moneyline|to win)\b/i.test(line)) {
                market = 'moneyline';
                entity = line.replace(/\b(ml|moneyline|to win)\b/gi, '').trim();
                entity = cleanEntityName(entity);
            }
            // Spread patterns: "Lakers -5.5", "Lakers +3", "Lakers -5.5 spread"
            else if (/[+-]\d+\\.?\d*/i.test(line) && !/\b(over|under|o\/u|pts|points|rebounds|assists|3pt)\b/i.test(line)) {
                market = 'spread';
                const spreadMatch = line.match(/([+-]\d+\\.?\d*)/);
                if (spreadMatch) {
                    value = spreadMatch[1];
                    entity = line.replace(/[+-]\d+\\.?\d*/g, '').replace(/\bspread\b/gi, '').trim();
                    entity = cleanEntityName(entity);
                }
            }
            // Total patterns: "over 220", "under 45.5", "Lakers o220", "Lakers u45"
            else if (/\b(over|under|o\/u)\b/i.test(line) || /[ou]\d+\\.?\d*/i.test(line)) {
                market = 'total';
                const overMatch = line.match(/\b(over|o)\s*(\d+\\.?\d*)/i);
                const underMatch = line.match(/\b(under|u)\s*(\d+\\.?\d*)/i);
                if (overMatch) {
                    value = 'over ' + overMatch[2];
                    entity = line.replace(/\b(over|o)\s*\d+\\.?\d*/gi, '').trim();
                } else if (underMatch) {
                    value = 'under ' + underMatch[2];
                    entity = line.replace(/\b(under|u)\s*\d+\\.?\d*/gi, '').trim();
                }
                entity = cleanEntityName(entity);
            }
            // Player prop patterns: "LeBron over 25.5 pts", "Curry 5.5+ 3pt"
            else if (/\b(pts|points|rebounds|assists|3pt|threes|steals|blocks)\b/i.test(line)) {
                market = 'player_prop';
                const propMatch = line.match(/(over|under)?\s*(\d+\\.?\d*)\s*(pts|points|rebounds|assists|3pt|threes|steals|blocks)/i);
                if (propMatch) {
                    const direction = propMatch[1] ? propMatch[1].toLowerCase() : 'over';
                    value = direction + ' ' + propMatch[2] + ' ' + propMatch[3].toLowerCase();
                }
                entity = line.replace(/(over|under)?\s*\d+\\.?\d*\s*(pts|points|rebounds|assists|3pt|threes|steals|blocks)/gi, '').trim();
                entity = cleanEntityName(entity);
            }
            // If no pattern matched, use the whole line as entity with unknown market
            else {
                entity = cleanEntityName(line);
            }

            // Skip empty entities
            if (!entity || entity.length < 2) {
                entity = line.split(/\s+/)[0] || line;
            }

            // Ticket 37: Generate deterministic leg_id
            const legData = { entity, market, value, sport };
            const leg_id = generateLegIdSync(legData);

            return {
                leg_id: leg_id,
                entity: entity,
                market: market,
                value: value,
                raw: raw,
                text: raw,
                sport: sport,
                source: 'ocr',
                clarity: getOcrLegClarity({ entity, market, value, raw })
            };
        }

        /**
         * Clean up entity name by removing common noise words.
         */
        function cleanEntityName(name) {
            return name
                .replace(/\b(nba|nfl|mlb|ncaa|college|basketball|football|baseball)\b/gi, '')
                .replace(/\b(game|match|vs|@|at)\b/gi, '')
                .replace(/[,()]/g, '')
                .replace(/\s+/g, ' ')
                .trim();
        }

        // ============================================================
        // Ticket 34 Part B: Per-Leg Confidence Indicators
        // ============================================================

        /**
         * Determine clarity indicator for an OCR-derived leg.
         * Returns: 'clear', 'review', or 'ambiguous'
         */
        function getOcrLegClarity(leg) {
            let score = 0;

            // Has recognized market type (+2)
            if (leg.market && leg.market !== 'unknown') {
                score += 2;
            }

            // Has clean entity name (+1)
            if (leg.entity && leg.entity.length >= 3 && /^[a-zA-Z\s]+$/.test(leg.entity)) {
                score += 1;
            }

            // Has numeric value for spread/total/prop (+1)
            if (leg.value && /\d/.test(leg.value)) {
                score += 1;
            }

            // Contains market keywords (+1)
            const marketKeywords = /(ml|moneyline|spread|over|under|pts|points|rebounds|assists)/i;
            if (marketKeywords.test(leg.raw)) {
                score += 1;
            }

            // Penalize if raw text is very short or has unusual characters
            if (leg.raw.length < 5) score -= 1;
            if (/[^a-zA-Z0-9\s.+-]/g.test(leg.raw)) score -= 1;

            // Determine clarity level
            if (score >= 4) return 'clear';
            if (score >= 2) return 'review';
            return 'ambiguous';
        }

        /**
         * Get clarity icon and label for display.
         */
        function getClarityDisplay(clarity) {
            const displays = {
                'clear': { icon: '&#10003;', label: 'Clear match', css: 'clear' },
                'review': { icon: '&#9888;', label: 'Review recommended', css: 'review' },
                'ambiguous': { icon: '?', label: 'Ambiguous', css: 'ambiguous' }
            };
            return displays[clarity] || displays['ambiguous'];
        }

        /**
         * Check if any OCR legs need review (have review or ambiguous clarity).
         */
        function hasLegsNeedingReview() {
            return builderLegs.some(leg =>
                leg.source === 'ocr' && (leg.clarity === 'review' || leg.clarity === 'ambiguous')
            );
        }

        // Ticket 32 Part A: Image Upload Handler
        if (imageInput) {
            imageInput.addEventListener('change', async (e) => {
                const file = e.target.files[0];
                if (!file) return;

                // Validate file type
                if (!file.type.match(/^image\/(png|jpeg|jpg|webp)$/)) {
                    imageStatus.textContent = 'Invalid file type. Use PNG, JPG, or WebP.';
                    imageStatus.className = 'image-status error';
                    imageStatus.style.display = 'block';
                    return;
                }

                // Validate file size (max 5MB)
                if (file.size > 5 * 1024 * 1024) {
                    imageStatus.textContent = 'File too large. Maximum 5MB.';
                    imageStatus.className = 'image-status error';
                    imageStatus.style.display = 'block';
                    return;
                }

                // Show loading state
                imageStatus.textContent = 'Extracting text from image...';
                imageStatus.className = 'image-status loading';
                imageStatus.style.display = 'block';
                ocrResult.style.display = 'none';

                try {
                    const formData = new FormData();
                    // Ticket 38A fix: Backend expects 'image' not 'file'
                    formData.append('image', file);

                    const response = await fetch('/leading-light/evaluate/image', {
                        method: 'POST',
                        body: formData
                    });

                    const data = await response.json();

                    if (!response.ok) {
                        // Ticket 38A: Safely extract error message from response
                        throw new Error(safeResponseError(data, 'OCR extraction failed'));
                    }

                    // Show extracted text with warning banner
                    const extractedText = data.extracted_text || data.image_parse?.extracted_text || '';
                    if (extractedText) {
                        ocrText.value = extractedText;
                        ocrResult.style.display = 'block';
                        imageStatus.textContent = 'Text extracted successfully.';
                        imageStatus.className = 'image-status';
                    } else {
                        imageStatus.textContent = 'No text found in image.';
                        imageStatus.className = 'image-status error';
                    }
                } catch (err) {
                    // Ticket 38A: Safe error string extraction
                    imageStatus.textContent = 'Error: ' + safeAnyToString(err, 'OCR extraction failed');
                    imageStatus.className = 'image-status error';
                }
            });
        }

        // Ticket 34: Use OCR Text Button - Now populates Builder with parsed legs
        // Ticket 36: Reset refine loop state when importing OCR (fresh start)
        if (useOcrBtn) {
            useOcrBtn.addEventListener('click', () => {
                const extractedText = ocrText.value.trim();
                if (extractedText) {
                    // Parse OCR text into canonical legs
                    const ocrLegs = parseOcrToLegs(extractedText);

                    if (ocrLegs.length > 0) {
                        // Ticket 36/37: Clear refine loop state - this is a fresh start
                        lockedLegIds.clear();
                        resultsLegs = [];

                        // Replace builder legs with OCR-derived legs
                        builderLegs = ocrLegs;
                        hasOcrLegs = true;

                        // Switch to Builder mode (not Paste mode)
                        document.querySelectorAll('.mode-btn').forEach(b => b.classList.remove('active'));
                        document.querySelector('.mode-btn[data-mode="builder"]')?.classList.add('active');
                        builderSection.classList.add('active');
                        pasteSection.classList.remove('active');
                        currentMode = 'builder';

                        // Update UI
                        renderLegs();
                        syncTextarea();

                        // Show OCR info box (Part D)
                        if (ocrInfoBox) {
                            ocrInfoBox.classList.add('active');
                        }

                        // Hide the OCR result section since legs are now in builder
                        ocrResult.style.display = 'none';
                        imageStatus.textContent = ocrLegs.length + ' leg(s) added to Builder.';
                        imageStatus.className = 'image-status';
                    } else {
                        // Fallback: copy to textarea if parsing failed
                        betInput.value = extractedText;
                        document.querySelectorAll('.mode-btn').forEach(b => b.classList.remove('active'));
                        document.querySelector('.mode-btn[data-mode="paste"]')?.classList.add('active');
                        builderSection.classList.remove('active');
                        pasteSection.classList.add('active');
                        currentMode = 'paste';
                    }
                }
            });
        }

        // ============================================================
        // Ticket 32 Part B: Session Manager (localStorage)
        // ============================================================
        const SessionManager = {
            STORAGE_KEY: 'dna_session',
            MAX_HISTORY: 5,

            // Get or create session
            getSession: function() {
                try {
                    const stored = localStorage.getItem(this.STORAGE_KEY);
                    if (stored) {
                        return JSON.parse(stored);
                    }
                } catch (e) {
                    console.warn('Session load failed:', e);
                }

                // Create new session
                const session = {
                    id: 'sess_' + Date.now() + '_' + Math.random().toString(36).substr(2, 9),
                    name: '',
                    createdAt: new Date().toISOString(),
                    lastActivity: new Date().toISOString(),
                    evaluations: [],
                    refinementState: null
                };
                this.saveSession(session);
                return session;
            },

            // Save session
            saveSession: function(session) {
                try {
                    session.lastActivity = new Date().toISOString();
                    localStorage.setItem(this.STORAGE_KEY, JSON.stringify(session));
                } catch (e) {
                    console.warn('Session save failed:', e);
                }
            },

            // Update session name
            setSessionName: function(name) {
                const session = this.getSession();
                session.name = name || '';
                this.saveSession(session);
            },

            // Add evaluation to history
            addEvaluation: function(evalData) {
                const session = this.getSession();
                const entry = {
                    id: 'eval_' + Date.now(),
                    timestamp: new Date().toISOString(),
                    input: evalData.input || '',
                    signal: evalData.signal || '',
                    grade: evalData.grade || '',
                    legCount: evalData.legCount || 0
                };
                session.evaluations.unshift(entry);
                // Keep only last MAX_HISTORY
                session.evaluations = session.evaluations.slice(0, this.MAX_HISTORY);
                this.saveSession(session);
                return entry;
            },

            // Get evaluation history
            getEvaluations: function() {
                return this.getSession().evaluations || [];
            },

            // Save refinement state
            saveRefinement: function(state) {
                const session = this.getSession();
                session.refinementState = state;
                this.saveSession(session);
            },

            // Get refinement state
            getRefinement: function() {
                return this.getSession().refinementState;
            },

            // Clear refinement state
            clearRefinement: function() {
                const session = this.getSession();
                session.refinementState = null;
                this.saveSession(session);
            },

            // Get session info for display
            getInfo: function() {
                const session = this.getSession();
                return {
                    id: session.id,
                    name: session.name,
                    evalCount: session.evaluations.length,
                    hasRefinement: !!session.refinementState
                };
            }
        };

        // Export for testing
        window.SessionManager = SessionManager;

        // Initialize session UI
        const sessionNameInput = document.getElementById('session-name');
        const sessionHistorySpan = document.getElementById('session-history');

        function updateSessionUI() {
            const info = SessionManager.getInfo();
            if (sessionNameInput) {
                sessionNameInput.value = info.name || '';
            }
            if (sessionHistorySpan) {
                sessionHistorySpan.textContent = info.evalCount + ' evaluation' + (info.evalCount !== 1 ? 's' : '');
            }
        }

        // Initialize session display
        updateSessionUI();

        // Handle session name changes
        if (sessionNameInput) {
            sessionNameInput.addEventListener('blur', () => {
                SessionManager.setSessionName(sessionNameInput.value.trim());
            });
            sessionNameInput.addEventListener('keydown', (e) => {
                if (e.key === 'Enter') {
                    sessionNameInput.blur();
                }
            });
        }

        // Hook into results display to update session UI
        const originalShowResults = showResults;
        // Will be reassigned after showResults is defined

        // Ticket 23: Mode Toggle
        document.querySelectorAll('.mode-btn').forEach(btn => {
            btn.addEventListener('click', () => {
                document.querySelectorAll('.mode-btn').forEach(b => b.classList.remove('active'));
                btn.classList.add('active');
                currentMode = btn.dataset.mode;
                if (currentMode === 'builder') {
                    builderSection.classList.add('active');
                    pasteSection.classList.remove('active');
                } else {
                    builderSection.classList.remove('active');
                    pasteSection.classList.add('active');
                }
            });
        });

        // Ticket 23: Quick Add Chips
        document.querySelectorAll('.quick-chip').forEach(chip => {
            chip.addEventListener('click', () => {
                const selectedMarket = chip.dataset.market;
                document.getElementById('builder-market').value = selectedMarket;
                updateLineRowVisibility(selectedMarket);
                document.getElementById('builder-team').focus();
            });
        });

        // Show/hide line row based on market type
        function updateLineRowVisibility(market) {
            const lineRow = document.getElementById('line-row');
            if (market === 'Spread' || market === 'Total' || market === 'Player Prop') {
                lineRow.classList.add('active');
            } else {
                lineRow.classList.remove('active');
            }
        }

        // Market dropdown change handler
        document.getElementById('builder-market').addEventListener('change', (e) => {
            updateLineRowVisibility(e.target.value);
        });

        // Ticket 23: Add Leg
        document.getElementById('add-leg-btn').addEventListener('click', addLeg);

        function addLeg() {
            const market = document.getElementById('builder-market').value;
            const team = document.getElementById('builder-team').value.trim();
            const sign = document.getElementById('builder-sign').value;
            const lineValue = document.getElementById('builder-line').value;
            const sport = document.getElementById('builder-sport').value;

            // Build the full line (sign + value)
            let line = '';
            if (lineValue) {
                line = sign + lineValue;
            }

            // Validation
            if (!market) {
                showBuilderWarning('Please select a market type');
                return;
            }
            if (!team) {
                showBuilderWarning('Please enter a team or player');
                return;
            }
            // Line is encouraged for Spread/Total/Prop but not strictly required
            if ((market === 'Spread' || market === 'Total' || market === 'Player Prop') && !lineValue) {
                showBuilderWarning('Line/value recommended for this market type');
                // Don't return - allow adding without line
            }

            hideBuilderWarning();

            // Ticket 27: Map UI market to canonical market type
            const marketMap = {
                'ML': 'moneyline',
                'Spread': 'spread',
                'Total': 'total',
                'Player Prop': 'player_prop'
            };
            const canonicalMarket = marketMap[market] || 'unknown';

            // Build leg text (for display and textarea)
            let legText = team;
            let legValue = null;
            if (market === 'ML') {
                legText += ' ML';
            } else if (market === 'Spread') {
                legText += ' ' + (line || '');
                legValue = line || null;
            } else if (market === 'Total') {
                // For totals, use "over" or "under" based on sign
                const overUnder = sign === '+' ? 'over' : 'under';
                const totalText = lineValue ? overUnder + ' ' + lineValue : '';
                legText += ' ' + totalText;
                legValue = totalText || null;
            } else if (market === 'Player Prop') {
                // For props, use "over" or "under" based on sign
                const overUnder = sign === '+' ? 'over' : 'under';
                const propText = lineValue ? overUnder + ' ' + lineValue : 'prop';
                legText += ' ' + propText;
                legValue = propText || null;
            }
            legText = legText.trim();

            // Ticket 27 Part B: Add to legs array with canonical schema
            // Ticket 37: Include deterministic leg_id
            const legData = { entity: team, market: canonicalMarket, value: legValue, sport: sport };
            const leg_id = generateLegIdSync(legData);

            builderLegs.push({
                leg_id: leg_id,
                entity: team,
                market: canonicalMarket,
                value: legValue,
                raw: legText,
                // Keep display fields for UI
                text: legText,
                sport: sport,
            });

            renderLegs();
            syncTextarea();
            clearBuilderInputs();
        }

        function removeLeg(index) {
            builderLegs.splice(index, 1);
            renderLegs();
            syncTextarea();
        }

        function renderLegs() {
            // Clear existing leg items (but keep empty message)
            legsList.querySelectorAll('.leg-item').forEach(el => el.remove());

            if (builderLegs.length === 0) {
                legsEmpty.style.display = 'block';
            } else {
                legsEmpty.style.display = 'none';
                builderLegs.forEach((leg, i) => {
                    const item = document.createElement('div');
                    const isOcr = leg.source === 'ocr';
                    item.className = 'leg-item' + (isOcr ? ' ocr-leg editable' : '');
                    item.dataset.index = i;

                    // Build leg HTML with OCR metadata if applicable
                    let legHtml = `<span class="leg-num">${i + 1}.</span>`;
                    legHtml += `<span class="leg-text">${escapeHtml(leg.text)}</span>`;

                    // Ticket 34: Add meta section for OCR legs
                    if (isOcr) {
                        const clarityDisplay = getClarityDisplay(leg.clarity || 'review');
                        legHtml += `<div class="leg-meta">`;
                        legHtml += `<span class="leg-clarity ${clarityDisplay.css}">${clarityDisplay.icon} ${clarityDisplay.label}</span>`;
                        legHtml += `<span class="leg-source-tag">Detected from slip</span>`;
                        legHtml += `</div>`;
                    }

                    legHtml += `<button class="remove-leg-btn" onclick="removeLeg(${i})">Remove</button>`;
                    item.innerHTML = legHtml;

                    // Ticket 34: Click to edit OCR legs
                    if (isOcr) {
                        item.addEventListener('click', (e) => {
                            // Don't trigger edit if clicking remove button
                            if (e.target.classList.contains('remove-leg-btn')) return;
                            startEditLeg(i);
                        });
                    }

                    legsList.appendChild(item);
                });
            }
        }

        // Ticket 34: Edit leg functionality
        let editingLegIndex = null;

        function startEditLeg(index) {
            // Don't start new edit if already editing
            if (editingLegIndex !== null) return;

            editingLegIndex = index;
            const leg = builderLegs[index];
            const item = legsList.querySelector(`.leg-item[data-index="${index}"]`);

            if (!item) return;

            // Replace content with edit form
            item.classList.add('editing');
            item.classList.remove('editable');
            item.innerHTML = `
                <div style="display:flex; align-items:center; gap:8px; width:100%;">
                    <span class="leg-num">${index + 1}.</span>
                    <input type="text" class="leg-edit-input" value="${escapeHtml(leg.raw)}" autofocus>
                </div>
                <div class="leg-edit-actions">
                    <button class="leg-edit-btn leg-edit-save">Save</button>
                    <button class="leg-edit-btn leg-edit-cancel">Cancel</button>
                </div>
            `;

            const input = item.querySelector('.leg-edit-input');
            const saveBtn = item.querySelector('.leg-edit-save');
            const cancelBtn = item.querySelector('.leg-edit-cancel');

            // Focus and select
            input.focus();
            input.select();

            // Prevent click from bubbling
            item.onclick = (e) => e.stopPropagation();

            // Save handler
            saveBtn.addEventListener('click', () => saveEditLeg(index, input.value));

            // Cancel handler
            cancelBtn.addEventListener('click', () => cancelEditLeg());

            // Enter to save, Escape to cancel
            input.addEventListener('keydown', (e) => {
                if (e.key === 'Enter') {
                    e.preventDefault();
                    saveEditLeg(index, input.value);
                } else if (e.key === 'Escape') {
                    cancelEditLeg();
                }
            });
        }

        function saveEditLeg(index, newText) {
            newText = newText.trim();
            if (newText) {
                // Re-parse the edited text
                const newLeg = parseOcrLine(newText);
                // Mark as edited by user (upgrades clarity to clear since user reviewed it)
                newLeg.clarity = 'clear';
                builderLegs[index] = newLeg;
            }
            editingLegIndex = null;
            renderLegs();
            syncTextarea();
        }

        function cancelEditLeg() {
            editingLegIndex = null;
            renderLegs();
        }

        function syncTextarea() {
            // Update textarea with current legs (single source of truth)
            betInput.value = builderLegs.map(l => l.text).join('\\n');
        }

        function clearBuilderInputs() {
            document.getElementById('builder-market').value = '';
            document.getElementById('builder-team').value = '';
            document.getElementById('builder-sign').value = '-';
            document.getElementById('builder-line').value = '';
            // Keep sport selected
            updateLineRowVisibility('');  // Hide line row when cleared
        }

        function showBuilderWarning(msg) {
            builderWarning.textContent = msg;
            builderWarning.classList.add('active');
        }

        function hideBuilderWarning() {
            builderWarning.classList.remove('active');
        }

        function escapeHtml(text) {
            const div = document.createElement('div');
            div.textContent = text;
            return div.innerHTML;
        }

        /**
         * Ticket 38A: Safe error message extraction.
         * Handles Error objects, API error responses, and unknown objects.
         * Never returns "[object Object]".
         */
        function safeAnyToString(x, fallback) {
            if (x === null || x === undefined) {
                return fallback || 'Unknown error';
            }
            if (typeof x === 'string') {
                return x;
            }
            // Error object
            if (x.message && typeof x.message === 'string') {
                return x.message;
            }
            // API error response shapes
            if (x.detail) {
                // Pydantic validation errors have detail as array
                if (Array.isArray(x.detail)) {
                    const msgs = x.detail.map(d => d.msg || d.message || JSON.stringify(d)).join('; ');
                    return msgs || fallback || 'Validation error';
                }
                if (typeof x.detail === 'string') {
                    return x.detail;
                }
                // detail is object
                if (x.detail.msg) return x.detail.msg;
                if (x.detail.message) return x.detail.message;
            }
            if (x.error && typeof x.error === 'string') {
                return x.error;
            }
            if (x.msg && typeof x.msg === 'string') {
                return x.msg;
            }
            // Custom toString (not Object.prototype.toString)
            if (typeof x.toString === 'function' && x.toString !== Object.prototype.toString) {
                const str = x.toString();
                if (str !== '[object Object]') {
                    return str;
                }
            }
            // Last resort: try JSON stringify (bounded length)
            try {
                const json = JSON.stringify(x);
                if (json && json !== '{}' && json.length < 200) {
                    return json;
                }
            } catch (e) {
                // ignore stringify errors
            }
            return fallback || 'Unknown error';
        }

        /**
         * Ticket 38A: Extract error message from API response.
         * Use for response.json() results.
         */
        function safeResponseError(resJson, fallback) {
            return safeAnyToString(resJson, fallback);
        }

        // Tier selector
        document.querySelectorAll('.tier-btn').forEach(btn => {
            btn.addEventListener('click', () => {
                document.querySelectorAll('.tier-btn').forEach(b => b.classList.remove('active'));
                btn.classList.add('active');
                selectedTier = btn.dataset.tier;
            });
        });

        // Submit handler
        submitBtn.addEventListener('click', async () => {
            // Always use textarea content as single source of truth
            const input = betInput.value.trim();
            if (!input) {
                if (currentMode === 'builder' && builderLegs.length === 0) {
                    showError('Please add at least one leg to your parlay');
                } else {
                    showError('Please enter a bet slip');
                }
                return;
            }

            // Ticket 34 Part C: Check if OCR legs need review
            if (hasOcrLegs && hasLegsNeedingReview()) {
                // Store the evaluation intent and show soft gate
                pendingEvaluation = { input, tier: selectedTier };
                showOcrReviewGate();
                return;
            }

            // Ticket 36/37: This is a fresh evaluation, not a re-evaluation
            // Clear stale lock state to prevent state collision
            isReEvaluation = false;
            lockedLegIds.clear();

            // Proceed with evaluation
            await runEvaluation(input);
        });

        // Ticket 34 Part C: Soft gate handlers
        if (gateReviewBtn) {
            gateReviewBtn.addEventListener('click', () => {
                hideOcrReviewGate();
                pendingEvaluation = null;
                // Focus the legs list for review
                const firstOcrLeg = legsList.querySelector('.leg-item.ocr-leg');
                if (firstOcrLeg) {
                    firstOcrLeg.scrollIntoView({ behavior: 'smooth', block: 'center' });
                }
            });
        }

        if (gateProceedBtn) {
            gateProceedBtn.addEventListener('click', async () => {
                hideOcrReviewGate();
                if (pendingEvaluation) {
                    // Ticket 36/37: This is a fresh evaluation from OCR, clear stale lock state
                    isReEvaluation = false;
                    lockedLegIds.clear();
                    await runEvaluation(pendingEvaluation.input);
                    pendingEvaluation = null;
                }
            });
        }

        function showOcrReviewGate() {
            if (ocrReviewGate) {
                ocrReviewGate.classList.add('active');
            }
        }

        function hideOcrReviewGate() {
            if (ocrReviewGate) {
                ocrReviewGate.classList.remove('active');
            }
        }

        // Core evaluation function
        async function runEvaluation(input) {
            showLoading();

            try {
                // Ticket 27 Part B: Build request with canonical legs if from builder
                const requestBody = { input, tier: selectedTier };

                // If we have builder legs, send canonical structure
                if (currentMode === 'builder' && builderLegs.length > 0) {
                    requestBody.legs = builderLegs.map(leg => ({
                        entity: leg.entity,
                        market: leg.market,
                        value: leg.value,
                        raw: leg.raw || leg.text
                    }));
                }

                const response = await fetch('/app/evaluate', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify(requestBody)
                });

                const data = await response.json();
                lastResponse = data;

                if (!response.ok) {
                    // Ticket 38A: Safely extract error message
                    showError(safeResponseError(data, 'Evaluation failed'));
                    return;
                }

                showResults(data);
            } catch (err) {
                showError('Network error. Please try again.');
            }
        }

        function showLoading() {
            inputSection.style.display = 'none';
            loading.classList.add('active');
            errorPanel.classList.remove('active');
            results.classList.remove('active');
            document.getElementById('action-buttons').classList.remove('active');
        }

        function showError(message) {
            loading.classList.remove('active');
            inputSection.style.display = 'block';
            errorPanel.textContent = message;
            errorPanel.classList.add('active');
            results.classList.remove('active');
            document.getElementById('action-buttons').classList.remove('active');
        }

        function showResults(data) {
            loading.classList.remove('active');
            errorPanel.classList.remove('active');
            results.classList.add('active');
            document.getElementById('action-buttons').classList.add('active');

            // Ticket 32 Part B: Save evaluation to session history
            const parlay = data.evaluatedParlay;
            if (parlay) {
                SessionManager.addEvaluation({
                    input: parlay.display_label || betInput.value.trim(),
                    signal: data.signalInfo?.signal || '',
                    grade: data.signalInfo?.grade || '',
                    legCount: (parlay.legs || []).length
                });
                updateSessionUI();
            }

            // Ticket 25: Evaluated Parlay Receipt
            // Ticket 26 Part A: Leg interpretation display
            // Ticket 35: Add remove/lock controls for inline refinement
            // Ticket 37: Use leg_id for identity instead of index
            if (parlay) {
                document.getElementById('parlay-label').textContent = parlay.display_label || 'Parlay';
                // Store legs for inline editing with deterministic leg_id
                resultsLegs = (parlay.legs || []).map((leg, i) => {
                    // Generate leg_id from canonical fields
                    const leg_id = generateLegIdSync({
                        entity: leg.entity || leg.text?.split(' ')[0] || '',
                        market: leg.bet_type || 'unknown',
                        value: leg.line_value || null,
                        sport: leg.sport || ''
                    });
                    return {
                        ...leg,
                        leg_id: leg_id,
                        originalIndex: i,
                        locked: lockedLegIds.has(leg_id)
                    };
                });
                renderResultsLegs();
            }

            // Grade/Signal (S3-A: Confidence Gradient System)
            const signal = data.signalInfo?.signal || 'yellow';
            const signalLabels = { blue: 'Stable', green: 'Composed', yellow: 'Pressured', red: 'Fragile' };
            const gradeSignal = document.getElementById('grade-signal');
            gradeSignal.className = 'grade-signal ' + signal;
            gradeSignal.textContent = signal[0].toUpperCase();

            document.getElementById('grade-title').textContent = signalLabels[signal] || 'Unknown';
            document.getElementById('grade-subtitle').textContent =
                data.evaluation?.recommendation?.reason ||
                data.humanSummary?.verdict ||
                'Evaluation complete';

            // S3-B: Delta Sentence (progress feedback)
            const deltaSentenceEl = document.getElementById('delta-sentence');
            if (data.delta && isReEvaluation) {
                const delta = data.delta;
                let deltaText = '';
                
                if (delta.legs_removed > 0 || delta.legs_added > 0) {
                    if (delta.legs_removed > 0 && delta.legs_added === 0) {
                        deltaText = `You removed ${delta.legs_removed} leg${delta.legs_removed > 1 ? 's' : ''}. `;
                    } else if (delta.legs_added > 0 && delta.legs_removed === 0) {
                        deltaText = `You added ${delta.legs_added} leg${delta.legs_added > 1 ? 's' : ''}. `;
                    } else {
                        deltaText = `You traded ${delta.legs_removed} for ${delta.legs_added}. `;
                    }
                }
                
                // Add structural direction
                if (delta.correlation_delta !== 0) {
                    if (delta.correlation_delta < 0) {
                        deltaText += 'Structure tightened.';
                    } else {
                        deltaText += 'Structure loosened.';
                    }
                }
                
                if (deltaText) {
                    deltaSentenceEl.textContent = deltaText.trim();
                    deltaSentenceEl.classList.remove('hidden');
                } else {
                    deltaSentenceEl.classList.add('hidden');
                }
            } else {
                deltaSentenceEl.classList.add('hidden');
            }

            // Risks
            const risksList = document.getElementById('risks-list');
            risksList.innerHTML = '';
            const risks = [];
            if (data.primaryFailure?.type) {
                risks.push(data.primaryFailure.type.replace(/_/g, ' '));
            }
            if (data.evaluation?.inductor?.explanation) {
                risks.push(data.evaluation.inductor.explanation);
            }
            if (data.secondaryFactors) {
                data.secondaryFactors.slice(0, 2).forEach(f => risks.push(f));
            }
            if (risks.length === 0) {
                risks.push('No significant risks detected');
            }
            risks.slice(0, 4).forEach(risk => {
                const li = document.createElement('li');
                li.textContent = risk;
                risksList.appendChild(li);
            });

            // Ticket 25: Notable Legs
            const notableSection = document.getElementById('notable-legs-section');
            const notableList = document.getElementById('notable-legs-list');
            notableList.innerHTML = '';
            const notable = data.notableLegs || [];
            if (notable.length === 0) {
                notableSection.style.display = 'none';
            } else {
                notableSection.style.display = 'block';
                notable.forEach(item => {
                    const li = document.createElement('li');
                    li.className = 'notable-leg';
                    li.innerHTML =
                        '<div class="notable-leg-text">' + escapeHtml(item.leg) + '</div>' +
                        '<div class="notable-leg-reason">' + escapeHtml(item.reason) + '</div>';
                    notableList.appendChild(li);
                });
            }

            // Artifacts
            const artifacts = data.proofSummary?.sample_artifacts || [];
            const counts = data.proofSummary?.dna_artifact_counts || {};
            const countStr = Object.entries(counts).map(([k,v]) => k + ':' + v).join(', ') || 'none';
            document.getElementById('artifact-count').textContent = countStr;

            const artifactsList = document.getElementById('artifacts-list');
            artifactsList.innerHTML = '';
            if (artifacts.length === 0) {
                const li = document.createElement('li');
                li.className = 'artifact-item';
                li.innerHTML = '<div class="artifact-label">(No artifacts)</div>';
                artifactsList.appendChild(li);
            } else {
                artifacts.slice(0, 5).forEach(a => {
                    const li = document.createElement('li');
                    const type = a.artifact_type || a.type || 'unknown';
                    li.className = 'artifact-item artifact-type-' + type;
                    li.innerHTML =
                        '<div class="artifact-label">' + (a.display_label || type) + '</div>' +
                        '<div class="artifact-text">' + (a.display_text || '') + '</div>';
                    artifactsList.appendChild(li);
                });
            }

            // Ticket 25: Final Verdict
            const verdict = data.finalVerdict;
            const verdictSection = document.getElementById('verdict-section');
            if (verdict && (verdict.verdictText || verdict.verdict_text)) {
                verdictSection.style.display = 'block';
                document.getElementById('verdict-text').textContent = verdict.verdictText || verdict.verdict_text;
                // Apply tone class
                verdictSection.className = 'card verdict-section';
                if (verdict.tone) {
                    verdictSection.classList.add('tone-' + verdict.tone);
                }
            } else {
                verdictSection.style.display = 'none';
            }

            // Ticket 26 Part C: Gentle Guidance
            const guidance = data.gentleGuidance;
            const guidanceSection = document.getElementById('guidance-section');
            if (guidance && guidance.suggestions && guidance.suggestions.length > 0) {
                guidanceSection.style.display = 'block';
                document.getElementById('guidance-header').textContent = guidance.header || 'If you wanted to adjust this:';
                const guidanceList = document.getElementById('guidance-list');
                guidanceList.innerHTML = '';
                guidance.suggestions.forEach(suggestion => {
                    const li = document.createElement('li');
                    li.textContent = suggestion;
                    guidanceList.appendChild(li);
                });
            } else {
                guidanceSection.style.display = 'none';
            }

            // Ticket 27 Part D: Grounding Warnings
            const groundingWarnings = data.groundingWarnings;
            const groundingSection = document.getElementById('grounding-warnings');
            if (groundingWarnings && groundingWarnings.length > 0) {
                groundingSection.style.display = 'block';
                const warningsList = document.getElementById('grounding-warnings-list');
                warningsList.innerHTML = '';
                groundingWarnings.forEach(warning => {
                    const li = document.createElement('li');
                    li.textContent = warning;
                    warningsList.appendChild(li);
                });
            } else {
                groundingSection.style.display = 'none';
            }

            // Ticket D1 / 38B-C3: Grounding Score Display
            const groundingScore = data.groundingScore;
            const groundingScorePanel = document.getElementById('grounding-score-panel');
            if (groundingScore) {
                groundingScorePanel.style.display = 'block';
                
                // Plain-language narrative (primary signal)
                const narrative = document.getElementById('grounding-score-narrative');
                const structural = groundingScore.structural || 0;
                const heuristics = groundingScore.heuristics || 0;
                const generic = groundingScore.generic || 0;
                
                let narrativeText = '';
                if (structural >= 50) {
                    narrativeText = 'This analysis is grounded mainly by structural features like leg relationships and bet types.';
                } else if (heuristics >= 50) {
                    narrativeText = 'This analysis relies heavily on bet-type patterns and established heuristics.';
                } else if (generic >= 50) {
                    narrativeText = 'This analysis uses general guidance with limited structural grounding.';
                } else if (structural >= heuristics && structural >= generic) {
                    narrativeText = 'This analysis draws primarily from structural features.';
                } else if (heuristics >= structural && heuristics >= generic) {
                    narrativeText = 'This analysis is more intuition-driven than structural.';
                } else {
                    narrativeText = 'This analysis blends structural, heuristic, and general insights.';
                }
                narrative.textContent = narrativeText;
                
                // Supporting numbers (secondary signal)
                document.getElementById('grounding-score-structural').textContent = structural + '%';
                document.getElementById('grounding-score-heuristics').textContent = heuristics + '%';
                document.getElementById('grounding-score-generic').textContent = generic + '%';
            } else {
                groundingScorePanel.style.display = 'none';
            }

            // Debug section
            if (debugMode) {
                document.getElementById('debug-section').classList.add('active');
                const uiStatus = data.proofSummary?.ui_contract_status || 'unknown';
                const uiVersion = data.proofSummary?.ui_contract_version || 'unknown';
                const statusEl = document.getElementById('ui-contract-status');
                statusEl.textContent = 'UI: ' + uiStatus + ' (' + uiVersion + ')';
                statusEl.className = 'contract-status ' + (uiStatus === 'PASS' ? 'pass' : 'fail');
                document.getElementById('debug-content').textContent = JSON.stringify(data, null, 2);
            }
        }

        function toggleDebug() {
            const content = document.getElementById('debug-content');
            content.style.display = content.style.display === 'none' ? 'block' : 'none';
        }

        function resetForm() {
            inputSection.style.display = 'block';
            results.classList.remove('active');
            document.getElementById('action-buttons').classList.remove('active');
            betInput.value = '';
            // Ticket 23: Also reset builder state
            builderLegs = [];
            renderLegs();
            clearBuilderInputs();
            hideBuilderWarning();
            // Ticket 34: Reset OCR state
            hasOcrLegs = false;
            pendingEvaluation = null;
            if (ocrInfoBox) ocrInfoBox.classList.remove('active');
            if (ocrResult) ocrResult.style.display = 'none';
            if (imageStatus) imageStatus.style.display = 'none';
            if (imageInput) imageInput.value = '';
            // Ticket 35: Reset refine loop state
            // Ticket 36: Also reset re-evaluation flag
            // Ticket 37: Use leg_id based tracking
            lockedLegIds.clear();
            resultsLegs = [];
            isReEvaluation = false;
            // Focus appropriate element based on mode
            if (currentMode === 'builder') {
                document.getElementById('builder-team').focus();
            } else {
                betInput.focus();
            }
        }

        // Ticket 25: Refine Parlay - returns to builder with legs preloaded
        // Ticket 35: Now uses resultsLegs (which may have been modified)
        function refineParlay() {
            // Use resultsLegs if available (reflects inline edits), otherwise fall back
            const legsToUse = resultsLegs.length > 0 ? resultsLegs :
                              (lastResponse?.evaluatedParlay?.legs || []);

            if (legsToUse.length === 0) {
                resetForm();
                return;
            }

            // Preload legs from the current results state
            // Ticket 37: Include leg_id for deterministic tracking
            builderLegs = legsToUse.map(leg => {
                const entity = leg.entity || leg.text?.split(' ')[0] || '';
                const market = leg.bet_type === 'player_prop' ? 'player_prop' :
                               leg.bet_type === 'total' ? 'total' :
                               leg.bet_type === 'spread' ? 'spread' : 'moneyline';
                const value = leg.line_value || null;
                const sport = leg.sport || '';
                // Use existing leg_id or generate new one
                const leg_id = leg.leg_id || generateLegIdSync({ entity, market, value, sport });
                return {
                    leg_id: leg_id,
                    entity: entity,
                    text: leg.text,
                    raw: leg.text,
                    sport: sport,
                    market: market,
                    value: value,
                    locked: leg.locked || false
                };
            });

            // Switch to builder mode
            currentMode = 'builder';
            document.querySelectorAll('.mode-btn').forEach(b => b.classList.remove('active'));
            document.querySelector('[data-mode="builder"]').classList.add('active');
            builderSection.classList.add('active');
            pasteSection.classList.remove('active');

            // Update UI
            renderLegs();
            syncTextarea();

            // Hide results, show input
            inputSection.style.display = 'block';
            results.classList.remove('active');
            document.getElementById('action-buttons').classList.remove('active');

            // Focus on builder
            document.getElementById('builder-team').focus();
        }

        // Enter key submits
        betInput.addEventListener('keydown', (e) => {
            if (e.key === 'Enter' && e.metaKey) {
                submitBtn.click();
            }
        });

        // ============================================================
        // Ticket 35: Inline Refine Loop
        // ============================================================

        /**
         * Render legs in results view with remove/lock controls.
         */
        function renderResultsLegs() {
            const parlayLegs = document.getElementById('parlay-legs');
            parlayLegs.innerHTML = '';

            resultsLegs.forEach((leg, i) => {
                const li = document.createElement('li');
                li.dataset.index = i;
                if (leg.locked) {
                    li.classList.add('locked');
                }

                // Leg number
                let html = '<span class="result-leg-num">' + (i + 1) + '.</span>';

                // Leg content
                html += '<div class="result-leg-content">';
                html += '<span class="result-leg-text">' + escapeHtml(leg.text) + '</span>';
                html += '<span class="leg-type">' + (leg.bet_type || '').replace('_', ' ') + '</span>';
                if (leg.interpretation) {
                    html += '<div class="leg-interpretation">' + escapeHtml(leg.interpretation) + '</div>';
                }
                html += '</div>';

                // Controls
                html += '<div class="result-leg-controls">';
                // Lock button
                const lockIcon = leg.locked ? '&#128274;' : '&#128275;'; // locked vs unlocked
                const lockClass = leg.locked ? 'leg-lock-btn locked' : 'leg-lock-btn';
                const lockTitle = leg.locked ? 'Unlock this leg' : 'Lock this leg (prevent removal)';
                html += '<button class="' + lockClass + '" onclick="toggleLegLock(' + i + ')" title="' + lockTitle + '">' + lockIcon + '</button>';
                // Remove button (disabled if locked)
                const removeDisabled = leg.locked ? 'disabled' : '';
                const removeTitle = leg.locked ? 'Unlock to remove' : 'Remove this leg';
                // Ticket 39: Use leg_id for robust removal (survives reordering)
                html += '<button class="leg-remove-btn" onclick="removeLegFromResults(\'' + leg.leg_id + '\')" ' + removeDisabled + ' title="' + removeTitle + '">Remove</button>';
                html += '</div>';

                li.innerHTML = html;
                parlayLegs.appendChild(li);
            });

            // Update the parlay label to reflect current count
            updateParlayLabel();
            // Update re-evaluate button state
            updateReEvaluateButton();
        }

        /**
         * Update parlay label to show current leg count.
         */
        function updateParlayLabel() {
            const count = resultsLegs.length;
            let label = '';
            if (count === 0) {
                label = 'No legs remaining';
            } else if (count === 1) {
                label = 'Single bet';
            } else {
                label = count + '-leg parlay';
            }
            document.getElementById('parlay-label').textContent = label;
        }

        /**
         * Update re-evaluate button enabled state.
         */
        function updateReEvaluateButton() {
            const btn = document.getElementById('reevaluate-btn');
            if (btn) {
                btn.disabled = resultsLegs.length === 0;
            }
        }

        /**
         * Toggle lock state for a leg.
         */
        function toggleLegLock(index) {
            if (index < 0 || index >= resultsLegs.length) return;

            const leg = resultsLegs[index];
            leg.locked = !leg.locked;

            // Ticket 37: Update lock tracking using deterministic leg_id
            if (leg.locked) {
                lockedLegIds.add(leg.leg_id);
            } else {
                lockedLegIds.delete(leg.leg_id);
            }

            renderResultsLegs();
        }

        /**
         * Remove a leg from results (inline refinement).
         * Ticket 39: Accepts leg_id (preferred) or index for robustness.
         * Does NOT remove locked legs.
         */
        function removeLegFromResults(identifier) {
            let index;
            if (typeof identifier === 'string') {
                // Ticket 39: leg_id-based removal (robust)
                index = resultsLegs.findIndex(leg => leg.leg_id === identifier);
            } else {
                // Legacy: index-based removal
                index = identifier;
            }
            if (index < 0 || index >= resultsLegs.length) return;

            const leg = resultsLegs[index];
            // Cannot remove locked leg
            if (leg.locked) return;

            // Remove from results
            resultsLegs.splice(index, 1);

            // Sync state: update builderLegs and textarea
            syncStateFromResults();

            // Re-render
            renderResultsLegs();
        }

        /**
         * Sync all state from resultsLegs.
         * Ensures builderLegs, textarea, and canonical state stay in sync.
         * Ticket 37: Includes leg_id for deterministic tracking.
         */
        function syncStateFromResults() {
            // Update builderLegs to match resultsLegs
            builderLegs = resultsLegs.map(leg => ({
                leg_id: leg.leg_id, // Ticket 37: Preserve deterministic leg_id
                entity: leg.entity || leg.text?.split(' ')[0] || '',
                market: leg.bet_type || 'unknown',
                value: leg.line_value || null,
                raw: leg.text,
                text: leg.text,
                sport: leg.sport || '',
                source: 'refined'
            }));

            // Update textarea
            syncTextarea();
        }

        /**
         * Re-evaluate parlay with current legs (after inline removals).
         * Ticket 36: This is a re-evaluation, so we preserve lock state.
         * Ticket 37: Uses deterministic leg_id for stable lock preservation.
         */
        async function reEvaluateParlay() {
            if (resultsLegs.length === 0) {
                showError('Add at least one leg to evaluate');
                return;
            }

            // Ticket 36: Mark this as a re-evaluation (lock state should be preserved)
            isReEvaluation = true;

            // Build input from current results legs
            const input = resultsLegs.map(l => l.text).join('\\n');

            // Ensure state is synced
            syncStateFromResults();

            // Ticket 37: lockedLegIds persists across re-evaluation
            // No need to save/restore - showResults will use lockedLegIds.has(leg_id)

            // Run evaluation
            await runEvaluation(input);

            // Ticket 37: Lock state is automatically restored in showResults
            // via lockedLegIds.has(leg_id) check
            renderResultsLegs();
        }
// S14: NEXUS INPUT PANEL - Jarvis Experience
// ============================================================
(function() {
    // Nexus elements
    const nexusTextInput = document.getElementById('nexus-text-input');
    const nexusAnalyzeBtn = document.getElementById('nexus-analyze-btn');
    const nexusUploadBtn = document.getElementById('nexus-upload-btn');
    const nexusFileInput = document.getElementById('nexus-file-input');
    const nexusImagePreview = document.getElementById('nexus-image-preview');
    const nexusPreviewThumb = document.getElementById('nexus-preview-thumb');
    const nexusPreviewName = document.getElementById('nexus-preview-name');
    const nexusClearImage = document.getElementById('nexus-clear-image');
    const nexusBuilderToggle = document.getElementById('nexus-builder-toggle');
    const nexusAdvancedPanel = document.getElementById('nexus-advanced-panel');
    const nexusWorking = document.getElementById('nexus-working');
    const nexusDetectedLegs = document.getElementById('nexus-detected-legs');
    const nexusLegsList = document.getElementById('nexus-legs-list');

    // State
    let nexusDetectedLegsData = [];

    // A: Text input analyze
    if (nexusAnalyzeBtn && nexusTextInput) {
        nexusAnalyzeBtn.addEventListener('click', function() {
            const text = nexusTextInput.value.trim();
            if (!text) {
                showToast('Enter your bet first');
                return;
            }
            // Use existing evaluation pipeline
            evaluateFromNexus(text);
        });

        // Enter key to submit
        nexusTextInput.addEventListener('keydown', function(e) {
            if (e.key === 'Enter' && (e.metaKey || e.ctrlKey)) {
                nexusAnalyzeBtn.click();
            }
        });
    }

    // B: Image upload
    if (nexusUploadBtn && nexusFileInput) {
        nexusUploadBtn.addEventListener('click', function() {
            nexusFileInput.click();
        });

        nexusFileInput.addEventListener('change', function(e) {
            const file = e.target.files[0];
            if (!file) return;
            handleNexusImage(file);
        });
    }

    // Clear image
    if (nexusClearImage) {
        nexusClearImage.addEventListener('click', function() {
            nexusFileInput.value = '';
            nexusImagePreview.classList.add('hidden');
        });
    }

    // C: Toggle advanced builder
    if (nexusBuilderToggle && nexusAdvancedPanel) {
        nexusBuilderToggle.addEventListener('click', function() {
            const isExpanded = !nexusAdvancedPanel.classList.contains('hidden');
            nexusAdvancedPanel.classList.toggle('hidden');
            nexusBuilderToggle.setAttribute('aria-expanded', !isExpanded);
        });
    }

    // Handle image file
    function handleNexusImage(file) {
        // Validate
        const validTypes = ['image/png', 'image/jpeg', 'image/jpg', 'image/webp'];
        if (!validTypes.includes(file.type)) {
            showToast('Please upload PNG, JPG, or WebP');
            return;
        }
        if (file.size > 5 * 1024 * 1024) {
            showToast('Image must be under 5MB');
            return;
        }

        // Show preview
        const reader = new FileReader();
        reader.onload = function(e) {
            nexusPreviewThumb.src = e.target.result;
            nexusPreviewName.textContent = file.name;
            nexusImagePreview.classList.remove('hidden');
        };
        reader.readAsDataURL(file);

        // Submit for OCR using existing endpoint
        submitNexusOCR(file);
    }

    // Submit to OCR (uses existing OCR endpoint)
    async function submitNexusOCR(file) {
        showNexusWorking(true);
        try {
            const formData = new FormData();
            formData.append('file', file);

            const response = await fetch('/api/evaluate/ocr', {
                method: 'POST',
                body: formData
            });

            if (!response.ok) throw new Error('OCR failed');

            const data = await response.json();
            if (data.text) {
                nexusTextInput.value = data.text;
                showToast('Text extracted - tap Analyze');
            }
        } catch (err) {
            console.error('OCR error:', err);
            showToast('Could not read image. Try typing instead.');
        } finally {
            showNexusWorking(false);
        }
    }

    // Evaluate from Nexus (bridges to existing pipeline)
    async function evaluateFromNexus(text) {
        showNexusWorking(true);
        try {
            // Use existing evaluation endpoint
            const tier = document.querySelector('input[name="eval-tier"]:checked')?.value || 'good';

            const response = await fetch('/api/evaluate', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ text: text, tier: tier })
            });

            if (!response.ok) throw new Error('Evaluation failed');

            const data = await response.json();

            // Store detected legs for S14-B
            if (data.legs || data.snapshot?.legs) {
                nexusDetectedLegsData = data.legs || data.snapshot.legs || [];
                renderDetectedLegs();
            }

            // Show results (existing display logic)
            displayNexusResults(data);

        } catch (err) {
            console.error('Evaluation error:', err);
            showToast('Analysis failed. Try again.');
        } finally {
            showNexusWorking(false);
        }
    }

    // Show/hide working state
    function showNexusWorking(show) {
        if (nexusWorking) {
            nexusWorking.classList.toggle('hidden', !show);
        }
        if (nexusAnalyzeBtn) {
            nexusAnalyzeBtn.disabled = show;
        }
    }

    // S14-B: Render detected legs
    function renderDetectedLegs() {
        if (!nexusLegsList) return;

        if (!nexusDetectedLegsData.length) {
            nexusLegsList.innerHTML = '<div class="nexus-no-legs">No legs detected</div>';
            nexusDetectedLegs.classList.remove('hidden');
            return;
        }

        nexusLegsList.innerHTML = nexusDetectedLegsData.map((leg, index) => {
            const type = leg.bet_type || leg.market || 'PROP';
            const text = leg.player || leg.team || leg.description || leg.text || `Leg ${index + 1}`;
            return `
                <div class="nexus-leg-pill" data-index="${index}">
                    <span class="leg-text" data-index="${index}">${escapeHtml(text)}</span>
                    <span class="leg-type">${type}</span>
                    <button type="button" class="leg-remove" data-index="${index}" title="Remove">×</button>
                </div>
            `;
        }).join('');

        nexusDetectedLegs.classList.remove('hidden');

        // Attach remove handlers
        nexusLegsList.querySelectorAll('.leg-remove').forEach(btn => {
            btn.addEventListener('click', function() {
                const idx = parseInt(this.dataset.index);
                removeDetectedLeg(idx);
            });
        });

        // Attach edit handlers (when in edit mode)
        nexusLegsList.querySelectorAll('.leg-text').forEach(span => {
            span.addEventListener('click', function() {
                if (nexusEditControls && !nexusEditControls.classList.contains('hidden')) {
                    const idx = parseInt(this.dataset.index);
                    editLegText(idx);
                }
            });
        });
    }

    // Remove a leg
    function removeDetectedLeg(index) {
        nexusDetectedLegsData.splice(index, 1);
        renderDetectedLegs();
        updateNexusTextFromLegs();
    }

    // Edit leg text inline
    function editLegText(index) {
        const leg = nexusDetectedLegsData[index];
        if (!leg) return;

        const currentText = leg.player || leg.team || leg.description || leg.text || '';
        const newText = prompt('Edit leg:', currentText);

        if (newText !== null && newText.trim() !== '') {
            // Update the leg text
            if (leg.player) leg.player = newText;
            else if (leg.team) leg.team = newText;
            else if (leg.description) leg.description = newText;
            else leg.text = newText;

            renderDetectedLegs();
            updateNexusTextFromLegs();
        }
    }

    // Update text input from legs data
    function updateNexusTextFromLegs() {
        const newText = nexusDetectedLegsData.map(l => {
            return l.player || l.team || l.description || l.text || '';
        }).filter(t => t).join(' + ');

        if (nexusTextInput) {
            nexusTextInput.value = newText;
        }
    }

    // S14-B: Edit mode toggle
    const nexusEditToggle = document.getElementById('nexus-edit-toggle');
    const nexusEditControls = document.getElementById('nexus-edit-controls');
    const nexusAddBtn = document.getElementById('nexus-add-btn');
    const nexusAddInput = document.getElementById('nexus-add-input');
    const nexusReanalyzeBtn = document.getElementById('nexus-reanalyze-btn');

    let nexusEditMode = false;

    if (nexusEditToggle && nexusEditControls) {
        nexusEditToggle.addEventListener('click', function() {
            nexusEditMode = !nexusEditMode;
            nexusEditControls.classList.toggle('hidden', !nexusEditMode);
            nexusEditToggle.textContent = nexusEditMode ? 'Done' : 'Edit';

            // Add visual indicator to leg pills in edit mode
            nexusLegsList.querySelectorAll('.nexus-leg-pill').forEach(pill => {
                pill.classList.toggle('edit-mode', nexusEditMode);
            });
        });
    }

    // Add new leg
    if (nexusAddBtn && nexusAddInput) {
        nexusAddBtn.addEventListener('click', function() {
            const text = nexusAddInput.value.trim();
            if (!text) return;

            // Add as generic leg
            nexusDetectedLegsData.push({
                text: text,
                bet_type: 'PROP',
                market: 'PROP'
            });

            nexusAddInput.value = '';
            renderDetectedLegs();
            updateNexusTextFromLegs();
        });

        // Enter key to add
        nexusAddInput.addEventListener('keydown', function(e) {
            if (e.key === 'Enter') {
                nexusAddBtn.click();
            }
        });
    }

    // Re-analyze with changes
    if (nexusReanalyzeBtn) {
        nexusReanalyzeBtn.addEventListener('click', function() {
            const text = nexusTextInput.value.trim();
            if (text) {
                evaluateFromNexus(text);
            }
        });
    }

    // Display results (bridges to existing result display)
    function displayNexusResults(data) {
        // S14-C: Show analyst take
        const analystTakeCard = document.getElementById('analyst-take-card');
        const analystTakeContent = document.getElementById('analyst-take-content');
        if (analystTakeCard && analystTakeContent && window.generateAnalystTake) {
            analystTakeContent.innerHTML = window.generateAnalystTake(data);
            analystTakeCard.classList.remove('hidden');
        }

        // Hide Nexus input, show results
        // This connects to existing result rendering logic
        if (window.displayEvaluationResults) {
            window.displayEvaluationResults(data);
        } else {
            // Fallback: trigger existing display
            showToast('Analysis complete');
        }
    }

    // Utility: escape HTML
    function escapeHtml(text) {
        const div = document.createElement('div');
        div.textContent = text;
        return div.innerHTML;
    }

    // Utility: show toast (uses existing toast if available)
    function showToast(message) {
        if (window.showToast) {
            window.showToast(message);
        } else {
            console.log('Toast:', message);
        }
    }

    // S14-C: Generate reality-anchored narrative
    function generateAnalystTake(data) {
        const legs = data.legs || data.snapshot?.legs || [];
        const correlations = data.correlations || data.snapshot?.correlations || [];
        const signal = data.signal || 'green';
        const fragility = data.fragility_score || data.fragilityScore || 0;

        let take = '';

        // Opening: Structure description
        const propLegs = legs.filter(l => (l.bet_type || l.market) === 'PROP').length;
        const gameCount = new Set(legs.map(l => l.game_id || l.game)).size;

        if (propLegs > 0 && propLegs === legs.length) {
            take += `This is a <span class="take-highlight">player prop heavy</span> parlay. `;
        } else if (propLegs > 0) {
            take += `This mix combines <span class="take-highlight">player props with team outcomes</span>. `;
        }

        // Game concentration
        if (gameCount === 1 && legs.length > 1) {
            take += `Everything rides on <span class="take-highlight">one game</span>, so late variance could swing everything. `;
        } else if (gameCount <= 2 && legs.length >= 3) {
            take += `Most of this is concentrated across just <span class="take-highlight">${gameCount} games</span>. `;
        }

        // Outcome types
        if (propLegs >= 2) {
            take += `Player props are <span class="take-highlight">volume outcomes</span> (stats can accumulate) rather than binary wins/losses. `;
        }

        // Correlation insight (without claiming real stats)
        if (correlations.length > 0) {
            take += `There's <span class="take-highlight">overlap in your legs</span> — if one hits, others might too (or not). `;
        }

        // Signal-based framing
        if (signal === 'red' || fragility > 70) {
            take += `Structure looks <span class="take-highlight">fragile</span> — multiple things need to go right in specific ways.`;
        } else if (signal === 'yellow' || fragility > 40) {
            take += `Some <span class="take-highlight">structural tension</span> here — not broken, but worth watching.`;
        } else if (signal === 'green' || fragility < 30) {
            take += `Structure looks <span class="take-highlight">balanced</span> — legs aren't fighting each other.`;
        }

        // Add structure breakdown
        const structure = [];
        if (propLegs > 0) structure.push(`${propLegs} player prop${propLegs > 1 ? 's' : ''}`);
        const mlLegs = legs.filter(l => (l.bet_type || l.market) === 'MONEYLINE').length;
        if (mlLegs > 0) structure.push(`${mlLegs} moneyline`);
        const spreadLegs = legs.filter(l => (l.bet_type || l.market) === 'SPREAD').length;
        if (spreadLegs > 0) structure.push(`${spreadLegs} spread`);

        let html = take;
        if (structure.length > 0) {
            html += `<div class="take-structure">Breakdown: ${structure.join(', ')}</div>`;
        }

        return html || 'Analysis based on your slip structure.';
    }

    // Make available globally
    window.generateAnalystTake = generateAnalystTake;
})();

// ============================================================
// S15: MESSAGING-STYLE INPUT HANDLERS
// ============================================================
(function() {
    // Elements
    const chatTextField = document.getElementById('chat-text-field');
    const chatSendBtn = document.getElementById('chat-send-btn');
    const chatCameraBtn = document.getElementById('chat-camera-btn');
    const chatFileInput = document.getElementById('chat-file-input');
    const chatPhotoPreview = document.getElementById('chat-photo-preview');
    const chatPreviewImg = document.getElementById('chat-preview-img');
    const chatRemovePhoto = document.getElementById('chat-remove-photo');
    const quickChips = document.querySelectorAll('.quick-chip');

    // Send/Analyze
    if (chatSendBtn && chatTextField) {
        chatSendBtn.addEventListener('click', function() {
            const text = chatTextField.value.trim();
            if (!text) {
                showToast('Enter your bet first');
                return;
            }
            analyzeBet(text);
        });

        // Enter key to submit
        chatTextField.addEventListener('keydown', function(e) {
            if (e.key === 'Enter' && !e.shiftKey) {
                e.preventDefault();
                chatSendBtn.click();
            }
        });
    }

    // Camera/Photo upload
    if (chatCameraBtn && chatFileInput) {
        chatCameraBtn.addEventListener('click', function() {
            chatFileInput.click();
        });

        chatFileInput.addEventListener('change', function(e) {
            const file = e.target.files[0];
            if (!file) return;
            handlePhoto(file);
        });
    }

    // Remove photo
    if (chatRemovePhoto) {
        chatRemovePhoto.addEventListener('click', function() {
            chatFileInput.value = '';
            chatPhotoPreview.classList.add('hidden');
        });
    }

    // Quick chips
    quickChips.forEach(chip => {
        chip.addEventListener('click', function() {
            const bet = this.dataset.bet;
            if (bet && chatTextField) {
                chatTextField.value = bet;
                chatTextField.focus();
            }
        });
    });

    // Handle photo
    function handlePhoto(file) {
        // Validate
        const validTypes = ['image/png', 'image/jpeg', 'image/jpg', 'image/webp'];
        if (!validTypes.includes(file.type)) {
            showToast('Please upload PNG, JPG, or WebP');
            return;
        }
        if (file.size > 5 * 1024 * 1024) {
            showToast('Image must be under 5MB');
            return;
        }

        // Show preview
        const reader = new FileReader();
        reader.onload = function(e) {
            chatPreviewImg.src = e.target.result;
            chatPhotoPreview.classList.remove('hidden');
        };
        reader.readAsDataURL(file);

        // Submit for OCR
        submitOCR(file);
    }

    // Submit OCR
    async function submitOCR(file) {
        chatSendBtn.disabled = true;
        chatSendBtn.textContent = 'Reading...';

        try {
            const formData = new FormData();
            formData.append('file', file);

            const response = await fetch('/api/evaluate/ocr', {
                method: 'POST',
                body: formData
            });

            if (!response.ok) throw new Error('OCR failed');

            const data = await response.json();
            if (data.text) {
                chatTextField.value = data.text;
                showToast('Text extracted - tap Analyze');
            }
        } catch (err) {
            console.error('OCR error:', err);
            showToast('Could not read image. Try typing.');
        } finally {
            chatSendBtn.disabled = false;
            chatSendBtn.textContent = 'Analyze';
        }
    }

    // Analyze bet
    async function analyzeBet(text) {
        chatSendBtn.disabled = true;
        chatSendBtn.textContent = 'Analyzing...';

        try {
            const response = await fetch('/api/evaluate', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ text: text, tier: 'good' })
            });

            if (!response.ok) throw new Error('Analysis failed');

            const data = await response.json();
            
            // Show results (existing display logic)
            if (window.showEvaluationResults) {
                window.showEvaluationResults(data);
            } else {
                showToast('Analysis complete');
            }

        } catch (err) {
            console.error('Analysis error:', err);
            showToast('Analysis failed. Try again.');
        } finally {
            chatSendBtn.disabled = false;
            chatSendBtn.textContent = 'Analyze';
        }
    }

    // Utility
    function showToast(message) {
        // Use existing toast or console
        if (window.showToast) {
            window.showToast(message);
        } else {
            console.log('Toast:', message);
        }
    }
})();
