from nonebug import App


async def test_gen_text(app: App):
    from nonebot_bison.post import Post

    p = Post(
        target_type="bili",
        text="111",
    )
    p_text = await p.generate_text_messages()
    assert p_text[0].data["text"] == "111\n来源: bili"

    p_c = Post(
        target_type="bili",
        text="222",
        category="动态",
    )
    p_c_text = await p_c.generate_text_messages()
    assert p_c_text[0].data["text"] == "[动态] 222\n来源: bili"
