"""
Comprehensive tests for constraint checker (S21-D).

Tests all constraint types:
- max_legs enforcement
- no_unders enforcement
- max_correlated_legs
- favorite_sports filtering
- avoid_teams/avoid_players
- odds range constraints
- risk profile warnings
- edge cases
"""

import pytest
from app.services.constraint_checker import (
    ConstraintChecker, 
    ConstraintViolation,
    ViolationSeverity,
    check_constraints_for_user
)


class TestMaxLegsConstraint:
    """Tests for max_legs constraint enforcement."""
    
    def test_max_legs_allows_within_limit(self):
        """Legs within limit should not trigger violation."""
        prefs = {
            "risk_profile": "balanced",
            "constraints": {"max_legs": 3}
        }
        checker = ConstraintChecker(prefs)
        
        picks = [
            {"entity": "Lakers", "market": "moneyline"},
            {"entity": "Warriors", "market": "spread"},
            {"entity": "Celtics", "market": "total"}
        ]
        
        violations = checker._check_max_legs(picks)
        assert len(violations) == 0
    
    def test_max_legs_blocks_excess_legs(self):
        """More legs than max_legs should trigger violation."""
        prefs = {
            "risk_profile": "balanced",
            "constraints": {"max_legs": 2}
        }
        checker = ConstraintChecker(prefs)
        
        picks = [
            {"entity": "Lakers", "market": "moneyline"},
            {"entity": "Warriors", "market": "spread"},
            {"entity": "Celtics", "market": "total"}
        ]
        
        violations = checker._check_max_legs(picks)
        assert len(violations) == 1
        assert violations[0].constraint_type == "max_legs"
        assert "3 legs exceeds your maximum of 2" in violations[0].message
        assert violations[0].severity == ViolationSeverity.WARNING
    
    def test_max_legs_uses_default_of_six(self):
        """Default max_legs should be 6 when not specified."""
        prefs = {
            "risk_profile": "balanced",
            "constraints": {}  # No max_legs specified
        }
        checker = ConstraintChecker(prefs)
        
        picks = [{"entity": f"Team{i}", "market": "moneyline"} for i in range(7)]
        
        violations = checker._check_max_legs(picks)
        assert len(violations) == 1
        assert "6" in violations[0].message  # Default is 6


class TestNoUndersConstraint:
    """Tests for no_unders constraint enforcement."""
    
    def test_no_unders_blocks_under_bets(self):
        """Under bets should be rejected when no_unders is True."""
        prefs = {
            "risk_profile": "balanced",
            "constraints": {"no_unders": True}
        }
        checker = ConstraintChecker(prefs)
        
        picks = [
            {"entity": "Lakers", "market": "total", "selection": "Under 220.5"}
        ]
        
        violations = checker._check_no_unders(picks)
        assert len(violations) == 1
        assert violations[0].constraint_type == "no_unders"
        assert "Under bet detected" in violations[0].message
    
    def test_no_unders_allows_over_bets(self):
        """Over bets should be allowed when no_unders is True."""
        prefs = {
            "risk_profile": "balanced",
            "constraints": {"no_unders": True}
        }
        checker = ConstraintChecker(prefs)
        
        picks = [
            {"entity": "Lakers", "market": "total", "selection": "Over 220.5"}
        ]
        
        violations = checker._check_no_unders(picks)
        assert len(violations) == 0
    
    def test_no_unders_disabled_allows_all(self):
        """When no_unders is False, all bets should be allowed."""
        prefs = {
            "risk_profile": "balanced",
            "constraints": {"no_unders": False}
        }
        checker = ConstraintChecker(prefs)
        
        picks = [
            {"entity": "Lakers", "market": "total", "selection": "Under 220.5"}
        ]
        
        violations = checker._check_no_unders(picks)
        assert len(violations) == 0
    
    def test_no_unders_detects_u_notation(self):
        """Should detect 'U' notation for under bets."""
        prefs = {
            "risk_profile": "balanced",
            "constraints": {"no_unders": True}
        }
        checker = ConstraintChecker(prefs)
        
        picks = [
            {"entity": "Lakers", "market": "total", "selection": "U 220.5"}
        ]
        
        violations = checker._check_no_unders(picks)
        assert len(violations) == 1


