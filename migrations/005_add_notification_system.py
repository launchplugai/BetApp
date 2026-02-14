"""
Migration: Add notification system tables (S20)
Run: python3 migrations/005_add_notification_system.py

Creates tables for:
- notification_events: Complete notification history and audit trail
- eligible_opportunities: Opportunities matching user DNA criteria
- Updates user_preferences with notification_rules JSON column
"""

import sys
sys.path.insert(0, '/root/.openclaw/workspace/DNA')

from sqlalchemy import Column, String, DateTime, Boolean, JSON, Integer, Float, inspect
from app.models import Base, get_engine
from app.models.notification_event import NotificationEvent
from app.models.eligible_opportunity import EligibleOpportunity
from app.models.user_preferences import UserPreferences


def migrate():
    """Create notification system tables."""
    engine = get_engine()
    
    # Create new tables
    print("Creating notification_events table...")
    NotificationEvent.__table__.create(engine, checkfirst=True)
    
    print("Creating eligible_opportunities table...")
    EligibleOpportunity.__table__.create(engine, checkfirst=True)
    
    # Check if notification_rules column exists in user_preferences
    inspector = inspect(engine)
    columns = [col['name'] for col in inspector.get_columns('user_preferences')]
    
    if 'notification_rules' not in columns:
        print("Adding notification_rules column to user_preferences...")
        # Use raw SQL to add column for SQLite compatibility
        from sqlalchemy import text
        with engine.connect() as conn:
            conn.execute(text("ALTER TABLE user_preferences ADD COLUMN notification_rules JSON DEFAULT '{}'"))
            conn.commit()
        print("✅ Added notification_rules column")
    else:
        print("✅ notification_rules column already exists")
    
    # Create indexes for performance using raw SQL
    from sqlalchemy import text
    
    with engine.connect() as conn:
        # Index on notification_events for user queries
        try:
            conn.execute(text("CREATE INDEX IF NOT EXISTS idx_ne_user_type ON notification_events (user_id, type)"))
            print("✅ Created index on notification_events (user_id, type)")
        except Exception as e:
            print(f"Index creation skipped: {e}")
        
        # Index on notification_events for created_at (for time-based queries)
        try:
            conn.execute(text("CREATE INDEX IF NOT EXISTS idx_ne_created_at ON notification_events (created_at)"))
            print("✅ Created index on notification_events (created_at)")
        except Exception as e:
            print(f"Index creation skipped: {e}")
        
        # Index on notification_events for status (for delivery tracking queries)
        try:
            conn.execute(text("CREATE INDEX IF NOT EXISTS idx_ne_status ON notification_events (status)"))
            print("✅ Created index on notification_events (status)")
        except Exception as e:
            print(f"Index creation skipped: {e}")
        
        # Composite index for user notification history queries
        try:
            conn.execute(text("CREATE INDEX IF NOT EXISTS idx_ne_user_created ON notification_events (user_id, created_at)"))
            print("✅ Created index on notification_events (user_id, created_at)")
        except Exception as e:
            print(f"Index creation skipped: {e}")
        
        # Index on eligible_opportunities for active opportunities
        try:
            conn.execute(text("CREATE INDEX IF NOT EXISTS idx_eo_user_status ON eligible_opportunities (user_id, status)"))
            print("✅ Created index on eligible_opportunities (user_id, status)")
        except Exception as e:
            print(f"Index creation skipped: {e}")
        
        # Index on eligible_opportunities for created_at
        try:
            conn.execute(text("CREATE INDEX IF NOT EXISTS idx_eo_created_at ON eligible_opportunities (created_at)"))
            print("✅ Created index on eligible_opportunities (created_at)")
        except Exception as e:
            print(f"Index creation skipped: {e}")
        
        # Index for protocol queries
        try:
            conn.execute(text("CREATE INDEX IF NOT EXISTS idx_eo_protocol ON eligible_opportunities (protocol_id, detected_at)"))
            print("✅ Created index on eligible_opportunities (protocol_id, detected_at)")
        except Exception as e:
            print(f"Index creation skipped: {e}")
        
        conn.commit()
    
    print("\n✅ Migration complete: Notification system tables created")
    print("   - notification_events: Tracks all notification activity")
    print("   - eligible_opportunities: Stores DNA-matched opportunities")
    print("   - user_preferences.notification_rules: User notification settings")


if __name__ == "__main__":
    migrate()
