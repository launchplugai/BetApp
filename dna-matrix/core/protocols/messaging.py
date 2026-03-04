# core/protocols/messaging.py
"""
User-Style Adapted Messaging — the emotional intelligence layer.

The system doesn't just calculate risk. It communicates it
in a way calibrated to the user's betting personality.

User Styles:
- risk_averse: Warns clearly, emphasizes caution
- aggressive: Reframes risk as opportunity, highlights variance edges
- novice: Simple language, explains concepts
- expert: Data-dense, statistical, no hand-holding

This customization is sticky — it makes the system feel like
a coach, not a critic.
"""
from __future__ import annotations

from typing import Any, Dict, List, Optional

from core.protocols.models import AggregatedRisk, ProtocolCategory, RiskLevel
from core.protocols.registry_loader import get_explain_template


class UserStyle:
    """User betting personality constants."""
    RISK_AVERSE = "risk_averse"
    AGGRESSIVE = "aggressive"
    NOVICE = "novice"
    EXPERT = "expert"

    ALL = [RISK_AVERSE, AGGRESSIVE, NOVICE, EXPERT]

    @classmethod
    def from_profile(cls, profile: Dict[str, Any]) -> str:
        """
        Derive user style from their betting profile.

        Factors:
        - historical bet types (parlays vs singles)
        - average stake
        - risk tolerance setting
        - betting history patterns
        """
        risk_tolerance = profile.get("risk_tolerance", "medium")
        avg_legs = profile.get("avg_parlay_legs", 2)
        experience = profile.get("experience_level", "intermediate")

        if experience in ("beginner", "new"):
            return cls.NOVICE

        if risk_tolerance == "high" or avg_legs >= 5:
            return cls.AGGRESSIVE

        if risk_tolerance == "low" or avg_legs <= 2:
            return cls.RISK_AVERSE

        return cls.EXPERT  # default for experienced users


def adapt_risk_summary(
    risk: AggregatedRisk,
    user_style: str = UserStyle.NOVICE,
) -> Dict[str, Any]:
    """
    Generate user-style adapted risk summary from protocol results.

    Returns a dict with:
    - headline: 1-line attention grabber
    - summary: 2-3 sentence explanation
    - signals: per-signal adapted explanations
    - action: suggested next step

    The same risk data produces different messaging per user style.
    """
    signals_adapted = []
    for result in risk.protocol_results:
        if not result.triggered:
            continue
        for signal in result.signals:
            template = get_explain_template(signal.protocol_name, user_style)
            signals_adapted.append({
                "protocol": signal.protocol_name,
                "category": signal.category.value,
                "risk": signal.risk_level.value,
                "title": template["title"],
                "explanation": template["summary"] or signal.explanation,
                "confidence": round(signal.confidence, 2),
            })

    headline = _headline_for_style(risk, user_style)
    summary = _summary_for_style(risk, user_style)
    action = _action_for_style(risk, user_style)

    return {
        "userStyle": user_style,
        "headline": headline,
        "summary": summary,
        "action": action,
        "signals": signals_adapted,
        "fragilityScore": round(risk.fragility_score, 3),
        "confidenceScore": round(risk.confidence_score, 3),
    }


def _headline_for_style(risk: AggregatedRisk, style: str) -> str:
    """Generate attention-grabbing headline adapted to user style."""
    frag = risk.fragility_score
    count = risk.triggered_count

    if style == UserStyle.RISK_AVERSE:
        if frag >= 0.7:
            return "Significant hidden risks detected"
        elif frag >= 0.4:
            return "Several risk factors need your attention"
        else:
            return "Minor concerns noted"

    elif style == UserStyle.AGGRESSIVE:
        if frag >= 0.7:
            return "High variance opportunity — know the risks"
        elif frag >= 0.4:
            return "Some edges found, but volatility is elevated"
        else:
            return "Clean setup — variance is manageable"

    elif style == UserStyle.NOVICE:
        if frag >= 0.7:
            return "This bet has some problems you should know about"
        elif frag >= 0.4:
            return "A few things could make this bet harder to win"
        else:
            return "This looks mostly okay, with a couple of notes"

    else:  # EXPERT
        if frag >= 0.7:
            return f"Fragility {frag:.0%} — {count} contextual risk factors active"
        elif frag >= 0.4:
            return f"Fragility {frag:.0%} — {count} protocols triggered"
        else:
            return f"Low contextual risk ({frag:.0%}) — {count} minor signals"


