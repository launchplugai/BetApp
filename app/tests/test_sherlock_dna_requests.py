from types import SimpleNamespace

from app.services.dna_fragments import build_protocol_dna_fragments
from app.services.sherlock_dna_requests import (
    build_nba_protocol_context_request,
    build_nba_protocol_context_response,
)


def _evaluation(correlation_penalty: float = 0.0):
    return SimpleNamespace(
        metrics=SimpleNamespace(correlation_penalty=correlation_penalty),
        correlations=[],
    )


def test_build_nba_protocol_context_request_has_expected_fragment_requirements():
    request = build_nba_protocol_context_request()

    assert request.protocol_bundle_id == "nba_fatigue_injury_pace_v1"
    assert request.sport == "nba"
    assert [item.fragment_type for item in request.requirements] == [
        "team_schedule_context",
        "player_availability",
        "game_tempo_context",
        "market_sensitivity",
    ]


def test_build_nba_protocol_context_response_resolves_expected_fragments():
    evaluation = _evaluation()
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
                "modifiers": [{"adjustment": -0.05, "reason": "LeBron questionable"}]
            },
            "missing_data": [],
        },
    )

    response = build_nba_protocol_context_response(
        input_text="ignored",
        entities={},
        evaluation=evaluation,
        blocks=[],
        nba_heuristics=None,
        context_data=None,
        dna_fragments=fragments,
    )

    assert response.missing_fragments == []
    assert set(response.fragments.keys()) == {
        "team_schedule_context",
        "player_availability",
        "game_tempo_context",
        "market_sensitivity",
    }
    assert response.fragments["team_schedule_context"]["context_summary"].startswith("Rest:")
