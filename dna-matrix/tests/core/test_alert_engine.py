# tests/core/test_alert_engine.py
"""
Tests for Alert Engine.

Tests alert generation from EvaluationResponse changes.
"""
import pytest
from uuid import uuid4

from core.alert_engine import (
    Alert,
    AlertType,
    AlertSeverity,
    compute_alerts,
    has_high_severity_alerts,
    get_alerts_by_type,
    get_alerts_by_severity,
    FRAGILITY_DELTA_THRESHOLD,
    CORRELATION_PENALTY_DELTA_THRESHOLD,
    OPPORTUNITY_MAX_FRAGILITY,
    STAKE_REDUCTION_THRESHOLD_PCT,
    _inductor_escalated,
    _inductor_deescalated,
)
from core.evaluation import (
    EvaluationResponse,
    InductorInfo,
    MetricsInfo,
    DNAInfo,
    Recommendation,
    RecommendationAction,
)
from core.risk_inductor import RiskInductor


# =============================================================================
# Fixtures
# =============================================================================


def _make_response(
    inductor_level: RiskInductor = RiskInductor.STABLE,
    final_fragility: float = 25.0,
    raw_fragility: float = 25.0,
    correlation_penalty: float = 0.0,
    correlation_multiplier: float = 1.0,
    violations: tuple = (),
    recommended_stake: float = None,
    base_stake_cap: float = None,
) -> EvaluationResponse:
    """Create a test EvaluationResponse."""
    return EvaluationResponse(
        parlay_id=uuid4(),
        inductor=InductorInfo(
            level=inductor_level,
            explanation="Test explanation",
        ),
        metrics=MetricsInfo(
            raw_fragility=raw_fragility,
            final_fragility=final_fragility,
            leg_penalty=5.0,
            correlation_penalty=correlation_penalty,
            correlation_multiplier=correlation_multiplier,
        ),
        correlations=(),
        dna=DNAInfo(
            violations=violations,
            base_stake_cap=base_stake_cap,
            recommended_stake=recommended_stake,
            max_legs=4,
            fragility_tolerance=50.0,
        ),
        recommendation=Recommendation(
            action=RecommendationAction.ACCEPT,
            reason="Test reason",
        ),
        suggestions=None,
    )


@pytest.fixture
def stable_response():
    """Stable, low-fragility response."""
    return _make_response(
        inductor_level=RiskInductor.STABLE,
        final_fragility=25.0,
    )


@pytest.fixture
def loaded_response():
    """Loaded response."""
    return _make_response(
        inductor_level=RiskInductor.LOADED,
        final_fragility=40.0,
    )


@pytest.fixture
def tense_response():
    """Tense response."""
    return _make_response(
        inductor_level=RiskInductor.TENSE,
        final_fragility=65.0,
    )


@pytest.fixture
def critical_response():
    """Critical response."""
    return _make_response(
        inductor_level=RiskInductor.CRITICAL,
        final_fragility=85.0,
        correlation_penalty=25.0,
        correlation_multiplier=1.3,
    )


# =============================================================================
# Required Test Vectors
# =============================================================================


