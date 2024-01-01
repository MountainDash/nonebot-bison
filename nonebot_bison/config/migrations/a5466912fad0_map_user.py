"""map user

Revision ID: a5466912fad0
Revises: 632b8086bc2b
Create Date: 2023-03-20 01:14:42.623789

"""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.orm import Session
from sqlalchemy.ext.automap import automap_base

# revision identifiers, used by Alembic.
revision = "a5466912fad0"
down_revision = "632b8086bc2b"
branch_labels = None
depends_on = None


def upgrade() -> None:
    Base = automap_base()
    Base.prepare(op.get_bind())
    User = Base.classes.nonebot_bison_user
    with Session(op.get_bind()) as sess:
        users = sess.scalars(sa.select(User)).all()
        for user in users:
            if user.type == "group":
                user.user_target = {"platform_type": "QQ Group", "group_id": user.uid}
            elif user.type == "private":
                user.user_target = {"platform_type": "QQ Private", "user_id": user.uid}
            else:
                sess.delete(user)
        sess.add_all(users)
        sess.commit()


def downgrade() -> None:
    Base = automap_base()
    Base.prepare(op.get_bind())
    User = Base.classes.nonebot_bison_user
    with Session(op.get_bind()) as sess:
        users = sess.scalars(sa.select(User)).all()
        for user in users:
            if user.user_target["platform_type"] == "QQ Group":
                user.uid = user.user_target["group_id"]
                user.type = "group"
            else:
                user.uid = user.user_target["user_id"]
                user.type = "private"
        sess.add_all(users)
        sess.commit()
