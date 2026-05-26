"""Add item photo metadata

Revision ID: 9a2c1f4d8b7e
Revises: b8eea77d74ad
Create Date: 2026-05-26 00:00:00.000000

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op


revision: str = "9a2c1f4d8b7e"
down_revision: Union[str, Sequence[str], None] = "b8eea77d74ad"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table(
        "item_photos",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("item_id", sa.Integer(), nullable=False),
        sa.Column("family_id", sa.Integer(), nullable=False),
        sa.Column("storage_provider", sa.String(), nullable=False),
        sa.Column("storage_key", sa.String(), nullable=False),
        sa.Column("mime_type", sa.String(), nullable=False),
        sa.Column("size_bytes", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(["family_id"], ["families.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["item_id"], ["items.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("storage_key"),
    )
    op.create_index(op.f("ix_item_photos_family_id"), "item_photos", ["family_id"], unique=False)
    op.create_index(op.f("ix_item_photos_id"), "item_photos", ["id"], unique=False)
    op.create_index(op.f("ix_item_photos_item_id"), "item_photos", ["item_id"], unique=False)
    op.create_index(op.f("ix_item_photos_storage_key"), "item_photos", ["storage_key"], unique=True)


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index(op.f("ix_item_photos_storage_key"), table_name="item_photos")
    op.drop_index(op.f("ix_item_photos_item_id"), table_name="item_photos")
    op.drop_index(op.f("ix_item_photos_id"), table_name="item_photos")
    op.drop_index(op.f("ix_item_photos_family_id"), table_name="item_photos")
    op.drop_table("item_photos")
