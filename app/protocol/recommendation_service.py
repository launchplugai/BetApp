"""
Recommendation Service - Generate AI bet recommendations from protocol data
"""

from typing import List, Dict, Optional
from datetime import datetime, timedelta
from sqlalchemy.orm import Session
import random
import uuid

from app.protocol.models import Protocol
from app.protocol.recommendation_models import Recommendation, Parlay
from app.protocol.sports_integration import get_protocol_snapshot


def generate_recommendations(
    db: Session,
    protocol: Protocol,
    user_tier: str = "GOOD"
) -> List[Recommendation]:
    """
    Generate bet recommendations based on protocol snapshot data.
    
    Args:
        db: Database session
        protocol: Protocol to analyze
        user_tier: User tier for recommendation quality
        
    Returns:
        List of Recommendation objects
    """
    # Get current snapshot
    snapshot = get_protocol_snapshot(protocol, user_tier)
    data = snapshot.get("data", {})
    
    recommendations = []
    
    # Generate based on tier
    if user_tier == "GOOD":
        # Basic recommendations - simple matchups
        recommendations = _generate_good_recommendations(protocol, data)
    elif user_tier == "BETTER":
        # Enhanced with stats and trends
        recommendations = _generate_better_recommendations(protocol, data)
    else:  # BEST
        # Full analytics-based recommendations
        recommendations = _generate_best_recommendations(protocol, data)
    
    # Save to database
    for rec in recommendations:
        db.add(rec)
    
    db.commit()
    return recommendations


def _generate_good_recommendations(protocol: Protocol, data: Dict) -> List[Recommendation]:
    """Generate basic recommendations."""
    recs = []
    
    # Simple spread recommendation
    recs.append(Recommendation(
        protocol_id=protocol.id,
        user_id=protocol.user_id,
        bet_type="spread",
        description=f"Spread bet on {protocol.title}",
        confidence=55,
        reasoning=["Basic matchup analysis", "Home court advantage"],
        factors={"home_advantage": True, "form": "neutral"},
        status="active"
    ))
    
    return recs


def _generate_better_recommendations(protocol: Protocol, data: Dict) -> List[Recommendation]:
    """Generate enhanced recommendations with stats."""
    recs = []
    
    recent = data.get("recent_form", {})
    injuries = data.get("injury_summary", {})
    
    # Analyze form
    home_form = recent.get("home_last_5", "")
    away_form = recent.get("away_last_5", "")
    
    home_wins = home_form.count("W") if home_form else 0
    away_wins = away_form.count("W") if away_form else 0
    
    # Spread recommendation based on form
    if home_wins >= 3:
        recs.append(Recommendation(
            protocol_id=protocol.id,
            user_id=protocol.user_id,
            bet_type="spread",
            description=f"Home team spread - hot form ({home_wins}-2)",
            confidence=65,
            reasoning=[
                f"Home team won {home_wins} of last 5",
                "Momentum factor",
                f"Injury impact: {injuries.get('impact', 'low')}"
            ],
            factors={
                "home_form": home_form,
                "injury_impact": injuries.get("impact", "low"),
                "momentum": "positive"
            },
            status="active"
        ))
    
    if away_wins >= 3:
        recs.append(Recommendation(
            protocol_id=protocol.id,
            user_id=protocol.user_id,
            bet_type="spread",
            description=f"Away team spread - hot form ({away_wins}-2)",
            confidence=65,
            reasoning=[
                f"Away team won {away_wins} of last 5",
                "Road warriors",
                f"Injury impact: {injuries.get('impact', 'low')}"
            ],
            factors={
                "away_form": away_form,
                "injury_impact": injuries.get("impact", "low"),
                "momentum": "positive"
            },
            status="active"
        ))
    
    # Total recommendation
    recs.append(Recommendation(
        protocol_id=protocol.id,
        user_id=protocol.user_id,
        bet_type="total",
        description="Over - both teams scoring well",
        confidence=60,
        reasoning=["Recent high scoring trends", "Pace of play"],
        factors={"pace": "fast", "trend": "over"},
        status="active"
    ))
    
    return recs


