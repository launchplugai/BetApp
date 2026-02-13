"""
Migration: Create user_dna_snapshots table
Run: python3 migrations/002_create_user_dna_snapshots.py
"""

import sys
sys.path.insert(0, '/root/.openclaw/workspace/DNA')

from app.models import Base, get_engine
from app.models.user_dna_snapshot import UserDnaSnapshot

def migrate():
    """Create user_dna_snapshots table."""
    engine = get_engine()
    
    # Create only the user_dna_snapshots table
    UserDnaSnapshot.__table__.create(engine, checkfirst=True)
    
    print("✅ Migration complete: user_dna_snapshots table created")

if __name__ == "__main__":
    migrate()
