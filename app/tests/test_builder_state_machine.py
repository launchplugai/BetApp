# app/tests/test_builder_state_machine.py
"""
Ticket 31: Builder State Machine Tests (DNA Parlay Builder Spec v1.0)

Tests for the locked specification:
- EMPTY: 0 legs
- SINGLE_BET: 1 leg
- STANDARD_PARLAY: 2-3 legs
- ELEVATED_PARLAY: 4-5 legs
- MAX_PARLAY: 6 legs
- BLOCKED: Rejected transition when attempting 7th leg (not a persistent state)

Test Coverage:
- T-001: State computation boundaries
- T-002: Language enforcement ("Single bet" vs "{N}-leg parlay")
- T-003: Blocked add at 6 legs -> attempt 7th rejected
- T-010: Single-leg removal IS allowed (SINGLE_BET -> EMPTY)
"""
import re
import pytest
from pathlib import Path


@pytest.fixture
def app_js_content():
    """Load the app.js file content for static analysis."""
    js_path = Path(__file__).parent.parent / "web_assets" / "static" / "app.js"
    return js_path.read_text()


class TestT001StateComputationBoundaries:
    """
    T-001: State computation from leg count per spec v1.0.

    Verifies that BuilderStateMachine.computeState() returns correct states:
    - 0 legs: EMPTY
    - 1 leg: SINGLE_BET
    - 2-3 legs: STANDARD_PARLAY
    - 4-5 legs: ELEVATED_PARLAY
    - 6+ legs: MAX_PARLAY
    """

    def test_state_machine_exists_in_app_js(self, app_js_content):
        """BuilderStateMachine object must exist in app.js."""
        assert "BuilderStateMachine" in app_js_content
        assert "computeState" in app_js_content

    def test_max_legs_constant_is_6(self, app_js_content):
        """MAX_LEGS must be 6 per spec."""
        assert "MAX_LEGS: 6" in app_js_content

    def test_empty_state_at_0_legs(self, app_js_content):
        """EMPTY state is defined for 0 legs."""
        assert "if (legCount === 0) return 'EMPTY'" in app_js_content

    def test_single_bet_state_at_1_leg(self, app_js_content):
        """SINGLE_BET state is defined for 1 leg."""
        assert "if (legCount === 1) return 'SINGLE_BET'" in app_js_content

    def test_standard_parlay_state_at_2_to_3_legs(self, app_js_content):
        """STANDARD_PARLAY state is defined for 2-3 legs."""
        assert "minLegs: 2, maxLegs: 3" in app_js_content
        assert "legCount >= 2 && legCount <= 3" in app_js_content
        assert "return 'STANDARD_PARLAY'" in app_js_content

    def test_elevated_parlay_state_at_4_to_5_legs(self, app_js_content):
        """ELEVATED_PARLAY state is defined for 4-5 legs."""
        assert "minLegs: 4, maxLegs: 5" in app_js_content
        assert "legCount >= 4 && legCount <= 5" in app_js_content
        assert "return 'ELEVATED_PARLAY'" in app_js_content

    def test_max_parlay_state_at_6_legs(self, app_js_content):
        """MAX_PARLAY state is defined for 6+ legs."""
        assert "minLegs: 6, maxLegs: 6" in app_js_content
        assert "legCount >= 6" in app_js_content
        assert "return 'MAX_PARLAY'" in app_js_content

    def test_no_7_to_12_leg_logic(self, app_js_content):
        """No 7-12 leg logic should exist (MAX is 6)."""
        # Should NOT have any references to 7-12 leg thresholds
        assert "legCount >= 7" not in app_js_content
        assert "legCount >= 12" not in app_js_content
        assert "maxLegs: 11" not in app_js_content
        assert "maxLegs: 12" not in app_js_content


