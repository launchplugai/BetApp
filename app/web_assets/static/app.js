// ============================================================
// TICKET 9: BUILDER IMPROVEMENT WORKBENCH
// ============================================================
(function() {
    // Elements
    const fixBlocked = document.getElementById('fix-blocked');
    const builderWorkbench = document.getElementById('builder-workbench');
    const builderUpdating = document.getElementById('builder-updating');
    const toast = document.getElementById('toast');

    // Fastest Fix elements
    const fastestFixCard = document.getElementById('fastest-fix-card');
    const fastestFixAction = document.getElementById('fastest-fix-action');
    const fastestFixDescription = document.getElementById('fastest-fix-description');
    const fastestFixReason = document.getElementById('fastest-fix-reason');
    const fastestFixButton = document.getElementById('fastest-fix-button');
    const fastestFixDisabledReason = document.getElementById('fastest-fix-disabled-reason');

    // Slip leg list elements
    const slipLegCount = document.getElementById('slip-leg-count');
    const slipLegRows = document.getElementById('slip-leg-rows');

    // Delta panel elements
    const deltaBeforeSignalWb = document.getElementById('delta-before-signal-wb');
    const deltaBeforeScoreWb = document.getElementById('delta-before-score-wb');
    const deltaAfterSignalWb = document.getElementById('delta-after-signal-wb');
    const deltaAfterScoreWb = document.getElementById('delta-after-score-wb');
    const deltaArrow = document.getElementById('delta-arrow');
    const deltaSignalArrow = document.getElementById('delta-signal-arrow');
    const deltaFragilityArrow = document.getElementById('delta-fragility-arrow');

    // Action bar elements
    const builderSaveBtn = document.getElementById('builder-save-btn');
    const builderBackBtn = document.getElementById('builder-back-btn');

    // State
    let currentLegs = [];
    let currentEvaluationId = null;
    let currentTier = 'good';
    let originalSignalInfo = null;
    let reEvalDebounceTimer = null;
    let currentBuilderState = 'EMPTY';

    // ============================================================
    // TICKET 31: BUILDER STATE MACHINE (DNA Parlay Builder Spec v1.0)
    // States: EMPTY(0), SINGLE_BET(1), STANDARD_PARLAY(2-3), ELEVATED_PARLAY(4-5), MAX_PARLAY(6)
    // BLOCKED is a rejected transition, not a persistent state
    // ============================================================
    const BuilderStateMachine = {
        // Maximum legs allowed (defense-in-depth)
        MAX_LEGS: 6,

        // State definitions with leg count thresholds per spec v1.0
        STATES: {
            EMPTY: { minLegs: 0, maxLegs: 0, label: 'Empty', canAdd: true, canRemove: false },
            SINGLE_BET: { minLegs: 1, maxLegs: 1, label: 'Single Bet', canAdd: true, canRemove: true },
            STANDARD_PARLAY: { minLegs: 2, maxLegs: 3, label: 'Standard Parlay', canAdd: true, canRemove: true },
            ELEVATED_PARLAY: { minLegs: 4, maxLegs: 5, label: 'Elevated Risk', canAdd: true, canRemove: true },
            MAX_PARLAY: { minLegs: 6, maxLegs: 6, label: 'Maximum Legs', canAdd: false, canRemove: true }
        },

        // Compute state from leg count (spec v1.0 thresholds)
        computeState: function(legCount) {
            if (legCount === 0) return 'EMPTY';
            if (legCount === 1) return 'SINGLE_BET';
            if (legCount >= 2 && legCount <= 3) return 'STANDARD_PARLAY';
            if (legCount >= 4 && legCount <= 5) return 'ELEVATED_PARLAY';
            if (legCount >= 6) return 'MAX_PARLAY';
            return 'EMPTY';
        },

        // Check if can add more legs
        canAddLeg: function(state) {
            const stateConfig = this.STATES[state];
            return stateConfig ? stateConfig.canAdd : false;
        },

        // Check if can remove legs
        canRemoveLeg: function(state) {
            const stateConfig = this.STATES[state];
            return stateConfig ? stateConfig.canRemove : false;
        },

        // Attempt to add a leg - returns { allowed, reason } for BLOCKED transition handling
        tryAddLeg: function(currentLegCount) {
            if (currentLegCount >= this.MAX_LEGS) {
                return {
                    allowed: false,
                    reason: 'Maximum 6 legs allowed',
                    blocked: true
                };
            }
            return { allowed: true, reason: null, blocked: false };
        },

        // Get state label for UI display
        getStateLabel: function(state) {
            const stateConfig = this.STATES[state];
            return stateConfig ? stateConfig.label : 'Unknown';
        },

        // Get bet term based on leg count (bet vs parlay)
        getBetTerm: function(legCount) {
            if (legCount === 0) return '';
            if (legCount === 1) return 'bet';
            return 'parlay';
        },

        // Get leg count text with proper terminology per spec
        // 1 leg: "Single bet"
        // 2+ legs: "{N}-leg parlay"
        getLegCountText: function(legCount) {
            if (legCount === 0) return 'Empty slip';
            if (legCount === 1) return 'Single bet';
            return legCount + '-leg parlay';
        },

        // Check if transitioning to elevated state (for warning)
        isTransitionToElevated: function(currentLegCount, newLegCount) {
            const currentState = this.computeState(currentLegCount);
            const newState = this.computeState(newLegCount);
            return currentState !== 'ELEVATED_PARLAY' && newState === 'ELEVATED_PARLAY';
        },

        // Check if at max (6 legs)
        isAtMax: function(legCount) {
            return legCount >= this.MAX_LEGS;
        }
    };

    // Export for testing
    window.BuilderStateMachine = BuilderStateMachine;

    // ============================================================
    // LEG PARSING
    // ============================================================
    function parseLegsFromText(text, options) {
        options = options || {};
        if (!text) return [];

        // Split by common delimiters
        let parts = text.split(/\s*\+\s*|\s*,\s*|\s+and\s+/i);

        // Clean up and filter empty parts
        parts = parts.map(p => p.trim()).filter(p => p.length > 0);

        // If only one part and contains 'parlay', try to split differently
        if (parts.length === 1 && parts[0].toLowerCase().includes('parlay')) {
            const beforeParlay = parts[0].replace(/\s+parlay$/i, '');
            parts = beforeParlay.split(/\s*\+\s*/);
        }

        // CHUNK 3: Enforce MAX_LEGS (6 leg cap)
        let wasBlocked = false;
        if (parts.length > BuilderStateMachine.MAX_LEGS) {
            wasBlocked = true;
            parts = parts.slice(0, BuilderStateMachine.MAX_LEGS);
        }

        // Detect bet type for each leg
        const legs = parts.map((legText, index) => {
            const lower = legText.toLowerCase();
            let betType = 'ml';

            if (/yards|points|rebounds|assists|touchdowns|td|passing|receiving|rushing|hits|strikeouts/i.test(lower)) {
                betType = 'prop';
            } else if (/over|under|o\/|u\//i.test(lower)) {
                betType = 'total';
            } else if (/[+-]\d+\.?\d*/i.test(lower) && !/over|under/i.test(lower)) {
                betType = 'spread';
            }

            return {
                id: 'leg_' + index,
                text: legText,
                betType: betType,
                index: index
            };
        });

        // Emit blocked event if legs were truncated (unless suppressed)
        if (wasBlocked && !options.suppressBlockedEvent) {
            // Defer to next tick so caller can finish before event fires
            setTimeout(function() {
                emitBlockedEvent('Input exceeded maximum of 6 legs');
            }, 0);
        }

        return legs;
    }

    // ============================================================
    // RENDER FUNCTIONS
    // ============================================================
    function updateBuilderState() {
        // Compute new state from leg count
        const newState = BuilderStateMachine.computeState(currentLegs.length);
        const previousState = currentBuilderState;
        currentBuilderState = newState;

        // Emit state change event for UI updates
        if (previousState !== newState) {
            const event = new CustomEvent('builderStateChange', {
                detail: {
                    previousState: previousState,
                    newState: newState,
                    legCount: currentLegs.length,
                    canAdd: BuilderStateMachine.canAddLeg(newState),
                    canRemove: BuilderStateMachine.canRemoveLeg(newState),
                    stateLabel: BuilderStateMachine.getStateLabel(newState),
                    isAtMax: BuilderStateMachine.isAtMax(currentLegs.length)
                }
            });
            document.dispatchEvent(event);
        }

        return newState;
    }

    // Emit blocked event when add is rejected at MAX_PARLAY
    function emitBlockedEvent(reason) {
        const event = new CustomEvent('builderAddBlocked', {
            detail: {
                state: currentBuilderState,
                legCount: currentLegs.length,
                reason: reason,
                maxLegs: BuilderStateMachine.MAX_LEGS
            }
        });
        document.dispatchEvent(event);
    }

    // ============================================================
    // TICKET 31 CHUNK 2: UI STATE RENDERING
    // Visibility matrix driven by BuilderStateMachine state
    // ============================================================

    // Get or create UI elements for state-driven rendering
    function getStateUIElements() {
        return {
            builderTitle: document.querySelector('.builder-title'),
            slipLegCount: document.getElementById('slip-leg-count'),
            fastestFixCard: document.getElementById('fastest-fix-card'),
            deltaPanel: document.getElementById('delta-panel'),
            // Create complexity banner if not exists
            complexityBanner: document.getElementById('complexity-banner') || createComplexityBanner(),
            // Create max warning if not exists
            maxWarning: document.getElementById('max-parlay-warning') || createMaxWarning(),
            // Create disclosure badge if not exists
            disclosureBadge: document.getElementById('disclosure-badge') || createDisclosureBadge()
        };
    }

    // Create complexity banner element (for ELEVATED_PARLAY state)
    function createComplexityBanner() {
        const banner = document.createElement('div');
        banner.id = 'complexity-banner';
        banner.className = 'complexity-banner hidden';
        banner.innerHTML = '<span class="complexity-icon">&#9888;</span> <span class="complexity-text">High complexity parlay - correlation risk increases</span>';
        // Insert after builder header
        const header = document.querySelector('.builder-header');
        if (header && header.parentNode) {
            header.parentNode.insertBefore(banner, header.nextSibling);
        }
        return banner;
    }

    // Create max parlay warning element (for MAX_PARLAY state)
    function createMaxWarning() {
        const warning = document.createElement('div');
        warning.id = 'max-parlay-warning';
        warning.className = 'max-parlay-warning hidden';
        warning.innerHTML = '<span class="max-warning-icon">&#128721;</span> <span class="max-warning-text">Maximum legs reached (6). Remove a leg to add more.</span>';
        // Insert after slip leg list header
        const slipList = document.getElementById('slip-leg-list');
        if (slipList) {
            const header = slipList.querySelector('.slip-leg-list-header');
            if (header && header.parentNode) {
                header.parentNode.insertBefore(warning, header.nextSibling);
            }
        }
        return warning;
    }

    // Create disclosure badge element (analysis transparency)
    function createDisclosureBadge() {
        const badge = document.createElement('div');
        badge.id = 'disclosure-badge';
        badge.className = 'disclosure-badge hidden';
        badge.innerHTML = '<span class="disclosure-icon">&#128269;</span> <span class="disclosure-text">Structural analysis only - no live odds data</span>';
        // Insert before fastest fix card
        const fastestFix = document.getElementById('fastest-fix-card');
        if (fastestFix && fastestFix.parentNode) {
            fastestFix.parentNode.insertBefore(badge, fastestFix);
        }
        return badge;
    }

    // Render UI based on current state (visibility matrix)
    function renderStateUI() {
        const state = currentBuilderState;
        const legCount = currentLegs.length;
        const ui = getStateUIElements();

        // Update header text based on state
        if (ui.builderTitle) {
            if (state === 'EMPTY') {
                ui.builderTitle.textContent = 'Add your first leg to begin';
            } else if (state === 'MAX_PARLAY') {
                ui.builderTitle.textContent = '6-leg parlay (maximum)';
            } else {
                ui.builderTitle.textContent = BuilderStateMachine.getLegCountText(legCount);
            }
        }

        // Disclosure badge: visible for SINGLE_BET and above
        if (ui.disclosureBadge) {
            if (state === 'EMPTY') {
                ui.disclosureBadge.classList.add('hidden');
            } else {
                ui.disclosureBadge.classList.remove('hidden');
            }
        }

        // Primary failure card (fastest fix): hidden for EMPTY and SINGLE_BET
        if (ui.fastestFixCard) {
            if (state === 'EMPTY' || state === 'SINGLE_BET') {
                ui.fastestFixCard.classList.add('state-hidden');
            } else {
                ui.fastestFixCard.classList.remove('state-hidden');
            }
        }

        // Delta panel: hidden for EMPTY
        if (ui.deltaPanel) {
            if (state === 'EMPTY') {
                ui.deltaPanel.classList.add('state-hidden');
            } else {
                ui.deltaPanel.classList.remove('state-hidden');
            }
        }

        // Complexity banner: visible for ELEVATED_PARLAY and MAX_PARLAY
        if (ui.complexityBanner) {
            if (state === 'ELEVATED_PARLAY' || state === 'MAX_PARLAY') {
                ui.complexityBanner.classList.remove('hidden');
            } else {
                ui.complexityBanner.classList.add('hidden');
            }
        }

        // Max parlay warning: visible only for MAX_PARLAY
        if (ui.maxWarning) {
            if (state === 'MAX_PARLAY') {
                ui.maxWarning.classList.remove('hidden');
            } else {
                ui.maxWarning.classList.add('hidden');
            }
        }
    }

    // Handle blocked add event (show toast, no evaluation)
    function handleBlockedAdd(event) {
        const detail = event.detail || {};
        showToast('Maximum of 6 legs supported', 'error');
        // No evaluation triggered - this is enforced by the blocked transition
    }

    // Listen for blocked add events
    document.addEventListener('builderAddBlocked', handleBlockedAdd);

    // Listen for state change events to update UI
    document.addEventListener('builderStateChange', function(event) {
        renderStateUI();
    });

    function renderLegList() {
        // Update state first
        const state = updateBuilderState();

        // Render state-driven UI elements (Chunk 2)
        renderStateUI();

        // Use state machine for terminology
        slipLegCount.textContent = BuilderStateMachine.getLegCountText(currentLegs.length);

        if (currentLegs.length === 0) {
            slipLegRows.innerHTML = '<div class="slip-empty-state">No legs in slip</div>';
            return;
        }

        // Get affected leg IDs from context
        const ctx = window._builderContext || {};
        const affectedIds = (ctx.primaryFailure && ctx.primaryFailure.affectedLegIds) || [];
        const candidateIds = (ctx.fastestFix && ctx.fastestFix.candidateLegIds) || [];

        // Check if remove is allowed based on state
        const canRemoveAny = BuilderStateMachine.canRemoveLeg(state);

        let html = '';
        currentLegs.forEach((leg, index) => {
            const isAffected = affectedIds.includes(leg.id) || candidateIds.includes(leg.id);
            const isProp = leg.betType === 'prop';

            let rowClass = 'slip-leg-row';
            if (isAffected) rowClass += ' affected';
            else if (isProp) rowClass += ' prop-leg';

            html += '<div class="' + rowClass + '" data-leg-index="' + index + '">';
            html += '<span class="slip-leg-text">' + escapeHtml(leg.text) + '</span>';

            if (leg.betType) {
                html += '<span class="slip-leg-tag ' + leg.betType + '">' + leg.betType.toUpperCase() + '</span>';
            }

            html += '<button type="button" class="slip-leg-remove" data-leg-index="' + index + '"' + (canRemoveAny ? '' : ' disabled') + '>&times;</button>';
            html += '</div>';
        });

        slipLegRows.innerHTML = html;

        // Attach remove handlers
        slipLegRows.querySelectorAll('.slip-leg-remove').forEach(btn => {
            btn.addEventListener('click', function() {
                if (!BuilderStateMachine.canRemoveLeg(currentBuilderState)) {
                    showToast('No legs to remove', 'error');
                    return;
                }
                const idx = parseInt(this.getAttribute('data-leg-index'));
                removeLeg(idx);
            });
        });
    }

    function renderDeltaPanel() {
        const ctx = window._builderContext || {};
        const dp = ctx.deltaPreview;
        const si = ctx.signalInfo;

        // Before state (original)
        if (originalSignalInfo) {
            deltaBeforeSignalWb.textContent = originalSignalInfo.signal.toUpperCase();
            deltaBeforeSignalWb.className = 'delta-panel-signal signal-' + originalSignalInfo.signal;
            deltaBeforeScoreWb.textContent = Math.round(originalSignalInfo.fragilityScore);
        } else if (si) {
            deltaBeforeSignalWb.textContent = si.signal.toUpperCase();
            deltaBeforeSignalWb.className = 'delta-panel-signal signal-' + si.signal;
            deltaBeforeScoreWb.textContent = Math.round(si.fragilityScore);
        }

        // After state (current/updated)
        if (si) {
            deltaAfterSignalWb.textContent = si.signal.toUpperCase();
            deltaAfterSignalWb.className = 'delta-panel-signal signal-' + si.signal;
            deltaAfterScoreWb.textContent = Math.round(si.fragilityScore);
        }

        // Change indicators
        if (dp && dp.change) {
            updateChangeArrow(deltaSignalArrow, dp.change.signal);
            updateChangeArrow(deltaFragilityArrow, dp.change.fragility);

            // Update main arrow color
            if (dp.change.signal === 'up' || dp.change.fragility === 'down') {
                deltaArrow.className = 'delta-panel-arrow improved';
                deltaArrow.innerHTML = '&rarr;';
            } else if (dp.change.signal === 'down' || dp.change.fragility === 'up') {
                deltaArrow.className = 'delta-panel-arrow worsened';
                deltaArrow.innerHTML = '&rarr;';
            } else {
                deltaArrow.className = 'delta-panel-arrow';
                deltaArrow.innerHTML = '&rarr;';
            }
        } else {
            deltaSignalArrow.className = 'arrow-same';
            deltaSignalArrow.innerHTML = '&mdash;';
            deltaFragilityArrow.className = 'arrow-same';
            deltaFragilityArrow.innerHTML = '&mdash;';
            deltaArrow.className = 'delta-panel-arrow';
        }
    }

    function updateChangeArrow(el, direction) {
        if (direction === 'up') {
            el.className = 'arrow-up';
            el.innerHTML = '&#9650;'; // Up arrow
        } else if (direction === 'down') {
            el.className = 'arrow-down';
            el.innerHTML = '&#9660;'; // Down arrow
        } else {
            el.className = 'arrow-same';
            el.innerHTML = '&mdash;';
        }
    }

    function renderFastestFix() {
        const ctx = window._builderContext || {};
        const pf = ctx.primaryFailure;
        const ff = ctx.fastestFix;

        if (!ff || !ff.action) {
            fastestFixCard.classList.add('disabled');
            fastestFixAction.textContent = 'N/A';
            fastestFixDescription.textContent = 'No fix recommendation available';
            fastestFixReason.textContent = '';
            fastestFixButton.disabled = true;
            fastestFixDisabledReason.classList.add('hidden');
            return;
        }

        const actionLabels = {
            'remove_leg': 'Remove Leg',
            'split_parlay': 'Split Parlay',
            'reduce_props': 'Reduce Props',
            'swap_leg': 'Swap Leg'
        };

        fastestFixCard.classList.remove('disabled');
        fastestFixAction.textContent = actionLabels[ff.action] || ff.action.replace(/_/g, ' ').toUpperCase();
        fastestFixDescription.textContent = ff.description || 'Apply recommended fix';

        // Build reason from primary failure
        if (pf && pf.description) {
            fastestFixReason.textContent = 'Why: ' + pf.description;
        } else {
            fastestFixReason.textContent = '';
        }

        // Check if action is supported
        const supportedActions = ['remove_leg', 'reduce_props'];
        const partialActions = ['split_parlay'];

        if (supportedActions.includes(ff.action)) {
            fastestFixButton.disabled = false;
            fastestFixButton.textContent = 'Apply Fix';
            fastestFixDisabledReason.classList.add('hidden');
        } else if (partialActions.includes(ff.action)) {
            // Visual-only for split_parlay
            fastestFixButton.disabled = false;
            fastestFixButton.textContent = 'Apply Fix';
            fastestFixDisabledReason.classList.add('hidden');
        } else {
            fastestFixButton.disabled = true;
            fastestFixButton.textContent = 'Apply Fix';
            fastestFixDisabledReason.textContent = 'Action "' + ff.action + '" requires manual editing';
            fastestFixDisabledReason.classList.remove('hidden');
        }

        // Check for empty case using state machine (SINGLE_BET allows removal per spec)
        if (!BuilderStateMachine.canRemoveLeg(currentBuilderState) && ff.action === 'remove_leg') {
            fastestFixButton.disabled = true;
            fastestFixDisabledReason.textContent = 'No legs to remove';
            fastestFixDisabledReason.classList.remove('hidden');
        }
    }

    function renderSaveButton() {
        if (currentEvaluationId) {
            builderSaveBtn.disabled = false;
        } else {
            builderSaveBtn.disabled = true;
        }
    }

    // ============================================================
    // ACTIONS
    // ============================================================

    // CHUNK 3: Add a leg with MAX_LEGS enforcement
    // Returns true if added, false if blocked (no evaluation triggered when blocked)
    function addLeg(legText) {
        // Use state machine to check if adding is allowed
        const result = BuilderStateMachine.tryAddLeg(currentLegs.length);

        if (!result.allowed) {
            // BLOCKED: emit event and short-circuit - NO evaluation
            emitBlockedEvent(result.reason);
            return false;
        }

        // Allowed: add the leg
        const lower = legText.toLowerCase();
        let betType = 'ml';
        if (/yards|points|rebounds|assists|touchdowns|td|passing|receiving|rushing|hits|strikeouts/i.test(lower)) {
            betType = 'prop';
        } else if (/over|under|o\/|u\//i.test(lower)) {
            betType = 'total';
        } else if (/[+-]\d+\.?\d*/i.test(lower) && !/over|under/i.test(lower)) {
            betType = 'spread';
        }

        const newLeg = {
            id: 'leg_' + currentLegs.length,
            text: legText,
            betType: betType,
            index: currentLegs.length
        };

        currentLegs.push(newLeg);
        renderLegList();
        triggerReEvaluate();
        return true;
    }

    function removeLeg(index) {
        // Use state machine to check if removal is allowed (only EMPTY blocks removal)
        if (!BuilderStateMachine.canRemoveLeg(currentBuilderState)) {
            showToast('No legs to remove', 'error');
            return;
        }

        currentLegs.splice(index, 1);
        // Re-index legs
        currentLegs.forEach((leg, i) => {
            leg.index = i;
            leg.id = 'leg_' + i;
        });

        renderLegList();
        triggerReEvaluate();
    }

    function applyFix() {
        const ctx = window._builderContext || {};
        const ff = ctx.fastestFix;

        if (!ff || !ff.action) return;

        if (ff.action === 'remove_leg') {
            // Find the leg to remove
            let legToRemove = -1;

            // First try candidateLegIds
            if (ff.candidateLegIds && ff.candidateLegIds.length > 0) {
                // Find the first candidate that exists in our legs
                for (let i = 0; i < currentLegs.length; i++) {
                    if (ff.candidateLegIds.includes(currentLegs[i].id)) {
                        legToRemove = i;
                        break;
                    }
                }
            }

            // Fallback: remove the last leg (highest penalty typically)
            if (legToRemove === -1 && currentLegs.length > 1) {
                legToRemove = currentLegs.length - 1;
            }

            if (legToRemove >= 0) {
                removeLeg(legToRemove);
            }
        } else if (ff.action === 'reduce_props') {
            // Find prop legs and remove one
            const propLegs = currentLegs.map((leg, idx) => ({ leg, idx })).filter(x => x.leg.betType === 'prop');

            if (propLegs.length > 0 && currentLegs.length > 1) {
                // Remove the last prop leg
                removeLeg(propLegs[propLegs.length - 1].idx);
            } else {
                showToast('No prop legs to remove', 'error');
            }
        } else if (ff.action === 'split_parlay') {
            // Visual-only: highlight legs that would be split
            showToast('Split preview: would create 2 smaller parlays', 'success');
            // For now, just remove one leg as a simplification
            if (currentLegs.length > 2) {
                removeLeg(currentLegs.length - 1);
            }
        } else {
            showToast('Action not yet supported: ' + ff.action, 'error');
        }
    }

    // ============================================================
    // RE-EVALUATE (DEBOUNCED)
    // ============================================================
    function triggerReEvaluate() {
        // Clear existing timer
        if (reEvalDebounceTimer) {
            clearTimeout(reEvalDebounceTimer);
        }

        // Show updating indicator
        builderUpdating.classList.remove('hidden');

        // Debounce at 500ms
        reEvalDebounceTimer = setTimeout(async function() {
            await reEvaluate();
        }, 500);
    }

    async function reEvaluate() {
        if (currentLegs.length === 0) {
            builderUpdating.classList.add('hidden');
            return;
        }

        // Build new input text from legs
        const newInputText = currentLegs.map(l => l.text).join(' + ');

        try {
            const response = await fetch('/app/evaluate', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    input: newInputText,
                    tier: currentTier
                })
            });

            const data = await response.json();

            if (response.ok) {
                // Update context with new evaluation
                currentEvaluationId = data.evaluationId || null;

                window._builderContext = {
                    ...window._builderContext,
                    evaluationId: currentEvaluationId,
                    signalInfo: data.signalInfo,
                    primaryFailure: data.primaryFailure,
                    fastestFix: data.primaryFailure ? data.primaryFailure.fastestFix : null,
                    deltaPreview: data.deltaPreview,
                    inputText: newInputText
                };

                // Re-render
                renderFastestFix();
                renderDeltaPanel();
                renderSaveButton();
                renderLegList(); // Re-render to update affected markers
            } else {
                console.error('Re-eval failed:', data);
                showToast('Evaluation failed', 'error');
            }
        } catch (err) {
            console.error('Re-eval error:', err);
            showToast('Network error', 'error');
        } finally {
            builderUpdating.classList.add('hidden');
        }
    }

    // ============================================================
    // SAVE TO HISTORY
    // ============================================================
    async function saveToHistory() {
        if (!currentEvaluationId) {
            showToast('No evaluation to save', 'error');
            return;
        }

        // The evaluation is already saved when /app/evaluate is called
        // Just show confirmation
        showToast('Saved to History', 'success');

        // Optionally switch to history tab after a delay
        // setTimeout(() => switchToTab('history'), 1000);
    }

    // ============================================================
    // TOAST
    // ============================================================
    function showToast(message, type) {
        toast.textContent = message;
        toast.className = 'toast ' + (type || '');
        toast.classList.add('visible');

        setTimeout(function() {
            toast.classList.remove('visible');
        }, 2500);
    }

    // ============================================================
    // UTILITY
    // ============================================================
    function escapeHtml(str) {
        const div = document.createElement('div');
        div.textContent = str;
        return div.innerHTML;
    }

    // ============================================================
    // MAIN CHECK FUNCTION
    // ============================================================
    function checkBuilderContext() {
        const ctx = window._fixContext;

        // Check if we have evaluation context (from Evaluate tab)
        if (!ctx || !ctx.inputText) {
            // No context → show blocked state
            fixBlocked.classList.remove('hidden');
            builderWorkbench.classList.add('hidden');
            return;
        }

        // Valid context → show workbench
        fixBlocked.classList.add('hidden');
        builderWorkbench.classList.remove('hidden');

        // Initialize builder context
        window._builderContext = {
            evaluationId: ctx.evaluationId,
            primaryFailure: ctx.primaryFailure,
            fastestFix: ctx.fastestFix,
            deltaPreview: ctx.deltaPreview,
            signalInfo: ctx.signalInfo || null,
            inputText: ctx.inputText,
            tier: ctx.tier || 'good'
        };

        // Store original signal info for comparison
        if (ctx.signalInfo) {
            originalSignalInfo = { ...ctx.signalInfo };
        } else if (ctx.deltaPreview && ctx.deltaPreview.before) {
            originalSignalInfo = { ...ctx.deltaPreview.before };
        }

        currentEvaluationId = ctx.evaluationId;
        currentTier = ctx.tier || 'good';

        // Parse legs from input text
        currentLegs = parseLegsFromText(ctx.inputText);

        // Render everything
        renderLegList();
        renderFastestFix();
        renderDeltaPanel();
        renderSaveButton();
    }

    // ============================================================
    // EVENT HANDLERS
    // ============================================================
    fastestFixButton.addEventListener('click', function() {
        if (!this.disabled) {
            applyFix();
        }
    });

    builderSaveBtn.addEventListener('click', function() {
        saveToHistory();
    });

    builderBackBtn.addEventListener('click', function() {
        // Clear context and return to evaluate
        window._fixContext = null;
        window._builderContext = null;
        switchToTab('evaluate');
    });

    // Export check function for tab switching
    window._checkFixContext = checkBuilderContext;

    // Export state getter for testing (Ticket 31)
    window._getBuilderState = function() {
        return {
            state: currentBuilderState,
            legCount: currentLegs.length,
            canAdd: BuilderStateMachine.canAddLeg(currentBuilderState),
            canRemove: BuilderStateMachine.canRemoveLeg(currentBuilderState),
            stateLabel: BuilderStateMachine.getStateLabel(currentBuilderState),
            betTerm: BuilderStateMachine.getBetTerm(currentLegs.length),
            isAtMax: BuilderStateMachine.isAtMax(currentLegs.length),
            maxLegs: BuilderStateMachine.MAX_LEGS
        };
    };

    // Export blocked event emitter for testing
    window._emitBlockedEvent = emitBlockedEvent;

    // Export addLeg function for testing (Ticket 31 Chunk 3)
    window._addLeg = addLeg;

    // Export parseLegsFromText for testing (Ticket 31 Chunk 3)
    window._parseLegsFromText = parseLegsFromText;

    // Export UI rendering function for testing (Ticket 31 Chunk 2)
    window._renderStateUI = renderStateUI;

    // Export visibility matrix info for testing (Ticket 31 Chunk 2)
    window._getVisibilityMatrix = function() {
        const state = currentBuilderState;
        return {
            state: state,
            headerText: state === 'EMPTY' ? 'Add your first leg to begin' :
                        state === 'MAX_PARLAY' ? '6-leg parlay (maximum)' :
                        BuilderStateMachine.getLegCountText(currentLegs.length),
            disclosureVisible: state !== 'EMPTY',
            primaryFailureVisible: state !== 'EMPTY' && state !== 'SINGLE_BET',
            complexityBannerVisible: state === 'ELEVATED_PARLAY' || state === 'MAX_PARLAY',
            maxWarningVisible: state === 'MAX_PARLAY',
            deltaPanelVisible: state !== 'EMPTY'
        };
    };

    // Initial check
    checkBuilderContext();
})();

