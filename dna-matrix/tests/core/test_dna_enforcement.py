# tests/core/test_dna_enforcement.py
"""
Tests for DNA Enforcement Engine.

Tests the profile-driven risk constraints that can only reduce risk (never upgrade).
"""
from uuid import uuid4

import pytest

from core.dna_enforcement import (
    VIOLATION_FRAGILITY_OVER_TOLERANCE,
    VIOLATION_LIVE_BETS_NOT_ALLOWED,
    VIOLATION_MAX_LEGS_EXCEEDED,
    VIOLATION_PROPS_NOT_ALLOWED,
    BehaviorProfile,
    DNAProfile,
    EnforcementResult,
    RiskProfile,
    apply_dna_enforcement,
    check_dna_compatible,
    has_live_bet,
    has_player_prop,
)
from core.models.leading_light import (
    BetBlock,
    BetType,
    ContextModifier,
    ContextModifiers,
    DNAEnforcement as DNAEnforcementModel,
    ParlayMetrics,
    ParlayState,
)


# =============================================================================
# Fixtures
# =============================================================================


@pytest.fixture
def zero_modifiers() -> ContextModifiers:
    """Create context modifiers with all zeros."""
    zero_mod = ContextModifier(applied=False, delta=0.0, reason=None)
    return ContextModifiers(
        weather=zero_mod,
        injury=zero_mod,
        trade=zero_mod,
        role=zero_mod,
    )


@pytest.fixture
def default_profile() -> DNAProfile:
    """Create a default DNA profile for testing."""
    return DNAProfile(
        risk=RiskProfile(
            tolerance=50,
            max_parlay_legs=4,
            max_stake_pct=0.10,
            avoid_live_bets=False,
            avoid_props=False,
        ),
        behavior=BehaviorProfile(discipline=0.5),
    )


@pytest.fixture
def conservative_profile() -> DNAProfile:
    """Create a conservative DNA profile."""
    return DNAProfile(
        risk=RiskProfile(
            tolerance=30,
            max_parlay_legs=2,
            max_stake_pct=0.05,
            avoid_live_bets=True,
            avoid_props=True,
        ),
        behavior=BehaviorProfile(discipline=0.8),
    )


def make_block(
    base_fragility: float,
    modifiers: ContextModifiers,
    bet_type: BetType = BetType.SPREAD,
    correlation_tags: tuple = (),
    player_id: str | None = None,
) -> BetBlock:
    """Helper to create a BetBlock."""
    return BetBlock(
        block_id=uuid4(),
        sport="NFL",
        game_id=f"game-{uuid4().hex[:8]}",
        bet_type=bet_type,
        selection="Test Selection",
        base_fragility=base_fragility,
        context_modifiers=modifiers,
        correlation_tags=correlation_tags,
        effective_fragility=base_fragility + modifiers.total_delta(),
        player_id=player_id,
        team_id=None,
    )


def make_parlay_state(
    blocks: list[BetBlock],
    final_fragility: float,
) -> ParlayState:
    """Helper to create a ParlayState with specific final fragility."""
    # Create a default DNAEnforcement for testing
    default_enforcement = DNAEnforcementModel(
        max_legs=10,
        fragility_tolerance=100.0,
        stake_cap=1000.0,
        violations=(),
    )
    return ParlayState(
        parlay_id=uuid4(),
        blocks=tuple(blocks),
        correlations=(),
        metrics=ParlayMetrics(
            raw_fragility=final_fragility,
            leg_penalty=8.0 * (len(blocks) ** 1.5) if blocks else 0.0,
            correlation_penalty=0.0,
            correlation_multiplier=1.0,
            final_fragility=final_fragility,
        ),
        dna_enforcement=default_enforcement,
    )


# =============================================================================
# DNAProfile Tests
# =============================================================================


