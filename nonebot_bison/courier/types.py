from collections.abc import Awaitable, Callable
from typing import TYPE_CHECKING, Annotated, Any

from nonebot.dependencies import Dependent

if TYPE_CHECKING:
    from .parcel import Parcel

type DeliveryReceiver[R] = Dependent["Parcel[R] | None"]
type DeliveryReceiverHandle[R] = Callable[..., "Parcel[R] | None"] | Callable[..., Awaitable["Parcel[R] | None"]]

type ChannelName = str

type Address = str


class MetadataFlag:
    def __repr__(self) -> str:
        return "MetadataFlag()"


_METADATA_FLAG = MetadataFlag()

type Metadata = Annotated[dict[str, Any], _METADATA_FLAG]


class DeadReasonFlag:
    def __repr__(self) -> str:
        return "DeadReasonFlag()"


_DEAD_REASON_FLAG = DeadReasonFlag()

type DEAD_REASON = Annotated[str, _DEAD_REASON_FLAG]
