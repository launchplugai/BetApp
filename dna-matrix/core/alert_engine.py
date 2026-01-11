# core/alert_engine.py
"""
Alert Engine - Generate user-facing alert candidates from EvaluationResponse.

Produces deterministic, sparse alerts tied to measurable changes.
Alerts only trigger when thresholds crossed or meaningful deltas occur.

No push notifications. No scheduling. No live APIs.
"""
from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import List, Optional

from core.evaluation import EvaluationResponse
from core.risk_inductor import RiskInductor


# =============================================================================
# Enums
# =============================================================================


class AlertType(str, Enum):
    """Types of alerts that can be generated."""
    OPPORTUNITY = "opportunity"
    RISK_SPIKE = "risk_spike"
    CORRELATION_SPIKE = "correlation_spike"
    CONTEXT_IMPACT = "context_impact"
    DNA_ENFORCED = "dna_enforced"


class AlertSeverity(str, Enum):
    """Severity levels for alerts."""
    LOW = "low"
    MED = "medium"
    HIGH = "high"


# =============================================================================
# Alert Dataclass
# =============================================================================


@dataclass(frozen=True)
class Alert:
    """
    A user-facing alert candidate.

    Attributes:
        type: The type of alert
        severity: Severity level (LOW, MED, HIGH)
        message: Human-readable message
        details: Optional dict with additional context
    """
    type: AlertType
    severity: AlertSeverity
    message: str
    details: Optional[dict] = None


# =============================================================================
# Constants
# =============================================================================

# Thresholds for triggering alerts
FRAGILITY_DELTA_THRESHOLD = 12
CORRELATION_PENALTY_DELTA_THRESHOLD = 10
OPPORTUNITY_MAX_FRAGILITY = 45
STAKE_REDUCTION_THRESHOLD_PCT = 0.25  # 25%


# =============================================================================
# Inductor Ordering
# =============================================================================

# Order for comparing inductor levels (higher = worse)
_INDUCTOR_ORDER = {
    RiskInductor.STABLE: 0,
    RiskInductor.LOADED: 1,
    RiskInductor.TENSE: 2,
    RiskInductor.CRITICAL: 3,
}


def _inductor_escalated(prev: RiskInductor, new: RiskInductor) -> bool:
    """Check if inductor level escalated (got worse)."""
    return _INDUCTOR_ORDER[new] > _INDUCTOR_ORDER[prev]


def _inductor_deescalated(prev: RiskInductor, new: RiskInductor) -> bool:
    """Check if inductor level de-escalated (got better)."""
    return _INDUCTOR_ORDER[new] < _INDUCTOR_ORDER[prev]


# =============================================================================
# Alert Generators
# =============================================================================


def _check_opportunity(
    prev: Optional[EvaluationResponse],
    new: EvaluationResponse,
) -> Optional[Alert]:
    """
    Check for OPPORTUNITY alert (rare, good news).

    Triggers when:
    - new.inductor.level in [STABLE, LOADED]
    - new.metrics.final_fragility <= 45
    - new.dna.violations is empty
    - AND one of:
      - prev is None
      - prev.inductor.level was TENSE/CRITICAL
      - prev.final_fragility - new.final_fragility >= 12
    """
    # Must be in favorable state
    if new.inductor.level not in (RiskInductor.STABLE, RiskInductor.LOADED):
        return None

    # Must have low fragility
    if new.metrics.final_fragility > OPPORTUNITY_MAX_FRAGILITY:
        return None

    # Must have no violations
    if len(new.dna.violations) > 0:
        return None

    # Check if this is a notable opportunity
    is_notable = False
    reason_parts: List[str] = []

    if prev is None:
        # First evaluation - notable if conditions met
        is_notable = True
        reason_parts.append("favorable initial structure")
    elif prev.inductor.level in (RiskInductor.TENSE, RiskInductor.CRITICAL):
        # De-escalation from risky state
        is_notable = True
        reason_parts.append(f"de-escalation from {prev.inductor.level.value}")
    elif prev.metrics.final_fragility - new.metrics.final_fragility >= FRAGILITY_DELTA_THRESHOLD:
        # Significant fragility improvement
        is_notable = True
        delta = prev.metrics.final_fragility - new.metrics.final_fragility
        reason_parts.append(f"fragility reduced by {delta:.1f}")

    if not is_notable:
        return None

    message = f"Opportunity detected: {new.inductor.level.value} state with {new.metrics.final_fragility:.1f} fragility"
    if reason_parts:
        message += f" ({'; '.join(reason_parts)})"

    return Alert(
        type=AlertType.OPPORTUNITY,
        severity=AlertSeverity.LOW,
        message=message,
        details={
            "inductor_level": new.inductor.level.value,
            "final_fragility": new.metrics.final_fragility,
            "reason": "; ".join(reason_parts),
        },
    )


