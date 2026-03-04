"""
Constraint checking service for user DNA preferences.
Checks picks against user constraints and returns violations/warnings.
"""

from typing import List, Dict, Any, Optional
from dataclasses import dataclass
from enum import Enum
from collections import Counter


class ViolationSeverity(str, Enum):
    """Severity levels for constraint violations."""
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"


@dataclass
class ConstraintViolation:
    """A single constraint violation."""
    constraint_type: str
    message: str
    severity: ViolationSeverity
    violated_value: Optional[str] = None
    constraint_value: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "constraint_type": self.constraint_type,
            "message": self.message,
            "severity": self.severity.value,
            "violated_value": self.violated_value,
            "constraint_value": self.constraint_value
        }


class ConstraintChecker:
    """Checks picks against user preferences constraints."""
    
    def __init__(self, preferences: Dict[str, Any]):
        """
        Initialize with user preferences.
        
        Args:
            preferences: UserPreferences.to_dict() output
        """
        self.preferences = preferences
        self.constraints = preferences.get("constraints", {})
        self.risk_profile = preferences.get("risk_profile", "balanced")
    
    def check_picks(self, picks: List[Dict[str, Any]]) -> List[ConstraintViolation]:
        """
        Check a list of picks against all constraints.
        
        Args:
            picks: List of pick dictionaries with game_id, selection, etc.
            
        Returns:
            List of constraint violations (empty if all pass)
        """
        violations = []
        
        # Check max legs
        violations.extend(self._check_max_legs(picks))
        
        # Check same-game correlation
        violations.extend(self._check_correlated_legs(picks))
        
        # Check no unders
        violations.extend(self._check_no_unders(picks))
        
        # Check favorite sports
        violations.extend(self._check_favorite_sports(picks))
        
        # Check avoid teams/players
        violations.extend(self._check_avoid_entities(picks))
        
        # Check odds range
        violations.extend(self._check_odds_range(picks))
        
        # Risk profile specific checks
        violations.extend(self._check_risk_profile(picks))
        
        return violations
    
    def _check_max_legs(self, picks: List[Dict[str, Any]]) -> List[ConstraintViolation]:
        """Check if pick count exceeds max_legs constraint."""
        max_legs = self.constraints.get("max_legs", 6)
        
        if len(picks) > max_legs:
            return [ConstraintViolation(
                constraint_type="max_legs",
                message=f"{len(picks)} legs exceeds your maximum of {max_legs}",
                severity=ViolationSeverity.WARNING,
                violated_value=str(len(picks)),
                constraint_value=str(max_legs)
            )]
        return []
    
    def _check_correlated_legs(self, picks: List[Dict[str, Any]]) -> List[ConstraintViolation]:
        """Check if too many legs come from the same game."""
        max_correlated = self.constraints.get("max_correlated_legs", 2)
        
        # Count legs per game
        game_counts = Counter()
        for pick in picks:
            game_id = pick.get("game_id") or pick.get("gameId")
            if game_id:
                game_counts[game_id] += 1
        
        violations = []
        for game_id, count in game_counts.items():
            if count > max_correlated:
                violations.append(ConstraintViolation(
                    constraint_type="max_correlated_legs",
                    message=f"{count} legs from same game exceeds your limit of {max_correlated}",
                    severity=ViolationSeverity.WARNING,
                    violated_value=str(count),
                    constraint_value=str(max_correlated)
                ))
        
        return violations
    
    def _check_no_unders(self, picks: List[Dict[str, Any]]) -> List[ConstraintViolation]:
        """Check for under bets if no_unders constraint is set."""
        if not self.constraints.get("no_unders", False):
            return []
        
        violations = []
        for pick in picks:
            selection = pick.get("selection", "").lower()
            if "under" in selection or "u" in selection.split():
                violations.append(ConstraintViolation(
                    constraint_type="no_unders",
                    message=f"Under bet detected: '{pick.get('selection')}' violates your 'no unders' preference",
                    severity=ViolationSeverity.WARNING,
                    violated_value=pick.get("selection"),
                    constraint_value="no unders"
                ))
        
        return violations
    
    def _check_favorite_sports(self, picks: List[Dict[str, Any]]) -> List[ConstraintViolation]:
        """Check if picks are from favorite sports only."""
        favorite_sports = self.constraints.get("favorite_sports", [])
        
        if not favorite_sports:
            return []  # No restriction
        
        violations = []
        for pick in picks:
            sport = pick.get("sport", "").upper()
            if sport and sport not in [s.upper() for s in favorite_sports]:
                violations.append(ConstraintViolation(
                    constraint_type="favorite_sports",
                    message=f"{sport} is not in your preferred sports ({', '.join(favorite_sports)})",
                    severity=ViolationSeverity.INFO,
                    violated_value=sport,
                    constraint_value=", ".join(favorite_sports)
                ))
        
        return violations
    
    def _check_avoid_entities(self, picks: List[Dict[str, Any]]) -> List[ConstraintViolation]:
        """Check for teams or players to avoid."""
        avoid_teams = self.constraints.get("avoid_teams", [])
        avoid_players = self.constraints.get("avoid_players", [])
        
        violations = []
        
        for pick in picks:
            selection = pick.get("selection", "").lower()
            
            # Check teams
            for team in avoid_teams:
                if team.lower() in selection:
                    violations.append(ConstraintViolation(
                        constraint_type="avoid_teams",
                        message=f"Selection includes team you avoid: {team}",
                        severity=ViolationSeverity.WARNING,
                        violated_value=pick.get("selection"),
                        constraint_value=team
                    ))
            
            # Check players
            for player in avoid_players:
                if player.lower() in selection:
                    violations.append(ConstraintViolation(
                        constraint_type="avoid_players",
                        message=f"Selection includes player you avoid: {player}",
                        severity=ViolationSeverity.WARNING,
                        violated_value=pick.get("selection"),
                        constraint_value=player
                    ))
        
        return violations
    
    def _check_odds_range(self, picks: List[Dict[str, Any]]) -> List[ConstraintViolation]:
        """Check if odds are within user-specified range."""
        min_odds = self.constraints.get("min_odds")
        max_odds = self.constraints.get("max_odds")
        
        violations = []
        
        for pick in picks:
            odds = pick.get("odds")
            if odds is None:
                continue
            
            # Convert odds to decimal if needed
            try:
                odds_val = float(odds)
            except (ValueError, TypeError):
                continue
            
            if min_odds is not None and odds_val < min_odds:
                violations.append(ConstraintViolation(
                    constraint_type="min_odds",
                    message=f"Odds {odds_val} below your minimum of {min_odds}",
                    severity=ViolationSeverity.INFO,
                    violated_value=str(odds_val),
                    constraint_value=str(min_odds)
                ))
            
            if max_odds is not None and odds_val > max_odds:
                violations.append(ConstraintViolation(
                    constraint_type="max_odds",
                    message=f"Odds {odds_val} above your maximum of {max_odds}",
                    severity=ViolationSeverity.INFO,
                    violated_value=str(odds_val),
                    constraint_value=str(max_odds)
                ))
        
        return violations
    
    def _check_risk_profile(self, picks: List[Dict[str, Any]]) -> List[ConstraintViolation]:
        """Apply risk profile specific checks."""
        violations = []
        
        if self.risk_profile == "conservative":
            # Conservative: warn on high odds (long shots)
            for pick in picks:
                odds = pick.get("odds")
                if odds and float(odds) > 5.0:
                    violations.append(ConstraintViolation(
                        constraint_type="risk_profile",
                        message=f"High odds ({odds}) - long shot bet doesn't match conservative profile",
                        severity=ViolationSeverity.INFO,
                        violated_value=str(odds),
                        constraint_value="conservative (odds > 5.0)"
                    ))
        
        elif self.risk_profile == "aggressive":
            # Aggressive: info on very safe bets (might want more upside)
            for pick in picks:
                odds = pick.get("odds")
                if odds and float(odds) < 1.5:
                    violations.append(ConstraintViolation(
                        constraint_type="risk_profile",
                        message=f"Very low odds ({odds}) - conservative for aggressive profile",
                        severity=ViolationSeverity.INFO,
                        violated_value=str(odds),
                        constraint_value="aggressive (odds < 1.5)"
                    ))
        
        return violations
    
    def get_constraint_summary(self) -> Dict[str, Any]:
        """Get a summary of active constraints."""
        return {
            "risk_profile": self.risk_profile,
            "max_legs": self.constraints.get("max_legs", 6),
            "max_correlated_legs": self.constraints.get("max_correlated_legs", 2),
            "no_unders": self.constraints.get("no_unders", False),
            "favorite_sports": self.constraints.get("favorite_sports", []),
            "min_odds": self.constraints.get("min_odds"),
            "max_odds": self.constraints.get("max_odds"),
            "avoid_teams_count": len(self.constraints.get("avoid_teams", [])),
            "avoid_players_count": len(self.constraints.get("avoid_players", []))
        }


def check_constraints_for_user(picks: List[Dict[str, Any]], 
                                preferences: Dict[str, Any]) -> List[Dict[str, Any]]:
    """
    Convenience function to check constraints and return dict output.
    
    Args:
        picks: List of pick dictionaries
        preferences: User preferences dict
        
    Returns:
        List of violation dictionaries
    """
    checker = ConstraintChecker(preferences)
    violations = checker.check_picks(picks)
    return [v.to_dict() for v in violations]
