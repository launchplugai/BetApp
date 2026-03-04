"""
Migration: Create user_preferences table
Run: python3 migrations/001_create_user_preferences.py
"""

import sys
sys.path.insert(0, '/root/.openclaw/workspace/DNA')

from app.models import Base, get_engine
from app.models.user_preferences import UserPreferences

def migrate():
    """Create user_preferences table."""
    engine = get_engine()
    
    # Create only the user_preferences table
    UserPreferences.__table__.create(engine, checkfirst=True)
    
    print("✅ Migration complete: user_preferences table created")

if __name__ == "__main__":
    migrate()
