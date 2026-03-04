"""
Intelligence Layer for Incentive Modeling
"""

from enum import Enum
from dataclasses import dataclass
from typing import Optional


class TeamCompetitiveState(str, Enum):
    """Canonical team competitive states."""
    CONTENDING = "contending"
    PLAYOFF_HUNTING = "playoff_hunting"
    PLAY_IN = "play_in"
    TANKING = "tanking"
    RESTING = "resting"
    DEVELOPMENT = "development"


class AlignmentType(str, Enum):
    """Player-team incentive alignment."""
    ALIGNED = "aligned"
    CONFLICTED = "conflicted"
    CONTRACT_CHASE = "contract_chase"
    LOAD_MANAGEMENT = "load_management"
    UNKNOWN = "unknown"


@dataclass(frozen=True)
class IncentiveIntelligence:
    """
    Immutable incentive intelligence packet.
    All scores bounded and deterministic.
    """
    team_competitive_state: TeamCompetitiveState
    tanking_score: float
    rotation_stability_score: float
    alignment_type: AlignmentType
    effort_decay_modifier: float

    def __post_init__(self):
        """Validate all bounds at construction."""
        assert 0.0 <= self.tanking_score <= 1.0, \
            f"tanking_score must be in [0, 1], got {self.tanking_score}"
        assert 0.0 <= self.rotation_stability_score <= 1.0, \
            f"rotation_stability_score must be in [0, 1], got {self.rotation_stability_score}"
        assert 0.8 <= self.effort_decay_modifier <= 1.0, \
            f"effort_decay_modifier must be in [0.8, 1.0], got {self.effort_decay_modifier}"

    def to_dict(self) -> dict:
        """Serialize to evaluation payload format."""
        return {
            "team_competitive_state": self.team_competitive_state.value,
            "tanking_score": round(self.tanking_score, 4),
            "rotation_stability_score": round(self.rotation_stability_score, 4),
            "alignment_type": self.alignment_type.value,
            "effort_decay_modifier": round(self.effort_decay_modifier, 4)
        }


def default_intelligence() -> IncentiveIntelligence:
    """Neutral baseline - no information, no adjustment."""
    return IncentiveIntelligence(
        team_competitive_state=TeamCompetitiveState.CONTENDING,
        tanking_score=0.0,
        rotation_stability_score=0.5,
        alignment_type=AlignmentType.UNKNOWN,
        effort_decay_modifier=1.0
    )
