"""Add spatial finding metadata

Revision ID: 4d5e6f7a8b9c
Revises: c6f0a1b2d3e4
Create Date: 2026-05-26 01:00:00.000000

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op


revision: str = "4d5e6f7a8b9c"
down_revision: Union[str, Sequence[str], None] = "c6f0a1b2d3e4"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column("locations", sa.Column("relative_position", sa.String(), nullable=True))
    op.add_column("locations", sa.Column("locator_hint", sa.Text(), nullable=True))
    op.add_column("locations", sa.Column("locator_photo_id", sa.Integer(), nullable=True))
    op.add_column("locations", sa.Column("marker_x", sa.Float(), nullable=True))
    op.add_column("locations", sa.Column("marker_y", sa.Float(), nullable=True))
    op.add_column("items", sa.Column("locator_hint", sa.Text(), nullable=True))
    op.add_column("items", sa.Column("marker_x", sa.Float(), nullable=True))
    op.add_column("items", sa.Column("marker_y", sa.Float(), nullable=True))
    op.create_table(
        "location_photos",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("location_id", sa.Integer(), nullable=False),
        sa.Column("family_id", sa.Integer(), nullable=False),
        sa.Column("storage_provider", sa.String(), nullable=False),
        sa.Column("storage_key", sa.String(), nullable=False),
        sa.Column("mime_type", sa.String(), nullable=False),
        sa.Column("size_bytes", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(["family_id"], ["families.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["location_id"], ["locations.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("storage_key"),
    )
    op.create_index(op.f("ix_location_photos_family_id"), "location_photos", ["family_id"], unique=False)
    op.create_index(op.f("ix_location_photos_id"), "location_photos", ["id"], unique=False)
    op.create_index(op.f("ix_location_photos_location_id"), "location_photos", ["location_id"], unique=False)
    op.create_index(op.f("ix_location_photos_storage_key"), "location_photos", ["storage_key"], unique=True)


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index(op.f("ix_location_photos_storage_key"), table_name="location_photos")
    op.drop_index(op.f("ix_location_photos_location_id"), table_name="location_photos")
    op.drop_index(op.f("ix_location_photos_id"), table_name="location_photos")
    op.drop_index(op.f("ix_location_photos_family_id"), table_name="location_photos")
    op.drop_table("location_photos")
    op.drop_column("items", "marker_y")
    op.drop_column("items", "marker_x")
    op.drop_column("items", "locator_hint")
    op.drop_column("locations", "marker_y")
    op.drop_column("locations", "marker_x")
    op.drop_column("locations", "locator_photo_id")
    op.drop_column("locations", "locator_hint")
    op.drop_column("locations", "relative_position")
