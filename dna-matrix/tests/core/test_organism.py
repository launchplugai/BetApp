# tests/core/test_organism.py
from datetime import datetime, timezone
import pytest

from core.models.organism import Organism


def test_organism_happy_path_and_api_roundtrip():
    """Test creating organism from API payload and roundtripping."""
    api_payload = {
        "id": "org_7b3f8a2c",
        "organismType": "brand",
        "name": "Apple",
        "tags": ["portfolio:consumer-tech", "sector:hardware"],
        "createdAt": "2025-12-25T00:00:00Z",
        "updatedAt": "2025-12-25T00:00:00Z",
    }

    o = Organism.from_api(api_payload)
    assert o.id == "org_7b3f8a2c"
    assert o.organism_type == "brand"
    assert o.name == "Apple"
    assert o.tags == ["portfolio:consumer-tech", "sector:hardware"]
    assert o.created_at.tzinfo is not None

    back = o.to_api()
    assert back["organismType"] == "brand"
    assert back["createdAt"].endswith("Z")
    assert back["updatedAt"].endswith("Z")


def test_organism_json_roundtrip():
    """Test internal JSON (snake_case) roundtripping."""
    json_payload = {
        "id": "org_abc123",
        "organism_type": "agent",
        "name": "TestAgent",
        "tags": ["test"],
        "created_at": "2025-01-01T00:00:00Z",
        "updated_at": "2025-01-01T00:00:00Z",
    }

    o = Organism.from_json(json_payload)
    assert o.organism_type == "agent"
    
    back = o.to_json()
    assert back["organism_type"] == "agent"
    assert back["created_at"].endswith("Z")


def test_organism_validates_id_prefix():
    """ID must start with org_ prefix."""
    with pytest.raises(ValueError, match="must be a string starting with 'org_'"):
        Organism(
            id="nope_123",
            organism_type="brand",
            name="X",
            tags=[],
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc),
        )


def test_organism_rejects_empty_organism_type():
    """organism_type cannot be empty."""
    with pytest.raises(ValueError, match="organism_type must be a non-empty string"):
        Organism(
            id="org_123",
            organism_type="",
            name="X",
            tags=[],
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc),
        )


def test_organism_rejects_empty_name():
    """name cannot be empty."""
    with pytest.raises(ValueError, match="name must be a non-empty string"):
        Organism(
            id="org_123",
            organism_type="brand",
            name="   ",
            tags=[],
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc),
        )


def test_organism_rejects_updated_before_created():
    """updated_at cannot be before created_at."""
    created = datetime(2025, 1, 2, tzinfo=timezone.utc)
    updated = datetime(2025, 1, 1, tzinfo=timezone.utc)
    with pytest.raises(ValueError, match="updated_at cannot be earlier than created_at"):
        Organism(
            id="org_123",
            organism_type="brand",
            name="X",
            tags=[],
            created_at=created,
            updated_at=updated,
        )


def test_organism_rejects_invalid_tags():
    """tags must be a list of strings."""
    with pytest.raises(TypeError, match="tags must be a list"):
        Organism(
            id="org_123",
            organism_type="brand",
            name="X",
            tags=[1, 2, 3],  # not strings
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc),
        )


def test_organism_is_immutable():
    """Organism is frozen - cannot be modified after creation."""
    o = Organism(
        id="org_123",
        organism_type="brand",
        name="Original",
        tags=[],
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc),
    )
    
    with pytest.raises(AttributeError):
        o.name = "Modified"


def test_organism_handles_naive_datetime():
    """Naive datetimes are treated as UTC."""
    naive_dt = datetime(2025, 1, 1, 12, 0, 0)  # no timezone
    
    o = Organism(
        id="org_123",
        organism_type="brand",
        name="X",
        tags=[],
        created_at=naive_dt,
        updated_at=naive_dt,
    )
    
    assert o.created_at.tzinfo is not None
    assert o.created_at.tzinfo == timezone.utc


def test_organism_default_timestamps():
    """Default timestamps are set to now if not provided."""
    before = datetime.now(timezone.utc)
    
    o = Organism(
        id="org_123",
        organism_type="brand",
        name="X",
    )
    
    after = datetime.now(timezone.utc)
    
    assert before <= o.created_at <= after
    assert before <= o.updated_at <= after


def test_organism_equality():
    """Two organisms with same fields are equal."""
    dt = datetime(2025, 1, 1, tzinfo=timezone.utc)
    
    o1 = Organism(
        id="org_123",
        organism_type="brand",
        name="X",
        tags=["a"],
        created_at=dt,
        updated_at=dt,
    )
    
    o2 = Organism(
        id="org_123",
        organism_type="brand",
        name="X",
        tags=["a"],
        created_at=dt,
        updated_at=dt,
    )
    
    assert o1 == o2