class TestMaxCorrelatedLegsConstraint:
    """Tests for max_correlated_legs constraint (same game limit)."""
    
    def test_same_game_legs_within_limit(self):
        """Legs from same game within limit should pass."""
        prefs = {
            "risk_profile": "balanced",
            "constraints": {"max_correlated_legs": 2}
        }
        checker = ConstraintChecker(prefs)
        
        picks = [
            {"entity": "LeBron", "market": "points", "game_id": "game_123"},
            {"entity": "Lakers", "market": "moneyline", "game_id": "game_123"}
        ]
        
        violations = checker._check_correlated_legs(picks)
        assert len(violations) == 0
    
    def test_same_game_legs_exceeds_limit(self):
        """Too many legs from same game should trigger violation."""
        prefs = {
            "risk_profile": "balanced",
            "constraints": {"max_correlated_legs": 2}
        }
        checker = ConstraintChecker(prefs)
        
        picks = [
            {"entity": "LeBron", "market": "points", "game_id": "game_123"},
            {"entity": "AD", "market": "rebounds", "game_id": "game_123"},
            {"entity": "Lakers", "market": "moneyline", "game_id": "game_123"}
        ]
        
        violations = checker._check_correlated_legs(picks)
        assert len(violations) == 1
        assert violations[0].constraint_type == "max_correlated_legs"
        assert "3 legs from same game exceeds your limit of 2" in violations[0].message
    
    def test_different_games_not_correlated(self):
        """Legs from different games should not count as correlated."""
        prefs = {
            "risk_profile": "balanced",
            "constraints": {"max_correlated_legs": 2}
        }
        checker = ConstraintChecker(prefs)
        
        picks = [
            {"entity": "LeBron", "market": "points", "game_id": "game_123"},
            {"entity": "Curry", "market": "points", "game_id": "game_456"},
            {"entity": "Lakers", "market": "moneyline", "game_id": "game_123"}
        ]
        
        violations = checker._check_correlated_legs(picks)
        assert len(violations) == 0
    
    def test_max_correlated_uses_default_of_two(self):
        """Default max_correlated_legs should be 2."""
        prefs = {
            "risk_profile": "balanced",
            "constraints": {}  # No max_correlated_legs
        }
        checker = ConstraintChecker(prefs)
        
        picks = [
            {"entity": "A", "market": "points", "game_id": "game_1"},
            {"entity": "B", "market": "points", "game_id": "game_1"},
            {"entity": "C", "market": "points", "game_id": "game_1"}
        ]
        
        violations = checker._check_correlated_legs(picks)
        assert len(violations) == 1
        assert "2" in violations[0].message  # Default is 2
    
    def test_game_id_alias_gameId(self):
        """Should work with gameId (camelCase) as well."""
        prefs = {
            "risk_profile": "balanced",
            "constraints": {"max_correlated_legs": 2}
        }
        checker = ConstraintChecker(prefs)
        
        picks = [
            {"entity": "A", "market": "points", "gameId": "game_1"},
            {"entity": "B", "market": "points", "gameId": "game_1"},
            {"entity": "C", "market": "points", "gameId": "game_1"}
        ]
        
        violations = checker._check_correlated_legs(picks)
        assert len(violations) == 1


