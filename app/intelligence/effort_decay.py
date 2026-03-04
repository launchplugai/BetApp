"""
Effort Decay Modeling

Bounded effort modifiers based on situational context.
No narrative. Pure signal aggregation.
"""

from typing import Optional


def calculate_effort_decay_modifier(
    games_played_last_14: int = 5,
    minutes_avg_last_5: float = 32.0,
    travel_miles_last_week: float = 0.0,
    is_back_to_back: bool = False,
    is_4_in_5_nights: bool = False,
    team_competitive_state: str = "contending",
    player_age: float = 27.0,
) -> float:
    """
    Calculate effort decay modifier for projection adjustments.
    Returns 0.8 - 1.0 (never below 0.8 to prevent extreme overcorrection).
    
    Factors (all bounded):
    - Fatigue (40%): recent games + minutes load
    - Travel (20%): miles accumulated
    - Schedule density (25%): B2B, 4-in-5
    - Context (15%): competitive state + age
    """
    # Guardrails on inputs
    games_played_last_14 = max(0, min(14, games_played_last_14))
    minutes_avg_last_5 = max(0.0, min(48.0, minutes_avg_last_5))
    travel_miles_last_week = max(0.0, min(10000.0, travel_miles_last_week))
    player_age = max(18.0, min(42.0, player_age))
    
    # Fatigue component (0.0 - 1.0, 1.0 = no fatigue)
    game_load = games_played_last_14 / 14  # normalized
    minute_load = minutes_avg_last_5 / 40   # normalized (40 min = heavy)
    fatigue_raw = 1.0 - ((game_load * 0.5) + (minute_load * 0.5))
    fatigue_component = max(0.0, min(1.0, fatigue_raw)) * 0.40
    
    # Travel component (0.0 - 1.0)
    # 3000+ miles in a week is heavy travel
    travel_penalty = min(1.0, travel_miles_last_week / 5000)
    travel_component = (1.0 - travel_penalty) * 0.20
    
    # Schedule density component (0.0 - 1.0)
    density_penalty = 0.0
    if is_4_in_5_nights:
        density_penalty = 0.30  # severe
    elif is_back_to_back:
        density_penalty = 0.15  # moderate
    density_component = (1.0 - density_penalty) * 0.25
    
    # Context component (0.0 - 1.0)
    context_bonus = 0.0
    if team_competitive_state == "contending":
        context_bonus = 0.10
    elif team_competitive_state == "playoff_hunting":
        context_bonus = 0.05
    
    # Age penalty: older players fatigue faster (minor effect)
    age_penalty = max(0.0, (player_age - 32) / 100)  # small linear penalty
    
    context_raw = 0.85 + context_bonus - age_penalty
    context_component = max(0.0, min(1.0, context_raw)) * 0.15
    
    # Aggregate
    total = fatigue_component + travel_component + density_component + context_component
    
    # Bound to [0.8, 1.0] - never too extreme
    return round(min(1.0, max(0.8, total)), 4)


def fatigue_rest_interaction(
    base_effort_modifier: float,
    rest_days: int = 1,
    is_home: bool = True,
) -> float:
    """
    Fine-tune effort modifier based on rest context.
    Applies small adjustments within the 0.8-1.0 bounds.
    """
    # Guardrails
    base_effort_modifier = max(0.8, min(1.0, base_effort_modifier))
    rest_days = max(0, min(5, rest_days))
    
    # Rest bonus: diminishing returns after 2 days
    rest_bonus = min(0.05, rest_days * 0.03)
    
    # Home court advantage (minor)
    home_bonus = 0.02 if is_home else 0.0
    
    adjusted = base_effort_modifier + rest_bonus + home_bonus
    return round(min(1.0, max(0.8, adjusted)), 4)