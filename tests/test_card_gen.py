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
        LiveContent,
        RepostContent,
        VideoContent,
    )

    header = CardHeader(
        face="quote.png", name="缪尔赛思", desc="泰拉历 xxxx-yy-zz hh:mm:ss", platform="TBS"
    )

    common = CommonContent(text="miumiu")

    video = VideoContent(
        text="miumiu",
        cover="quote.png",
        title="miumiu",
        brief="miumiu",
        category="miumiu",
    )

    live = LiveContent(
        text="miumiu",
        cover="quote.png",
    )

    card_gen = partial(Card, header=header)
    repost = RepostContent(
        text="miumiu", repost=card_gen(type="common", content=common)
    )

    with pytest.raises(pydantic.ValidationError):
        card_gen(type="common", content=video)

    with pytest.raises(pydantic.ValidationError):
        card_gen(type="video", content=common)

    with pytest.raises(pydantic.ValidationError):
        card_gen(type="repost", content=live)

    with pytest.raises(pydantic.ValidationError):
        card_gen(type="video", content=repost)

    with pytest.raises(pydantic.ValidationError):
        card_gen(type="live", content=repost)


@pytest.mark.asyncio
async def test_card_nested_repost(app: App):
    from nonebot_bison.post.types import Card, CardHeader, RepostContent, VideoContent

    header = CardHeader(
        face="quote.png", name="缪尔赛思", desc="泰拉历 xxxx-yy-zz hh:mm:ss", platform="TBS"
    )

    video = VideoContent(
        text="miumiu",
        cover="quote.png",
        title="miumiu",
        brief="miumiu",
        category="miumiu",
    )

    card_gen = partial(Card, header=header)
    video_card = card_gen(type="video", content=video)
    repost = RepostContent(text="miumiu", repost=video_card)

    repost_card = card_gen(type="repost", content=repost)

    # nested repost card
    with pytest.raises(pydantic.ValidationError):
        card_gen(type="repost", content=repost_card)

    # nested repost content
    with pytest.raises(pydantic.ValidationError):
        RepostContent(text="miumiumiu", repost=repost_card)
