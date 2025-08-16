import anyio

from .channel import Conveyor


def create_dead_letter_conveyor():
    return Conveyor(*anyio.create_memory_object_stream())