class TestT002LanguageEnforcement:
    """
    T-002: Terminology enforcement per spec.

    - 1 leg: "Single bet", bet_term="bet"
    - 2+ legs: "{N}-leg parlay", bet_term="parlay"
    - NOT "N legs (parlay)" format
    """

    def test_get_bet_term_function_exists(self, app_js_content):
        """getBetTerm function must exist."""
        assert "getBetTerm:" in app_js_content

    def test_single_leg_returns_bet(self, app_js_content):
        """1 leg should return 'bet'."""
        assert "if (legCount === 1) return 'bet'" in app_js_content

    def test_multi_leg_returns_parlay(self, app_js_content):
        """2+ legs should return 'parlay'."""
        # Default return for multi-leg
        get_bet_term_match = re.search(
            r"getBetTerm:\s*function\s*\(legCount\)\s*\{[^}]+\}",
            app_js_content,
            re.DOTALL
        )
        assert get_bet_term_match is not None
        func_body = get_bet_term_match.group(0)
        assert "return 'parlay'" in func_body

    def test_zero_legs_returns_empty(self, app_js_content):
        """0 legs should return empty string."""
        assert "if (legCount === 0) return ''" in app_js_content

    def test_single_bet_display_text(self, app_js_content):
        """Single bet should display as 'Single bet' (not '1 leg (single bet)')."""
        # Check getLegCountText
        assert "if (legCount === 1) return 'Single bet'" in app_js_content
        # Should NOT have old format
        assert "1 leg (single bet)" not in app_js_content

    def test_multi_leg_display_format(self, app_js_content):
        """Multi-leg should display as '{N}-leg parlay' format."""
        # Check getLegCountText returns proper format
        assert "return legCount + '-leg parlay'" in app_js_content
        # Should NOT have old format
        assert "legs (' + this.getBetTerm" not in app_js_content


class TestT003BlockedTransitionAt6Legs:
    """
    T-003: Blocked add at 6 legs -> attempt to add 7th is rejected.

    BLOCKED is not a persistent state; it's a rejected transition.
    - tryAddLeg() should return { allowed: false, blocked: true } at 6 legs
    - State remains MAX_PARLAY after blocked attempt
    - Blocked event should be emittable
    """

    def test_try_add_leg_function_exists(self, app_js_content):
        """tryAddLeg function must exist for blocked transition handling."""
        assert "tryAddLeg:" in app_js_content

    def test_try_add_leg_returns_blocked_at_max(self, app_js_content):
        """tryAddLeg returns blocked=true when at MAX_LEGS."""
        try_add_match = re.search(
            r"tryAddLeg:\s*function\s*\(currentLegCount\)\s*\{[^}]+\}",
            app_js_content,
            re.DOTALL
        )
        assert try_add_match is not None, "tryAddLeg function not found"

        func_body = try_add_match.group(0)
        assert "currentLegCount >= this.MAX_LEGS" in func_body
        assert "allowed: false" in func_body
        assert "blocked: true" in func_body

    def test_try_add_leg_returns_allowed_when_under_max(self, app_js_content):
        """tryAddLeg returns allowed=true when under MAX_LEGS."""
        # Search the full function body (multiple return statements)
        # The function returns { allowed: true, blocked: false } for under-max case
        assert "return { allowed: true, reason: null, blocked: false }" in app_js_content

    def test_max_parlay_cannot_add(self, app_js_content):
        """MAX_PARLAY state must have canAdd: false."""
        max_match = re.search(
            r"MAX_PARLAY:\s*\{[^}]+\}",
            app_js_content
        )
        assert max_match is not None, "MAX_PARLAY state not found"
        assert "canAdd: false" in max_match.group(0)

    def test_blocked_event_emitter_exists(self, app_js_content):
        """emitBlockedEvent function should exist."""
        assert "function emitBlockedEvent" in app_js_content
        assert "builderAddBlocked" in app_js_content

    def test_blocked_event_includes_reason(self, app_js_content):
        """Blocked event should include reason."""
        blocked_match = re.search(
            r"function emitBlockedEvent\(reason\)\s*\{[^}]+\}",
            app_js_content,
            re.DOTALL
        )
        assert blocked_match is not None
        func_body = blocked_match.group(0)
        assert "reason:" in func_body

    def test_blocked_event_exported(self, app_js_content):
        """emitBlockedEvent should be exported for testing."""
        assert "window._emitBlockedEvent = emitBlockedEvent" in app_js_content


