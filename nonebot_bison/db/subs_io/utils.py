from typing import Any

from sqlalchemy.orm import DeclarativeBase


class NBESFVerMatchErr(Exception): ...


class NBESFParseErr(Exception): ...


def row2dict(row: DeclarativeBase) -> dict[str, Any]:
    d = {}
    for column in row.__table__.columns:
        d[column.name] = str(getattr(row, column.name))

    return d