class TestRiskProfile:
    """Tests for RiskProfile validation."""

    def test_valid_creation(self):
        """Valid profile creates successfully."""
        profile = RiskProfile(
            tolerance=50,
            max_parlay_legs=4,
            max_stake_pct=0.10,
            avoid_live_bets=False,
            avoid_props=False,
        )
        assert profile.tolerance == 50
        assert profile.max_parlay_legs == 4
        assert profile.max_stake_pct == 0.10
        assert profile.avoid_live_bets is False
        assert profile.avoid_props is False

    def test_tolerance_bounds(self):
        """Tolerance must be 0-100."""
        with pytest.raises(ValueError, match="tolerance must be between"):
            RiskProfile(
                tolerance=-1,
                max_parlay_legs=4,
                max_stake_pct=0.10,
                avoid_live_bets=False,
                avoid_props=False,
            )
        with pytest.raises(ValueError, match="tolerance must be between"):
            RiskProfile(
                tolerance=101,
                max_parlay_legs=4,
                max_stake_pct=0.10,
                avoid_live_bets=False,
                avoid_props=False,
            )

    def test_tolerance_edge_values(self):
        """Tolerance at edges (0 and 100) should be valid."""
        profile_min = RiskProfile(
            tolerance=0,
            max_parlay_legs=4,
            max_stake_pct=0.10,
            avoid_live_bets=False,
            avoid_props=False,
        )
        assert profile_min.tolerance == 0

        profile_max = RiskProfile(
            tolerance=100,
            max_parlay_legs=4,
            max_stake_pct=0.10,
            avoid_live_bets=False,
            avoid_props=False,
        )
        assert profile_max.tolerance == 100

    def test_max_parlay_legs_must_be_positive(self):
        """Max parlay legs must be at least 1."""
        with pytest.raises(ValueError, match="max_parlay_legs must be at least 1"):
            RiskProfile(
                tolerance=50,
                max_parlay_legs=0,
                max_stake_pct=0.10,
                avoid_live_bets=False,
                avoid_props=False,
            )

    def test_max_stake_pct_bounds(self):
        """Max stake pct must be 0.01-0.25."""
        with pytest.raises(ValueError, match="max_stake_pct must be between"):
            RiskProfile(
                tolerance=50,
                max_parlay_legs=4,
                max_stake_pct=0.005,  # Too low
                avoid_live_bets=False,
                avoid_props=False,
            )
        with pytest.raises(ValueError, match="max_stake_pct must be between"):
            RiskProfile(
                tolerance=50,
                max_parlay_legs=4,
                max_stake_pct=0.30,  # Too high
                avoid_live_bets=False,
                avoid_props=False,
            )

    def test_max_stake_pct_edge_values(self):
        """Max stake pct at edges (0.01 and 0.25) should be valid."""
        profile_min = RiskProfile(
            tolerance=50,
            max_parlay_legs=4,
            max_stake_pct=0.01,
            avoid_live_bets=False,
            avoid_props=False,
        )
        assert profile_min.max_stake_pct == 0.01

        profile_max = RiskProfile(
            tolerance=50,
            max_parlay_legs=4,
            max_stake_pct=0.25,
            avoid_live_bets=False,
            avoid_props=False,
        )
        assert profile_max.max_stake_pct == 0.25


class TestBehaviorProfile:
    """Tests for BehaviorProfile validation."""

    def test_valid_creation(self):
        """Valid profile creates successfully."""
        profile = BehaviorProfile(discipline=0.7)
        assert profile.discipline == 0.7

    def test_discipline_bounds(self):
        """Discipline must be 0.0-1.0."""
        with pytest.raises(ValueError, match="discipline must be between"):
            BehaviorProfile(discipline=-0.1)
        with pytest.raises(ValueError, match="discipline must be between"):
            BehaviorProfile(discipline=1.1)

    def test_discipline_edge_values(self):
        """Discipline at edges (0.0 and 1.0) should be valid."""
        profile_min = BehaviorProfile(discipline=0.0)
        assert profile_min.discipline == 0.0

        profile_max = BehaviorProfile(discipline=1.0)
        assert profile_max.discipline == 1.0