class TestT010SingleLegRemovalAllowed:
    """
    T-010: Single-leg removal IS allowed per spec.

    SINGLE_BET state must have canRemove: true (allows SINGLE_BET -> EMPTY).
    """

    def test_single_bet_can_remove(self, app_js_content):
        """SINGLE_BET state must have canRemove: true."""
        single_bet_match = re.search(
            r"SINGLE_BET:\s*\{[^}]+\}",
            app_js_content
        )
        assert single_bet_match is not None, "SINGLE_BET state not found"
        assert "canRemove: true" in single_bet_match.group(0)

    def test_empty_cannot_remove(self, app_js_content):
        """EMPTY state must have canRemove: false."""
        empty_match = re.search(
            r"EMPTY:\s*\{[^}]+\}",
            app_js_content
        )
        assert empty_match is not None, "EMPTY state not found"
        assert "canRemove: false" in empty_match.group(0)

    def test_standard_parlay_can_remove(self, app_js_content):
        """STANDARD_PARLAY state must have canRemove: true."""
        standard_match = re.search(
            r"STANDARD_PARLAY:\s*\{[^}]+\}",
            app_js_content
        )
        assert standard_match is not None
        assert "canRemove: true" in standard_match.group(0)

    def test_elevated_parlay_can_remove(self, app_js_content):
        """ELEVATED_PARLAY state must have canRemove: true."""
        elevated_match = re.search(
            r"ELEVATED_PARLAY:\s*\{[^}]+\}",
            app_js_content
        )
        assert elevated_match is not None
        assert "canRemove: true" in elevated_match.group(0)

    def test_max_parlay_can_remove(self, app_js_content):
        """MAX_PARLAY state must have canRemove: true."""
        max_match = re.search(
            r"MAX_PARLAY:\s*\{[^}]+\}",
            app_js_content
        )
        assert max_match is not None
        assert "canRemove: true" in max_match.group(0)

    def test_remove_leg_uses_state_machine(self, app_js_content):
        """removeLeg function must check state machine."""
        remove_leg_match = re.search(
            r"function removeLeg\([^)]*\)\s*\{[^}]+\}",
            app_js_content,
            re.DOTALL
        )
        assert remove_leg_match is not None, "removeLeg function not found"
        remove_body = remove_leg_match.group(0)
        assert "BuilderStateMachine.canRemoveLeg" in remove_body


class TestBuilderStateExports:
    """
    Verify that state machine is properly exported for external access.
    """

    def test_state_machine_exported_to_window(self, app_js_content):
        """BuilderStateMachine should be exported to window."""
        assert "window.BuilderStateMachine = BuilderStateMachine" in app_js_content

    def test_get_builder_state_exported(self, app_js_content):
        """_getBuilderState getter should be exported."""
        assert "window._getBuilderState" in app_js_content

    def test_get_builder_state_includes_max_legs(self, app_js_content):
        """_getBuilderState should include maxLegs."""
        get_state_match = re.search(
            r"window\._getBuilderState\s*=\s*function\s*\(\)\s*\{[^}]+return\s*\{[^}]+\}",
            app_js_content,
            re.DOTALL
        )
        assert get_state_match is not None
        func_body = get_state_match.group(0)
        assert "maxLegs:" in func_body

    def test_get_builder_state_includes_is_at_max(self, app_js_content):
        """_getBuilderState should include isAtMax."""
        get_state_match = re.search(
            r"window\._getBuilderState\s*=\s*function\s*\(\)\s*\{[^}]+return\s*\{[^}]+\}",
            app_js_content,
            re.DOTALL
        )
        assert get_state_match is not None
        func_body = get_state_match.group(0)
        assert "isAtMax:" in func_body