// ============================================================
// TAB SWITCHING
// ============================================================
// Global function for programmatic tab switching
function switchToTab(tabName) {
    const navTabs = document.querySelectorAll('.nav-tab');
    const tabContents = document.querySelectorAll('.tab-content');

    // Update URL
    const url = new URL(window.location);
    url.searchParams.set('tab', tabName);
    window.history.pushState({}, '', url);

    // Switch tabs
    navTabs.forEach(t => t.classList.remove('active'));
    tabContents.forEach(c => c.classList.remove('active'));

    const activeTab = document.querySelector('.nav-tab[data-tab="' + tabName + '"]');
    if (activeTab) activeTab.classList.add('active');
    const activeContent = document.getElementById('tab-' + tabName);
    if (activeContent) activeContent.classList.add('active');

    // Load history if switching to history tab
    if (tabName === 'history') {
        loadHistory();
    }

    // VC-2: Check fix context when switching to builder
    if (tabName === 'builder' && typeof window._checkFixContext === 'function') {
        window._checkFixContext();
    }
}

(function() {
    const navTabs = document.querySelectorAll('.nav-tab');

    navTabs.forEach(tab => {
        tab.addEventListener('click', function() {
            switchToTab(this.dataset.tab);
        });
    });
})();

// ============================================================
// TICKET 8: DISCOVER BUNDLE HANDOFF
// ============================================================
// Global function for quick evaluation from Discover bundles
async function evaluateBundle(bundleText) {
    // Switch to Evaluate tab
    switchToTab('evaluate');

    // Set the text input
    const textInput = document.getElementById('eval-text-input');
    if (textInput) {
        textInput.value = bundleText;
    }

    // Ensure text mode is active
    const inputTabs = document.querySelectorAll('.input-tab');
    const inputPanels = document.querySelectorAll('.input-panel');
    inputTabs.forEach(t => t.classList.remove('active'));
    inputPanels.forEach(p => p.classList.remove('active'));
    const textTab = document.querySelector('.input-tab[data-input="text"]');
    const textPanel = document.getElementById('text-input-panel');
    if (textTab) textTab.classList.add('active');
    if (textPanel) textPanel.classList.add('active');

    // Auto-submit after short delay
    setTimeout(function() {
        const submitBtn = document.getElementById('eval-submit-btn');
        if (submitBtn && !submitBtn.disabled) {
            submitBtn.click();
        }
    }, 100);
}