class TestRequiredVectors:
    """Required test vectors from specification."""

    def test_vector_a_no_spam(self):
        """
        Test A: No spam.

        prev == new exactly
        Expected: alerts=[]
        """
        response = _make_response(
            inductor_level=RiskInductor.LOADED,
            final_fragility=40.0,
            correlation_penalty=8.0,
            recommended_stake=100.0,
        )

        # Same response twice
        alerts = compute_alerts(response, response)

        assert alerts == []

    def test_vector_b_opportunity(self):
        """
        Test B: Opportunity.

        prev TENSE, new LOADED with finalFragility 40, no DNA violations
        Expected: one OPPORTUNITY alert
        """
        prev = _make_response(
            inductor_level=RiskInductor.TENSE,
            final_fragility=65.0,
        )
        new = _make_response(
            inductor_level=RiskInductor.LOADED,
            final_fragility=40.0,
            violations=(),
        )

        alerts = compute_alerts(prev, new)

        opportunity_alerts = get_alerts_by_type(alerts, AlertType.OPPORTUNITY)
        assert len(opportunity_alerts) == 1
        assert opportunity_alerts[0].severity == AlertSeverity.LOW
        assert "opportunity" in opportunity_alerts[0].message.lower()

    def test_vector_c_risk_spike(self):
        """
        Test C: Risk spike.

        prev final=40, new final=55
        Expected: RISK_SPIKE alert
        """
        prev = _make_response(
            inductor_level=RiskInductor.LOADED,
            final_fragility=40.0,
        )
        new = _make_response(
            inductor_level=RiskInductor.TENSE,
            final_fragility=55.0,
        )

        alerts = compute_alerts(prev, new)

        risk_alerts = get_alerts_by_type(alerts, AlertType.RISK_SPIKE)
        assert len(risk_alerts) == 1
        assert risk_alerts[0].severity == AlertSeverity.HIGH

    def test_vector_d_correlation_spike(self):
        """
        Test D: Correlation spike.

        prev corrPenalty=8, new corrPenalty=20
        Expected: CORRELATION_SPIKE alert
        """
        prev = _make_response(
            inductor_level=RiskInductor.LOADED,
            final_fragility=45.0,
            correlation_penalty=8.0,
            correlation_multiplier=1.0,
        )
        new = _make_response(
            inductor_level=RiskInductor.LOADED,
            final_fragility=50.0,
            correlation_penalty=20.0,
            correlation_multiplier=1.15,
        )

        alerts = compute_alerts(prev, new)

        correlation_alerts = get_alerts_by_type(alerts, AlertType.CORRELATION_SPIKE)
        assert len(correlation_alerts) == 1
        assert correlation_alerts[0].severity == AlertSeverity.HIGH

    def test_vector_e_dna_enforced(self):
        """
        Test E: DNA enforced.

        prev recommendedStake=100, new recommendedStake=70
        Expected: DNA_ENFORCED alert
        """
        prev = _make_response(
            inductor_level=RiskInductor.LOADED,
            final_fragility=45.0,
            recommended_stake=100.0,
        )
        new = _make_response(
            inductor_level=RiskInductor.LOADED,
            final_fragility=45.0,
            recommended_stake=70.0,
        )

        alerts = compute_alerts(prev, new)

        dna_alerts = get_alerts_by_type(alerts, AlertType.DNA_ENFORCED)
        assert len(dna_alerts) == 1
        assert "stake" in dna_alerts[0].message.lower()


# =============================================================================
# OPPORTUNITY Alert Tests
# =============================================================================


