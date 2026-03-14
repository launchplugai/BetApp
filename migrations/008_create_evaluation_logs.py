"""
Migration: Create evaluation_logs table
Run: python3 migrations/008_create_evaluation_logs.py
"""

from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from sqlalchemy import text

from app.models import get_engine
from app.models.evaluation_log import EvaluationLog


def migrate():
    """Create evaluation_logs table and indexes."""
    engine = get_engine()
    EvaluationLog.__table__.create(engine, checkfirst=True)

    with engine.connect() as conn:
        try:
            conn.execute(text("CREATE INDEX IF NOT EXISTS idx_eval_logs_timestamp ON evaluation_logs (timestamp)"))
            conn.execute(text("CREATE INDEX IF NOT EXISTS idx_eval_logs_sport_market ON evaluation_logs (sport, market_type)"))
            conn.execute(text("CREATE INDEX IF NOT EXISTS idx_eval_logs_user_timestamp ON evaluation_logs (user_id, timestamp)"))
            conn.commit()
        except Exception as exc:
            print(f"Index creation skipped: {exc}")

    print("✅ Migration complete: evaluation_logs table created")


if __name__ == "__main__":
    migrate()
