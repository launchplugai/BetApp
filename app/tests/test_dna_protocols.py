from types import SimpleNamespace
from uuid import uuid4

from app.services.dna_fragments import build_protocol_dna_fragments
from app.services.dna_protocols import evaluate_tier1_protocols


def _evaluation(correlation_penalty: float = 0.0):
    return SimpleNamespace(
        metrics=SimpleNamespace(correlation_penalty=correlation_penalty),
        correlations=[],
    )


def _correlation(type_: str, penalty: float = 0.0):
    return SimpleNamespace(
        type=type_,
        penalty=penalty,
        block_a=uuid4(),
        block_b=uuid4(),
    )


def test_injury_instability_can_trigger_from_context_data():
    protocols = evaluate_tier1_protocols(
        input_text="Lakers ML",
        blocks=[object()],
        entities={"markets_detected": [], "same_game_indicator": {"same_game_count": 0}},
        evaluation=_evaluation(),
        nba_heuristics=None,
        context_data={
            "impact": {
                "modifiers": [
                    {
                        "adjustment": -0.05,
                        "reason": "Anthony Davis (LAL): questionable - Right knee",
                        "affected_players": ["Anthony Davis"],
                    }
                ]
            },
            "missing_data": [],
        },
    )

    injury_protocol = next(p for p in protocols if p.id == "matchup_injury_instability")
    assert injury_protocol.trigger_confidence == 0.89
    assert "Anthony Davis (LAL): questionable - Right knee" in injury_protocol.evidence


def test_injury_instability_includes_context_missing_data_signals():
    protocols = evaluate_tier1_protocols(
        input_text="Lakers ML",
        blocks=[object()],
        entities={"markets_detected": [], "same_game_indicator": {"same_game_count": 0}},
        evaluation=_evaluation(),
        nba_heuristics=None,
        context_data={
            "impact": {"modifiers": []},
            "missing_data": ["availability_source_unreachable", "Using sample data as fallback"],
        },
    )

    injury_protocol = next(p for p in protocols if p.id == "matchup_injury_instability")
    assert "availability_source_unreachable" in injury_protocol.evidence
    assert "Using sample data as fallback" in injury_protocol.evidence


def test_back_to_back_fatigue_uses_explicit_rest_signals():
    protocols = evaluate_tier1_protocols(
        input_text="Lakers ML",
        blocks=[object()],
        entities={"markets_detected": [], "same_game_indicator": {"same_game_count": 0}},
        evaluation=_evaluation(),
        nba_heuristics={
            "context_summary": "Rest: LAL 0d vs BOS 1d",
            "risk_flags": [],
        },
        context_data=None,
    )

    fatigue_protocol = next(p for p in protocols if p.id == "fatigue_back_to_back")
    assert fatigue_protocol.trigger_confidence == 0.88
    assert "Rest: LAL 0d vs BOS 1d" in fatigue_protocol.evidence


def test_back_to_back_fatigue_increases_confidence_when_both_teams_are_on_zero_rest():
    protocols = evaluate_tier1_protocols(
        input_text="Lakers ML",
        blocks=[object()],
        entities={"markets_detected": [], "same_game_indicator": {"same_game_count": 0}},
        evaluation=_evaluation(),
        nba_heuristics={
            "context_summary": "Rest: LAL 0d vs BOS 0d",
            "risk_flags": ["🔴 Both teams on back-to-back (unpredictable)"],
        },
        context_data=None,
    )

    fatigue_protocol = next(p for p in protocols if p.id == "fatigue_back_to_back")
    assert fatigue_protocol.trigger_confidence == 0.93
    assert "🔴 Both teams on back-to-back (unpredictable)" in fatigue_protocol.evidence


def test_pace_mismatch_uses_pace_sensitive_same_game_structure():
    protocols = evaluate_tier1_protocols(
        input_text="Lakers team total over + LeBron points + Davis rebounds",
        blocks=[object(), object(), object()],
        entities={
            "markets_detected": ["total", "points", "rebounds"],
            "same_game_indicator": {"same_game_count": 3},
        },
        evaluation=_evaluation(),
        nba_heuristics=None,
        context_data=None,
    )

    pace_protocol = next(p for p in protocols if p.id == "matchup_pace_mismatch")
    assert pace_protocol.trigger_confidence == 0.78
    assert "Slip stacks same-game pace-sensitive markets." in pace_protocol.evidence
    assert "3 legs from one game raise tempo sensitivity." in pace_protocol.evidence