class TestOpportunityAlert:
    """Tests for OPPORTUNITY alert."""

    def test_opportunity_on_first_evaluation(self):
        """OPPORTUNITY triggers on first favorable evaluation."""
        new = _make_response(
            inductor_level=RiskInductor.STABLE,
            final_fragility=30.0,
            violations=(),
        )

        alerts = compute_alerts(None, new)

        opportunity_alerts = get_alerts_by_type(alerts, AlertType.OPPORTUNITY)
        assert len(opportunity_alerts) == 1
        assert "initial" in opportunity_alerts[0].details["reason"].lower()

    def test_opportunity_on_deescalation(self):
        """OPPORTUNITY triggers when de-escalating from TENSE/CRITICAL."""
        prev = _make_response(
            inductor_level=RiskInductor.CRITICAL,
            final_fragility=85.0,
        )
        new = _make_response(
            inductor_level=RiskInductor.LOADED,
            final_fragility=42.0,
            violations=(),
        )

        alerts = compute_alerts(prev, new)

        opportunity_alerts = get_alerts_by_type(alerts, AlertType.OPPORTUNITY)
        assert len(opportunity_alerts) == 1
        assert "de-escalation" in opportunity_alerts[0].details["reason"].lower()

    def test_opportunity_on_fragility_improvement(self):
        """OPPORTUNITY triggers on significant fragility improvement."""
        prev = _make_response(
            inductor_level=RiskInductor.LOADED,
            final_fragility=55.0,
        )
        new = _make_response(
            inductor_level=RiskInductor.LOADED,
            final_fragility=40.0,
            violations=(),
        )

        alerts = compute_alerts(prev, new)

        opportunity_alerts = get_alerts_by_type(alerts, AlertType.OPPORTUNITY)
        assert len(opportunity_alerts) == 1
        assert "fragility reduced" in opportunity_alerts[0].details["reason"].lower()

    def test_no_opportunity_with_violations(self):
        """No OPPORTUNITY when violations present."""
        prev = _make_response(
            inductor_level=RiskInductor.TENSE,
            final_fragility=65.0,
        )
        new = _make_response(
            inductor_level=RiskInductor.LOADED,
            final_fragility=40.0,
            violations=("max_legs_exceeded",),
        )

        alerts = compute_alerts(prev, new)

        opportunity_alerts = get_alerts_by_type(alerts, AlertType.OPPORTUNITY)
        assert len(opportunity_alerts) == 0

    def test_no_opportunity_high_fragility(self):
        """No OPPORTUNITY when fragility > 45."""
        prev = _make_response(
            inductor_level=RiskInductor.TENSE,
            final_fragility=65.0,
        )
        new = _make_response(
            inductor_level=RiskInductor.LOADED,
            final_fragility=50.0,
            violations=(),
        )

        alerts = compute_alerts(prev, new)

        opportunity_alerts = get_alerts_by_type(alerts, AlertType.OPPORTUNITY)
        assert len(opportunity_alerts) == 0

    def test_no_opportunity_tense_state(self):
        """No OPPORTUNITY when in TENSE state."""
        prev = _make_response(
            inductor_level=RiskInductor.CRITICAL,
            final_fragility=85.0,
        )
        new = _make_response(
            inductor_level=RiskInductor.TENSE,
            final_fragility=40.0,
            violations=(),
        )

        alerts = compute_alerts(prev, new)

        opportunity_alerts = get_alerts_by_type(alerts, AlertType.OPPORTUNITY)
        assert len(opportunity_alerts) == 0


# =============================================================================
# RISK_SPIKE Alert Tests
# =============================================================================


class TestRiskSpikeAlert:
    """Tests for RISK_SPIKE alert."""

    def test_risk_spike_fragility_increase(self):
        """RISK_SPIKE triggers on fragility increase >= 12."""
        prev = _make_response(
            inductor_level=RiskInductor.LOADED,
            final_fragility=40.0,
        )
        new = _make_response(
            inductor_level=RiskInductor.LOADED,
            final_fragility=52.0,  # +12
        )

        alerts = compute_alerts(prev, new)

        risk_alerts = get_alerts_by_type(alerts, AlertType.RISK_SPIKE)
        assert len(risk_alerts) == 1
        assert risk_alerts[0].severity == AlertSeverity.HIGH
        assert "fragility increased" in risk_alerts[0].message.lower()

    def test_risk_spike_inductor_escalation(self):
        """RISK_SPIKE triggers on inductor escalation."""
        prev = _make_response(
            inductor_level=RiskInductor.LOADED,
            final_fragility=50.0,
        )
        new = _make_response(
            inductor_level=RiskInductor.TENSE,
            final_fragility=56.0,  # Only +6, but inductor escalated
        )

        alerts = compute_alerts(prev, new)

        risk_alerts = get_alerts_by_type(alerts, AlertType.RISK_SPIKE)
        assert len(risk_alerts) == 1
        assert "escalated" in risk_alerts[0].message.lower()

    def test_no_risk_spike_below_threshold(self):
        """No RISK_SPIKE when below threshold."""
        prev = _make_response(
            inductor_level=RiskInductor.LOADED,
            final_fragility=40.0,
        )
        new = _make_response(
            inductor_level=RiskInductor.LOADED,
            final_fragility=50.0,  # +10, below 12 threshold
        )

        alerts = compute_alerts(prev, new)

        risk_alerts = get_alerts_by_type(alerts, AlertType.RISK_SPIKE)
        assert len(risk_alerts) == 0

    def test_no_risk_spike_no_prev(self):
        """No RISK_SPIKE on first evaluation."""
        new = _make_response(
            inductor_level=RiskInductor.TENSE,
            final_fragility=65.0,
        )

        alerts = compute_alerts(None, new)

        risk_alerts = get_alerts_by_type(alerts, AlertType.RISK_SPIKE)
        assert len(risk_alerts) == 0


