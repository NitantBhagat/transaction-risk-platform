"""Initial transaction risk platform schema.

Revision ID: 0001_initial_schema
Revises: None
Create Date: 2026-03-12
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa


revision = "0001_initial_schema"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "accounts",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("external_id", sa.String(length=64), nullable=False, unique=True),
        sa.Column("status", sa.String(length=32), nullable=False, server_default="active"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )

    op.create_index("ix_accounts_external_id", "accounts", ["external_id"])
    op.create_index("ix_accounts_status", "accounts", ["status"])

    op.create_table(
        "merchants",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("external_id", sa.String(length=64), nullable=False, unique=True),
        sa.Column("name", sa.String(length=255), nullable=True),
        sa.Column("category", sa.String(length=64), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )

    op.create_index("ix_merchants_external_id", "merchants", ["external_id"])

    op.create_table(
        "transactions",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("external_id", sa.String(length=64), nullable=False, unique=True),
        sa.Column("account_id", sa.Integer(), sa.ForeignKey("accounts.id"), nullable=False),
        sa.Column("merchant_id", sa.Integer(), sa.ForeignKey("merchants.id"), nullable=True),
        sa.Column("amount", sa.Numeric(18, 4), nullable=False),
        sa.Column("currency", sa.String(length=3), nullable=False),
        sa.Column("occurred_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("ingested_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False, server_default="pending"),
    )

    op.create_index("ix_transactions_external_id", "transactions", ["external_id"])
    op.create_index("ix_transactions_account_id", "transactions", ["account_id"])
    op.create_index("ix_transactions_merchant_id", "transactions", ["merchant_id"])
    op.create_index("ix_transactions_occurred_at", "transactions", ["occurred_at"])
    op.create_index("ix_transactions_status", "transactions", ["status"])

    op.create_table(
        "risk_evaluations",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column(
            "transaction_id",
            sa.Integer(),
            sa.ForeignKey("transactions.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("score", sa.Numeric(5, 2), nullable=False),
        sa.Column("outcome", sa.String(length=32), nullable=False),
        sa.Column("reason", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )

    op.create_index("ix_risk_evaluations_transaction_id", "risk_evaluations", ["transaction_id"])
    op.create_index("ix_risk_evaluations_score", "risk_evaluations", ["score"])
    op.create_index("ix_risk_evaluations_outcome", "risk_evaluations", ["outcome"])

    op.create_table(
        "alerts",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column(
            "transaction_id",
            sa.Integer(),
            sa.ForeignKey("transactions.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("severity", sa.String(length=16), nullable=False),
        sa.Column("title", sa.String(length=255), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("is_resolved", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("resolved_at", sa.DateTime(timezone=True), nullable=True),
    )

    op.create_index("ix_alerts_transaction_id", "alerts", ["transaction_id"])
    op.create_index("ix_alerts_severity", "alerts", ["severity"])
    op.create_index("ix_alerts_is_resolved", "alerts", ["is_resolved"])

    op.create_table(
        "transaction_audit_logs",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column(
            "transaction_id",
            sa.Integer(),
            sa.ForeignKey("transactions.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("action", sa.String(length=32), nullable=False),
        sa.Column("request_id", sa.String(length=64), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )

    op.create_index(
        "ix_transaction_audit_logs_transaction_id", "transaction_audit_logs", ["transaction_id"]
    )
    op.create_index("ix_transaction_audit_logs_action", "transaction_audit_logs", ["action"])
    op.create_index(
        "ix_transaction_audit_logs_request_id", "transaction_audit_logs", ["request_id"]
    )


def downgrade() -> None:
    op.drop_index("ix_alerts_is_resolved", table_name="alerts")
    op.drop_index("ix_alerts_severity", table_name="alerts")
    op.drop_index("ix_alerts_transaction_id", table_name="alerts")
    op.drop_table("alerts")

    op.drop_index(
        "ix_transaction_audit_logs_request_id", table_name="transaction_audit_logs"
    )
    op.drop_index("ix_transaction_audit_logs_action", table_name="transaction_audit_logs")
    op.drop_index(
        "ix_transaction_audit_logs_transaction_id", table_name="transaction_audit_logs"
    )
    op.drop_table("transaction_audit_logs")

    op.drop_index("ix_risk_evaluations_outcome", table_name="risk_evaluations")
    op.drop_index("ix_risk_evaluations_score", table_name="risk_evaluations")
    op.drop_index("ix_risk_evaluations_transaction_id", table_name="risk_evaluations")
    op.drop_table("risk_evaluations")

    op.drop_index("ix_transactions_status", table_name="transactions")
    op.drop_index("ix_transactions_occurred_at", table_name="transactions")
    op.drop_index("ix_transactions_merchant_id", table_name="transactions")
    op.drop_index("ix_transactions_account_id", table_name="transactions")
    op.drop_index("ix_transactions_external_id", table_name="transactions")
    op.drop_table("transactions")

    op.drop_index("ix_merchants_external_id", table_name="merchants")
    op.drop_table("merchants")

    op.drop_index("ix_accounts_status", table_name="accounts")
    op.drop_index("ix_accounts_external_id", table_name="accounts")
    op.drop_table("accounts")