class TestDNAProfile:
    """Tests for DNAProfile."""

    def test_from_dict(self):
        """Create profile from dictionary."""
        data = {
            "risk": {
                "tolerance": 40,
                "max_parlay_legs": 3,
                "max_stake_pct": 0.08,
                "avoid_live_bets": True,
                "avoid_props": False,
            },
            "behavior": {
                "discipline": 0.6,
            },
        }
        profile = DNAProfile.from_dict(data)

        assert profile.risk.tolerance == 40
        assert profile.risk.max_parlay_legs == 3
        assert profile.risk.max_stake_pct == 0.08
        assert profile.risk.avoid_live_bets is True
        assert profile.risk.avoid_props is False
        assert profile.behavior.discipline == 0.6

    def test_to_dict(self, default_profile: DNAProfile):
        """Convert profile to dictionary."""
        data = default_profile.to_dict()

        assert data["risk"]["tolerance"] == 50
        assert data["risk"]["max_parlay_legs"] == 4
        assert data["risk"]["max_stake_pct"] == 0.10
        assert data["risk"]["avoid_live_bets"] is False
        assert data["risk"]["avoid_props"] is False
        assert data["behavior"]["discipline"] == 0.5

    def test_roundtrip(self, default_profile: DNAProfile):
        """Dict roundtrip preserves values."""
        data = default_profile.to_dict()
        restored = DNAProfile.from_dict(data)

        assert restored.risk.tolerance == default_profile.risk.tolerance
        assert restored.risk.max_parlay_legs == default_profile.risk.max_parlay_legs
        assert restored.risk.max_stake_pct == default_profile.risk.max_stake_pct
        assert restored.behavior.discipline == default_profile.behavior.discipline


# =============================================================================
# Detection Function Tests
# =============================================================================


class TestHasPlayerProp:
    """Tests for has_player_prop detection."""

    def test_no_props(self, zero_modifiers: ContextModifiers):
        """No player props returns False."""
        blocks = [
            make_block(10.0, zero_modifiers, bet_type=BetType.SPREAD),
            make_block(10.0, zero_modifiers, bet_type=BetType.ML),
        ]
        assert has_player_prop(blocks) is False

    def test_has_prop(self, zero_modifiers: ContextModifiers):
        """Player prop present returns True."""
        blocks = [
            make_block(10.0, zero_modifiers, bet_type=BetType.SPREAD),
            make_block(10.0, zero_modifiers, bet_type=BetType.PLAYER_PROP),
        ]
        assert has_player_prop(blocks) is True

    def test_empty_blocks(self):
        """Empty blocks returns False."""
        assert has_player_prop([]) is False


class TestHasLiveBet:
    """Tests for has_live_bet detection."""

    def test_no_live(self, zero_modifiers: ContextModifiers):
        """No live bets returns False."""
        blocks = [
            make_block(10.0, zero_modifiers, correlation_tags=()),
            make_block(10.0, zero_modifiers, correlation_tags=("team_game",)),
        ]
        assert has_live_bet(blocks) is False

    def test_has_live(self, zero_modifiers: ContextModifiers):
        """Live bet present returns True."""
        blocks = [
            make_block(10.0, zero_modifiers, correlation_tags=()),
            make_block(10.0, zero_modifiers, correlation_tags=("live",)),
        ]
        assert has_live_bet(blocks) is True

    def test_live_among_other_tags(self, zero_modifiers: ContextModifiers):
        """Live tag among other tags is detected."""
        blocks = [
            make_block(10.0, zero_modifiers, correlation_tags=("team_game", "live", "pace")),
        ]
        assert has_live_bet(blocks) is True

    def test_empty_blocks(self):
        """Empty blocks returns False."""
        assert has_live_bet([]) is False


# =============================================================================
# Required Test Vectors
# =============================================================================