# =============================================================================
# CORRELATION_SPIKE Alert Tests
# =============================================================================


class TestCorrelationSpikeAlert:
    """Tests for CORRELATION_SPIKE alert."""

    def test_correlation_spike_penalty_increase(self):
        """CORRELATION_SPIKE triggers on penalty increase >= 10."""
        prev = _make_response(
            inductor_level=RiskInductor.LOADED,
            final_fragility=45.0,
            correlation_penalty=5.0,
        )
        new = _make_response(
            inductor_level=RiskInductor.LOADED,
            final_fragility=50.0,
            correlation_penalty=15.0,  # +10
        )

        alerts = compute_alerts(prev, new)

        corr_alerts = get_alerts_by_type(alerts, AlertType.CORRELATION_SPIKE)
        assert len(corr_alerts) == 1
        assert "penalty increased" in corr_alerts[0].message.lower()

    def test_correlation_spike_multiplier_increase(self):
        """CORRELATION_SPIKE triggers on multiplier increase."""
        prev = _make_response(
            inductor_level=RiskInductor.LOADED,
            final_fragility=45.0,
            correlation_penalty=12.0,
            correlation_multiplier=1.0,
        )
        new = _make_response(
            inductor_level=RiskInductor.LOADED,
            final_fragility=48.0,
            correlation_penalty=15.0,  # +3, below threshold
            correlation_multiplier=1.15,  # Increased
        )

        alerts = compute_alerts(prev, new)

        corr_alerts = get_alerts_by_type(alerts, AlertType.CORRELATION_SPIKE)
        assert len(corr_alerts) == 1
        assert "multiplier increased" in corr_alerts[0].message.lower()

    def test_no_correlation_spike_below_threshold(self):
        """No CORRELATION_SPIKE when below threshold."""
        prev = _make_response(
            inductor_level=RiskInductor.LOADED,
            final_fragility=45.0,
            correlation_penalty=10.0,
            correlation_multiplier=1.0,
        )
        new = _make_response(
            inductor_level=RiskInductor.LOADED,
            final_fragility=48.0,
            correlation_penalty=18.0,  # +8, below 10 threshold
            correlation_multiplier=1.0,  # No change
        )

        alerts = compute_alerts(prev, new)

        corr_alerts = get_alerts_by_type(alerts, AlertType.CORRELATION_SPIKE)
        assert len(corr_alerts) == 0


# =============================================================================
# CONTEXT_IMPACT Alert Tests
# =============================================================================


