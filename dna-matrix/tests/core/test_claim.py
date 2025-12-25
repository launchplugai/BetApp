# tests/core/test_claim.py
from datetime import datetime, timezone
import pytest

from core.models.common import Value, ValueKind, LensRef, Baseline, BaselineMode
from core.models.claim import Claim


def make_claim(**overrides) -> Claim:
    """Helper to create valid claims with defaults."""
    defaults = {
        "id": "clm_test123",
        "organism_id": "org_abc",
        "lens_id": "lns_voice_tone",
        "lens": LensRef(cluster="brand", key="voice.tone"),
        "value": Value(kind=ValueKind.ENUM, data="luxury"),
        "weight": 0.8,
        "constraints": [],
        "baseline": None,
        "last_mutation_id": None,
        "version": 1,
        "created_at": datetime.now(timezone.utc),
        "updated_at": datetime.now(timezone.utc),
    }
    defaults.update(overrides)
    return Claim(**defaults)


class TestClaimCreation:
    def test_claim_happy_path(self):
        c = make_claim()
        assert c.id == "clm_test123"
        assert c.organism_id == "org_abc"
        assert c.weight == 0.8
        assert c.version == 1

    def test_claim_validates_id_prefix(self):
        with pytest.raises(ValueError, match="must be a string starting with 'clm_'"):
            make_claim(id="bad_id")

    def test_claim_validates_organism_id_prefix(self):
        with pytest.raises(ValueError, match="must be a string starting with 'org_'"):
            make_claim(organism_id="bad_org")

    def test_claim_validates_lens_id_prefix(self):
        with pytest.raises(ValueError, match="must be a string starting with 'lns_'"):
            make_claim(lens_id="bad_lens")

    def test_claim_validates_weight_range(self):
        with pytest.raises(ValueError, match="weight must be between 0.0 and 1.0"):
            make_claim(weight=1.5)

    def test_claim_validates_weight_negative(self):
        with pytest.raises(ValueError, match="weight must be between 0.0 and 1.0"):
            make_claim(weight=-0.1)

    def test_claim_validates_version_positive(self):
        with pytest.raises(ValueError, match="version must be a positive integer"):
            make_claim(version=0)

    def test_claim_validates_last_mutation_id_prefix(self):
        with pytest.raises(ValueError, match="must be a string starting with 'mut_'"):
            make_claim(last_mutation_id="bad_mut")

    def test_claim_is_immutable(self):
        c = make_claim()
        with pytest.raises(AttributeError):
            c.weight = 0.5


class TestClaimWithBaseline:
    def test_claim_with_baseline(self):
        baseline = Baseline(
            mode=BaselineMode.SNAPSHOT,
            value=Value(kind=ValueKind.ENUM, data="premium"),
            captured_at=datetime(2024, 6, 1, tzinfo=timezone.utc)
        )
        c = make_claim(baseline=baseline)
        assert c.baseline is not None
        assert c.baseline.value.data == "premium"

    def test_claim_compute_drift_no_baseline(self):
        c = make_claim(baseline=None)
        assert c.compute_drift() == 0.0

    def test_claim_compute_drift_same_value(self):
        baseline = Baseline(
            mode=BaselineMode.SNAPSHOT,
            value=Value(kind=ValueKind.ENUM, data="luxury")
        )
        c = make_claim(
            value=Value(kind=ValueKind.ENUM, data="luxury"),
            baseline=baseline
        )
        assert c.compute_drift() == 0.0

    def test_claim_compute_drift_different_enum(self):
        baseline = Baseline(
            mode=BaselineMode.SNAPSHOT,
            value=Value(kind=ValueKind.ENUM, data="premium")
        )
        c = make_claim(
            value=Value(kind=ValueKind.ENUM, data="luxury"),
            baseline=baseline
        )
        assert c.compute_drift() == 1.0

    def test_claim_compute_drift_number(self):
        baseline = Baseline(
            mode=BaselineMode.SNAPSHOT,
            value=Value(kind=ValueKind.NUMBER, data=0.5)
        )
        c = make_claim(
            value=Value(kind=ValueKind.NUMBER, data=0.8),
            baseline=baseline
        )
        drift = c.compute_drift()
        assert 0.29 < drift < 0.31  # approximately 0.3

    def test_claim_compute_weighted_drift(self):
        baseline = Baseline(
            mode=BaselineMode.SNAPSHOT,
            value=Value(kind=ValueKind.ENUM, data="premium")
        )
        c = make_claim(
            value=Value(kind=ValueKind.ENUM, data="luxury"),
            baseline=baseline,
            weight=0.5
        )
        assert c.compute_drift() == 1.0
        assert c.compute_weighted_drift() == 0.5