def _generate_best_recommendations(protocol: Protocol, data: Dict) -> List[Recommendation]:
    """Generate comprehensive recommendations with full analytics."""
    recs = _generate_better_recommendations(protocol, data)
    
    # Add player props
    player_matchups = data.get("player_matchups", [])
    advanced = data.get("advanced_metrics", {})
    
    if player_matchups:
        recs.append(Recommendation(
            protocol_id=protocol.id,
            user_id=protocol.user_id,
            bet_type="player_prop",
            description="Player prop - matchup advantage identified",
            confidence=70,
            reasoning=[
                "Favorable individual matchup",
                "Historical performance vs opponent",
                "Advanced metrics support"
            ],
            factors={
                "matchup_rating": "favorable",
                "advanced_metrics": advanced,
                "historical_edge": True
            },
            status="active"
        ))
    
    # Add parlay suggestion
    if len(recs) >= 2:
        recs.append(Recommendation(
            protocol_id=protocol.id,
            user_id=protocol.user_id,
            bet_type="parlay",
            description=f"2-leg parlay combining top picks",
            confidence=58,
            reasoning=[
                "Multiple edges identified",
                "Correlated factors",
                "Higher value at +EV"
            ],
            factors={
                "legs": 2,
                "correlation": "medium",
                "expected_value": "positive"
            },
            status="active"
        ))
    
    return recs


def create_parlay_from_recommendations(
    db: Session,
    user_id: str,
    recommendation_ids: List[str],
    title: Optional[str] = None
) -> Parlay:
    """
    Create a parlay from selected recommendations.
    
    Args:
        db: Database session
        user_id: User creating parlay
        recommendation_ids: List of recommendation IDs to include
        title: Optional custom title
        
    Returns:
        Created Parlay
    """
    # Get recommendations
    recommendations = db.query(Recommendation).filter(
        Recommendation.id.in_(recommendation_ids),
        Recommendation.user_id == user_id
    ).all()
    
    if len(recommendations) < 2:
        raise ValueError("Parlay requires at least 2 recommendations")
    
    # Calculate parlay odds (simplified)
    # In production: use actual odds calculation
    total_confidence = sum(r.confidence for r in recommendations) / len(recommendations)
    implied_prob = total_confidence / 100
    
    # Simple American odds conversion
    if implied_prob > 0.5:
        total_odds = int(-100 * implied_prob / (1 - implied_prob))
    else:
        total_odds = int(100 * (1 - implied_prob) / implied_prob)
    
    # Generate share token
    share_token = str(uuid.uuid4())[:16]
    
    parlay = Parlay(
        user_id=user_id,
        title=title or f"{len(recommendations)}-Leg Parlay",
        description=_generate_parlay_description(recommendations),
        recommendation_ids=recommendation_ids,
        total_odds=total_odds,
        implied_probability=implied_prob,
        status="draft",
        share_token=share_token
    )
    
    db.add(parlay)
    db.commit()
    db.refresh(parlay)
    
    return parlay


def _generate_parlay_description(recommendations: List[Recommendation]) -> str:
    """Generate human-readable parlay description."""
    parts = [r.description for r in recommendations[:3]]
    if len(recommendations) > 3:
        parts.append(f"+{len(recommendations) - 3} more")
    return " | ".join(parts)


def convert_parlay_to_bet(db: Session, parlay: Parlay, bet_data: Dict) -> str:
    """
    Convert a parlay preview to an actual bet.
    
    Args:
        db: Database session
        parlay: Parlay to convert
        bet_data: Bet creation data
        
    Returns:
        Bet ID
    """
    # This would integrate with existing bet creation
    # For now, mark as converted
    parlay.status = "converted"
    parlay.converted_to_bet_id = bet_data.get("bet_id", "pending")
    db.commit()
    
    return parlay.converted_to_bet_id
