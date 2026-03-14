"""
Migration: Create promotion_audit table
Run: python3 migrations/010_create_promotion_audit.py
"""

from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from sqlalchemy import text

from app.models import get_engine
from app.models.promotion_audit import PromotionAuditRecord


def migrate():
    """Create promotion_audit table and indexes."""
    engine = get_engine()
    PromotionAuditRecord.__table__.create(engine, checkfirst=True)

    with engine.connect() as conn:
        try:
            conn.execute(text("CREATE INDEX IF NOT EXISTS idx_promo_proposal_id ON promotion_audit (proposal_id)"))
            conn.execute(text("CREATE INDEX IF NOT EXISTS idx_promo_new_version ON promotion_audit (new_version)"))
            conn.commit()
        except Exception as exc:
            print(f"Index creation skipped: {exc}")

    print("✅ Migration complete: promotion_audit table created")


if __name__ == "__main__":
    migrate()
