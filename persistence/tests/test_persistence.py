# persistence/tests/test_persistence.py
"""Tests for persistence layer."""

import pytest
import os
from datetime import datetime, timedelta
from pathlib import Path

# Set test database path before imports
os.environ["DNA_DB_PATH"] = "/tmp/test_dna.db"

from persistence.db import init_db, get_db, reset_db, get_db_path
from persistence.evaluations import (
    save_evaluation,
    get_evaluation,
    get_evaluation_by_parlay,
    get_evaluation_by_token,
    cleanup_expired,
)
from persistence.shares import (
    create_share,
    get_share,
    delete_share,
    get_shares_for_evaluation,
)
from persistence.alerts import (
    save_alert,
    get_alert,
    get_recent_alerts,
    get_alerts_by_correlation,
    get_alert_count,
    clear_all as clear_all_alerts,
)
from persistence.metrics import (
    record_metric,
    record_counter,
    get_metric_count,
    get_provider_health_summary,
    METRIC_PROVIDER_SUCCESS,
)


@pytest.fixture(autouse=True)
def reset_database():
    """Reset database before and after each test."""
    reset_db()
    init_db()
    yield
    reset_db()


class TestDatabaseInit:
    """Test database initialization."""

    def test_init_creates_tables(self):
        init_db()
        with get_db() as conn:
            # Check tables exist
            tables = conn.execute(
                "SELECT name FROM sqlite_master WHERE type='table'"
            ).fetchall()
            table_names = [t["name"] for t in tables]

            assert "evaluations" in table_names
            assert "shares" in table_names
            assert "alerts" in table_names
            assert "metrics" in table_names

    def test_init_is_idempotent(self):
        init_db()
        init_db()  # Should not raise


class TestEvaluations:
    """Test evaluation storage."""

    def test_save_and_get_evaluation(self):
        eval_id = save_evaluation(
            parlay_id="test-parlay-123",
            tier="best",
            input_text="Lakers -3.5, Celtics ML",
            result={"fragility": 45.5},
        )

        retrieved = get_evaluation(eval_id)

        assert retrieved is not None
        assert retrieved["parlay_id"] == "test-parlay-123"
        assert retrieved["tier"] == "best"
        assert retrieved["input_text"] == "Lakers -3.5, Celtics ML"
        assert retrieved["result"]["fragility"] == 45.5

    def test_get_nonexistent_evaluation(self):
        result = get_evaluation("nonexistent-id")
        assert result is None

    def test_get_evaluation_by_parlay(self):
        save_evaluation(
            parlay_id="parlay-abc",
            tier="good",
            input_text="Test bet",
            result={},
        )

        retrieved = get_evaluation_by_parlay("parlay-abc")

        assert retrieved is not None
        assert retrieved["parlay_id"] == "parlay-abc"

    def test_correlation_id_saved(self):
        eval_id = save_evaluation(
            parlay_id="test-parlay",
            tier="best",
            input_text="Test",
            result={},
            correlation_id="session-xyz",
        )

        retrieved = get_evaluation(eval_id)
        assert retrieved["correlation_id"] == "session-xyz"