def _summary_for_style(risk: AggregatedRisk, style: str) -> str:
    """Generate 2-3 sentence summary adapted to user style."""
    frag = risk.fragility_score
    count = risk.triggered_count
    cats = risk.category_risks

    # Find dominant risk categories
    high_cats = [c for c, r in cats.items() if r in (RiskLevel.HIGH, RiskLevel.CRITICAL)]
    mod_cats = [c for c, r in cats.items() if r == RiskLevel.MODERATE]

    if style == UserStyle.RISK_AVERSE:
        if frag >= 0.7:
            parts = [f"This bet has {count} hidden risk factors that weaken its stability."]
            if high_cats:
                parts.append(f"The biggest concerns are in {' and '.join(high_cats)} areas.")
            parts.append("Consider reducing exposure or waiting for better conditions.")
            return " ".join(parts)
        elif frag >= 0.4:
            return (
                f"There are {count} contextual factors adding uncertainty to this bet. "
                "It's not a dealbreaker, but you should be aware of the risks before committing."
            )
        else:
            return "Minor contextual factors are present but unlikely to significantly impact the outcome."

    elif style == UserStyle.AGGRESSIVE:
        if frag >= 0.7:
            parts = [f"High variance situation with {count} active protocols."]
            if high_cats:
                parts.append(f"The volatility comes from {' and '.join(high_cats)}.")
            parts.append("If the payout justifies the risk, it could be worth it — but size accordingly.")
            return " ".join(parts)
        elif frag >= 0.4:
            return (
                f"{count} protocols flagged moderate risk. "
                "The market may not have fully adjusted to these factors — "
                "look for mispricing opportunities on the other side."
            )
        else:
            return "Clean contextual profile. Standard analysis applies."

    elif style == UserStyle.NOVICE:
        if frag >= 0.7:
            parts = ["There are some important things happening behind this game that could affect your bet."]
            if "physical" in high_cats:
                parts.append("One of the teams might be tired from playing recently or traveling a lot.")
            if "volatility" in high_cats:
                parts.append("There are lineup changes or injuries that make the game less predictable.")
            if "market" in high_cats:
                parts.append("The betting odds have been moving in a suspicious way.")
            return " ".join(parts[:3])
        elif frag >= 0.4:
            return (
                "A few things could make this bet trickier than it looks. "
                "It's not necessarily bad, but being aware of these factors helps you make a better decision."
            )
        else:
            return "This bet looks pretty straightforward. Nothing major to worry about."

    else:  # EXPERT
        if frag >= 0.7:
            cat_str = ", ".join(f"{c}={r.value}" for c, r in cats.items() if r != RiskLevel.NONE)
            return (
                f"Aggregate fragility {frag:.0%} across {count} triggered protocols. "
                f"Category breakdown: {cat_str}. "
                f"Stability modifier at {1.0 - frag * 0.35:.0%}. Consider position sizing or hedging."
            )
        elif frag >= 0.4:
            return (
                f"{count} protocols triggered, aggregate fragility {frag:.0%}. "
                "Moderate contextual headwinds present. Standard sizing with awareness."
            )
        else:
            return f"Low contextual noise ({frag:.0%}). {count} minor signals — baseline analysis sufficient."


def _action_for_style(risk: AggregatedRisk, style: str) -> str:
    """Generate suggested action adapted to user style."""
    frag = risk.fragility_score

    if style == UserStyle.RISK_AVERSE:
        if frag >= 0.7:
            return "Consider passing on this bet or reducing your stake significantly."
        elif frag >= 0.4:
            return "Proceed with smaller stake than usual."
        else:
            return "Proceed as planned."

    elif style == UserStyle.AGGRESSIVE:
        if frag >= 0.7:
            return "High risk, high reward. Size down but don't avoid — the payoff could justify the variance."
        elif frag >= 0.4:
            return "Standard play. Look for value on the less popular side."
        else:
            return "Fire away."

    elif style == UserStyle.NOVICE:
        if frag >= 0.7:
            return "This bet is riskier than it looks. Maybe try a smaller bet or skip this one."
        elif frag >= 0.4:
            return "This bet is okay but not great. Don't bet more than you're comfortable losing."
        else:
            return "This looks good. Just remember — nothing is guaranteed in sports!"

    else:  # EXPERT
        if frag >= 0.7:
            return "Reduce position size or hedge. Contextual headwinds exceed baseline tolerance."
        elif frag >= 0.4:
            return "Standard sizing with awareness of active protocols."
        else:
            return "Green light. Minimal contextual interference."
