from weakref import ReferenceType

import anyio

from .channel import Conveyor
from .courier import Courier
from .parcel import DeliveryReceipt, Parcel


def create_dead_letter_conveyor():
    return Conveyor(*anyio.create_memory_object_stream())

async def post_to_courier[T](parcel: Parcel[T]) -> ReferenceType[DeliveryReceipt] | None:
    """将包裹投递到 Courier"""
    courier = Courier.get_instance()
    return await courier.post(parcel)

