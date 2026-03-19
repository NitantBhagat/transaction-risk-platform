"""Add risk assessments table.

Revision ID: 0002_risk_assessments
Revises: 0001_initial_schema
Create Date: 2026-03-12
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa


revision = "0002_risk_assessments"
down_revision = "0001_initial_schema"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "risk_assessments",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column(
            "transaction_id",
            sa.Integer(),
            sa.ForeignKey("transactions.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("event_id", sa.String(length=64), nullable=False, unique=True),
        sa.Column("risk_score", sa.Numeric(5, 2), nullable=False),
        sa.Column("risk_level", sa.String(length=16), nullable=False),
        sa.Column("decision", sa.String(length=16), nullable=False),
        sa.Column("rule_hits", sa.Text(), nullable=False),
        sa.Column("processed_at", sa.DateTime(timezone=True), nullable=False),
    )

    op.create_index(
        "ix_risk_assessments_transaction_id", "risk_assessments", ["transaction_id"]
    )
    op.create_index("ix_risk_assessments_risk_level", "risk_assessments", ["risk_level"])
    op.create_index("ix_risk_assessments_decision", "risk_assessments", ["decision"])


def downgrade() -> None:
    op.drop_index("ix_risk_assessments_decision", table_name="risk_assessments")
    op.drop_index("ix_risk_assessments_risk_level", table_name="risk_assessments")
    op.drop_index("ix_risk_assessments_transaction_id", table_name="risk_assessments")
    op.drop_table("risk_assessments")