class TestStateLabels:
    """
    Verify state labels are defined for UI display.
    """

    def test_get_state_label_function_exists(self, app_js_content):
        """getStateLabel function should exist."""
        assert "getStateLabel:" in app_js_content

    def test_all_states_have_labels(self, app_js_content):
        """All states should have human-readable labels."""
        labels_expected = [
            "label: 'Empty'",
            "label: 'Single Bet'",
            "label: 'Standard Parlay'",
            "label: 'Elevated Risk'",
            "label: 'Maximum Legs'"
        ]
        for label in labels_expected:
            assert label in app_js_content, f"Missing label: {label}"


class TestStateChangeEvents:
    """
    Verify state change events include required fields.
    """

    def test_state_change_event_emitted(self, app_js_content):
        """State changes should emit a CustomEvent."""
        assert "CustomEvent" in app_js_content
        assert "builderStateChange" in app_js_content

    def test_event_includes_is_at_max(self, app_js_content):
        """Event should include isAtMax flag in builderStateChange event."""
        # Check that the builderStateChange event detail includes isAtMax
        # The event spans multiple lines, so search for the pattern in full content
        assert "builderStateChange" in app_js_content
        assert "isAtMax: BuilderStateMachine.isAtMax" in app_js_content


class TestIsAtMaxFunction:
    """
    Verify isAtMax function checks against MAX_LEGS (6).
    """

    def test_is_at_max_function_exists(self, app_js_content):
        """isAtMax function should exist."""
        assert "isAtMax:" in app_js_content

    def test_is_at_max_checks_max_legs(self, app_js_content):
        """isAtMax should check against MAX_LEGS constant."""
        is_at_max_match = re.search(
            r"isAtMax:\s*function\s*\(legCount\)\s*\{[^}]+\}",
            app_js_content,
            re.DOTALL
        )
        assert is_at_max_match is not None
        func_body = is_at_max_match.group(0)
        assert "this.MAX_LEGS" in func_body


class TestDefenseInDepth:
    """
    Verify defense-in-depth: MAX_LEGS=6, no 7-12 leg support.
    """

    def test_no_elevated_parlay_7_to_11_range(self, app_js_content):
        """ELEVATED_PARLAY should NOT span 7-11 legs."""
        elevated_match = re.search(
            r"ELEVATED_PARLAY:\s*\{[^}]+\}",
            app_js_content
        )
        assert elevated_match is not None
        state_def = elevated_match.group(0)
        # Should be 4-5, not 7-11
        assert "minLegs: 4" in state_def
        assert "maxLegs: 5" in state_def
        assert "minLegs: 7" not in state_def
        assert "maxLegs: 11" not in state_def

    def test_blocked_message_mentions_6_legs(self, app_js_content):
        """Blocked message should mention 6 legs limit."""
        assert "Maximum 6 legs allowed" in app_js_content


# ============================================================
# TICKET 31 CHUNK 2: UI STATE RENDERING TESTS
# ============================================================

class TestChunk2UIStateRendering:
    """
    Chunk 2: UI State Rendering tests.

    Verifies visibility matrix implementation:
    - EMPTY: header "Add your first leg to begin", disclosure hidden
    - SINGLE_BET: header "Single bet", disclosure visible, primary failure hidden
    - STANDARD_PARLAY: header "{N}-leg parlay", disclosure visible, primary failure visible
    - ELEVATED_PARLAY: complexity banner visible, primary failure visible
    - MAX_PARLAY: header "6-leg parlay (maximum)", complexity banner visible, max warning visible, primary failure visible
    """

    def test_render_state_ui_function_exists(self, app_js_content):
        """renderStateUI function must exist."""
        assert "function renderStateUI()" in app_js_content

    def test_render_state_ui_exported(self, app_js_content):
        """renderStateUI should be exported for testing."""
        assert "window._renderStateUI = renderStateUI" in app_js_content

    def test_visibility_matrix_exported(self, app_js_content):
        """_getVisibilityMatrix should be exported."""
        assert "window._getVisibilityMatrix" in app_js_content