class TestContextImpactAlert:
    """Tests for CONTEXT_IMPACT alert."""

    def test_context_impact_weather(self):
        """CONTEXT_IMPACT triggers for weather signal."""
        prev = _make_response()
        new = _make_response()

        context_applied = {
            "weather_delta": 4.0,
            "injury_delta": 0.0,
            "trade_delta": 0.0,
            "role_delta": 0.0,
        }

        alerts = compute_alerts(prev, new, context_applied)

        context_alerts = get_alerts_by_type(alerts, AlertType.CONTEXT_IMPACT)
        assert len(context_alerts) == 1
        assert "weather" in context_alerts[0].message.lower()
        assert "+4.0" in context_alerts[0].message

    def test_context_impact_injury(self):
        """CONTEXT_IMPACT triggers for injury signal."""
        prev = _make_response()
        new = _make_response()

        context_applied = {
            "weather_delta": 0.0,
            "injury_delta": 10.0,
            "trade_delta": 0.0,
            "role_delta": 3.0,
        }

        alerts = compute_alerts(prev, new, context_applied)

        context_alerts = get_alerts_by_type(alerts, AlertType.CONTEXT_IMPACT)
        assert len(context_alerts) == 1
        assert "injury" in context_alerts[0].message.lower()
        assert "role" in context_alerts[0].message.lower()

    def test_context_impact_multiple(self):
        """CONTEXT_IMPACT shows all impacts."""
        prev = _make_response()
        new = _make_response()

        context_applied = {
            "weather_delta": 7.0,
            "injury_delta": 6.0,
            "trade_delta": 5.0,
            "role_delta": 4.0,
        }

        alerts = compute_alerts(prev, new, context_applied)

        context_alerts = get_alerts_by_type(alerts, AlertType.CONTEXT_IMPACT)
        assert len(context_alerts) == 1
        # Should mention all four
        message = context_alerts[0].message.lower()
        assert "weather" in message
        assert "injury" in message
        assert "trade" in message
        assert "role" in message

    def test_no_context_impact_zero_delta(self):
        """No CONTEXT_IMPACT when all deltas are zero."""
        prev = _make_response()
        new = _make_response()

        context_applied = {
            "weather_delta": 0.0,
            "injury_delta": 0.0,
            "trade_delta": 0.0,
            "role_delta": 0.0,
        }

        alerts = compute_alerts(prev, new, context_applied)

        context_alerts = get_alerts_by_type(alerts, AlertType.CONTEXT_IMPACT)
        assert len(context_alerts) == 0

    def test_no_context_impact_no_context(self):
        """No CONTEXT_IMPACT when no context provided."""
        prev = _make_response()
        new = _make_response()

        alerts = compute_alerts(prev, new, None)

        context_alerts = get_alerts_by_type(alerts, AlertType.CONTEXT_IMPACT)
        assert len(context_alerts) == 0


# =============================================================================
# DNA_ENFORCED Alert Tests
# =============================================================================