// ============================================================
// EVALUATE TAB FUNCTIONALITY
// ============================================================
(function() {
    const inputTabs = document.querySelectorAll('.input-tab');
    const inputPanels = document.querySelectorAll('.input-panel');
    const textInput = document.getElementById('eval-text-input');
    const evalSubmitBtn = document.getElementById('eval-submit-btn');
    const evalResultsPlaceholder = document.getElementById('eval-results-placeholder');
    const evalResultsContent = document.getElementById('eval-results-content');
    const evalErrorPanel = document.getElementById('eval-error-panel');

    // Image upload elements
    const fileInput = document.getElementById('file-input');
    const fileUploadArea = document.getElementById('file-upload-area');
    const fileUploadIcon = document.getElementById('file-upload-icon');
    const fileUploadText = document.getElementById('file-upload-text');
    const fileSelected = document.getElementById('file-selected');
    const fileNameSpan = document.getElementById('file-name');
    const clearFileBtn = document.getElementById('clear-file');
    const imageError = document.getElementById('image-error');

    let currentInputMode = 'text';
    let selectedFile = null;
    const MAX_FILE_SIZE = 5 * 1024 * 1024; // 5MB
    const ALLOWED_TYPES = ['image/png', 'image/jpeg', 'image/jpg', 'image/webp'];

    // Input type tabs (text/image)
    inputTabs.forEach(tab => {
        tab.addEventListener('click', function() {
            const inputType = this.dataset.input;
            currentInputMode = inputType;

            inputTabs.forEach(t => t.classList.remove('active'));
            inputPanels.forEach(p => p.classList.remove('active'));

            this.classList.add('active');
            document.getElementById(inputType + '-input-panel').classList.add('active');

            updateEvalSubmitState();
        });
    });

    // Text input change
    textInput.addEventListener('input', updateEvalSubmitState);

    // ========== FILE UPLOAD HANDLING ==========

    // Click to upload
    fileUploadArea.addEventListener('click', function(e) {
        if (e.target === clearFileBtn || clearFileBtn.contains(e.target)) return;
        fileInput.click();
    });

    // Drag and drop
    fileUploadArea.addEventListener('dragover', function(e) {
        e.preventDefault();
        e.stopPropagation();
        this.classList.add('dragover');
    });

    fileUploadArea.addEventListener('dragleave', function(e) {
        e.preventDefault();
        e.stopPropagation();
        this.classList.remove('dragover');
    });

    fileUploadArea.addEventListener('drop', function(e) {
        e.preventDefault();
        e.stopPropagation();
        this.classList.remove('dragover');
        if (e.dataTransfer.files.length > 0) {
            handleFileSelect(e.dataTransfer.files[0]);
        }
    });

    // File input change
    fileInput.addEventListener('change', function() {
        if (this.files.length > 0) {
            handleFileSelect(this.files[0]);
        }
    });

    // Clear file
    clearFileBtn.addEventListener('click', function(e) {
        e.preventDefault();
        e.stopPropagation();
        clearFile();
    });

    function handleFileSelect(file) {
        hideImageError();

        // Validate type
        if (!ALLOWED_TYPES.includes(file.type)) {
            showImageError('Invalid file type. Please use PNG, JPG, or WebP.');
            return;
        }

        // Validate size
        if (file.size > MAX_FILE_SIZE) {
            showImageError('File too large. Maximum size is 5MB.');
            return;
        }

        selectedFile = file;
        fileUploadArea.classList.add('has-file');
        fileUploadIcon.classList.add('hidden');
        fileUploadText.classList.add('hidden');
        fileSelected.classList.remove('hidden');
        fileNameSpan.textContent = file.name;

        // Show image preview with thumbnail
        const previewContainer = document.getElementById('image-preview-container');
        const previewThumb = document.getElementById('image-preview-thumb');
        const previewName = document.getElementById('image-preview-name');
        const previewStatus = document.getElementById('image-preview-status');
        if (previewContainer && previewThumb) {
            const reader = new FileReader();
            reader.onload = function(e) {
                previewThumb.src = e.target.result;
                previewName.textContent = file.name;
                previewStatus.textContent = 'Ready to extract';
                previewContainer.classList.remove('hidden');
            };
            reader.readAsDataURL(file);
        }

        updateEvalSubmitState();
    }

    function clearFile() {
        selectedFile = null;
        fileInput.value = '';
        fileUploadArea.classList.remove('has-file');
        fileUploadIcon.classList.remove('hidden');
        fileUploadText.classList.remove('hidden');
        fileSelected.classList.add('hidden');
        hideImageError();

        // Hide image preview
        const previewContainer = document.getElementById('image-preview-container');
        const extractedContainer = document.getElementById('extracted-text-container');
        if (previewContainer) previewContainer.classList.add('hidden');
        if (extractedContainer) extractedContainer.classList.add('hidden');

        updateEvalSubmitState();
    }

    // Show extracted text from image evaluation
    function showExtractedText(extractedText, confidence) {
        const container = document.getElementById('extracted-text-container');
        const content = document.getElementById('extracted-text-content');
        const confSpan = document.getElementById('extracted-confidence');
        if (container && content) {
            content.value = extractedText || '';
            confSpan.textContent = confidence ? (Math.round(confidence * 100) + '% confidence') : '';
            container.classList.remove('hidden');
        }
    }

    // Use extracted text button handler
    const useExtractedBtn = document.getElementById('use-extracted-btn');
    if (useExtractedBtn) {
        useExtractedBtn.addEventListener('click', function() {
            const extractedText = document.getElementById('extracted-text-content').value.trim();
            if (extractedText) {
                textInput.value = extractedText;
                // Switch to text mode
                currentInputMode = 'text';
                inputTabs.forEach(t => t.classList.remove('active'));
                inputPanels.forEach(p => p.classList.remove('active'));
                document.querySelector('.input-tab[data-input="text"]').classList.add('active');
                document.getElementById('text-input-panel').classList.add('active');
                updateEvalSubmitState();
            }
        });
    }

    function showImageError(message) {
        imageError.textContent = message;
        imageError.classList.remove('hidden');
    }

    function hideImageError() {
        imageError.classList.add('hidden');
    }

    // ========== EVALUATION FUNCTIONS ==========

    function updateEvalSubmitState() {
        if (currentInputMode === 'text') {
            evalSubmitBtn.disabled = textInput.value.trim().length < 5;
        } else if (currentInputMode === 'image') {
            evalSubmitBtn.disabled = !selectedFile;
        } else {
            // Bundle mode - submit button not used (redirects to builder)
            evalSubmitBtn.disabled = true;
        }
    }

    function getEvalTier() {
        const selected = document.querySelector('input[name="eval-tier"]:checked');
        return selected ? selected.value : 'good';
    }

    function showEvalError(message) {
        evalResultsPlaceholder.classList.add('hidden');
        evalResultsContent.classList.add('hidden');
        evalErrorPanel.classList.remove('hidden');
        document.getElementById('eval-error-text').textContent = message;
    }

    function showEvalResults(data, imageParse, showPayoff) {
        evalResultsPlaceholder.classList.add('hidden');
        evalErrorPanel.classList.add('hidden');
        evalResultsContent.classList.remove('hidden');

        const evaluation = data.evaluation;
        const interpretation = data.interpretation;
        const fragility = interpretation.fragility;
        const explain = data.explain || {};
        const tier = (data.input && data.input.tier) || 'good';
        const metrics = evaluation.metrics;
        const correlations = evaluation.correlations || [];
        const si = data.signalInfo || {};
        const pf = data.primaryFailure;
        const dp = data.deltaPreview;

        // ========================================
        // PAYOFF BANNER (shows after apply-fix)
        // ========================================
        const payoffBanner = document.getElementById('payoff-banner');
        if (showPayoff && window._fixApplied) {
            const fa = window._fixApplied;
            const before = fa.before;
            const after = fa.after || (dp && dp.after);
            const beforeScore = before ? Math.round(before.fragilityScore) : null;
            const afterScore = after ? Math.round(after.fragilityScore) : (si.fragilityScore ? Math.round(si.fragilityScore) : null);
            const improved = (beforeScore !== null && afterScore !== null && afterScore < beforeScore);
            const delta = (beforeScore !== null && afterScore !== null) ? (beforeScore - afterScore) : 0;

            const payoffLine = document.getElementById('payoff-line');
            const payoffStatus = document.getElementById('payoff-status');

            if (before && afterScore !== null) {
                payoffLine.innerHTML = 'Signal: <strong>' + (before.signal || '').toUpperCase() + '</strong> &rarr; <strong>' + (si.signal || (after && after.signal) || '').toUpperCase() + '</strong> | Fragility: <strong>' + beforeScore + '</strong> &rarr; <strong>' + afterScore + '</strong> (<span class="delta-num">&Delta; ' + delta + '</span>)';
            } else {
                payoffLine.textContent = 'Fix applied successfully';
            }

            payoffStatus.textContent = improved ? 'Improved' : 'No improvement';
            payoffStatus.className = 'payoff-status ' + (improved ? 'improved' : 'no-change');
            payoffBanner.classList.remove('hidden');
        } else {
            payoffBanner.classList.add('hidden');
            window._fixApplied = null;
        }

        // ========================================
        // TICKET 8: STRUCTURED OUTPUT CARDS
        // ========================================

        // Card 1: SIGNAL BAR
        const signalBarCard = document.getElementById('signal-bar-card');
        const signal = si.signal || 'green';
        signalBarCard.className = 'result-card signal-bar-card signal-' + signal;
        document.getElementById('signal-bar-badge').textContent = (si.label || 'Solid').toUpperCase();
        document.getElementById('signal-bar-label').textContent = si.signalLine || 'Overall parlay health';
        document.getElementById('signal-bar-grade').textContent = si.grade || 'B';
        document.getElementById('signal-bar-score').textContent = 'Fragility: ' + Math.round(si.fragilityScore || fragility.display_value || 0);

        // Card 2: PRIMARY FAILURE
        const pfCard = document.getElementById('pf-card');
        const pfBadge = document.getElementById('pf-card-badge');
        const pfDesc = document.getElementById('pf-card-description');
        if (pf && pf.description) {
            pfCard.className = 'result-card pf-card severity-' + pf.severity;
            pfBadge.textContent = pf.type.replace(/_/g, ' ').toUpperCase() + ' \u00B7 ' + pf.severity.toUpperCase();
            pfDesc.textContent = pf.description;
        } else {
            pfCard.className = 'result-card pf-card severity-low';
            pfBadge.textContent = 'NO MAJOR ISSUES';
            pfDesc.textContent = 'This parlay has no critical risk factors identified.';
        }

        // Card 3: FASTEST FIX
        const fixCard = document.getElementById('fix-card');
        if (pf && pf.fastestFix && pf.fastestFix.description) {
            document.getElementById('fix-card-action').textContent = pf.fastestFix.action.replace(/_/g, ' ').toUpperCase();
            document.getElementById('fix-card-description').textContent = pf.fastestFix.description;
            fixCard.classList.remove('hidden');
            fixCard.onclick = function() {
                window._fixContext = {
                    evaluationId: data.evaluationId || null,
                    primaryFailure: pf,
                    fastestFix: pf.fastestFix,
                    deltaPreview: dp || null,
                    inputText: data.input ? data.input.bet_text : null,
                    signalInfo: si || null,
                    tier: tier || 'good'
                };
                switchToTab('builder');
            };
        } else {
            fixCard.classList.add('hidden');
        }

        // Card 4: DELTA PREVIEW
        const deltaCard = document.getElementById('delta-card');
        if (dp && dp.before && dp.after) {
            document.getElementById('delta-before-signal').textContent = dp.before.signal.toUpperCase();
            document.getElementById('delta-before-signal').className = 'delta-state-signal signal-' + dp.before.signal;
            document.getElementById('delta-before-signal').style.color = 'var(--signal-' + dp.before.signal + ')';
            document.getElementById('delta-before-score').textContent = dp.before.grade + ' (' + Math.round(dp.before.fragilityScore) + ')';

            document.getElementById('delta-after-signal').textContent = dp.after.signal.toUpperCase();
            document.getElementById('delta-after-signal').className = 'delta-state-signal signal-' + dp.after.signal;
            document.getElementById('delta-after-signal').style.color = 'var(--signal-' + dp.after.signal + ')';
            document.getElementById('delta-after-score').textContent = dp.after.grade + ' (' + Math.round(dp.after.fragilityScore) + ')';

            deltaCard.classList.remove('hidden');
        } else {
            deltaCard.classList.add('hidden');
        }

        // Card 5: WARNINGS (always shown for GOOD+)
        const warningsCard = document.getElementById('warnings-card');
        const warningsList = document.getElementById('warnings-list');
        const warnings = explain.warnings || [];
        // Add context modifiers to warnings
        const ctxMods = (data.context && data.context.impact && data.context.impact.modifiers) || [];
        ctxMods.forEach(function(m) {
            if (m.reason) warnings.push(m.reason);
        });
        if (warnings.length > 0) {
            warningsList.innerHTML = warnings.map(function(w) { return '<li>' + w + '</li>'; }).join('');
            warningsCard.classList.remove('hidden');
        } else {
            warningsCard.classList.add('hidden');
        }

        // Card 6: TIPS (always shown for GOOD+)
        const tipsCard = document.getElementById('tips-card');
        const tipsList = document.getElementById('tips-list');
        const tips = explain.tips || [];
        const whatToDo = fragility.what_to_do || '';
        const meaning = fragility.meaning || '';
        let allTips = tips.slice();
        if (meaning) allTips.push(meaning);
        if (whatToDo) allTips.push(whatToDo);
        if (allTips.length > 0) {
            tipsList.innerHTML = allTips.map(function(t) { return '<li>' + t + '</li>'; }).join('');
            tipsCard.classList.remove('hidden');
        } else {
            tipsCard.classList.add('hidden');
        }

        // ========================================
        // TIER-GATED CARDS (BETTER+ / BEST)
        // ========================================

        // BETTER+ Card: CORRELATIONS
        const correlationsCard = document.getElementById('correlations-card');
        const correlationsList = document.getElementById('correlations-list');
        if ((tier === 'better' || tier === 'best') && correlations.length > 0) {
            let corrHtml = '';
            correlations.forEach(function(c) {
                corrHtml += '<div style="display: flex; justify-content: space-between; padding: var(--sp-2) 0; border-bottom: 1px solid var(--border-subtle); font-size: var(--text-sm);">';
                corrHtml += '<span style="color: var(--fg-secondary);">' + c.type.replace(/_/g, ' ') + '</span>';
                corrHtml += '<span style="color: var(--signal-yellow); font-weight: 600;">+' + (c.penalty || 0).toFixed(1) + '</span>';
                corrHtml += '</div>';
            });
            correlationsList.innerHTML = corrHtml;
            correlationsCard.classList.remove('hidden');
        } else {
            correlationsCard.classList.add('hidden');
        }

        // BETTER+ Card: INSIGHTS
        const insightsCard = document.getElementById('insights-card');
        const insightsList = document.getElementById('insights-list');
        const summaryItems = explain.summary || [];
        if ((tier === 'better' || tier === 'best') && summaryItems.length > 0) {
            insightsList.innerHTML = summaryItems.map(function(s) {
                return '<div style="padding: var(--sp-2) 0; font-size: var(--text-sm); color: var(--fg-secondary); border-bottom: 1px solid var(--border-subtle);">' + s + '</div>';
            }).join('');
            insightsCard.classList.remove('hidden');
        } else {
            insightsCard.classList.add('hidden');
        }

        // BEST Card: ALERTS
        const alertsCard = document.getElementById('alerts-card');
        const alertsList = document.getElementById('alerts-list');
        const alertItems = explain.alerts || [];
        const contextAlerts = (data.context && data.context.alerts_generated) || 0;
        if (tier === 'best' && (alertItems.length > 0 || contextAlerts > 0)) {
            let alertsHtml = '';
            alertItems.forEach(function(a) {
                alertsHtml += '<div style="padding: var(--sp-2) 0; font-size: var(--text-sm); color: var(--signal-red); border-bottom: 1px solid var(--border-subtle);">\u26A0 ' + a + '</div>';
            });
            if (contextAlerts > 0) {
                alertsHtml += '<div style="padding: var(--sp-2) 0; font-size: var(--text-sm); color: var(--signal-red);">\u26A0 Live conditions affecting this parlay</div>';
            }
            alertsList.innerHTML = alertsHtml;
            alertsCard.classList.remove('hidden');
        } else {
            alertsCard.classList.add('hidden');
        }

        // BEST Card: RECOMMENDED NEXT STEP
        const nextStepCard = document.getElementById('next-step-card');
        const nextStepContent = document.getElementById('next-step-content');
        if (tier === 'best' && explain.recommended_next_step) {
            nextStepContent.innerHTML = '<div style="font-size: var(--text-base); color: var(--fg-primary);">' + explain.recommended_next_step + '</div>';
            nextStepCard.classList.remove('hidden');
        } else {
            nextStepCard.classList.add('hidden');
        }

        // ========================================
        // IMPROVE IN BUILDER BUTTON
        // ========================================
        const improveBtn = document.getElementById('improve-btn');
        if (pf && pf.fastestFix) {
            improveBtn.disabled = false;
            improveBtn.onclick = function() {
                window._fixContext = {
                    evaluationId: data.evaluationId || null,
                    primaryFailure: pf,
                    fastestFix: pf.fastestFix,
                    deltaPreview: dp || null,
                    inputText: data.input ? data.input.bet_text : null,
                    signalInfo: si || null,
                    tier: tier || 'good'
                };
                switchToTab('builder');
            };
        } else {
            improveBtn.disabled = true;
            improveBtn.onclick = null;
        }

        // ========================================
        // DETAILS ACCORDION (Raw Metrics)
        // ========================================
        // Signal + Fragility (for test compatibility)
        document.getElementById('detail-signal').textContent = (si.label || 'Solid') + ' (' + (si.signal || 'green').toUpperCase() + ')';
        document.getElementById('detail-signal').className = 'detail-value signal-' + (si.signal || 'green');
        document.getElementById('detail-fragility').textContent = Math.round(si.fragilityScore || fragility.display_value || 0);

        document.getElementById('detail-leg-penalty').textContent = '+' + (metrics.leg_penalty || 0).toFixed(1);
        document.getElementById('detail-correlation').textContent = '+' + (metrics.correlation_penalty || 0).toFixed(1);
        document.getElementById('detail-corr-mult').textContent = (metrics.correlation_multiplier || 1).toFixed(2) + 'x';

        // Contributors
        const detailContributors = document.getElementById('detail-contributors');
        const detailContributorsList = document.getElementById('detail-contributors-list');
        const contributors = explain.contributors || [];
        if (contributors.length > 0) {
            let contribHtml = '';
            contributors.forEach(function(c) {
                contribHtml += '<div style="display: flex; justify-content: space-between; padding: var(--sp-1) 0;">';
                contribHtml += '<span style="color: var(--fg-muted);">' + c.type + '</span>';
                contribHtml += '<span style="font-weight: 600; color: var(--fg-primary);">' + c.impact + '</span>';
                contribHtml += '</div>';
            });
            detailContributorsList.innerHTML = contribHtml;
            detailContributors.classList.remove('hidden');
        } else {
            detailContributors.classList.add('hidden');
        }

        // Warnings (for test compatibility - sync with warnings card)
        const detailWarnings = document.getElementById('detail-warnings');
        const detailWarningsList = document.getElementById('detail-warnings-list');
        if (warnings.length > 0) {
            detailWarningsList.innerHTML = warnings.map(function(w) { return '<li>' + w + '</li>'; }).join('');
            detailWarnings.classList.remove('hidden');
        } else {
            detailWarnings.classList.add('hidden');
        }

        // Tips (for test compatibility - sync with tips card)
        const detailTips = document.getElementById('detail-tips');
        const detailTipsList = document.getElementById('detail-tips-list');
        if (allTips.length > 0) {
            detailTipsList.innerHTML = allTips.map(function(t) { return '<li>' + t + '</li>'; }).join('');
            detailTips.classList.remove('hidden');
        } else {
            detailTips.classList.add('hidden');
        }

        // VC-3: Show/hide "Try Another Fix" button
        const loopTryFix = document.getElementById('loop-try-fix');
        if (loopTryFix) {
            if (pf && pf.fastestFix && dp && dp.after) {
                loopTryFix.classList.remove('hidden');
            } else {
                loopTryFix.classList.add('hidden');
            }
        }

        // ========================================
        // TICKET 18: SYSTEM PROOF PANEL
        // Visible for BEST tier or ?debug=1
        // ========================================
        const proofPanel = document.getElementById('system-proof-panel');
        const proof = data.proof;
        const debugParam = new URLSearchParams(window.location.search).get('debug');
        const showProof = tier === 'best' || debugParam === '1';

        if (proofPanel && showProof && proof) {
            // Sherlock/DNA flag status
            const sherlockEnabled = document.getElementById('proof-sherlock-enabled');
            const dnaEnabled = document.getElementById('proof-dna-enabled');
            const sherlockRan = document.getElementById('proof-sherlock-ran');
            const auditStatus = document.getElementById('proof-audit-status');
            const auditNotes = document.getElementById('proof-audit-notes');
            const auditNotesRow = document.getElementById('proof-audit-notes-row');
            const artifactsSection = document.getElementById('proof-artifacts-section');

            // Set enabled/disabled status with styling
            sherlockEnabled.textContent = proof.sherlock_enabled ? 'YES' : 'NO';
            sherlockEnabled.className = 'proof-value ' + (proof.sherlock_enabled ? 'proof-enabled' : 'proof-disabled');

            dnaEnabled.textContent = proof.dna_recording_enabled ? 'YES' : 'NO';
            dnaEnabled.className = 'proof-value ' + (proof.dna_recording_enabled ? 'proof-enabled' : 'proof-disabled');

            if (proof.record) {
                const rec = proof.record;

                // Sherlock ran status
                sherlockRan.textContent = rec.sherlock_ran ? 'YES' : 'NO';
                sherlockRan.className = 'proof-value ' + (rec.sherlock_ran ? 'proof-enabled' : 'proof-disabled');

                // Audit status
                auditStatus.textContent = rec.audit_status || 'N/A';
                if (rec.audit_status === 'PASS') {
                    auditStatus.className = 'proof-value proof-pass';
                } else if (rec.audit_status === 'FAIL') {
                    auditStatus.className = 'proof-value proof-fail';
                } else {
                    auditStatus.className = 'proof-value proof-skip';
                }

                // Audit notes (show if present)
                if (rec.audit_notes) {
                    auditNotes.textContent = rec.audit_notes;
                    auditNotesRow.classList.remove('hidden');
                } else {
                    auditNotesRow.classList.add('hidden');
                }

                // Artifacts (show if present)
                if (rec.artifacts && proof.dna_recording_enabled) {
                    const arts = rec.artifacts;
                    document.getElementById('proof-artifact-correlations').textContent = arts.correlation_count || 0;
                    document.getElementById('proof-artifact-fragility').textContent = arts.fragility_computed ? 'YES' : 'NO';
                    document.getElementById('proof-artifact-inductor').textContent = arts.inductor_level || '--';
                    document.getElementById('proof-artifact-recommendation').textContent = arts.recommendation_action || '--';
                    document.getElementById('proof-artifact-suggestions').textContent = arts.suggestion_count || 0;
                    document.getElementById('proof-artifact-total').textContent = arts.total_artifacts || 0;
                    artifactsSection.classList.remove('hidden');
                } else {
                    artifactsSection.classList.add('hidden');
                }

                // Metadata
                document.getElementById('proof-id').textContent = rec.proof_id || '--';
                document.getElementById('proof-timestamp').textContent = rec.timestamp_utc || '--';
                document.getElementById('proof-derived').textContent = rec.derived ? 'true' : 'false';
            } else {
                // No record (features disabled)
                sherlockRan.textContent = 'N/A';
                sherlockRan.className = 'proof-value proof-skip';
                auditStatus.textContent = 'SKIPPED';
                auditStatus.className = 'proof-value proof-skip';
                auditNotesRow.classList.add('hidden');
                artifactsSection.classList.add('hidden');
                document.getElementById('proof-id').textContent = '--';
                document.getElementById('proof-timestamp').textContent = '--';
            }

            proofPanel.classList.remove('hidden');
        } else if (proofPanel) {
            proofPanel.classList.add('hidden');
        }

        // Store last eval data for re-evaluate
        window._lastEvalData = data;
    }

    // Submit evaluation
    evalSubmitBtn.addEventListener('click', async function() {
        const tier = getEvalTier();
        const workingOverlay = document.getElementById('working-overlay');
        const workingText = document.getElementById('working-text');

        evalSubmitBtn.disabled = true;
        evalSubmitBtn.textContent = 'Evaluating...';

        // Show working overlay
        if (workingOverlay) {
            workingOverlay.classList.remove('hidden');
            workingText.textContent = 'Working...';
        }

        try {
            let response, data;

            if (currentInputMode === 'text') {
                // Text evaluation
                const input = textInput.value.trim();
                if (input.length < 5) {
                    showEvalError('Please enter more text to evaluate');
                    if (workingOverlay) workingOverlay.classList.add('hidden');
                    return;
                }

                if (workingText) workingText.textContent = 'Analyzing bet structure...';

                response = await fetch('/app/evaluate', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ input, tier })
                });

                data = await response.json();

                if (!response.ok) {
                    showEvalError(data.detail || 'Evaluation failed');
                    if (workingOverlay) workingOverlay.classList.add('hidden');
                    return;
                }

                showEvalResults(data, null);

            } else {
                // Image evaluation
                if (!selectedFile) {
                    showEvalError('Please select an image');
                    if (workingOverlay) workingOverlay.classList.add('hidden');
                    return;
                }

                fileUploadArea.classList.add('uploading');
                if (workingText) workingText.textContent = 'Extracting text from image...';

                // Update preview status
                const previewStatus = document.getElementById('image-preview-status');
                if (previewStatus) previewStatus.textContent = 'Extracting...';

                const formData = new FormData();
                formData.append('file', selectedFile);
                formData.append('tier', tier);

                response = await fetch('/app/evaluate/image', {
                    method: 'POST',
                    body: formData
                });

                data = await response.json();

                fileUploadArea.classList.remove('uploading');

                if (!response.ok) {
                    showEvalError(data.detail || 'Image evaluation failed');
                    if (workingOverlay) workingOverlay.classList.add('hidden');
                    if (previewStatus) previewStatus.textContent = 'Extraction failed';
                    return;
                }

                // Show extracted text if available
                if (data.image_parse && data.image_parse.extracted_text) {
                    showExtractedText(data.image_parse.extracted_text, data.image_parse.confidence);
                    if (previewStatus) previewStatus.textContent = 'Extracted successfully';
                } else if (previewStatus) {
                    previewStatus.textContent = 'Extraction complete';
                }

                showEvalResults(data, data.image_parse);
            }
        } catch (err) {
            showEvalError('Network error: ' + err.message);
            if (fileUploadArea) fileUploadArea.classList.remove('uploading');
            if (workingOverlay) workingOverlay.classList.add('hidden');
        } finally {
            evalSubmitBtn.disabled = false;
            evalSubmitBtn.textContent = 'Evaluate';
            updateEvalSubmitState();
            // Hide working overlay
            if (workingOverlay) workingOverlay.classList.add('hidden');
        }
    });

    // VC-3: Payoff banner dismiss
    const payoffDismiss = document.getElementById('payoff-dismiss');
    if (payoffDismiss) {
        payoffDismiss.addEventListener('click', function() {
            document.getElementById('payoff-banner').classList.add('hidden');
            document.getElementById('mini-diff').classList.add('hidden');
            window._fixApplied = null;
        });
    }

    // VC-3: Loop Shortcuts
    // Re-Evaluate button: reset results and focus input
    const loopReeval = document.getElementById('loop-reeval');
    if (loopReeval) {
        loopReeval.addEventListener('click', function() {
            evalResultsContent.classList.add('hidden');
            evalResultsPlaceholder.classList.remove('hidden');
            evalErrorPanel.classList.add('hidden');
            // Clear payoff state
            document.getElementById('payoff-banner').classList.add('hidden');
            document.getElementById('mini-diff').classList.add('hidden');
            window._fixApplied = null;
            if (currentInputMode === 'text') {
                textInput.focus();
                textInput.select();
            }
            updateEvalSubmitState();
        });
    }

    // Try Another Fix button: go to builder with current context
    const loopTryFix = document.getElementById('loop-try-fix');
    if (loopTryFix) {
        loopTryFix.addEventListener('click', function() {
            if (window._lastEvalData) {
                const data = window._lastEvalData;
                const pf = data.primaryFailure;
                const dp = data.deltaPreview;
                const si = data.signalInfo;
                if (pf && pf.fastestFix) {
                    window._fixContext = {
                        evaluationId: data.evaluationId || null,
                        primaryFailure: pf,
                        fastestFix: pf.fastestFix,
                        deltaPreview: dp || null,
                        inputText: data.input ? data.input.bet_text : null,
                        signalInfo: si || null,
                        tier: data.input ? data.input.tier : 'good'
                    };
                    switchToTab('builder');
                }
            }
        });
    }

    // Save button: persist evaluation
    const loopSave = document.getElementById('loop-save');
    if (loopSave) {
        loopSave.addEventListener('click', function() {
            if (window._lastEvalData && window._lastEvalData.evaluation_id) {
                loopSave.textContent = 'Saved';
                loopSave.disabled = true;
                loopSave.style.background = '#4ade80';
                loopSave.style.color = '#000';
            } else {
                loopSave.textContent = 'Login to Save';
                loopSave.disabled = true;
            }
        });
    }
})();