def test_pace_mismatch_can_still_use_nba_heuristic_summary_when_available():
    protocols = evaluate_tier1_protocols(
        input_text="Game total over 228",
        blocks=[object()],
        entities={
            "markets_detected": ["total"],
            "same_game_indicator": {"same_game_count": 0},
        },
        evaluation=_evaluation(),
        nba_heuristics={
            "context_summary": "Pace edge: one team pushes tempo while the other bleeds transition points",
            "risk_flags": [],
        },
        context_data=None,
    )

    pace_protocol = next(p for p in protocols if p.id == "matchup_pace_mismatch")
    assert pace_protocol.trigger_confidence == 0.66
    assert any("Pace edge:" in item for item in pace_protocol.evidence)


def test_correlation_risk_scales_for_light_dependency():
    evaluation = _evaluation(correlation_penalty=4.0)
    evaluation.correlations = [_correlation("same_game_dependency", penalty=4.0)]

    protocols = evaluate_tier1_protocols(
        input_text="Lakers ML + game over",
        blocks=[object(), object()],
        entities={"markets_detected": ["moneyline", "total"], "same_game_indicator": {"same_game_count": 2}},
        evaluation=evaluation,
        nba_heuristics=None,
        context_data=None,
    )

    correlation_protocol = next(p for p in protocols if p.id == "structure_correlation_risk")
    assert correlation_protocol.trigger_confidence == 0.88
    assert correlation_protocol.impact.fragility_delta == 6


def test_correlation_risk_scales_up_for_heavy_dependency_stack():
    evaluation = _evaluation(correlation_penalty=12.0)
    evaluation.correlations = [
        _correlation("same_player_multi_props", penalty=4.0),
        _correlation("same_game_dependency", penalty=4.0),
        _correlation("market_conflict", penalty=4.0),
    ]

    protocols = evaluate_tier1_protocols(
        input_text="Lakers ML + LeBron over + AD rebounds + game over",
        blocks=[object(), object(), object(), object()],
        entities={"markets_detected": ["moneyline", "points", "rebounds", "total"], "same_game_indicator": {"same_game_count": 4}},
        evaluation=evaluation,
        nba_heuristics=None,
        context_data=None,
    )

    correlation_protocol = next(p for p in protocols if p.id == "structure_correlation_risk")
    assert correlation_protocol.trigger_confidence == 0.95
    assert correlation_protocol.impact.fragility_delta == 14
    assert "Correlation stack is severe enough to materially weaken the slip." in correlation_protocol.evidence


def test_protocols_can_run_from_explicit_dna_fragments_with_minimal_raw_context():
    evaluation = _evaluation(correlation_penalty=9.0)
    evaluation.correlations = [
        _correlation("same_game_dependency", penalty=4.5),
        _correlation("same_player_multi_props", penalty=4.5),
    ]
    fragments = build_protocol_dna_fragments(
        input_text="Lakers ML + LeBron points + game over",
        entities={
            "markets_detected": ["moneyline", "points", "total"],
            "same_game_indicator": {"same_game_count": 3},
        },
        evaluation=evaluation,
        blocks=[object(), object(), object()],
        nba_heuristics={
            "context_summary": "Rest: LAL 0d vs BOS 1d with pace pressure.",
            "risk_flags": ["Back-to-back spot"],
        },
        context_data={
            "impact": {
                "modifiers": [
                    {"adjustment": -0.05, "reason": "LeBron James questionable - ankle management"}
                ]
            },
            "missing_data": [],
        },
    )

    protocols = evaluate_tier1_protocols(
        input_text="Lakers ML",
        blocks=[],
        entities={},
        evaluation=evaluation,
        nba_heuristics=None,
        context_data=None,
        dna_fragments=fragments,
    )

    protocol_ids = {protocol.id for protocol in protocols}
    assert "fatigue_back_to_back" in protocol_ids
    assert "structure_correlation_risk" in protocol_ids
    assert "matchup_pace_mismatch" in protocol_ids
    assert "matchup_injury_instability" in protocol_ids