class TestDNAEnforcedAlert:
    """Tests for DNA_ENFORCED alert."""

    def test_dna_enforced_new_violations(self):
        """DNA_ENFORCED triggers on new violations."""
        prev = _make_response(
            inductor_level=RiskInductor.LOADED,
            final_fragility=45.0,
            violations=(),
        )
        new = _make_response(
            inductor_level=RiskInductor.LOADED,
            final_fragility=45.0,
            violations=("max_legs_exceeded",),
        )

        alerts = compute_alerts(prev, new)

        dna_alerts = get_alerts_by_type(alerts, AlertType.DNA_ENFORCED)
        assert len(dna_alerts) == 1
        assert "max_legs_exceeded" in dna_alerts[0].message

    def test_dna_enforced_stake_reduction_25pct(self):
        """DNA_ENFORCED triggers on 25% stake reduction."""
        prev = _make_response(
            inductor_level=RiskInductor.LOADED,
            final_fragility=45.0,
            recommended_stake=100.0,
        )
        new = _make_response(
            inductor_level=RiskInductor.LOADED,
            final_fragility=45.0,
            recommended_stake=75.0,  # -25%
        )

        alerts = compute_alerts(prev, new)

        dna_alerts = get_alerts_by_type(alerts, AlertType.DNA_ENFORCED)
        assert len(dna_alerts) == 1
        assert "stake" in dna_alerts[0].message.lower()
        assert dna_alerts[0].severity == AlertSeverity.MED

    def test_dna_enforced_stake_reduction_50pct_high_severity(self):
        """DNA_ENFORCED has HIGH severity on 50%+ stake reduction."""
        prev = _make_response(
            inductor_level=RiskInductor.LOADED,
            final_fragility=45.0,
            recommended_stake=100.0,
        )
        new = _make_response(
            inductor_level=RiskInductor.LOADED,
            final_fragility=45.0,
            recommended_stake=45.0,  # -55%
        )

        alerts = compute_alerts(prev, new)

        dna_alerts = get_alerts_by_type(alerts, AlertType.DNA_ENFORCED)
        assert len(dna_alerts) == 1
        assert dna_alerts[0].severity == AlertSeverity.HIGH

    def test_dna_enforced_initial_violations(self):
        """DNA_ENFORCED triggers on first evaluation with violations."""
        new = _make_response(
            inductor_level=RiskInductor.LOADED,
            final_fragility=45.0,
            violations=("props_not_allowed",),
        )

        alerts = compute_alerts(None, new)

        dna_alerts = get_alerts_by_type(alerts, AlertType.DNA_ENFORCED)
        assert len(dna_alerts) == 1

    def test_no_dna_enforced_no_change(self):
        """No DNA_ENFORCED when violations and stake unchanged."""
        prev = _make_response(
            inductor_level=RiskInductor.LOADED,
            final_fragility=45.0,
            violations=("max_legs_exceeded",),
            recommended_stake=100.0,
        )
        new = _make_response(
            inductor_level=RiskInductor.LOADED,
            final_fragility=45.0,
            violations=("max_legs_exceeded",),  # Same
            recommended_stake=100.0,  # Same
        )

        alerts = compute_alerts(prev, new)

        dna_alerts = get_alerts_by_type(alerts, AlertType.DNA_ENFORCED)
        assert len(dna_alerts) == 0

    def test_no_dna_enforced_small_stake_change(self):
        """No DNA_ENFORCED on small stake reduction."""
        prev = _make_response(
            inductor_level=RiskInductor.LOADED,
            final_fragility=45.0,
            recommended_stake=100.0,
        )
        new = _make_response(
            inductor_level=RiskInductor.LOADED,
            final_fragility=45.0,
            recommended_stake=80.0,  # -20%, below 25% threshold
        )

        alerts = compute_alerts(prev, new)

        dna_alerts = get_alerts_by_type(alerts, AlertType.DNA_ENFORCED)
        assert len(dna_alerts) == 0


# =============================================================================
# No Spam Tests
# =============================================================================


class TestNoSpam:
    """Tests for spam prevention."""

    def test_identical_responses_no_alerts(self, stable_response):
        """Identical responses produce no alerts."""
        alerts = compute_alerts(stable_response, stable_response)
        assert alerts == []

    def test_minor_changes_no_alerts(self):
        """Minor changes don't trigger alerts."""
        prev = _make_response(
            inductor_level=RiskInductor.LOADED,
            final_fragility=45.0,
            correlation_penalty=10.0,
            recommended_stake=100.0,
        )
        new = _make_response(
            inductor_level=RiskInductor.LOADED,  # Same
            final_fragility=50.0,  # +5, below 12 threshold
            correlation_penalty=15.0,  # +5, below 10 threshold
            recommended_stake=90.0,  # -10%, below 25% threshold
        )

        alerts = compute_alerts(prev, new)
        assert alerts == []

    def test_stable_to_stable_no_opportunity(self):
        """STABLE to STABLE without significant improvement = no opportunity."""
        prev = _make_response(
            inductor_level=RiskInductor.STABLE,
            final_fragility=25.0,
            violations=(),
        )
        new = _make_response(
            inductor_level=RiskInductor.STABLE,
            final_fragility=24.0,  # -1, below 12 threshold
            violations=(),
        )

        alerts = compute_alerts(prev, new)

        opportunity_alerts = get_alerts_by_type(alerts, AlertType.OPPORTUNITY)
        assert len(opportunity_alerts) == 0


# =============================================================================
# Helper Function Tests
# =============================================================================