class TestRequiredVectors:
    """Required test vectors from specification."""

    def test_vector_a_fragility_over_tolerance_reduces_stake(
        self, zero_modifiers: ContextModifiers
    ):
        """
        Test A: Fragility over tolerance reduces stake

        - bankroll=1000
        - risk.max_stake_pct=0.10
        - risk.tolerance=30
        - finalFragility=60

        Expected:
        - violation includes "fragility_over_tolerance"
        - base cap = 100
        - recommendedStake = 100 * (30/60) = 50
        """
        profile = DNAProfile(
            risk=RiskProfile(
                tolerance=30,
                max_parlay_legs=4,
                max_stake_pct=0.10,
                avoid_live_bets=False,
                avoid_props=False,
            ),
            behavior=BehaviorProfile(discipline=0.5),
        )

        block = make_block(10.0, zero_modifiers)
        parlay = make_parlay_state([block], final_fragility=60.0)

        result = apply_dna_enforcement(parlay, profile, bankroll=1000.0)

        assert VIOLATION_FRAGILITY_OVER_TOLERANCE in result.dna_enforcement.violations
        assert result.base_stake_cap == 100.0
        assert result.recommended_stake == 50.0  # 100 * (30/60)

    def test_vector_b_max_legs_violation(self, zero_modifiers: ContextModifiers):
        """
        Test B: Max legs violation

        - max_parlay_legs=2
        - legs=4

        Expected:
        - violation includes "max_legs_exceeded"
        """
        profile = DNAProfile(
            risk=RiskProfile(
                tolerance=80,
                max_parlay_legs=2,
                max_stake_pct=0.10,
                avoid_live_bets=False,
                avoid_props=False,
            ),
            behavior=BehaviorProfile(discipline=0.5),
        )

        blocks = [make_block(10.0, zero_modifiers) for _ in range(4)]
        parlay = make_parlay_state(blocks, final_fragility=50.0)

        result = apply_dna_enforcement(parlay, profile, bankroll=1000.0)

        assert VIOLATION_MAX_LEGS_EXCEEDED in result.dna_enforcement.violations

    def test_vector_c_avoid_props(self, zero_modifiers: ContextModifiers):
        """
        Test C: Avoid props

        - avoid_props=true
        - includes player_prop

        Expected:
        - violation includes "props_not_allowed"
        """
        profile = DNAProfile(
            risk=RiskProfile(
                tolerance=80,
                max_parlay_legs=4,
                max_stake_pct=0.10,
                avoid_live_bets=False,
                avoid_props=True,
            ),
            behavior=BehaviorProfile(discipline=0.5),
        )

        blocks = [
            make_block(10.0, zero_modifiers, bet_type=BetType.SPREAD),
            make_block(10.0, zero_modifiers, bet_type=BetType.PLAYER_PROP),
        ]
        parlay = make_parlay_state(blocks, final_fragility=30.0)

        result = apply_dna_enforcement(parlay, profile, bankroll=1000.0)

        assert VIOLATION_PROPS_NOT_ALLOWED in result.dna_enforcement.violations

    def test_vector_c_avoid_props_dna_compatible(
        self, zero_modifiers: ContextModifiers
    ):
        """
        Test C (continued): dnaCompatible false for suggestions that add props
        """
        profile = DNAProfile(
            risk=RiskProfile(
                tolerance=80,
                max_parlay_legs=4,
                max_stake_pct=0.10,
                avoid_live_bets=False,
                avoid_props=True,
            ),
            behavior=BehaviorProfile(discipline=0.5),
        )

        # Non-prop candidate should be compatible
        spread_candidate = make_block(10.0, zero_modifiers, bet_type=BetType.SPREAD)
        assert check_dna_compatible(spread_candidate, current_legs=1, dna_profile=profile) is True

        # Prop candidate should NOT be compatible
        prop_candidate = make_block(10.0, zero_modifiers, bet_type=BetType.PLAYER_PROP)
        assert check_dna_compatible(prop_candidate, current_legs=1, dna_profile=profile) is False

    def test_vector_d_combined_violations(self, zero_modifiers: ContextModifiers):
        """
        Test D: Combined violations

        - tolerance exceeded + max legs exceeded + avoid props

        Expected:
        - all relevant violations present
        - recommendedStake respects cap and reduction
        """
        profile = DNAProfile(
            risk=RiskProfile(
                tolerance=30,  # tolerance exceeded (fragility=60)
                max_parlay_legs=2,  # max legs exceeded (4 legs)
                max_stake_pct=0.10,
                avoid_live_bets=True,  # live bets not allowed
                avoid_props=True,  # props not allowed
            ),
            behavior=BehaviorProfile(discipline=0.5),
        )

        blocks = [
            make_block(10.0, zero_modifiers, bet_type=BetType.SPREAD),
            make_block(10.0, zero_modifiers, bet_type=BetType.PLAYER_PROP),
            make_block(10.0, zero_modifiers, correlation_tags=("live",)),
            make_block(10.0, zero_modifiers, bet_type=BetType.ML),
        ]
        parlay = make_parlay_state(blocks, final_fragility=60.0)

        result = apply_dna_enforcement(parlay, profile, bankroll=1000.0)

        # All violations should be present
        assert VIOLATION_FRAGILITY_OVER_TOLERANCE in result.dna_enforcement.violations
        assert VIOLATION_MAX_LEGS_EXCEEDED in result.dna_enforcement.violations
        assert VIOLATION_PROPS_NOT_ALLOWED in result.dna_enforcement.violations
        assert VIOLATION_LIVE_BETS_NOT_ALLOWED in result.dna_enforcement.violations

        # Stake should be reduced due to fragility over tolerance
        # base_cap = 1000 * 0.10 = 100
        # reduction = 30 / 60 = 0.5
        # recommended = 100 * 0.5 = 50
        assert result.base_stake_cap == 100.0
        assert result.recommended_stake == 50.0