class TestClaimSerialization:
    def test_claim_api_roundtrip(self):
        api_payload = {
            "id": "clm_8x9f2k4m",
            "organismId": "org_7b3f8a2c",
            "lensId": "lns_voice_tone",
            "lens": {"cluster": "brand", "key": "voice.tone"},
            "value": {"kind": "enum", "data": "luxury"},
            "weight": 0.83,
            "constraints": ["cst_enum_check"],
            "baseline": {
                "mode": "snapshot",
                "value": {"kind": "enum", "data": "premium"},
                "capturedAt": "2024-06-01T00:00:00Z"
            },
            "lastMutationId": "mut_abc123",
            "version": 3,
            "createdAt": "2024-06-01T00:00:00Z",
            "updatedAt": "2025-01-20T14:30:00Z",
        }

        c = Claim.from_api(api_payload)
        assert c.organism_id == "org_7b3f8a2c"
        assert c.lens.cluster == "brand"
        assert c.value.data == "luxury"
        assert c.baseline.value.data == "premium"
        assert c.last_mutation_id == "mut_abc123"

        back = c.to_api()
        assert back["organismId"] == "org_7b3f8a2c"
        assert back["lastMutationId"] == "mut_abc123"

    def test_claim_json_roundtrip(self):
        json_payload = {
            "id": "clm_abc",
            "organism_id": "org_xyz",
            "lens_id": "lns_test",
            "lens": {"cluster": "test", "key": "metric"},
            "value": {"kind": "number", "data": 42},
            "weight": 0.5,
            "constraints": [],
            "version": 1,
            "created_at": "2025-01-01T00:00:00Z",
            "updated_at": "2025-01-01T00:00:00Z",
        }

        c = Claim.from_json(json_payload)
        assert c.value.data == 42

        back = c.to_json()
        assert back["organism_id"] == "org_xyz"


class TestClaimMutation:
    def test_with_mutation_creates_new_version(self):
        original = make_claim(version=1)
        new_value = Value(kind=ValueKind.ENUM, data="bold")
        
        mutated = original.with_mutation(
            value=new_value,
            mutation_id="mut_new123"
        )
        
        # Original unchanged
        assert original.version == 1
        assert original.value.data == "luxury"
        
        # Mutated is new version
        assert mutated.version == 2
        assert mutated.value.data == "bold"
        assert mutated.last_mutation_id == "mut_new123"
        assert mutated.id == original.id  # Same claim

    def test_with_mutation_weight_only(self):
        original = make_claim(weight=0.5, version=1)
        
        mutated = original.with_mutation(
            weight=0.9,
            mutation_id="mut_reweight"
        )
        
        assert mutated.weight == 0.9
        assert mutated.value == original.value  # Value unchanged
        assert mutated.version == 2

    def test_with_mutation_baseline(self):
        original = make_claim(baseline=None)
        new_baseline = Baseline(
            mode=BaselineMode.DECLARED,
            value=Value(kind=ValueKind.ENUM, data="current")
        )
        
        mutated = original.with_mutation(
            baseline=new_baseline,
            mutation_id="mut_rebaseline"
        )
        
        assert mutated.baseline is not None
        assert mutated.baseline.mode == BaselineMode.DECLARED