class TestChunk2EmptyStateUI:
    """
    EMPTY state: header "Add your first leg to begin", disclosure hidden.
    """

    def test_empty_header_text(self, app_js_content):
        """EMPTY state shows 'Add your first leg to begin' header."""
        assert "state === 'EMPTY'" in app_js_content
        assert "'Add your first leg to begin'" in app_js_content

    def test_empty_disclosure_hidden(self, app_js_content):
        """EMPTY state hides disclosure badge."""
        # Check that disclosure is hidden for EMPTY
        assert "if (state === 'EMPTY')" in app_js_content
        assert "disclosureBadge.classList.add('hidden')" in app_js_content


class TestChunk2SingleBetStateUI:
    """
    SINGLE_BET state: header "Single bet", disclosure visible, primary failure hidden.
    """

    def test_single_bet_primary_failure_hidden(self, app_js_content):
        """SINGLE_BET state hides primary failure card."""
        # Check that fastest fix card is hidden for SINGLE_BET
        assert "state === 'SINGLE_BET'" in app_js_content
        assert "fastestFixCard.classList.add('state-hidden')" in app_js_content


class TestChunk2StandardParlayStateUI:
    """
    STANDARD_PARLAY state: header "{N}-leg parlay", disclosure visible, primary failure visible.
    """

    def test_standard_parlay_uses_leg_count_text(self, app_js_content):
        """STANDARD_PARLAY uses getLegCountText for header."""
        assert "BuilderStateMachine.getLegCountText(legCount)" in app_js_content


class TestChunk2ElevatedParlayStateUI:
    """
    ELEVATED_PARLAY state: complexity banner visible.
    """

    def test_elevated_parlay_shows_complexity_banner(self, app_js_content):
        """ELEVATED_PARLAY shows complexity banner."""
        assert "state === 'ELEVATED_PARLAY'" in app_js_content
        assert "complexityBanner.classList.remove('hidden')" in app_js_content

    def test_complexity_banner_created(self, app_js_content):
        """Complexity banner element is created."""
        assert "function createComplexityBanner()" in app_js_content
        assert "complexity-banner" in app_js_content
        assert "High complexity parlay" in app_js_content


class TestChunk2MaxParlayStateUI:
    """
    MAX_PARLAY state: header "6-leg parlay (maximum)", complexity banner visible, max warning visible, primary failure visible.
    """

    def test_max_parlay_header_text(self, app_js_content):
        """MAX_PARLAY shows '6-leg parlay (maximum)' header."""
        assert "state === 'MAX_PARLAY'" in app_js_content
        assert "'6-leg parlay (maximum)'" in app_js_content

    def test_max_parlay_shows_warning(self, app_js_content):
        """MAX_PARLAY shows max warning."""
        assert "maxWarning.classList.remove('hidden')" in app_js_content

    def test_max_warning_created(self, app_js_content):
        """Max parlay warning element is created."""
        assert "function createMaxWarning()" in app_js_content
        assert "max-parlay-warning" in app_js_content
        assert "Maximum legs reached" in app_js_content

    def test_max_parlay_shows_complexity_banner(self, app_js_content):
        """MAX_PARLAY shows complexity banner (both warnings)."""
        # The condition should include MAX_PARLAY for complexity banner
        assert "state === 'MAX_PARLAY'" in app_js_content
        # Check that MAX_PARLAY is included in complexity banner logic
        assert "ELEVATED_PARLAY' || state === 'MAX_PARLAY'" in app_js_content

    def test_max_parlay_shows_primary_failure(self, app_js_content):
        """MAX_PARLAY shows primary failure card (not hidden)."""
        # Primary failure is only hidden for EMPTY and SINGLE_BET
        # MAX_PARLAY should NOT be in the hidden condition
        assert "state === 'EMPTY' || state === 'SINGLE_BET'" in app_js_content
        assert "fastestFixCard.classList.remove('state-hidden')" in app_js_content