# =============================================================================
# apply_dna_enforcement Tests
# =============================================================================


class TestApplyDnaEnforcement:
    """Tests for apply_dna_enforcement function."""

    def test_no_violations(
        self, default_profile: DNAProfile, zero_modifiers: ContextModifiers
    ):
        """Parlay within all limits has no violations."""
        blocks = [make_block(10.0, zero_modifiers)]
        parlay = make_parlay_state(blocks, final_fragility=30.0)

        result = apply_dna_enforcement(parlay, default_profile, bankroll=1000.0)

        assert len(result.dna_enforcement.violations) == 0
        assert result.recommended_stake == result.base_stake_cap

    def test_stake_cap_computed_correctly(
        self, default_profile: DNAProfile, zero_modifiers: ContextModifiers
    ):
        """Stake cap is bankroll * max_stake_pct."""
        blocks = [make_block(10.0, zero_modifiers)]
        parlay = make_parlay_state(blocks, final_fragility=30.0)

        result = apply_dna_enforcement(parlay, default_profile, bankroll=2000.0)

        # default_profile has max_stake_pct = 0.10
        assert result.base_stake_cap == 200.0

    def test_recommended_stake_never_exceeds_cap(
        self, zero_modifiers: ContextModifiers
    ):
        """Recommended stake is always <= base_stake_cap."""
        profile = DNAProfile(
            risk=RiskProfile(
                tolerance=100,  # Very high tolerance
                max_parlay_legs=10,
                max_stake_pct=0.05,
                avoid_live_bets=False,
                avoid_props=False,
            ),
            behavior=BehaviorProfile(discipline=0.5),
        )

        blocks = [make_block(10.0, zero_modifiers)]
        parlay = make_parlay_state(blocks, final_fragility=30.0)

        result = apply_dna_enforcement(parlay, profile, bankroll=1000.0)

        assert result.recommended_stake <= result.base_stake_cap

    def test_recommended_stake_non_negative(
        self, zero_modifiers: ContextModifiers
    ):
        """Recommended stake is always >= 0."""
        profile = DNAProfile(
            risk=RiskProfile(
                tolerance=1,  # Very low tolerance
                max_parlay_legs=10,
                max_stake_pct=0.10,
                avoid_live_bets=False,
                avoid_props=False,
            ),
            behavior=BehaviorProfile(discipline=0.5),
        )

        blocks = [make_block(10.0, zero_modifiers)]
        parlay = make_parlay_state(blocks, final_fragility=100.0)

        result = apply_dna_enforcement(parlay, profile, bankroll=1000.0)

        assert result.recommended_stake >= 0

    def test_negative_bankroll_rejected(
        self, default_profile: DNAProfile, zero_modifiers: ContextModifiers
    ):
        """Negative bankroll raises error."""
        blocks = [make_block(10.0, zero_modifiers)]
        parlay = make_parlay_state(blocks, final_fragility=30.0)

        with pytest.raises(ValueError, match="bankroll must be non-negative"):
            apply_dna_enforcement(parlay, default_profile, bankroll=-100.0)

    def test_zero_bankroll(
        self, default_profile: DNAProfile, zero_modifiers: ContextModifiers
    ):
        """Zero bankroll produces zero stake."""
        blocks = [make_block(10.0, zero_modifiers)]
        parlay = make_parlay_state(blocks, final_fragility=30.0)

        result = apply_dna_enforcement(parlay, default_profile, bankroll=0.0)

        assert result.base_stake_cap == 0.0
        assert result.recommended_stake == 0.0

    def test_empty_parlay(
        self, default_profile: DNAProfile
    ):
        """Empty parlay has no violations."""
        parlay = make_parlay_state([], final_fragility=0.0)

        result = apply_dna_enforcement(parlay, default_profile, bankroll=1000.0)

        assert len(result.dna_enforcement.violations) == 0

    def test_dna_enforcement_values_set(
        self, default_profile: DNAProfile, zero_modifiers: ContextModifiers
    ):
        """DNAEnforcement has correct values from profile."""
        blocks = [make_block(10.0, zero_modifiers)]
        parlay = make_parlay_state(blocks, final_fragility=30.0)

        result = apply_dna_enforcement(parlay, default_profile, bankroll=1000.0)

        assert result.dna_enforcement.max_legs == default_profile.risk.max_parlay_legs
        assert result.dna_enforcement.fragility_tolerance == default_profile.risk.tolerance
        assert result.dna_enforcement.stake_cap == 100.0  # 1000 * 0.10


