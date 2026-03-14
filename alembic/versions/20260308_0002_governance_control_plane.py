"""create governance control-plane tables

Revision ID: 20260308_0002
Revises: 20260308_0001
Create Date: 2026-03-08 21:35:00
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "20260308_0002"
down_revision = "20260308_0001"
branch_labels = None
depends_on = None


def _table_exists(table_name: str) -> bool:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    return table_name in inspector.get_table_names()


def _index_exists(table_name: str, index_name: str) -> bool:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    return any(index["name"] == index_name for index in inspector.get_indexes(table_name))


def upgrade() -> None:
    if not _table_exists("model_registry"):
        op.create_table(
            "model_registry",
            sa.Column("id", sa.String(), nullable=False),
            sa.Column("entity_type", sa.String(), nullable=False),
            sa.Column("entity_name", sa.String(), nullable=False),
            sa.Column("version", sa.String(), nullable=False),
            sa.Column("status", sa.String(), nullable=False),
            sa.Column("scope", sa.JSON(), nullable=False),
            sa.Column("created_at", sa.DateTime(), nullable=False),
            sa.Column("promoted_at", sa.DateTime(), nullable=True),
            sa.Column("rollback_version", sa.String(), nullable=True),
            sa.Column("source_proposal_id", sa.String(), nullable=True),
            sa.Column("metadata", sa.JSON(), nullable=False),
            sa.PrimaryKeyConstraint("id"),
        )

    if not _index_exists("model_registry", "ix_model_registry_entity_type"):
        op.create_index("ix_model_registry_entity_type", "model_registry", ["entity_type"], unique=False)
    if not _index_exists("model_registry", "ix_model_registry_version"):
        op.create_index("ix_model_registry_version", "model_registry", ["version"], unique=False)
    if not _index_exists("model_registry", "ix_model_registry_status"):
        op.create_index("ix_model_registry_status", "model_registry", ["status"], unique=False)
    if not _index_exists("model_registry", "ix_model_registry_source_proposal_id"):
        op.create_index(
            "ix_model_registry_source_proposal_id",
            "model_registry",
            ["source_proposal_id"],
            unique=False,
        )

    if not _table_exists("evaluation_logs"):
        op.create_table(
            "evaluation_logs",
            sa.Column("id", sa.String(), nullable=False),
            sa.Column("evaluation_id", sa.String(), nullable=False),
            sa.Column("bet_id", sa.String(), nullable=True),
            sa.Column("user_id", sa.String(), nullable=True),
            sa.Column("timestamp", sa.DateTime(), nullable=False),
            sa.Column("sport", sa.String(), nullable=False),
            sa.Column("market_type", sa.String(), nullable=False),
            sa.Column("bet_type", sa.String(), nullable=True),
            sa.Column("legs", sa.Integer(), nullable=False),
            sa.Column("stake", sa.Integer(), nullable=True),
            sa.Column("odds_snapshot", sa.JSON(), nullable=False),
            sa.Column("best_book", sa.String(), nullable=True),
            sa.Column("edge_score", sa.Integer(), nullable=True),
            sa.Column("confidence_score", sa.Integer(), nullable=False),
            sa.Column("fragility_score", sa.Integer(), nullable=False),
            sa.Column("stability_score", sa.Integer(), nullable=False),
            sa.Column("dna_mode", sa.String(), nullable=False),
            sa.Column("triggered_protocols", sa.JSON(), nullable=False),
            sa.Column("recommendation_type", sa.String(), nullable=False),
            sa.Column("recommendation_details", sa.JSON(), nullable=False),
            sa.Column("user_action", sa.String(), nullable=False),
            sa.Column("final_result", sa.String(), nullable=True),
            sa.Column("legs_won", sa.Integer(), nullable=True),
            sa.Column("legs_lost", sa.Integer(), nullable=True),
            sa.Column("settlement_timestamp", sa.DateTime(), nullable=True),
            sa.Column("dna_model_version", sa.String(), nullable=False),
            sa.Column("protocol_library_version", sa.String(), nullable=False),
            sa.Column("calibration_version", sa.String(), nullable=False),
            sa.Column("recommendation_version", sa.String(), nullable=False),
            sa.Column("metadata", sa.JSON(), nullable=False),
            sa.PrimaryKeyConstraint("id"),
            sa.UniqueConstraint("evaluation_id"),
        )

    for index_name, columns in (
        ("ix_evaluation_logs_evaluation_id", ["evaluation_id"]),
        ("ix_evaluation_logs_bet_id", ["bet_id"]),
        ("ix_evaluation_logs_user_id", ["user_id"]),
        ("ix_evaluation_logs_timestamp", ["timestamp"]),
        ("ix_evaluation_logs_sport", ["sport"]),
        ("ix_evaluation_logs_market_type", ["market_type"]),
        ("idx_eval_logs_sport_market", ["sport", "market_type"]),
        ("idx_eval_logs_user_timestamp", ["user_id", "timestamp"]),
    ):
        if not _index_exists("evaluation_logs", index_name):
            op.create_index(index_name, "evaluation_logs", columns, unique=False)

    if not _table_exists("learning_proposals"):
        op.create_table(
            "learning_proposals",
            sa.Column("id", sa.String(), nullable=False),
            sa.Column("proposal_type", sa.String(), nullable=False),
            sa.Column("created_at", sa.DateTime(), nullable=False),
            sa.Column("status", sa.String(), nullable=False),
            sa.Column("target", sa.JSON(), nullable=False),
            sa.Column("current_value", sa.JSON(), nullable=True),
            sa.Column("proposed_value", sa.JSON(), nullable=True),
            sa.Column("reason", sa.String(), nullable=False),
            sa.Column("evidence", sa.JSON(), nullable=False),
            sa.Column("allowed_range", sa.JSON(), nullable=False),
            sa.Column("model_scope", sa.JSON(), nullable=False),
            sa.Column("review", sa.JSON(), nullable=False),
            sa.Column("metadata", sa.JSON(), nullable=False),
            sa.PrimaryKeyConstraint("id"),
        )

    if not _index_exists("learning_proposals", "ix_learning_proposals_proposal_type"):
        op.create_index("ix_learning_proposals_proposal_type", "learning_proposals", ["proposal_type"], unique=False)
    if not _index_exists("learning_proposals", "ix_learning_proposals_created_at"):
        op.create_index("ix_learning_proposals_created_at", "learning_proposals", ["created_at"], unique=False)
    if not _index_exists("learning_proposals", "ix_learning_proposals_status"):
        op.create_index("ix_learning_proposals_status", "learning_proposals", ["status"], unique=False)

    if not _table_exists("promotion_audit"):
        op.create_table(
            "promotion_audit",
            sa.Column("id", sa.String(), nullable=False),
            sa.Column("proposal_id", sa.String(), nullable=False),
            sa.Column("promoted_at", sa.DateTime(), nullable=False),
            sa.Column("approved_by", sa.String(), nullable=False),
            sa.Column("old_version", sa.String(), nullable=False),
            sa.Column("new_version", sa.String(), nullable=False),
            sa.Column("rollback_version", sa.String(), nullable=True),
            sa.Column("notes", sa.String(), nullable=True),
            sa.Column("metadata", sa.JSON(), nullable=False),
            sa.PrimaryKeyConstraint("id"),
        )

    for index_name, columns in (
        ("ix_promotion_audit_proposal_id", ["proposal_id"]),
        ("ix_promotion_audit_promoted_at", ["promoted_at"]),
        ("ix_promotion_audit_approved_by", ["approved_by"]),
        ("ix_promotion_audit_new_version", ["new_version"]),
        ("idx_promo_proposal_id", ["proposal_id"]),
        ("idx_promo_new_version", ["new_version"]),
    ):
        if not _index_exists("promotion_audit", index_name):
            op.create_index(index_name, "promotion_audit", columns, unique=False)


def downgrade() -> None:
    for table_name, indexes in (
        (
            "promotion_audit",
            [
                "idx_promo_new_version",
                "idx_promo_proposal_id",
                "ix_promotion_audit_new_version",
                "ix_promotion_audit_approved_by",
                "ix_promotion_audit_promoted_at",
                "ix_promotion_audit_proposal_id",
            ],
        ),
        (
            "learning_proposals",
            [
                "ix_learning_proposals_status",
                "ix_learning_proposals_created_at",
                "ix_learning_proposals_proposal_type",
            ],
        ),
        (
            "evaluation_logs",
            [
                "idx_eval_logs_user_timestamp",
                "idx_eval_logs_sport_market",
                "ix_evaluation_logs_market_type",
                "ix_evaluation_logs_sport",
                "ix_evaluation_logs_timestamp",
                "ix_evaluation_logs_user_id",
                "ix_evaluation_logs_bet_id",
                "ix_evaluation_logs_evaluation_id",
            ],
        ),
        (
            "model_registry",
            [
                "ix_model_registry_source_proposal_id",
                "ix_model_registry_status",
                "ix_model_registry_version",
                "ix_model_registry_entity_type",
            ],
        ),
    ):
        if _table_exists(table_name):
            for index_name in indexes:
                if _index_exists(table_name, index_name):
                    op.drop_index(index_name, table_name=table_name)
            op.drop_table(table_name)
