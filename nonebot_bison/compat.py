from typing import Literal, overload

from nonebot.compat import PYDANTIC_V2
from pydantic import BaseModel

__all__ = ("model_rebuild", "model_validator")


if PYDANTIC_V2:
    from pydantic import model_validator as model_validator

    def model_rebuild(model: type[BaseModel]):
        return model.model_rebuild()

else:
    from pydantic import root_validator

    @overload
    def model_validator(*, mode: Literal["before"]): ...

    @overload
    def model_validator(*, mode: Literal["after"]): ...

    def model_validator(*, mode: Literal["before", "after"]):
        return root_validator(pre=mode == "before", allow_reuse=True)

    def model_rebuild(model: type[BaseModel]):
        return model.update_forward_refs()
