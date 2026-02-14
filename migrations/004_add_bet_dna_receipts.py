"""
Migration: Add DNA receipt columns to bets table
Run: python3 migrations/004_add_bet_dna_receipts.py

Adds columns for S21-E: History Receipts:
- user_dna_snapshot_id: References the DNA snapshot at bet time
- applied_constraints: JSON list of constraints that were applied
- blocked_actions: JSON list of blocked actions with reasons
- risk_profile_at_bet: Risk profile used when placing the bet
"""

import sys
sys.path.insert(0, '/root/.openclaw/workspace/DNA')

from sqlalchemy import Column, String, JSON, inspect
from app.models import get_engine, Base, Bet

def migrate():
    """Add DNA receipt columns to bets table."""
    engine = get_engine()
    
    # Check if columns already exist
    inspector = inspect(engine)
    columns = [col['name'] for col in inspector.get_columns('bets')]
    
    new_columns = []
    
    # Add user_dna_snapshot_id column
    if 'user_dna_snapshot_id' not in columns:
        user_dna_snapshot_id_col = Column('user_dna_snapshot_id', String, nullable=True, index=True)
        user_dna_snapshot_id_col.create(Bet.__table__, populate_default=True)
        new_columns.append('user_dna_snapshot_id')
    
    # Add applied_constraints column
    if 'applied_constraints' not in columns:
        applied_constraints_col = Column('applied_constraints', JSON, default=list)
        applied_constraints_col.create(Bet.__table__, populate_default=True)
        new_columns.append('applied_constraints')
    
    # Add blocked_actions column
    if 'blocked_actions' not in columns:
        blocked_actions_col = Column('blocked_actions', JSON, default=list)
        blocked_actions_col.create(Bet.__table__, populate_default=True)
        new_columns.append('blocked_actions')
    
    # Add risk_profile_at_bet column
    if 'risk_profile_at_bet' not in columns:
        risk_profile_at_bet_col = Column('risk_profile_at_bet', String, nullable=True)
        risk_profile_at_bet_col.create(Bet.__table__, populate_default=True)
        new_columns.append('risk_profile_at_bet')
    
    if new_columns:
        print(f"✅ Migration complete: Added columns {', '.join(new_columns)} to bets table")
    else:
        print("✅ Migration complete: All columns already exist")

if __name__ == "__main__":
    migrate()
