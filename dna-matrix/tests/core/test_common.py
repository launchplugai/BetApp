# tests/core/test_common.py
from datetime import datetime, timezone
import pytest

from core.models.common import (
    Value, ValueKind,
    LensRef,
    Actor, ActorType,
    TradeoffEntry,
    Baseline, BaselineMode,
)


class TestValue:
    def test_value_string(self):
        v = Value(kind=ValueKind.STRING, data="hello")
        assert v.kind == ValueKind.STRING
        assert v.data == "hello"

    def test_value_number(self):
        v = Value(kind=ValueKind.NUMBER, data=42.5)
        assert v.data == 42.5

    def test_value_bool(self):
        v = Value(kind=ValueKind.BOOL, data=True)
        assert v.data is True

    def test_value_enum(self):
        v = Value(kind=ValueKind.ENUM, data="luxury")
        assert v.data == "luxury"

    def test_value_json(self):
        v = Value(kind=ValueKind.JSON, data={"nested": [1, 2, 3]})
        assert v.data == {"nested": [1, 2, 3]}

    def test_value_rejects_wrong_type_string(self):
        with pytest.raises(TypeError, match="data must be str for kind=string"):
            Value(kind=ValueKind.STRING, data=123)

    def test_value_rejects_wrong_type_number(self):
        with pytest.raises(TypeError, match="data must be int/float for kind=number"):
            Value(kind=ValueKind.NUMBER, data="not a number")

    def test_value_rejects_wrong_type_bool(self):
        with pytest.raises(TypeError, match="data must be bool for kind=bool"):
            Value(kind=ValueKind.BOOL, data=1)  # int is not bool

    def test_value_from_dict(self):
        v = Value.from_dict({"kind": "enum", "data": "premium"})
        assert v.kind == ValueKind.ENUM
        assert v.data == "premium"

    def test_value_to_dict(self):
        v = Value(kind=ValueKind.NUMBER, data=0.75)
        d = v.to_dict()
        assert d == {"kind": "number", "data": 0.75}

    def test_value_roundtrip(self):
        original = Value(kind=ValueKind.JSON, data={"a": 1, "b": [2, 3]})
        roundtrip = Value.from_dict(original.to_dict())
        assert roundtrip == original


class TestLensRef:
    def test_lens_ref_creation(self):
        lens = LensRef(cluster="brand", key="voice.tone")
        assert lens.cluster == "brand"
        assert lens.key == "voice.tone"

    def test_lens_ref_to_string(self):
        lens = LensRef(cluster="brand", key="voice.tone")
        assert lens.to_string() == "brand.voice.tone"
        assert str(lens) == "brand.voice.tone"

    def test_lens_ref_from_string(self):
        lens = LensRef.from_string("brand.voice.tone")
        assert lens.cluster == "brand"
        assert lens.key == "voice.tone"

    def test_lens_ref_from_string_nested(self):
        lens = LensRef.from_string("product.features.auth.sso")
        assert lens.cluster == "product"
        assert lens.key == "features.auth.sso"

    def test_lens_ref_from_string_invalid(self):
        with pytest.raises(ValueError, match="Invalid lens string"):
            LensRef.from_string("nocluster")

    def test_lens_ref_rejects_empty_cluster(self):
        with pytest.raises(ValueError, match="cluster must be a non-empty string"):
            LensRef(cluster="", key="something")

    def test_lens_ref_rejects_empty_key(self):
        with pytest.raises(ValueError, match="key must be a non-empty string"):
            LensRef(cluster="brand", key="")

    def test_lens_ref_roundtrip(self):
        original = LensRef(cluster="org", key="values.innovation")
        roundtrip = LensRef.from_dict(original.to_dict())
        assert roundtrip.cluster == original.cluster
        assert roundtrip.key == original.key


class TestActor:
    def test_actor_creation(self):
        actor = Actor(type=ActorType.HUMAN, id="usr_alice", label="Alice Chen")
        assert actor.type == ActorType.HUMAN
        assert actor.id == "usr_alice"
        assert actor.label == "Alice Chen"

    def test_actor_from_string_type(self):
        actor = Actor(type="agent", id="agt_001", label="AutoBot")
        assert actor.type == ActorType.AGENT

    def test_actor_rejects_empty_id(self):
        with pytest.raises(ValueError, match="id must be a non-empty string"):
            Actor(type=ActorType.SYSTEM, id="", label="System")

    def test_actor_roundtrip(self):
        original = Actor(type=ActorType.HUMAN, id="usr_bob", label="Bob")
        d = original.to_dict()
        roundtrip = Actor.from_dict(d)
        assert roundtrip.type == original.type
        assert roundtrip.id == original.id
        assert roundtrip.label == original.label


class TestTradeoffEntry:
    def test_tradeoff_creation(self):
        t = TradeoffEntry(
            gave_up={"lens": "brand.accessibility", "delta": -0.2},
            gained={"lens": "brand.exclusivity", "delta": 0.3},
            weight=0.7,
            cost="reduced reach",
            justification="brand integrity"
        )
        assert t.weight == 0.7
        assert t.cost == "reduced reach"

    def test_tradeoff_rejects_invalid_weight(self):
        with pytest.raises(ValueError, match="weight must be between 0.0 and 1.0"):
            TradeoffEntry(
                gave_up={},
                gained={},
                weight=1.5
            )

    def test_tradeoff_roundtrip(self):
        original = TradeoffEntry(
            gave_up={"lens": "a", "delta": -0.1},
            gained={"lens": "b", "delta": 0.2},
            weight=0.5,
            justification="test"
        )
        d = original.to_dict()
        roundtrip = TradeoffEntry.from_dict(d)
        assert roundtrip.gave_up == original.gave_up
        assert roundtrip.gained == original.gained
        assert roundtrip.weight == original.weight


class TestBaseline:
    def test_baseline_snapshot(self):
        b = Baseline(
            mode=BaselineMode.SNAPSHOT,
            ref="clm_old123",
            value=Value(kind=ValueKind.ENUM, data="premium"),
            captured_at=datetime(2024, 6, 1, tzinfo=timezone.utc)
        )
        assert b.mode == BaselineMode.SNAPSHOT
        assert b.value.data == "premium"

    def test_baseline_declared(self):
        b = Baseline(mode=BaselineMode.DECLARED)
        assert b.mode == BaselineMode.DECLARED
        assert b.value is None

    def test_baseline_from_string_mode(self):
        b = Baseline(mode="ideal")
        assert b.mode == BaselineMode.IDEAL

    def test_baseline_roundtrip(self):
        original = Baseline(
            mode=BaselineMode.HISTORICAL,
            value=Value(kind=ValueKind.NUMBER, data=100),
            captured_at=datetime(2020, 1, 1, tzinfo=timezone.utc)
        )
        d = original.to_dict()
        roundtrip = Baseline.from_dict(d)
        assert roundtrip.mode == original.mode
        assert roundtrip.value == original.value