# =============================================================================
# check_dna_compatible Tests
# =============================================================================


class TestCheckDnaCompatible:
    """Tests for check_dna_compatible function."""

    def test_compatible_within_all_limits(
        self, default_profile: DNAProfile, zero_modifiers: ContextModifiers
    ):
        """Candidate within all limits is compatible."""
        candidate = make_block(10.0, zero_modifiers, bet_type=BetType.SPREAD)

        result = check_dna_compatible(candidate, current_legs=2, dna_profile=default_profile)

        assert result is True

    def test_incompatible_exceeds_max_legs(
        self, zero_modifiers: ContextModifiers
    ):
        """Candidate that would exceed max legs is incompatible."""
        profile = DNAProfile(
            risk=RiskProfile(
                tolerance=80,
                max_parlay_legs=3,
                max_stake_pct=0.10,
                avoid_live_bets=False,
                avoid_props=False,
            ),
            behavior=BehaviorProfile(discipline=0.5),
        )

        candidate = make_block(10.0, zero_modifiers)

        # Adding to 3 legs would make 4, exceeding max of 3
        result = check_dna_compatible(candidate, current_legs=3, dna_profile=profile)

        assert result is False

    def test_incompatible_prop_when_avoided(
        self, zero_modifiers: ContextModifiers
    ):
        """Player prop is incompatible when avoid_props is true."""
        profile = DNAProfile(
            risk=RiskProfile(
                tolerance=80,
                max_parlay_legs=10,
                max_stake_pct=0.10,
                avoid_live_bets=False,
                avoid_props=True,
            ),
            behavior=BehaviorProfile(discipline=0.5),
        )

        candidate = make_block(10.0, zero_modifiers, bet_type=BetType.PLAYER_PROP)

        result = check_dna_compatible(candidate, current_legs=1, dna_profile=profile)

        assert result is False

    def test_incompatible_live_when_avoided(
        self, zero_modifiers: ContextModifiers
    ):
        """Live bet is incompatible when avoid_live_bets is true."""
        profile = DNAProfile(
            risk=RiskProfile(
                tolerance=80,
                max_parlay_legs=10,
                max_stake_pct=0.10,
                avoid_live_bets=True,
                avoid_props=False,
            ),
            behavior=BehaviorProfile(discipline=0.5),
        )

        candidate = make_block(10.0, zero_modifiers, correlation_tags=("live",))

        result = check_dna_compatible(candidate, current_legs=1, dna_profile=profile)

        assert result is False

    def test_compatible_prop_when_allowed(
        self, default_profile: DNAProfile, zero_modifiers: ContextModifiers
    ):
        """Player prop is compatible when avoid_props is false."""
        candidate = make_block(10.0, zero_modifiers, bet_type=BetType.PLAYER_PROP)

        result = check_dna_compatible(candidate, current_legs=1, dna_profile=default_profile)

        assert result is True

    def test_compatible_live_when_allowed(
        self, default_profile: DNAProfile, zero_modifiers: ContextModifiers
    ):
        """Live bet is compatible when avoid_live_bets is false."""
        candidate = make_block(10.0, zero_modifiers, correlation_tags=("live",))

        result = check_dna_compatible(candidate, current_legs=1, dna_profile=default_profile)

        assert result is True