class TestChunk2BlockedAddUX:
    """
    Blocked add UX: toast message when trying to add 7th leg.
    """

    def test_blocked_add_event_listener(self, app_js_content):
        """Should listen for builderAddBlocked event."""
        assert "document.addEventListener('builderAddBlocked'" in app_js_content

    def test_blocked_add_shows_toast(self, app_js_content):
        """Blocked add shows toast message."""
        assert "Maximum of 6 legs supported" in app_js_content

    def test_handle_blocked_add_function(self, app_js_content):
        """handleBlockedAdd function exists."""
        assert "function handleBlockedAdd(event)" in app_js_content


class TestChunk2DisclosureBadge:
    """
    Disclosure badge: analysis transparency indicator.
    """

    def test_disclosure_badge_created(self, app_js_content):
        """Disclosure badge element is created."""
        assert "function createDisclosureBadge()" in app_js_content
        assert "disclosure-badge" in app_js_content

    def test_disclosure_badge_text(self, app_js_content):
        """Disclosure badge has correct text."""
        assert "Structural analysis only" in app_js_content


class TestChunk2StateChangeListener:
    """
    State change event listener updates UI.
    """

    def test_state_change_listener(self, app_js_content):
        """Should listen for builderStateChange event."""
        assert "document.addEventListener('builderStateChange'" in app_js_content

    def test_render_leg_list_calls_render_state_ui(self, app_js_content):
        """renderLegList should call renderStateUI."""
        assert "renderStateUI()" in app_js_content


@pytest.fixture
def app_css_content():
    """Load the app.css file content for static analysis."""
    css_path = Path(__file__).parent.parent / "web_assets" / "static" / "app.css"
    return css_path.read_text()


class TestChunk2CSSStyles:
    """
    Verify CSS styles for Chunk 2 UI elements.
    """

    def test_state_hidden_class(self, app_css_content):
        """state-hidden CSS class exists."""
        assert ".state-hidden" in app_css_content
        assert "display: none" in app_css_content

    def test_disclosure_badge_styles(self, app_css_content):
        """Disclosure badge has CSS styles."""
        assert ".disclosure-badge" in app_css_content

    def test_complexity_banner_styles(self, app_css_content):
        """Complexity banner has CSS styles."""
        assert ".complexity-banner" in app_css_content

    def test_max_parlay_warning_styles(self, app_css_content):
        """Max parlay warning has CSS styles."""
        assert ".max-parlay-warning" in app_css_content


# ============================================================
# CHUNK 3: GUARDRAILS & ENFORCEMENT TESTS
# ============================================================


class TestChunk3MaxLegsEnforcement:
    """
    Chunk 3: MAX_LEGS enforcement at 6 legs.

    Verifies:
    - parseLegsFromText enforces MAX_LEGS cap
    - addLeg function blocks when at max
    - Blocked event fires when enforcement triggers
    """

    def test_parse_legs_enforces_max_legs(self, app_js_content):
        """parseLegsFromText enforces MAX_LEGS cap."""
        # Check for MAX_LEGS enforcement in parseLegsFromText
        assert "parts.length > BuilderStateMachine.MAX_LEGS" in app_js_content
        assert "parts.slice(0, BuilderStateMachine.MAX_LEGS)" in app_js_content

    def test_parse_legs_emits_blocked_on_truncation(self, app_js_content):
        """parseLegsFromText emits blocked event when legs truncated."""
        assert "wasBlocked" in app_js_content
        assert "emitBlockedEvent('Input exceeded maximum of 6 legs')" in app_js_content

    def test_add_leg_function_exists(self, app_js_content):
        """addLeg function exists for single leg addition."""
        assert "function addLeg(legText)" in app_js_content

    def test_add_leg_exported(self, app_js_content):
        """addLeg function is exported for testing."""
        assert "window._addLeg = addLeg" in app_js_content

    def test_parse_legs_exported(self, app_js_content):
        """parseLegsFromText is exported for testing."""
        assert "window._parseLegsFromText = parseLegsFromText" in app_js_content

    def test_add_leg_uses_try_add_leg(self, app_js_content):
        """addLeg uses tryAddLeg for enforcement."""
        assert "BuilderStateMachine.tryAddLeg(currentLegs.length)" in app_js_content

    def test_add_leg_returns_false_on_block(self, app_js_content):
        """addLeg returns false when blocked."""
        # Check that blocked path returns false
        assert "if (!result.allowed)" in app_js_content
        assert "return false" in app_js_content