class TestFavoriteSportsConstraint:
    """Tests for favorite_sports filtering."""
    
    def test_sport_in_favorites_allowed(self):
        """Picks from favorite sports should be allowed."""
        prefs = {
            "risk_profile": "balanced",
            "constraints": {"favorite_sports": ["NBA", "NFL"]}
        }
        checker = ConstraintChecker(prefs)
        
        picks = [
            {"entity": "Lakers", "market": "moneyline", "sport": "NBA"}
        ]
        
        violations = checker._check_favorite_sports(picks)
        assert len(violations) == 0
    
    def test_sport_not_in_favorites_warns(self):
        """Picks from non-favorite sports should trigger info warning."""
        prefs = {
            "risk_profile": "balanced",
            "constraints": {"favorite_sports": ["NBA"]}
        }
        checker = ConstraintChecker(prefs)
        
        picks = [
            {"entity": "Yankees", "market": "moneyline", "sport": "MLB"}
        ]
        
        violations = checker._check_favorite_sports(picks)
        assert len(violations) == 1
        assert violations[0].constraint_type == "favorite_sports"
        assert "MLB is not in your preferred sports" in violations[0].message
        assert violations[0].severity == ViolationSeverity.INFO
    
    def test_favorite_sports_case_insensitive(self):
        """Favorite sports matching should be case insensitive."""
        prefs = {
            "risk_profile": "balanced",
            "constraints": {"favorite_sports": ["nba", "nfl"]}
        }
        checker = ConstraintChecker(prefs)
        
        picks = [
            {"entity": "Lakers", "market": "moneyline", "sport": "NBA"}
        ]
        
        violations = checker._check_favorite_sports(picks)
        assert len(violations) == 0
    
    def test_empty_favorite_sports_allows_all(self):
        """Empty favorite_sports list should allow all sports."""
        prefs = {
            "risk_profile": "balanced",
            "constraints": {"favorite_sports": []}
        }
        checker = ConstraintChecker(prefs)
        
        picks = [
            {"entity": "Lakers", "market": "moneyline", "sport": "NBA"},
            {"entity": "Yankees", "market": "moneyline", "sport": "MLB"}
        ]
        
        violations = checker._check_favorite_sports(picks)
        assert len(violations) == 0
    
    def test_no_favorite_sports_constraint_allows_all(self):
        """Missing favorite_sports constraint should allow all sports."""
        prefs = {
            "risk_profile": "balanced",
            "constraints": {}
        }
        checker = ConstraintChecker(prefs)
        
        picks = [
            {"entity": "Lakers", "market": "moneyline", "sport": "NBA"}
        ]
        
        violations = checker._check_favorite_sports(picks)
        assert len(violations) == 0


class TestAvoidTeamsConstraint:
    """Tests for avoid_teams constraint."""
    
    def test_avoided_team_detected(self):
        """Picks including avoided team should trigger warning."""
        prefs = {
            "risk_profile": "balanced",
            "constraints": {"avoid_teams": ["Lakers", "Celtics"]}
        }
        checker = ConstraintChecker(prefs)
        
        picks = [
            {"entity": "LeBron", "market": "points", "selection": "Lakers to win"}
        ]
        
        violations = checker._check_avoid_entities(picks)
        assert len(violations) == 1
        assert violations[0].constraint_type == "avoid_teams"
        assert "Lakers" in violations[0].message
    
    def test_non_avoided_team_allowed(self):
        """Picks not including avoided teams should pass."""
        prefs = {
            "risk_profile": "balanced",
            "constraints": {"avoid_teams": ["Celtics"]}
        }
        checker = ConstraintChecker(prefs)
        
        picks = [
            {"entity": "LeBron", "market": "points", "selection": "Lakers to win"}
        ]
        
        violations = checker._check_avoid_entities(picks)
        assert len(violations) == 0
    
    def test_avoid_teams_case_insensitive(self):
        """Avoid teams matching should be case insensitive."""
        prefs = {
            "risk_profile": "balanced",
            "constraints": {"avoid_teams": ["lakers"]}
        }
        checker = ConstraintChecker(prefs)
        
        picks = [
            {"entity": "LeBron", "market": "points", "selection": "LAKERS to win"}
        ]
        
        violations = checker._check_avoid_entities(picks)
        assert len(violations) == 1


class TestAvoidPlayersConstraint:
    """Tests for avoid_players constraint."""
    
    def test_avoided_player_detected(self):
        """Picks including avoided player should trigger warning."""
        prefs = {
            "risk_profile": "balanced",
            "constraints": {"avoid_players": ["LeBron James", "Steph Curry"]}
        }
        checker = ConstraintChecker(prefs)
        
        picks = [
            {"entity": "LeBron James", "market": "points", "selection": "LeBron James Over 25.5"}
        ]
        
        violations = checker._check_avoid_entities(picks)
        assert len(violations) >= 1
        player_violations = [v for v in violations if v.constraint_type == "avoid_players"]
        assert len(player_violations) == 1
        assert "LeBron James" in player_violations[0].message
    
    def test_non_avoided_player_allowed(self):
        """Picks not including avoided players should pass."""
        prefs = {
            "risk_profile": "balanced",
            "constraints": {"avoid_players": ["Steph Curry"]}
        }
        checker = ConstraintChecker(prefs)
        
        picks = [
            {"entity": "LeBron James", "market": "points", "selection": "LeBron James Over 25.5"}
        ]
        
        violations = checker._check_avoid_entities(picks)
        player_violations = [v for v in violations if v.constraint_type == "avoid_players"]
        assert len(player_violations) == 0


