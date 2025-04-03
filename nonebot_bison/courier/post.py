from weakref import ReferenceType

from .courier import Courier
from .parcel import DeliveryReceipt, Parcel


async def post_to_courier[T](parcel: Parcel[T]) -> ReferenceType[DeliveryReceipt] | None:
    """将包裹投递到 Courier"""
    courier = Courier.get_instance()
    return await courier.post(parcel)