class TestChunk3BlockedNoEvaluation:
    """
    Chunk 3: Blocked-add must not trigger evaluation.

    Verifies:
    - tryAddLeg returning allowed:false short-circuits evaluation
    - No triggerReEvaluate call when blocked
    """

    def test_add_leg_short_circuits_on_block(self, app_js_content):
        """addLeg short-circuits before evaluation when blocked."""
        # The code should return before calling triggerReEvaluate
        # Check that return false comes before any triggerReEvaluate in addLeg
        add_leg_start = app_js_content.find("function addLeg(legText)")
        add_leg_end = app_js_content.find("function removeLeg(index)")
        add_leg_code = app_js_content[add_leg_start:add_leg_end]

        # Find positions of key elements
        return_false_pos = add_leg_code.find("return false")
        trigger_eval_pos = add_leg_code.find("triggerReEvaluate()")

        # Blocked path (return false) should come before successful path (triggerReEvaluate)
        assert return_false_pos < trigger_eval_pos, "return false must come before triggerReEvaluate"

    def test_blocked_emits_event_not_evaluation(self, app_js_content):
        """Blocked path emits event, not evaluation."""
        add_leg_start = app_js_content.find("function addLeg(legText)")
        add_leg_end = app_js_content.find("function removeLeg(index)")
        add_leg_code = app_js_content[add_leg_start:add_leg_end]

        # Check that emitBlockedEvent is called when not allowed
        assert "emitBlockedEvent(result.reason)" in add_leg_code


class TestChunk3ForbiddenLanguageGuardrails:
    """
    Chunk 3: Forbidden language guardrails.

    Verifies UI text does NOT contain:
    - Odds patterns: "+150", "-110"
    - Payout language: "potential win", "return", "multiplier", "payout"
    - Pricing language: "value", "edge"
    - Recommendation language: "recommended", "best pick", "safe"
    - Probability claims: "% chance", "will win", "guaranteed"
    """

    def test_no_odds_patterns_in_ui_strings(self, app_js_content):
        """UI strings must not contain odds patterns like +150 or -110."""
        import re
        # Find all string literals in the code
        string_literals = re.findall(r"'[^']*'|\"[^\"]*\"", app_js_content)

        # Odds patterns to reject (as display text, not as regex detection patterns)
        odds_pattern = re.compile(r'[+-]\d{3}')  # +150, -110, etc.

        for literal in string_literals:
            # Skip regex patterns (used for detection, not display)
            if r'\d' in literal or 'test(' in literal:
                continue
            # Check for odds patterns in display strings
            if odds_pattern.search(literal):
                # Allow if it's in a comment or regex pattern context
                if not ('RegExp' in literal or 'regex' in literal.lower()):
                    assert False, f"Found forbidden odds pattern in UI string: {literal}"

    def test_no_payout_language(self, app_js_content):
        """UI strings must not contain payout language."""
        forbidden = ["potential win", "payout", "multiplier"]
        # Find user-facing text (strings in textContent, innerHTML, showToast)
        import re
        ui_strings = re.findall(r"(?:textContent|innerHTML|showToast)\s*[=\(]\s*['\"]([^'\"]+)['\"]", app_js_content)

        for string in ui_strings:
            lower = string.lower()
            for word in forbidden:
                assert word not in lower, f"Found forbidden payout language '{word}' in: {string}"

    def test_no_pricing_language(self, app_js_content):
        """UI strings must not contain pricing language like 'value' or 'edge'."""
        # These terms should not appear in user-facing evaluation context
        # Check toast messages and header text specifically
        import re
        ui_strings = re.findall(r"showToast\(['\"]([^'\"]+)['\"]", app_js_content)

        for string in ui_strings:
            lower = string.lower()
            # 'value' and 'edge' are forbidden in betting context
            if 'bet' in lower or 'parlay' in lower or 'leg' in lower:
                assert 'value' not in lower, f"Found 'value' in betting context: {string}"
                assert 'edge' not in lower, f"Found 'edge' in betting context: {string}"

    def test_no_recommendation_language(self, app_js_content):
        """UI strings must not contain recommendation language."""
        forbidden = ["recommended", "best pick", "safe bet"]
        import re
        ui_strings = re.findall(r"(?:textContent|innerHTML|showToast)\s*[=\(]\s*['\"]([^'\"]+)['\"]", app_js_content)

        for string in ui_strings:
            lower = string.lower()
            for phrase in forbidden:
                assert phrase not in lower, f"Found forbidden recommendation '{phrase}' in: {string}"

    def test_no_probability_claims(self, app_js_content):
        """UI strings must not contain probability claims."""
        forbidden = ["% chance", "will win", "guaranteed", "certain to"]
        import re
        ui_strings = re.findall(r"(?:textContent|innerHTML|showToast)\s*[=\(]\s*['\"]([^'\"]+)['\"]", app_js_content)

        for string in ui_strings:
            lower = string.lower()
            for phrase in forbidden:
                assert phrase not in lower, f"Found forbidden probability claim '{phrase}' in: {string}"