class TestOddsRangeConstraint:
    """Tests for odds range constraints (min_odds, max_odds)."""
    
    def test_odds_above_minimum_allowed(self):
        """Odds above min_odds should pass."""
        prefs = {
            "risk_profile": "balanced",
            "constraints": {"min_odds": 1.5}
        }
        checker = ConstraintChecker(prefs)
        
        picks = [
            {"entity": "Lakers", "market": "moneyline", "odds": 2.0}
        ]
        
        violations = checker._check_odds_range(picks)
        assert len(violations) == 0
    
    def test_odds_below_minimum_warns(self):
        """Odds below min_odds should trigger info."""
        prefs = {
            "risk_profile": "balanced",
            "constraints": {"min_odds": 1.5}
        }
        checker = ConstraintChecker(prefs)
        
        picks = [
            {"entity": "Lakers", "market": "moneyline", "odds": 1.2}
        ]
        
        violations = checker._check_odds_range(picks)
        assert len(violations) == 1
        assert violations[0].constraint_type == "min_odds"
        assert "below your minimum" in violations[0].message
    
    def test_odds_below_maximum_allowed(self):
        """Odds below max_odds should pass."""
        prefs = {
            "risk_profile": "balanced",
            "constraints": {"max_odds": 5.0}
        }
        checker = ConstraintChecker(prefs)
        
        picks = [
            {"entity": "Lakers", "market": "moneyline", "odds": 3.0}
        ]
        
        violations = checker._check_odds_range(picks)
        assert len(violations) == 0
    
    def test_odds_above_maximum_warns(self):
        """Odds above max_odds should trigger info."""
        prefs = {
            "risk_profile": "balanced",
            "constraints": {"max_odds": 5.0}
        }
        checker = ConstraintChecker(prefs)
        
        picks = [
            {"entity": "Lakers", "market": "moneyline", "odds": 10.0}
        ]
        
        violations = checker._check_odds_range(picks)
        assert len(violations) == 1
        assert violations[0].constraint_type == "max_odds"
        assert "above your maximum" in violations[0].message
    
    def test_odds_range_both_constraints(self):
        """Both min and max odds constraints should work together."""
        prefs = {
            "risk_profile": "balanced",
            "constraints": {"min_odds": 1.5, "max_odds": 5.0}
        }
        checker = ConstraintChecker(prefs)
        
        # Within range
        picks_ok = [{"entity": "Lakers", "market": "moneyline", "odds": 2.5}]
        assert len(checker._check_odds_range(picks_ok)) == 0
        
        # Below minimum
        picks_low = [{"entity": "Lakers", "market": "moneyline", "odds": 1.2}]
        assert len(checker._check_odds_range(picks_low)) == 1
        
        # Above maximum
        picks_high = [{"entity": "Lakers", "market": "moneyline", "odds": 10.0}]
        assert len(checker._check_odds_range(picks_high)) == 1


class TestRiskProfileConstraints:
    """Tests for risk profile specific warnings."""
    
    def test_conservative_warns_on_long_shots(self):
        """Conservative profile should warn on high odds (long shots)."""
        prefs = {
            "risk_profile": "conservative",
            "constraints": {}
        }
        checker = ConstraintChecker(prefs)
        
        picks = [
            {"entity": "Underdog", "market": "moneyline", "odds": 10.0}
        ]
        
        violations = checker._check_risk_profile(picks)
        assert len(violations) == 1
        assert violations[0].constraint_type == "risk_profile"
        assert "conservative" in violations[0].message.lower()
        assert "long shot" in violations[0].message.lower()
    
    def test_conservative_allows_safe_bets(self):
        """Conservative profile should allow safe bets (lower odds)."""
        prefs = {
            "risk_profile": "conservative",
            "constraints": {}
        }
        checker = ConstraintChecker(prefs)
        
        picks = [
            {"entity": "Favorite", "market": "moneyline", "odds": 1.5}
        ]
        
        violations = checker._check_risk_profile(picks)
        assert len(violations) == 0
    
    def test_aggressive_warns_on_safe_bets(self):
        """Aggressive profile should warn on very safe bets."""
        prefs = {
            "risk_profile": "aggressive",
            "constraints": {}
        }
        checker = ConstraintChecker(prefs)
        
        picks = [
            {"entity": "Favorite", "market": "moneyline", "odds": 1.2}
        ]
        
        violations = checker._check_risk_profile(picks)
        assert len(violations) == 1
        assert violations[0].constraint_type == "risk_profile"
        assert "aggressive" in violations[0].message.lower()
    
    def test_aggressive_allows_long_shots(self):
        """Aggressive profile should allow long shots."""
        prefs = {
            "risk_profile": "aggressive",
            "constraints": {}
        }
        checker = ConstraintChecker(prefs)
        
        picks = [
            {"entity": "Underdog", "market": "moneyline", "odds": 10.0}
        ]
        
        violations = checker._check_risk_profile(picks)
        assert len(violations) == 0
    
    def test_balanced_no_specific_warnings(self):
        """Balanced profile should not add specific warnings."""
        prefs = {
            "risk_profile": "balanced",
            "constraints": {}
        }
        checker = ConstraintChecker(prefs)
        
        picks = [
            {"entity": "A", "market": "moneyline", "odds": 1.2},
            {"entity": "B", "market": "moneyline", "odds": 10.0}
        ]
        
        violations = checker._check_risk_profile(picks)
        assert len(violations) == 0


