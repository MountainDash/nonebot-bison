from collections.abc import Iterable
from typing import override

from nonebot_bison.core.platform import FilterMixin


class NewMessageFilter[RawPost](FilterMixin):
    @override
    async def filter(self, raw_posts: Iterable[RawPost]) -> tuple[RawPost, ...]:
        pass