# =============================================================================
# Avoid Live Bets Tests
# =============================================================================


class TestAvoidLiveBets:
    """Tests for live bet detection and enforcement."""

    def test_live_bet_violation(self, zero_modifiers: ContextModifiers):
        """Live bet triggers violation when avoid_live_bets is true."""
        profile = DNAProfile(
            risk=RiskProfile(
                tolerance=80,
                max_parlay_legs=4,
                max_stake_pct=0.10,
                avoid_live_bets=True,
                avoid_props=False,
            ),
            behavior=BehaviorProfile(discipline=0.5),
        )

        blocks = [
            make_block(10.0, zero_modifiers),
            make_block(10.0, zero_modifiers, correlation_tags=("live",)),
        ]
        parlay = make_parlay_state(blocks, final_fragility=30.0)

        result = apply_dna_enforcement(parlay, profile, bankroll=1000.0)

        assert VIOLATION_LIVE_BETS_NOT_ALLOWED in result.dna_enforcement.violations

    def test_no_violation_when_allowed(self, zero_modifiers: ContextModifiers):
        """Live bet does not trigger violation when avoid_live_bets is false."""
        profile = DNAProfile(
            risk=RiskProfile(
                tolerance=80,
                max_parlay_legs=4,
                max_stake_pct=0.10,
                avoid_live_bets=False,  # Live bets allowed
                avoid_props=False,
            ),
            behavior=BehaviorProfile(discipline=0.5),
        )

        blocks = [
            make_block(10.0, zero_modifiers),
            make_block(10.0, zero_modifiers, correlation_tags=("live",)),
        ]
        parlay = make_parlay_state(blocks, final_fragility=30.0)

        result = apply_dna_enforcement(parlay, profile, bankroll=1000.0)

        assert VIOLATION_LIVE_BETS_NOT_ALLOWED not in result.dna_enforcement.violations


# =============================================================================
# Edge Cases
# =============================================================================