class TestEdgeCases:
    """Tests for edge cases and boundary conditions."""
    
    def test_no_preferences_uses_defaults(self):
        """Empty preferences should use sensible defaults."""
        prefs = {}
        checker = ConstraintChecker(prefs)
        
        picks = [
            {"entity": "Lakers", "market": "moneyline"}
        ]
        
        # Should not crash
        violations = checker.check_picks(picks)
        assert isinstance(violations, list)
    
    def test_empty_constraints_allows_all(self):
        """Empty constraints should allow all picks."""
        prefs = {
            "risk_profile": "balanced",
            "constraints": {}
        }
        checker = ConstraintChecker(prefs)
        
        picks = [
            {"entity": "Lakers", "market": "moneyline", "sport": "NBA"},
            {"entity": "Celtics", "market": "spread", "sport": "NBA"},
            {"entity": "Yankees", "market": "moneyline", "sport": "MLB"}
        ]
        
        violations = checker.check_picks(picks)
        assert len(violations) == 0
    
    def test_empty_picks_list(self):
        """Empty picks list should return no violations."""
        prefs = {
            "risk_profile": "balanced",
            "constraints": {"max_legs": 2}
        }
        checker = ConstraintChecker(prefs)
        
        violations = checker.check_picks([])
        assert len(violations) == 0
    
    def test_missing_pick_fields_handled_gracefully(self):
        """Picks with missing fields should be handled gracefully."""
        prefs = {
            "risk_profile": "balanced",
            "constraints": {
                "favorite_sports": ["NBA"],
                "avoid_teams": ["Lakers"]
            }
        }
        checker = ConstraintChecker(prefs)
        
        picks = [
            {"entity": "Lakers"}  # Missing most fields
        ]
        
        # Should not crash
        violations = checker.check_picks(picks)
        assert isinstance(violations, list)
    
    def test_mid_session_preference_update(self):
        """Checker should use current preferences (mid-session updates)."""
        prefs = {
            "risk_profile": "balanced",
            "constraints": {"max_legs": 2}
        }
        checker = ConstraintChecker(prefs)
        
        # First check - within limit
        picks = [
            {"entity": "A", "market": "ml"},
            {"entity": "B", "market": "ml"}
        ]
        assert len(checker.check_picks(picks)) == 0
        
        # Update preferences (simulating mid-session update)
        checker.preferences["constraints"]["max_legs"] = 1
        
        # Same picks now violate
        assert len(checker.check_picks(picks)) == 1
    
    def test_pick_without_game_id_not_correlated(self):
        """Picks without game_id should not count toward correlation limit."""
        prefs = {
            "risk_profile": "balanced",
            "constraints": {"max_correlated_legs": 2}
        }
        checker = ConstraintChecker(prefs)
        
        picks = [
            {"entity": "A", "market": "points"},  # No game_id
            {"entity": "B", "market": "points"},  # No game_id
            {"entity": "C", "market": "points"}   # No game_id
        ]
        
        violations = checker._check_correlated_legs(picks)
        assert len(violations) == 0
    
    def test_multiple_violations_accumulate(self):
        """Multiple constraint violations should all be returned."""
        prefs = {
            "risk_profile": "conservative",
            "constraints": {
                "max_legs": 2,
                "no_unders": True,
                "avoid_teams": ["Lakers"]
            }
        }
        checker = ConstraintChecker(prefs)
        
        picks = [
            {"entity": "Lakers", "market": "total", "selection": "Lakers Under 220.5", "odds": 10.0},
            {"entity": "Warriors", "market": "ml"},
            {"entity": "Celtics", "market": "ml"}  # Exceeds max_legs
        ]
        
        violations = checker.check_picks(picks)
        
        # Should have: max_legs, no_unders, avoid_teams, risk_profile (conservative warning on high odds)
        violation_types = [v.constraint_type for v in violations]
        assert "max_legs" in violation_types
        assert "no_unders" in violation_types
        assert "avoid_teams" in violation_types
        assert "risk_profile" in violation_types


