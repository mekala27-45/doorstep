"""checks, their scores and the audit log

Revision ID: 0001
Revises:
Create Date: 2026-10-22
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "0001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "checks",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("check_id", sa.String(), nullable=False),
        sa.Column("cbsa_code", sa.String(), nullable=False),
        sa.Column("income", sa.Integer(), nullable=False),
        sa.Column("down_share", sa.Float(), nullable=False),
        sa.Column("rate", sa.Float(), nullable=False),
        sa.Column("horizon_years", sa.Integer(), nullable=False),
        sa.Column("quarter", sa.String(), nullable=False),
        sa.Column("median_home", sa.Float(), nullable=False),
        sa.Column("payment", sa.Float(), nullable=False),
        sa.Column("payment_share", sa.Float(), nullable=False),
        sa.Column("affordable_price", sa.Float(), nullable=False),
        sa.Column("affordable_share", sa.Float(), nullable=True),
        sa.Column("breakeven_years", sa.Float(), nullable=True),
        sa.Column("breakeven_low", sa.Float(), nullable=True),
        sa.Column("breakeven_high", sa.Float(), nullable=True),
        sa.Column("expected_next_payment_share", sa.Float(), nullable=False),
        sa.Column("model_version", sa.String(), nullable=False),
        sa.Column("note", sa.String(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_checks_check_id", "checks", ["check_id"], unique=True)
    op.create_index("ix_checks_cbsa_code", "checks", ["cbsa_code"])
    op.create_index("ix_checks_quarter", "checks", ["quarter"])
    op.create_table(
        "check_scores",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("check_id", sa.String(), sa.ForeignKey("checks.check_id"), nullable=False),
        sa.Column("scored_quarter", sa.String(), nullable=False),
        sa.Column("realized_payment_share", sa.Float(), nullable=False),
        sa.Column("absolute_error", sa.Float(), nullable=False),
        sa.Column("price_moved", sa.Float(), nullable=False),
        sa.Column("rate_moved", sa.Float(), nullable=False),
        sa.Column("scored_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_check_scores_check_id", "check_scores", ["check_id"], unique=True)
    op.create_table(
        "audit_log",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("actor", sa.String(), nullable=False),
        sa.Column("action", sa.String(), nullable=False),
        sa.Column("resource", sa.String(), nullable=False),
        sa.Column("resource_id", sa.String(), nullable=False),
        sa.Column("detail", sa.JSON(), nullable=False),
    )
    op.create_index("ix_audit_log_at", "audit_log", ["at"])


def downgrade() -> None:
    op.drop_index("ix_audit_log_at", table_name="audit_log")
    op.drop_table("audit_log")
    op.drop_index("ix_check_scores_check_id", table_name="check_scores")
    op.drop_table("check_scores")
    op.drop_index("ix_checks_quarter", table_name="checks")
    op.drop_index("ix_checks_cbsa_code", table_name="checks")
    op.drop_index("ix_checks_check_id", table_name="checks")
    op.drop_table("checks")
