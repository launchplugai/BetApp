"""
User statistics and dashboard data service for S18-B.
"""

from typing import Optional
from sqlalchemy import func
from app.models import get_session, Bet, User


def get_user_stats(user_id: str) -> dict:
    """
    Calculate user statistics from bet history.
    
    Returns:
        {
            total_bets: int,
            total_protocols: int,
            win_rate: float,  # 0-100
            profit_loss: float,
            current_streak: int,
            best_streak: int
        }
    """
    db = get_session()
    
    # Total bets
    total_bets = db.query(Bet).filter(Bet.user_id == user_id).count()
    
    # Wins/losses
    wins = db.query(Bet).filter(
        Bet.user_id == user_id,
        Bet.status == "won"
    ).count()
    
    losses = db.query(Bet).filter(
        Bet.user_id == user_id,
        Bet.status == "lost"
    ).count()
    
    # Win rate
    settled = wins + losses
    win_rate = (wins / settled * 100) if settled > 0 else 0
    
    # Profit/loss
    total_wagered = db.query(func.sum(Bet.wager)).filter(
        Bet.user_id == user_id
    ).scalar() or 0
    
    total_won = db.query(func.sum(Bet.actual_payout)).filter(
        Bet.user_id == user_id,
        Bet.status == "won"
    ).scalar() or 0
    
    profit_loss = total_won - total_wagered
    
    # Streak calculation (current and best)
    bets = db.query(Bet).filter(
        Bet.user_id == user_id,
        Bet.status.in_(["won", "lost"])
    ).order_by(Bet.settled_at.desc()).all()
    
    current_streak = 0
    best_streak = 0
    temp_streak = 0
    
    for i, bet in enumerate(bets):
        if i == 0:
            # Start current streak
            if bet.status == "won":
                current_streak = 1
                temp_streak = 1
        else:
            # Continue streak if same status
            if bet.status == bets[i-1].status:
                temp_streak += 1
                if i == 0:
                    current_streak = temp_streak
            else:
                best_streak = max(best_streak, temp_streak)
                temp_streak = 1
    
    best_streak = max(best_streak, temp_streak, current_streak)
    
    return {
        "total_bets": total_bets,
        "total_protocols": total_bets,  # TODO: Track unique protocols
        "win_rate": round(win_rate, 1),
        "profit_loss": profit_loss,
        "current_streak": current_streak,
        "best_streak": best_streak
    }


def get_recent_bets(user_id: str, limit: int = 5) -> list:
    """Get user's recent bets."""
    db = get_session()
    
    bets = db.query(Bet).filter(
        Bet.user_id == user_id
    ).order_by(Bet.created_at.desc()).limit(limit).all()
    
    return [bet.to_dict() for bet in bets]


def save_bet(
    user_id: str,
    input_text: str,
    legs: list,
    wager: int,
    total_odds: int,
    potential_payout: int,
    verdict: str,
    confidence: int,
    fragility: int
) -> str:
    """
    Save a bet to history.
    
    Returns:
        bet_id
    """
    db = get_session()
    
    bet = Bet(
        user_id=user_id,
        input_text=input_text,
        legs=legs,
        wager=wager,
        total_odds=total_odds,
        potential_payout=potential_payout,
        verdict=verdict,
        confidence=confidence,
        fragility=fragility,
        status="pending"
    )
    
    db.add(bet)
    db.commit()
    db.refresh(bet)
    
    return bet.id