def _check_risk_spike(
    prev: Optional[EvaluationResponse],
    new: EvaluationResponse,
) -> Optional[Alert]:
    """
    Check for RISK_SPIKE alert.

    Triggers when:
    - new.final_fragility - prev.final_fragility >= 12
    - OR inductor escalates upward (LOADED->TENSE, TENSE->CRITICAL)
    """
    if prev is None:
        return None

    fragility_delta = new.metrics.final_fragility - prev.metrics.final_fragility
    inductor_escalated = _inductor_escalated(prev.inductor.level, new.inductor.level)

    if fragility_delta < FRAGILITY_DELTA_THRESHOLD and not inductor_escalated:
        return None

    reason_parts: List[str] = []

    if fragility_delta >= FRAGILITY_DELTA_THRESHOLD:
        reason_parts.append(f"fragility increased by {fragility_delta:.1f}")

    if inductor_escalated:
        reason_parts.append(
            f"risk level escalated from {prev.inductor.level.value} to {new.inductor.level.value}"
        )

    message = f"Risk spike detected: {'; '.join(reason_parts)}"

    return Alert(
        type=AlertType.RISK_SPIKE,
        severity=AlertSeverity.HIGH,
        message=message,
        details={
            "prev_fragility": prev.metrics.final_fragility,
            "new_fragility": new.metrics.final_fragility,
            "fragility_delta": fragility_delta,
            "prev_inductor": prev.inductor.level.value,
            "new_inductor": new.inductor.level.value,
            "inductor_escalated": inductor_escalated,
        },
    )


def _check_correlation_spike(
    prev: Optional[EvaluationResponse],
    new: EvaluationResponse,
) -> Optional[Alert]:
    """
    Check for CORRELATION_SPIKE alert.

    Triggers when:
    - new.correlation_penalty - prev.correlation_penalty >= 10
    - OR multiplier increases (1.0 -> 1.15, etc.)
    """
    if prev is None:
        return None

    penalty_delta = new.metrics.correlation_penalty - prev.metrics.correlation_penalty
    multiplier_increased = new.metrics.correlation_multiplier > prev.metrics.correlation_multiplier

    if penalty_delta < CORRELATION_PENALTY_DELTA_THRESHOLD and not multiplier_increased:
        return None

    reason_parts: List[str] = []

    if penalty_delta >= CORRELATION_PENALTY_DELTA_THRESHOLD:
        reason_parts.append(f"correlation penalty increased by {penalty_delta:.1f}")

    if multiplier_increased:
        reason_parts.append(
            f"correlation multiplier increased from {prev.metrics.correlation_multiplier}x "
            f"to {new.metrics.correlation_multiplier}x"
        )

    message = f"Correlation spike detected: {'; '.join(reason_parts)}"

    return Alert(
        type=AlertType.CORRELATION_SPIKE,
        severity=AlertSeverity.HIGH,
        message=message,
        details={
            "prev_correlation_penalty": prev.metrics.correlation_penalty,
            "new_correlation_penalty": new.metrics.correlation_penalty,
            "penalty_delta": penalty_delta,
            "prev_multiplier": prev.metrics.correlation_multiplier,
            "new_multiplier": new.metrics.correlation_multiplier,
        },
    )


def _check_context_impact(
    prev: Optional[EvaluationResponse],
    new: EvaluationResponse,
    context_applied: Optional[dict] = None,
) -> Optional[Alert]:
    """
    Check for CONTEXT_IMPACT alert.

    Triggers when:
    - context_signals were applied AND they increased any modifier delta > 0

    Args:
        prev: Previous evaluation response (optional)
        new: New evaluation response
        context_applied: Optional dict with context impact info
            {
                "weather_delta": 4.0,
                "injury_delta": 10.0,
                "trade_delta": 0.0,
                "role_delta": 3.0,
            }
    """
    if context_applied is None:
        return None

    # Sum all positive deltas
    total_delta = sum(
        v for v in context_applied.values()
        if isinstance(v, (int, float)) and v > 0
    )

    if total_delta == 0:
        return None

    # Build factual message
    impact_parts: List[str] = []
    for key, value in context_applied.items():
        if isinstance(value, (int, float)) and value > 0:
            # Convert key like "weather_delta" to "Weather"
            signal_type = key.replace("_delta", "").capitalize()
            impact_parts.append(f"{signal_type} added +{value:.1f} fragility")

    message = f"Context impact: {'; '.join(impact_parts)}"

    return Alert(
        type=AlertType.CONTEXT_IMPACT,
        severity=AlertSeverity.MED,
        message=message,
        details={
            "total_context_delta": total_delta,
            **context_applied,
        },
    )


