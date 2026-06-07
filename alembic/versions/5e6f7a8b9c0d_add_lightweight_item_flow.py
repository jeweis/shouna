"""Add lightweight item flow fields

Revision ID: 5e6f7a8b9c0d
Revises: 4d5e6f7a8b9c
Create Date: 2026-05-26 15:55:00.000000

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op


revision: str = "5e6f7a8b9c0d"
down_revision: Union[str, Sequence[str], None] = "4d5e6f7a8b9c"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # 注意：新增带 NOT NULL 的 item_status 列与移除其默认值必须分两个
    # batch_alter_table 块执行。SQLite 的表重建是按"最终schema"一次性
    # 计算 DDL 与数据搬迁的 INSERT 语句的：若在同一个块内既声明
    # server_default="normal" 又随后清除该默认值，Alembic 会用"无默认值
    # 的 NOT NULL"这个最终形态去搬迁旧数据，导致已有行因没有默认值可回填
    # 而触发 NOT NULL 约束失败（IntegrityError）。先在带默认值的状态下
    # 完成建列与回填，再单独清除默认值，才能让旧数据安全过渡。
    with op.batch_alter_table("items") as batch_op:
        batch_op.add_column(sa.Column("item_status", sa.String(), nullable=False, server_default="normal"))
        batch_op.add_column(sa.Column("held_by_user_id", sa.Integer(), nullable=True))
        batch_op.add_column(sa.Column("held_at", sa.DateTime(), nullable=True))
        batch_op.add_column(sa.Column("hold_note", sa.Text(), nullable=True))
        batch_op.add_column(sa.Column("last_location_id", sa.Integer(), nullable=True))
        batch_op.create_foreign_key(
            "fk_items_held_by_user_id_users",
            "users",
            ["held_by_user_id"],
            ["id"],
            ondelete="SET NULL",
        )
        batch_op.create_foreign_key(
            "fk_items_last_location_id_locations",
            "locations",
            ["last_location_id"],
            ["id"],
            ondelete="SET NULL",
        )

    with op.batch_alter_table("items") as batch_op:
        batch_op.alter_column("item_status", server_default=None)


def downgrade() -> None:
    """Downgrade schema."""
    with op.batch_alter_table("items") as batch_op:
        batch_op.drop_constraint("fk_items_last_location_id_locations", type_="foreignkey")
        batch_op.drop_constraint("fk_items_held_by_user_id_users", type_="foreignkey")
        batch_op.drop_column("last_location_id")
        batch_op.drop_column("hold_note")
        batch_op.drop_column("held_at")
        batch_op.drop_column("held_by_user_id")
        batch_op.drop_column("item_status")