class TestShares:
    """Test share functionality."""

    def test_create_share(self):
        # First create an evaluation
        eval_id = save_evaluation(
            parlay_id="share-test-parlay",
            tier="best",
            input_text="Test bet",
            result={"fragility": 30},
        )

        # Create share
        token = create_share(eval_id)

        assert token is not None
        assert len(token) == 8  # Default token length

    def test_create_share_nonexistent_evaluation(self):
        token = create_share("nonexistent-id")
        assert token is None

    def test_get_share(self):
        eval_id = save_evaluation(
            parlay_id="share-parlay",
            tier="best",
            input_text="Test",
            result={},
        )
        token = create_share(eval_id)

        share = get_share(token)

        assert share is not None
        assert share["token"] == token
        assert share["evaluation_id"] == eval_id

    def test_get_evaluation_by_token(self):
        eval_id = save_evaluation(
            parlay_id="token-parlay",
            tier="best",
            input_text="Test bet",
            result={"fragility": 50},
        )
        token = create_share(eval_id)

        # Get evaluation via token
        evaluation = get_evaluation_by_token(token)

        assert evaluation is not None
        assert evaluation["parlay_id"] == "token-parlay"
        assert evaluation["share_token"] == token
        assert evaluation["view_count"] >= 1

    def test_delete_share(self):
        eval_id = save_evaluation(
            parlay_id="delete-test",
            tier="best",
            input_text="Test",
            result={},
        )
        token = create_share(eval_id)

        # Delete
        result = delete_share(token)
        assert result is True

        # Verify deleted
        share = get_share(token)
        assert share is None

    def test_existing_share_returns_same_token(self):
        eval_id = save_evaluation(
            parlay_id="dupe-test",
            tier="best",
            input_text="Test",
            result={},
        )

        token1 = create_share(eval_id)
        token2 = create_share(eval_id)

        assert token1 == token2  # Same token for same evaluation


class TestPersistentAlerts:
    """Test persistent alert storage."""

    def test_save_and_get_alert(self):
        from uuid import uuid4

        alert_id = uuid4()
        save_alert(
            alert_id=alert_id,
            alert_type="player_now_out",
            severity="critical",
            title="LeBron is OUT",
            message="Status changed",
            player_name="LeBron James",
            team="LAL",
        )

        retrieved = get_alert(str(alert_id))

        assert retrieved is not None
        assert retrieved["title"] == "LeBron is OUT"
        assert retrieved["player_name"] == "LeBron James"

    def test_get_recent_alerts(self):
        from uuid import uuid4

        # Add multiple alerts
        for i in range(5):
            save_alert(
                alert_id=uuid4(),
                alert_type="player_now_out",
                severity="critical",
                title=f"Alert {i}",
                message="Test",
            )

        recent = get_recent_alerts(limit=3)

        assert len(recent) == 3

    def test_get_alerts_by_correlation(self):
        from uuid import uuid4

        corr_id = "test-session-123"

        save_alert(
            alert_id=uuid4(),
            alert_type="player_now_out",
            severity="critical",
            title="Alert 1",
            message="Test",
            correlation_id=corr_id,
        )
        save_alert(
            alert_id=uuid4(),
            alert_type="player_now_out",
            severity="warning",
            title="Alert 2",
            message="Test",
            correlation_id=corr_id,
        )
        save_alert(
            alert_id=uuid4(),
            alert_type="player_now_out",
            severity="info",
            title="Alert 3",
            message="Test",
            correlation_id="other-session",
        )

        alerts = get_alerts_by_correlation(corr_id)

        assert len(alerts) == 2

    def test_get_alert_count(self):
        from uuid import uuid4

        clear_all_alerts()

        for i in range(4):
            save_alert(
                alert_id=uuid4(),
                alert_type="player_now_out",
                severity="critical",
                title=f"Alert {i}",
                message="Test",
            )

        count = get_alert_count()
        assert count == 4


class TestMetrics:
    """Test metrics recording."""

    def test_record_metric(self):
        record_metric("test.metric", 42.5, {"label": "value"})

        count = get_metric_count("test.metric")
        assert count >= 1

    def test_record_counter(self):
        record_counter("test.counter")
        record_counter("test.counter")
        record_counter("test.counter")

        count = get_metric_count("test.counter")
        assert count >= 3

    def test_provider_health_summary(self):
        # Record some provider metrics
        record_counter(METRIC_PROVIDER_SUCCESS, {"source": "nba-official"})
        record_counter(METRIC_PROVIDER_SUCCESS, {"source": "nba-official"})

        summary = get_provider_health_summary(since_hours=1)

        assert "success_count" in summary
        assert "fallback_count" in summary
        assert "error_count" in summary
        assert "success_rate" in summary
