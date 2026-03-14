from app.services.dna_fragments import build_protocol_dna_fragments


class _EvaluationStub:
    correlation_count = 2
    correlation_penalty = 9.5


def test_build_protocol_dna_fragments_returns_expected_fragment_types():
    fragments = build_protocol_dna_fragments(
        input_text="LeBron over 27.5 points + Lakers ML",
        entities={
            "same_game_indicator": {"same_game_count": 2},
            "markets_detected": ["points", "moneyline", "total"],
        },
        evaluation=_EvaluationStub(),
        blocks=[{"id": 1}, {"id": 2}],
        nba_heuristics={
            "context_summary": "Both teams on back-to-back with pace pressure.",
            "risk_flags": ["Back-to-back spot", "Pace mismatch possible"],
        },
        context_data={
            "impact": {
                "modifiers": [
                    {"reason": "LeBron questionable", "adjustment": -0.12},
                    {"reason": "Neutral note", "adjustment": 0.0},
                ]
            },
            "missing_data": ["availability fallback used"],
        },
    )

    assert set(fragments.keys()) == {
        "slip_structure",
        "team_schedule_context",
        "player_availability",
        "team_lineup_stability",
        "game_tempo_context",
        "market_sensitivity",
    }

    assert fragments["slip_structure"]["leg_count"] == 2
    assert fragments["slip_structure"]["correlation_count"] == 2
    assert fragments["slip_structure"]["correlation_penalty"] == 9.5
    assert fragments["market_sensitivity"]["has_pace_sensitive_market"] is True
    assert fragments["player_availability"]["negative_modifiers"][0]["reason"] == "LeBron questionable"
    assert fragments["team_schedule_context"]["context_summary"] == "Both teams on back-to-back with pace pressure."
