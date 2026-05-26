"""Add idempotency records

Revision ID: c6f0a1b2d3e4
Revises: 9a2c1f4d8b7e
Create Date: 2026-05-26 00:10:00.000000

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op


revision: str = "c6f0a1b2d3e4"
down_revision: Union[str, Sequence[str], None] = "9a2c1f4d8b7e"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table(
        "idempotency_records",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("family_id", sa.Integer(), nullable=False),
        sa.Column("operation", sa.String(), nullable=False),
        sa.Column("key", sa.String(), nullable=False),
        sa.Column("status_code", sa.Integer(), nullable=False),
        sa.Column("response_body", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("family_id", "operation", "key", name="uq_idempotency_scope"),
    )
    op.create_index(op.f("ix_idempotency_records_family_id"), "idempotency_records", ["family_id"], unique=False)
    op.create_index(op.f("ix_idempotency_records_id"), "idempotency_records", ["id"], unique=False)
    op.create_index(op.f("ix_idempotency_records_key"), "idempotency_records", ["key"], unique=False)
    op.create_index(op.f("ix_idempotency_records_operation"), "idempotency_records", ["operation"], unique=False)


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index(op.f("ix_idempotency_records_operation"), table_name="idempotency_records")
    op.drop_index(op.f("ix_idempotency_records_key"), table_name="idempotency_records")
    op.drop_index(op.f("ix_idempotency_records_id"), table_name="idempotency_records")
    op.drop_index(op.f("ix_idempotency_records_family_id"), table_name="idempotency_records")
    op.drop_table("idempotency_records")
