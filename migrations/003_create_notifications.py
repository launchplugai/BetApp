"""
Migration: Create notifications tables
Run: python3 migrations/003_create_notifications.py
"""

import sys
sys.path.insert(0, '/root/.openclaw/workspace/DNA')

from app.models import Base, get_engine
from app.models.notification import Notification
from app.models.notification_preferences import NotificationPreferences
from app.models.user_device import UserDevice

def migrate():
    """Create notifications tables."""
    engine = get_engine()
    
    # Create tables
    Notification.__table__.create(engine, checkfirst=True)
    NotificationPreferences.__table__.create(engine, checkfirst=True)
    UserDevice.__table__.create(engine, checkfirst=True)
    
    print("✅ Migration complete: notifications tables created")

if __name__ == "__main__":
    migrate()
