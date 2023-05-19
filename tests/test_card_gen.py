from functools import partial

import pydantic
import pytest
from nonebug.app import App


@pytest.mark.asyncio
async def test_card_type_no_match(app: App):
    from nonebot_bison.post.types import (
        Card,
        CardHeader,
        CommonContent,
        RepostContent,
        VideoContent,
    )

    header = CardHeader(
        face="quote.png", name="缪尔赛思", time="泰拉历 xxxx-yy-zz hh:mm:ss", platform="TBS"
    )

    common = CommonContent(text="miumiu")

    video = VideoContent(
        text="miumiu",
        cover="quote.png",
        title="miumiu",
        brief="miumiu",
        category="miumiu",
    )

    card_gen = partial(Card, header=header)

    repost_card_gen = partial(card_gen, type="repost")

    with pytest.raises(pydantic.ValidationError):
        err_card1 = card_gen(type="common", content=video)

    with pytest.raises(pydantic.ValidationError):
        err_card2 = card_gen(type="video", content=common)

    with pytest.raises(pydantic.ValidationError):
        err_card3 = card_gen(type="repost", content=common)

    with pytest.raises(pydantic.ValidationError):
        err_card4 = repost_card_gen(content=repost_card_gen(content=video))

    with pytest.raises(pydantic.ValidationError):
        err_repost = RepostContent(text="miumiu", repost=repost_card_gen(content=video))
