from typing import Literal, overload

from pydantic import BaseModel
from nonebot.compat import PYDANTIC_V2

__all__ = ("model_validator", "model_rebuild")


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
