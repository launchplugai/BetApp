"""
Migration: Add notification receipts table (S20-P4)
Run: python3 migrations/006_add_notification_receipts.py

Creates notification_receipts table for comprehensive telemetry tracking.
Tracks notification lifecycle from detection through delivery or suppression.
"""

import sys
sys.path.insert(0, '/root/.openclaw/workspace/DNA')

from sqlalchemy import inspect, text
from app.models import Base, get_engine
from app.models.notification_receipt import NotificationReceipt


def migrate():
    """Create notification receipts table."""
    engine = get_engine()

    print("Creating notification_receipts table...")
    NotificationReceipt.__table__.create(engine, checkfirst=True)

    # Create indexes for performance
    with engine.connect() as conn:
        # Index on user_id for user-specific queries
        try:
            conn.execute(text("CREATE INDEX IF NOT EXISTS idx_nr_user_id ON notification_receipts (user_id)"))
            print("✅ Created index on notification_receipts (user_id)")
        except Exception as e:
            print(f"Index creation skipped: {e}")

        # Index on opportunity_id for opportunity lookups
        try:
            conn.execute(text("CREATE INDEX IF NOT EXISTS idx_nr_opportunity_id ON notification_receipts (opportunity_id)"))
            print("✅ Created index on notification_receipts (opportunity_id)")
        except Exception as e:
            print(f"Index creation skipped: {e}")

        # Index on status for status-based queries
        try:
            conn.execute(text("CREATE INDEX IF NOT EXISTS idx_nr_status ON notification_receipts (status)"))
            print("✅ Created index on notification_receipts (status)")
        except Exception as e:
            print(f"Index creation skipped: {e}")

        # Index on created_at for time-based queries
        try:
            conn.execute(text("CREATE INDEX IF NOT EXISTS idx_nr_created_at ON notification_receipts (created_at)"))
            print("✅ Created index on notification_receipts (created_at)")
        except Exception as e:
            print(f"Index creation skipped: {e}")

        # Index on detected_at for detection time queries
        try:
            conn.execute(text("CREATE INDEX IF NOT EXISTS idx_nr_detected_at ON notification_receipts (detected_at)"))
            print("✅ Created index on notification_receipts (detected_at)")
        except Exception as e:
            print(f"Index creation skipped: {e}")

        # Index on updated_at for suppression tracking
        try:
            conn.execute(text("CREATE INDEX IF NOT EXISTS idx_nr_updated_at ON notification_receipts (updated_at)"))
            print("✅ Created index on notification_receipts (updated_at)")
        except Exception as e:
            print(f"Index creation skipped: {e}")

        # Composite index for user + status queries
        try:
            conn.execute(text("CREATE INDEX IF NOT EXISTS idx_nr_user_status ON notification_receipts (user_id, status)"))
            print("✅ Created index on notification_receipts (user_id, status)")
        except Exception as e:
            print(f"Index creation skipped: {e}")

        # Composite index for suppression reason queries
        try:
            conn.execute(text("CREATE INDEX IF NOT EXISTS idx_nr_suppression ON notification_receipts (status, suppression_reason)"))
            print("✅ Created index on notification_receipts (status, suppression_reason)")
        except Exception as e:
            print(f"Index creation skipped: {e}")

        conn.commit()

    print("\n✅ Migration complete: Notification receipts table created")
    print("   - notification_receipts: Tracks notification lifecycle for telemetry")
    print("   - Indexes created for efficient queries on user_id, opportunity_id, status")


if __name__ == "__main__":
    migrate()
