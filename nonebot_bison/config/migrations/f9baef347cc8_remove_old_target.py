"""remove_old_target

Revision ID: f9baef347cc8
Revises: 8d3863e9d74b
Create Date: 2023-08-25 00:20:51.511329

"""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.orm import Session
from sqlalchemy.ext.automap import automap_base

# revision identifiers, used by Alembic.
revision = "f9baef347cc8"
down_revision = "8d3863e9d74b"
branch_labels = None
depends_on = None


def upgrade() -> None:
    Base = automap_base()
    Base.prepare(op.get_bind())
    User = Base.classes.nonebot_bison_user
    with Session(op.get_bind()) as sess:
        users = sess.scalars(sa.select(User)).all()
        for user in users:
            if user.user_target["platform_type"] == "Unknow Onebot 12 Platform":
                sess.delete(user)
        sess.commit()


def downgrade() -> None:
    pass
