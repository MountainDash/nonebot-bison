"""init_db

迁移 ID: 0f2a5973c8ae
父迁移:
创建时间: 2025-03-03 20:02:32.225092

"""

from __future__ import annotations

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = "0f2a5973c8ae"
down_revision: str | Sequence[str] | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade(name: str = "") -> None:
    if name:
        return
    # ### commands auto generated by Alembic - please adjust! ###
    op.create_table(
        "nonebot_bison_cookie",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("site_name", sa.String(length=100), nullable=False),
        sa.Column("content", sa.String(length=1024), nullable=False),
        sa.Column("cookie_name", sa.String(length=1024), nullable=False),
        sa.Column("last_usage", sa.DateTime(), nullable=False),
        sa.Column("status", sa.String(length=20), nullable=False),
        sa.Column("cd_milliseconds", sa.Integer(), nullable=False),
        sa.Column("is_universal", sa.Boolean(), nullable=False),
        sa.Column("is_anonymous", sa.Boolean(), nullable=False),
        sa.Column(
            "tags", sa.JSON().with_variant(postgresql.JSONB(astext_type=sa.Text()), "postgresql"), nullable=False
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_nonebot_bison_cookie")),
        info={"bind_key": "nonebot_bison"},
    )
    op.create_table(
        "nonebot_bison_target",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("platform_name", sa.String(length=20), nullable=False),
        sa.Column("target", sa.String(length=1024), nullable=False),
        sa.Column("target_name", sa.String(length=1024), nullable=False),
        sa.Column("default_schedule_weight", sa.Integer(), nullable=False),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_nonebot_bison_target")),
        sa.UniqueConstraint("target", "platform_name", name="unique-target-constraint"),
        info={"bind_key": "nonebot_bison"},
    )
    op.create_table(
        "nonebot_bison_user",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column(
            "user_target", sa.JSON().with_variant(postgresql.JSONB(astext_type=sa.Text()), "postgresql"), nullable=False
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_nonebot_bison_user")),
        info={"bind_key": "nonebot_bison"},
    )
    op.create_table(
        "nonebot_bison_cookietarget",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("target_id", sa.Integer(), nullable=False),
        sa.Column("cookie_id", sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(
            ["cookie_id"],
            ["nonebot_bison_cookie.id"],
            name=op.f("fk_nonebot_bison_cookietarget_cookie_id_nonebot_bison_cookie"),
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["target_id"],
            ["nonebot_bison_target.id"],
            name=op.f("fk_nonebot_bison_cookietarget_target_id_nonebot_bison_target"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_nonebot_bison_cookietarget")),
        info={"bind_key": "nonebot_bison"},
    )
    op.create_table(
        "nonebot_bison_scheduletimeweight",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("target_id", sa.Integer(), nullable=False),
        sa.Column("start_time", sa.Time(), nullable=False),
        sa.Column("end_time", sa.Time(), nullable=False),
        sa.Column("weight", sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(
            ["target_id"],
            ["nonebot_bison_target.id"],
            name=op.f("fk_nonebot_bison_scheduletimeweight_target_id_nonebot_bison_target"),
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_nonebot_bison_scheduletimeweight")),
        info={"bind_key": "nonebot_bison"},
    )
    op.create_table(
        "nonebot_bison_subscribe",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("target_id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("categories", sa.JSON(), nullable=False),
        sa.Column("tags", sa.JSON(), nullable=False),
        sa.ForeignKeyConstraint(
            ["target_id"],
            ["nonebot_bison_target.id"],
            name=op.f("fk_nonebot_bison_subscribe_target_id_nonebot_bison_target"),
        ),
        sa.ForeignKeyConstraint(
            ["user_id"], ["nonebot_bison_user.id"], name=op.f("fk_nonebot_bison_subscribe_user_id_nonebot_bison_user")
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_nonebot_bison_subscribe")),
        sa.UniqueConstraint("target_id", "user_id", name="unique-subscribe-constraint"),
        info={"bind_key": "nonebot_bison"},
    )
    # ### end Alembic commands ###


def downgrade(name: str = "") -> None:
    if name:
        return
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_table("nonebot_bison_subscribe")
    op.drop_table("nonebot_bison_scheduletimeweight")
    op.drop_table("nonebot_bison_cookietarget")
    op.drop_table("nonebot_bison_user")
    op.drop_table("nonebot_bison_target")
    op.drop_table("nonebot_bison_cookie")
    # ### end Alembic commands ###