class TestEdgeCases:
    """Edge case tests."""

    def test_fragility_at_tolerance_boundary(self, zero_modifiers: ContextModifiers):
        """Fragility exactly at tolerance does not trigger violation."""
        profile = DNAProfile(
            risk=RiskProfile(
                tolerance=50,
                max_parlay_legs=4,
                max_stake_pct=0.10,
                avoid_live_bets=False,
                avoid_props=False,
            ),
            behavior=BehaviorProfile(discipline=0.5),
        )

        blocks = [make_block(10.0, zero_modifiers)]
        parlay = make_parlay_state(blocks, final_fragility=50.0)  # Exactly at tolerance

        result = apply_dna_enforcement(parlay, profile, bankroll=1000.0)

        assert VIOLATION_FRAGILITY_OVER_TOLERANCE not in result.dna_enforcement.violations

    def test_fragility_just_over_tolerance(self, zero_modifiers: ContextModifiers):
        """Fragility just over tolerance triggers violation."""
        profile = DNAProfile(
            risk=RiskProfile(
                tolerance=50,
                max_parlay_legs=4,
                max_stake_pct=0.10,
                avoid_live_bets=False,
                avoid_props=False,
            ),
            behavior=BehaviorProfile(discipline=0.5),
        )

        blocks = [make_block(10.0, zero_modifiers)]
        parlay = make_parlay_state(blocks, final_fragility=50.01)  # Just over

        result = apply_dna_enforcement(parlay, profile, bankroll=1000.0)

        assert VIOLATION_FRAGILITY_OVER_TOLERANCE in result.dna_enforcement.violations

    def test_legs_at_max_boundary(self, zero_modifiers: ContextModifiers):
        """Legs exactly at max does not trigger violation."""
        profile = DNAProfile(
            risk=RiskProfile(
                tolerance=80,
                max_parlay_legs=4,
                max_stake_pct=0.10,
                avoid_live_bets=False,
                avoid_props=False,
            ),
            behavior=BehaviorProfile(discipline=0.5),
        )

        blocks = [make_block(10.0, zero_modifiers) for _ in range(4)]
        parlay = make_parlay_state(blocks, final_fragility=30.0)

        result = apply_dna_enforcement(parlay, profile, bankroll=1000.0)

        assert VIOLATION_MAX_LEGS_EXCEEDED not in result.dna_enforcement.violations

    def test_legs_just_over_max(self, zero_modifiers: ContextModifiers):
        """Legs just over max triggers violation."""
        profile = DNAProfile(
            risk=RiskProfile(
                tolerance=80,
                max_parlay_legs=4,
                max_stake_pct=0.10,
                avoid_live_bets=False,
                avoid_props=False,
            ),
            behavior=BehaviorProfile(discipline=0.5),
        )

        blocks = [make_block(10.0, zero_modifiers) for _ in range(5)]
        parlay = make_parlay_state(blocks, final_fragility=30.0)

        result = apply_dna_enforcement(parlay, profile, bankroll=1000.0)

        assert VIOLATION_MAX_LEGS_EXCEEDED in result.dna_enforcement.violations

    def test_check_compatible_at_max_legs(self, zero_modifiers: ContextModifiers):
        """Candidate at exactly max legs boundary is compatible."""
        profile = DNAProfile(
            risk=RiskProfile(
                tolerance=80,
                max_parlay_legs=4,
                max_stake_pct=0.10,
                avoid_live_bets=False,
                avoid_props=False,
            ),
            behavior=BehaviorProfile(discipline=0.5),
        )

        candidate = make_block(10.0, zero_modifiers)

        # Adding to 3 legs makes 4, which equals max
        result = check_dna_compatible(candidate, current_legs=3, dna_profile=profile)

        assert result is True

    def test_zero_final_fragility_with_tolerance_check(
        self, zero_modifiers: ContextModifiers
    ):
        """Zero final fragility does not cause division by zero."""
        profile = DNAProfile(
            risk=RiskProfile(
                tolerance=0,  # Zero tolerance
                max_parlay_legs=4,
                max_stake_pct=0.10,
                avoid_live_bets=False,
                avoid_props=False,
            ),
            behavior=BehaviorProfile(discipline=0.5),
        )

        parlay = make_parlay_state([], final_fragility=0.0)

        result = apply_dna_enforcement(parlay, profile, bankroll=1000.0)

        # Should not raise and should have no fragility violation (0 is not > 0)
        assert VIOLATION_FRAGILITY_OVER_TOLERANCE not in result.dna_enforcement.violations