class TestChunk3LanguageConsistency:
    """
    Chunk 3: Language consistency tests.

    Verifies:
    - 1 leg: UI must not contain "parlay"
    - 2+ legs: must use "{N}-leg parlay", not label as "bet"
    """

    def test_single_bet_terminology(self, app_js_content):
        """getLegCountText returns 'Single bet' for 1 leg, not 'parlay'."""
        # Verify the function logic
        assert "if (legCount === 1) return 'Single bet'" in app_js_content

    def test_multi_leg_uses_parlay_terminology(self, app_js_content):
        """getLegCountText uses '{N}-leg parlay' for 2+ legs."""
        assert "return legCount + '-leg parlay'" in app_js_content

    def test_get_bet_term_returns_bet_for_single(self, app_js_content):
        """getBetTerm returns 'bet' for single leg."""
        assert "if (legCount === 1) return 'bet'" in app_js_content

    def test_get_bet_term_returns_parlay_for_multi(self, app_js_content):
        """getBetTerm returns 'parlay' for multiple legs."""
        assert "return 'parlay'" in app_js_content

    def test_no_parlay_in_single_bet_header(self, app_js_content):
        """Single bet header text does not mention parlay."""
        # The 'Single bet' text should be returned for 1 leg, not any parlay mention
        assert "'Single bet'" in app_js_content

    def test_empty_slip_terminology(self, app_js_content):
        """Empty slip uses 'Empty slip' or 'Add your first leg' - no parlay."""
        assert "'Empty slip'" in app_js_content
        assert "'Add your first leg to begin'" in app_js_content


class TestChunk3VisibilityMatrixSync:
    """
    Chunk 3: Ensure _getVisibilityMatrix export is in sync with renderStateUI.
    """

    def test_visibility_matrix_empty_header(self, app_js_content):
        """Visibility matrix EMPTY header matches renderStateUI."""
        # Both should use 'Add your first leg to begin' for EMPTY
        matrix_text = "headerText: state === 'EMPTY' ? 'Add your first leg to begin'"
        assert matrix_text in app_js_content

    def test_visibility_matrix_complexity_includes_max_parlay(self, app_js_content):
        """Visibility matrix shows complexity banner for both ELEVATED and MAX."""
        assert "complexityBannerVisible: state === 'ELEVATED_PARLAY' || state === 'MAX_PARLAY'" in app_js_content
