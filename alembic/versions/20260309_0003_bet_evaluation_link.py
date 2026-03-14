"""add evaluation_id to bets

Revision ID: 20260309_0003
Revises: 20260308_0002
Create Date: 2026-03-09 11:10:00
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa


revision = "20260309_0003"
down_revision = "20260308_0002"
branch_labels = None
depends_on = None


def _table_exists(table_name: str) -> bool:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    return table_name in inspector.get_table_names()


def _column_exists(table_name: str, column_name: str) -> bool:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    return any(column["name"] == column_name for column in inspector.get_columns(table_name))


def _index_exists(table_name: str, index_name: str) -> bool:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    return any(index["name"] == index_name for index in inspector.get_indexes(table_name))


def upgrade() -> None:
    if _table_exists("bets") and not _column_exists("bets", "evaluation_id"):
        op.add_column("bets", sa.Column("evaluation_id", sa.String(), nullable=True))

    if _table_exists("bets") and not _index_exists("bets", "ix_bets_evaluation_id"):
        op.create_index("ix_bets_evaluation_id", "bets", ["evaluation_id"], unique=False)


def downgrade() -> None:
    if _table_exists("bets") and _index_exists("bets", "ix_bets_evaluation_id"):
        op.drop_index("ix_bets_evaluation_id", table_name="bets")
    if _table_exists("bets") and _column_exists("bets", "evaluation_id"):
        op.drop_column("bets", "evaluation_id")
