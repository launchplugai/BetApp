from types import SimpleNamespace

from app.services.dna_scoring import build_canonical_scoring_payload


def _evaluation(final_fragility: float) -> SimpleNamespace:
    return SimpleNamespace(metrics=SimpleNamespace(final_fragility=final_fragility))


def test_protocol_penalties_raise_fragility_and_reduce_stability():
    payload = build_canonical_scoring_payload(
        evaluation=_evaluation(42.0),
        signal_info={"signal": "yellow", "grade": "C", "fragilityScore": 42},
        triggered_protocols=[
            {
                "name": "Leg Count Risk",
                "impact": {"fragility_delta": 16, "stability_delta": 0, "edge_delta": 0, "volatility_delta": 0},
                "evidence": ["Parlay contains 6 legs."],
            },
            {
                "name": "Pace Mismatch",
                "impact": {"fragility_delta": 0, "stability_delta": 0, "edge_delta": 0, "volatility_delta": 5},
                "evidence": ["Possession tempo mismatch increases scoring variance."],
            },
        ],
        protocol_summary={
            "fragility_penalty": 16,
            "stability_penalty": 0,
            "edge_bonus": 0,
            "volatility_penalty": 5,
        },
        primary_failure={"description": "Too many stacked legs.", "fastestFix": {"description": "Cut the slip down."}},
    )

    assert payload["score_model_version"] == "1.2.0"
    assert payload["scores"]["fragility"] == 60
    assert payload["scores"]["stability"] == 88
    assert payload["components"]["base_fragility"] == 42
    assert payload["components"]["protocol_fragility_penalty"] == 16
    assert payload["components"]["protocol_volatility_penalty"] == 5
    assert payload["components"]["calibration_adjustment"] < 0
    assert payload["explanation"]["risks"][0] == "Too many stacked legs."


def test_signal_baseline_can_create_positive_edge_without_protocol_bonus():
    payload = build_canonical_scoring_payload(
        evaluation=_evaluation(24.0),
        signal_info={"signal": "green", "grade": "B", "fragilityScore": 24},
        triggered_protocols=[],
        protocol_summary={
            "fragility_penalty": 0,
            "stability_penalty": 0,
            "edge_bonus": 0,
            "volatility_penalty": 0,
        },
        primary_failure={},
    )

    assert payload["scores"]["edge"] == 4
    assert payload["components"]["edge_baseline"] == 4
    assert payload["badge"] == "orange"
    assert payload["calibration"]["adjustment"] == 0


def test_high_protocol_risk_pushes_recommendation_to_avoid():
    payload = build_canonical_scoring_payload(
        evaluation=_evaluation(58.0),
        signal_info={"signal": "red", "grade": "D", "fragilityScore": 58},
        triggered_protocols=[
            {
                "name": "Correlation Risk",
                "impact": {"fragility_delta": 10, "stability_delta": 0, "edge_delta": 0, "volatility_delta": 0},
                "evidence": ["3 correlated leg pair(s) detected."],
            },
            {
                "name": "Injury Instability",
                "impact": {"fragility_delta": 5, "stability_delta": -7, "edge_delta": 0, "volatility_delta": 0},
                "evidence": ["Input references injury or availability uncertainty."],
            },
            {
                "name": "Pace Mismatch",
                "impact": {"fragility_delta": 0, "stability_delta": 0, "edge_delta": 0, "volatility_delta": 5},
                "evidence": ["Possession tempo mismatch increases scoring variance."],
            },
        ],
        protocol_summary={
            "fragility_penalty": 15,
            "stability_penalty": 7,
            "edge_bonus": 0,
            "volatility_penalty": 5,
        },
        primary_failure={"description": "Slip is structurally fragile.", "fastestFix": {}},
    )

    assert payload["scores"]["fragility"] >= 75
    assert payload["recommendation"] == "avoid_fragile_structure"
    assert payload["explanation"]["recommendation"] == "avoid_fragile_structure"
    assert payload["components"]["calibration_adjustment"] <= -6