def _check_dna_enforced(
    prev: Optional[EvaluationResponse],
    new: EvaluationResponse,
) -> Optional[Alert]:
    """
    Check for DNA_ENFORCED alert.

    Triggers when:
    - violations newly appear
    - OR recommendedStake drops by >= 25%
    """
    if prev is None:
        # Check for initial violations
        if len(new.dna.violations) > 0:
            message = f"DNA constraints violated: {', '.join(new.dna.violations)}"
            return Alert(
                type=AlertType.DNA_ENFORCED,
                severity=AlertSeverity.MED,
                message=message,
                details={
                    "violations": list(new.dna.violations),
                    "new_violations": list(new.dna.violations),
                },
            )
        return None

    # Check for new violations
    prev_violations = set(prev.dna.violations)
    new_violations = set(new.dna.violations)
    added_violations = new_violations - prev_violations

    # Check for stake reduction
    stake_reduced_significantly = False
    stake_reduction_pct = 0.0

    if (
        prev.dna.recommended_stake is not None
        and new.dna.recommended_stake is not None
        and prev.dna.recommended_stake > 0
    ):
        stake_reduction_pct = (
            (prev.dna.recommended_stake - new.dna.recommended_stake)
            / prev.dna.recommended_stake
        )
        stake_reduced_significantly = stake_reduction_pct >= STAKE_REDUCTION_THRESHOLD_PCT

    if not added_violations and not stake_reduced_significantly:
        return None

    reason_parts: List[str] = []
    severity = AlertSeverity.MED

    if added_violations:
        reason_parts.append(f"new violations: {', '.join(added_violations)}")

    if stake_reduced_significantly:
        reason_parts.append(
            f"recommended stake reduced by {stake_reduction_pct * 100:.0f}% "
            f"(from {prev.dna.recommended_stake:.2f} to {new.dna.recommended_stake:.2f})"
        )
        # Higher severity for significant stake reduction
        if stake_reduction_pct >= 0.5:  # 50%+ reduction
            severity = AlertSeverity.HIGH

    message = f"DNA enforcement triggered: {'; '.join(reason_parts)}"

    return Alert(
        type=AlertType.DNA_ENFORCED,
        severity=severity,
        message=message,
        details={
            "violations": list(new.dna.violations),
            "new_violations": list(added_violations) if added_violations else [],
            "prev_stake": prev.dna.recommended_stake,
            "new_stake": new.dna.recommended_stake,
            "stake_reduction_pct": stake_reduction_pct if stake_reduced_significantly else 0.0,
        },
    )


# =============================================================================
# Main Function
# =============================================================================


def compute_alerts(
    prev: Optional[EvaluationResponse],
    new: EvaluationResponse,
    context_applied: Optional[dict] = None,
) -> List[Alert]:
    """
    Compute alerts based on changes between evaluation responses.

    Alerts are:
    - Deterministic
    - Sparse (avoid spam - no alerts if nothing changed)
    - Tied to measurable changes

    Args:
        prev: Previous evaluation response (None for first evaluation)
        new: New evaluation response
        context_applied: Optional dict with context signal impact info

    Returns:
        List of Alert objects (may be empty)
    """
    alerts: List[Alert] = []

    # Check each alert type
    opportunity = _check_opportunity(prev, new)
    if opportunity:
        alerts.append(opportunity)

    risk_spike = _check_risk_spike(prev, new)
    if risk_spike:
        alerts.append(risk_spike)

    correlation_spike = _check_correlation_spike(prev, new)
    if correlation_spike:
        alerts.append(correlation_spike)

    context_impact = _check_context_impact(prev, new, context_applied)
    if context_impact:
        alerts.append(context_impact)

    dna_enforced = _check_dna_enforced(prev, new)
    if dna_enforced:
        alerts.append(dna_enforced)

    return alerts


# =============================================================================
# Convenience Functions
# =============================================================================


def has_high_severity_alerts(alerts: List[Alert]) -> bool:
    """Check if any alerts have HIGH severity."""
    return any(alert.severity == AlertSeverity.HIGH for alert in alerts)


def get_alerts_by_type(alerts: List[Alert], alert_type: AlertType) -> List[Alert]:
    """Filter alerts by type."""
    return [alert for alert in alerts if alert.type == alert_type]


def get_alerts_by_severity(alerts: List[Alert], severity: AlertSeverity) -> List[Alert]:
    """Filter alerts by severity."""
    return [alert for alert in alerts if alert.severity == severity]