class TestInductorOrdering:
    """Tests for inductor ordering helpers."""

    def test_escalated_loaded_to_tense(self):
        """LOADED -> TENSE is escalation."""
        assert _inductor_escalated(RiskInductor.LOADED, RiskInductor.TENSE) is True

    def test_escalated_tense_to_critical(self):
        """TENSE -> CRITICAL is escalation."""
        assert _inductor_escalated(RiskInductor.TENSE, RiskInductor.CRITICAL) is True

    def test_not_escalated_same_level(self):
        """Same level is not escalation."""
        assert _inductor_escalated(RiskInductor.LOADED, RiskInductor.LOADED) is False

    def test_not_escalated_deescalation(self):
        """TENSE -> LOADED is not escalation."""
        assert _inductor_escalated(RiskInductor.TENSE, RiskInductor.LOADED) is False

    def test_deescalated_tense_to_loaded(self):
        """TENSE -> LOADED is de-escalation."""
        assert _inductor_deescalated(RiskInductor.TENSE, RiskInductor.LOADED) is True

    def test_deescalated_critical_to_stable(self):
        """CRITICAL -> STABLE is de-escalation."""
        assert _inductor_deescalated(RiskInductor.CRITICAL, RiskInductor.STABLE) is True


class TestHelperFunctions:
    """Tests for helper functions."""

    def test_has_high_severity_true(self):
        """has_high_severity_alerts returns True when HIGH alert present."""
        alerts = [
            Alert(AlertType.RISK_SPIKE, AlertSeverity.HIGH, "Test", {}),
        ]
        assert has_high_severity_alerts(alerts) is True

    def test_has_high_severity_false(self):
        """has_high_severity_alerts returns False when no HIGH alert."""
        alerts = [
            Alert(AlertType.OPPORTUNITY, AlertSeverity.LOW, "Test", {}),
            Alert(AlertType.CONTEXT_IMPACT, AlertSeverity.MED, "Test", {}),
        ]
        assert has_high_severity_alerts(alerts) is False

    def test_has_high_severity_empty(self):
        """has_high_severity_alerts returns False for empty list."""
        assert has_high_severity_alerts([]) is False

    def test_get_alerts_by_type(self):
        """get_alerts_by_type filters correctly."""
        alerts = [
            Alert(AlertType.RISK_SPIKE, AlertSeverity.HIGH, "Risk", {}),
            Alert(AlertType.OPPORTUNITY, AlertSeverity.LOW, "Opportunity", {}),
            Alert(AlertType.RISK_SPIKE, AlertSeverity.HIGH, "Another Risk", {}),
        ]

        risk_alerts = get_alerts_by_type(alerts, AlertType.RISK_SPIKE)
        assert len(risk_alerts) == 2

        opp_alerts = get_alerts_by_type(alerts, AlertType.OPPORTUNITY)
        assert len(opp_alerts) == 1

    def test_get_alerts_by_severity(self):
        """get_alerts_by_severity filters correctly."""
        alerts = [
            Alert(AlertType.RISK_SPIKE, AlertSeverity.HIGH, "High", {}),
            Alert(AlertType.CONTEXT_IMPACT, AlertSeverity.MED, "Med", {}),
            Alert(AlertType.OPPORTUNITY, AlertSeverity.LOW, "Low", {}),
        ]

        high_alerts = get_alerts_by_severity(alerts, AlertSeverity.HIGH)
        assert len(high_alerts) == 1

        low_alerts = get_alerts_by_severity(alerts, AlertSeverity.LOW)
        assert len(low_alerts) == 1


# =============================================================================
# Determinism Tests
# =============================================================================


class TestDeterminism:
    """Tests for deterministic behavior."""

    def test_same_inputs_same_outputs(self):
        """Same inputs always produce same outputs."""
        prev = _make_response(
            inductor_level=RiskInductor.TENSE,
            final_fragility=65.0,
        )
        new = _make_response(
            inductor_level=RiskInductor.LOADED,
            final_fragility=40.0,
            violations=(),
        )

        alerts1 = compute_alerts(prev, new)
        alerts2 = compute_alerts(prev, new)

        assert len(alerts1) == len(alerts2)
        for a1, a2 in zip(alerts1, alerts2):
            assert a1.type == a2.type
            assert a1.severity == a2.severity
            assert a1.message == a2.message
