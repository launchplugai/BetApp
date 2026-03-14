"""
Migration: Create model_registry table
Run: python3 migrations/007_create_model_registry.py
"""

from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from app.models import get_engine
from app.models.model_registry import ModelRegistryEntry


def migrate():
    """Create model_registry table."""
    engine = get_engine()
    ModelRegistryEntry.__table__.create(engine, checkfirst=True)
    print("✅ Migration complete: model_registry table created")


if __name__ == "__main__":
    migrate()