class TestConstraintViolationDataclass:
    """Tests for ConstraintViolation dataclass."""
    
    def test_to_dict_conversion(self):
        """to_dict should convert all fields correctly."""
        violation = ConstraintViolation(
            constraint_type="max_legs",
            message="Too many legs",
            severity=ViolationSeverity.WARNING,
            violated_value="5",
            constraint_value="3"
        )
        
        d = violation.to_dict()
        assert d["constraint_type"] == "max_legs"
        assert d["message"] == "Too many legs"
        assert d["severity"] == "warning"
        assert d["violated_value"] == "5"
        assert d["constraint_value"] == "3"
    
    def test_violation_severity_enum(self):
        """ViolationSeverity enum should have expected values."""
        assert ViolationSeverity.INFO.value == "info"
        assert ViolationSeverity.WARNING.value == "warning"
        assert ViolationSeverity.ERROR.value == "error"


class TestCheckConstraintsForUser:
    """Tests for the check_constraints_for_user convenience function."""
    
    def test_returns_list_of_dicts(self):
        """Should return list of violation dictionaries."""
        prefs = {
            "risk_profile": "balanced",
            "constraints": {"max_legs": 1}
        }
        picks = [
            {"entity": "A", "market": "ml"},
            {"entity": "B", "market": "ml"}
        ]
        
        violations = check_constraints_for_user(picks, prefs)
        
        assert isinstance(violations, list)
        assert len(violations) == 1
        assert isinstance(violations[0], dict)
        assert "constraint_type" in violations[0]
        assert "message" in violations[0]
        assert "severity" in violations[0]
    
    def test_returns_empty_list_when_no_violations(self):
        """Should return empty list when no violations."""
        prefs = {
            "risk_profile": "balanced",
            "constraints": {"max_legs": 5}
        }
        picks = [
            {"entity": "A", "market": "ml"}
        ]
        
        violations = check_constraints_for_user(picks, prefs)
        
        assert violations == []


class TestGetConstraintSummary:
    """Tests for the get_constraint_summary method."""
    
    def test_returns_summary_dict(self):
        """Should return dictionary with constraint summary."""
        prefs = {
            "risk_profile": "conservative",
            "constraints": {
                "max_legs": 3,
                "max_correlated_legs": 2,
                "no_unders": True,
                "favorite_sports": ["NBA"],
                "avoid_teams": ["Lakers"],
                "avoid_players": ["LeBron"],
                "min_odds": 1.5,
                "max_odds": 5.0
            }
        }
        checker = ConstraintChecker(prefs)
        
        summary = checker.get_constraint_summary()
        
        assert summary["risk_profile"] == "conservative"
        assert summary["max_legs"] == 3
        assert summary["max_correlated_legs"] == 2
        assert summary["no_unders"] == True
        assert summary["favorite_sports"] == ["NBA"]
        assert summary["avoid_teams_count"] == 1
        assert summary["avoid_players_count"] == 1
        assert summary["min_odds"] == 1.5
        assert summary["max_odds"] == 5.0
    
    def test_uses_defaults_for_missing_constraints(self):
        """Should use defaults for missing constraints in summary."""
        prefs = {
            "risk_profile": "balanced",
            "constraints": {}
        }
        checker = ConstraintChecker(prefs)
        
        summary = checker.get_constraint_summary()
        
        assert summary["risk_profile"] == "balanced"
        assert summary["max_legs"] == 6  # Default
        assert summary["max_correlated_legs"] == 2  # Default
        assert summary["no_unders"] == False  # Default
        assert summary["favorite_sports"] == []
        assert summary["avoid_teams_count"] == 0
        assert summary["avoid_players_count"] == 0
        assert summary["min_odds"] is None
        assert summary["max_odds"] is None