// ============================================================
// HISTORY TAB FUNCTIONALITY (Ticket 6)
// ============================================================
(function() {
    let historyLoaded = false;

    // Re-evaluate: load input into Evaluate tab and trigger evaluation
    window.historyReEvaluate = async function(itemId) {
        try {
            const response = await fetch('/app/history/' + itemId);
            const data = await response.json();
            if (data.item && data.item.raw) {
                const inputText = data.item.inputText || (data.item.raw.input && data.item.raw.input.bet_text) || '';
                const textInput = document.getElementById('text-input');
                if (textInput && inputText) {
                    textInput.value = inputText;
                    switchToTab('evaluate');
                    // Focus the input
                    textInput.focus();
                }
            }
        } catch (err) {
            console.error('Failed to load history item for re-evaluate:', err);
        }
    };

    // Edit: load into Builder with fix context (if available)
    window.historyEdit = async function(itemId) {
        try {
            const response = await fetch('/app/history/' + itemId);
            const data = await response.json();
            if (data.item && data.item.raw) {
                const raw = data.item.raw;
                // Set up fix context if we have primaryFailure
                if (raw.primaryFailure && raw.primaryFailure.fastestFix) {
                    window._fixContext = {
                        evaluationId: itemId,
                        primaryFailure: raw.primaryFailure,
                        fastestFix: raw.primaryFailure.fastestFix,
                        deltaPreview: raw.deltaPreview || null,
                        inputText: raw.input ? raw.input.bet_text : (data.item.input_text || null),
                        signalInfo: raw.signalInfo || null,
                        tier: raw.input ? raw.input.tier : 'good'
                    };
                } else {
                    // Even without fastestFix, allow builder access with input text
                    window._fixContext = {
                        evaluationId: itemId,
                        primaryFailure: raw.primaryFailure || null,
                        fastestFix: null,
                        deltaPreview: raw.deltaPreview || null,
                        inputText: raw.input ? raw.input.bet_text : (data.item.input_text || null),
                        signalInfo: raw.signalInfo || null,
                        tier: raw.input ? raw.input.tier : 'good'
                    };
                }
                switchToTab('builder');
            }
        } catch (err) {
            console.error('Failed to load history item for edit:', err);
        }
    };

    window.loadHistory = async function(forceReload) {
        if (historyLoaded && !forceReload) return;

        const historyContent = document.getElementById('history-content');
        const historyEmpty = document.getElementById('history-empty');

        historyContent.innerHTML = '<div class="history-loading">Loading history...</div>';
        if (historyEmpty) historyEmpty.classList.add('hidden');

        try {
            const response = await fetch('/app/history');
            const data = await response.json();
            const items = data.items || [];

            if (items.length === 0) {
                historyContent.innerHTML = '';
                if (historyEmpty) historyEmpty.classList.remove('hidden');
                historyLoaded = true;
                return;
            }

            if (historyEmpty) historyEmpty.classList.add('hidden');

            let html = '';
            items.forEach(function(item) {
                const date = new Date(item.createdAt).toLocaleString();
                const score = Math.round(item.fragilityScore || 0);
                const signal = item.signal || 'green';
                const label = item.label || 'Solid';
                const sport = item.sport || '';

                html += '<div class="history-item" data-id="' + item.id + '">';
                html += '<div class="history-item-header">';
                html += '<div class="history-item-meta">';
                html += '<div class="history-date">' + date + '</div>';
                if (sport) { html += '<div class="history-sport">' + sport + '</div>'; }
                html += '</div>';
                html += '<div class="history-item-actions">';
                html += '<button type="button" class="history-action-btn primary" onclick="historyReEvaluate(\'' + item.id + '\')">Re-Evaluate</button>';
                html += '<button type="button" class="history-action-btn" onclick="historyEdit(\'' + item.id + '\')">Edit</button>';
                html += '</div>';
                html += '</div>';
                html += '<div class="history-text">' + (item.inputText || 'N/A') + '</div>';
                html += '<span class="history-grade ' + signal + '">' + score + ' - ' + label + '</span>';
                html += '</div>';
            });

            historyContent.innerHTML = html;
            historyLoaded = true;

        } catch (err) {
            console.error('Failed to load history:', err);
            historyContent.innerHTML = "<div class='history-empty-state'><p>Failed to load history</p></div>";
        }
    };

    // Load history if starting on history tab
    const activeTab = new URLSearchParams(window.location.search).get('tab');
    if (activeTab === 'history') {
        loadHistory();
    }
})();
