"""
Migration: Create learning_proposals table
Run: python3 migrations/009_create_learning_proposals.py
"""

from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from app.models import get_engine
from app.models.learning_proposal import LearningProposal


def migrate():
    """Create learning_proposals table."""
    engine = get_engine()
    LearningProposal.__table__.create(engine, checkfirst=True)
    print("✅ Migration complete: learning_proposals table created")


if __name__ == "__main__":
    migrate()
