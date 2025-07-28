import contextlib
from typing import cast

from nonebot.adapters import Bot, Event
from nonebot.params import Depends
from nonebot.typing import T_State
from nonebot_plugin_alconna import Alconna, CommandMeta, on_alconna
from nonebot_plugin_saa import PlatformTarget, SupportedAdapters, Text
from nonebot_plugin_waiter import waiter

from nonebot_bison.apis import check_sub_target
from nonebot_bison.config import config
from nonebot_bison.config.db_config import SubscribeDupException
from nonebot_bison.platform import Platform, platform_manager, unavailable_paltforms
from nonebot_bison.types import Target

from .depends import BisonCancelExtension, BisonToMeCheckExtension, admin_permission, bison_target_user_info
from .utils import common_platform

add_sub_alc = Alconna(
    "添加订阅",
    meta=CommandMeta(description="Bison 添加订阅指令", usage="输入“添加订阅”，跟随 Bot 提示信息进行"),
)

add_sub_command = on_alconna(
    add_sub_alc,
    use_cmd_start=True,
    # use_cmd_sep=True,
    auto_send_output=True,
    priority=5,
    block=True,
    permission=admin_permission(),
    extensions=[
        BisonToMeCheckExtension(),
        BisonCancelExtension("已中止订阅"),
    ],
)


@add_sub_command.handle()
async def add_sub_handler(
    bot: Bot,
    event: Event,
    state: T_State,
    target_user_info: PlatformTarget = Depends(bison_target_user_info),
):
    # 1. 获取平台
    await add_sub_command.send(
        "请输入想要订阅的平台，目前支持，请输入冒号左边的名称：\n"
        + "".join([f"{platform_name}: {platform_manager[platform_name].name}\n" for platform_name in common_platform])
        + "要查看全部平台请输入：“全部”\n中止订阅过程请输入：“取消”"
    )

    @waiter(waits=["message"], keep_session=True)
    async def check_platform(event: Event):
        return event.get_plaintext().strip()

    async for platform in check_platform(timeout=600, retry=5, prompt=""):
        if platform is None:
            await add_sub_command.finish("等待超时！")
        if platform == "全部":
            await add_sub_command.send(
                "全部平台\n"
                + "\n".join(
                    [f"{platform_name}: {platform.name}" for platform_name, platform in platform_manager.items()]
                )
            )
            continue
        elif platform == "取消":
            await add_sub_command.finish("已中止订阅")
        elif platform in platform_manager:
            if platform in unavailable_paltforms:
                await add_sub_command.finish(f"无法订阅 {platform}，{unavailable_paltforms[platform]}")
            state["platform"] = platform
            break
        else:
            await add_sub_command.send("平台输入错误")
            continue
    else:
        await add_sub_command.send("输入失败")
    # 2. 获取id
    cur_platform = platform_manager[state["platform"]]
    if cur_platform.has_target:

        @waiter(waits=["message"], keep_session=True)
        async def check_raw_id(event: Event):
            return event.get_plaintext().strip()

        await add_sub_command.send(
            ("1." + cur_platform.parse_target_promot + "\n2.")
            if cur_platform.parse_target_promot
            else "" + "请输入订阅用户的id\n查询id获取方法请回复:“查询”"
        )
        async for raw_id_text in check_raw_id(timeout=600, retry=5, prompt=""):
            try:
                if raw_id_text is None:
                    await add_sub_command.finish("等待超时！")
                if raw_id_text == "查询":
                    url = "https://nonebot-bison.netlify.app/usage/#%E6%89%80%E6%94%AF%E6%8C%81%E5%B9%B3%E5%8F%B0%E7%9A%84-uid"
                    msg = Text(url)
                    with contextlib.suppress(ImportError):
                        from nonebot.adapters.onebot.v11 import MessageSegment

                        title = "Bison所支持的平台UID"
                        content = "查询相关平台的uid格式或获取方式"
                        image = "https://s3.bmp.ovh/imgs/2022/03/ab3cc45d83bd3dd3.jpg"
                        msg.overwrite(
                            SupportedAdapters.onebot_v11,
                            MessageSegment.share(url=url, title=title, content=content, image=image),
                        )
                    await msg.send()
                    continue
                with contextlib.suppress(ImportError):
                    from nonebot.adapters.onebot.v11 import Message
                    from nonebot.adapters.onebot.v11.utils import unescape

                    if isinstance(raw_id_text, Message):
                        raw_id_text = unescape(raw_id_text)
                raw_id_text = await cur_platform.parse_target(raw_id_text)
                name = await check_sub_target(state["platform"], raw_id_text)
                if not name:
                    await add_sub_command.send("id输入错误，请重新输入")
                    continue
                state["id"] = raw_id_text
                state["name"] = name
                await add_sub_command.send(
                    f"即将订阅的用户为:{state['platform']} {state['name']} {state['id']}\n如有错误请输入“取消”重新订阅"
                )
                break
            except Platform.ParseTargetException as e:
                await add_sub_command.send(
                    "不能从你的输入中提取出id，请检查你输入的内容是否符合预期" + (f"\n{e.prompt}" if e.prompt else "")
                )
                continue
    else:
        state["id"] = "default"
        state["name"] = await check_sub_target(state["platform"], Target(""))

    # 3. 分类
    if cur_platform.categories:

        @waiter(waits=["message"], keep_session=True)
        async def check_category(event: Event):
            return event.get_plaintext().strip()

        await add_sub_command.send(
            "请输入要订阅的类别，以空格分隔，支持的类别有：{}".format(" ".join(list(cur_platform.categories.values())))
        )
        async for raw_cats_text in check_category(timeout=600, retry=5, prompt=""):
            if raw_cats_text is None:
                await add_sub_command.finish("等待超时！")
            res = []
            unsupported_flag = False
            for cat in raw_cats_text.split():
                if cat not in cur_platform.reverse_category:
                    await add_sub_command.send(f"不支持 {cat}，请重新输入")
                    unsupported_flag = True
                    break
                res.append(cur_platform.reverse_category[cat])
            if not unsupported_flag:
                state["cats"] = res
                break
    else:
        state["cats"] = []

    # 4. 标记标签
    if cur_platform.enable_tag:

        @waiter(waits=["message"], keep_session=True)
        async def check_tag(event: Event):
            return event.get_plaintext().strip()

        await add_sub_command.send(
            '请输入要订阅/屏蔽的标签(不含#号)\n多个标签请使用空格隔开\n订阅所有标签输入"全部标签"\n具体规则回复"详情"'
        )
        async for raw_tags_text in check_tag(timeout=600, retry=5, prompt=""):
            if raw_tags_text is None:
                await add_sub_command.finish("等待超时！")
            if raw_tags_text == "详情":
                await add_sub_command.send(
                    "订阅标签直接输入标签内容\n"
                    "屏蔽标签请在标签名称前添加~号\n"
                    "详见https://nonebot-bison.netlify.app/usage/#%E5%B9%B3%E5%8F%B0%E8%AE%A2%E9%98%85%E6%A0%87%E7%AD%BE-tag"
                )
                continue
            if raw_tags_text in ["全部标签", "全部", "全标签"]:
                state["tags"] = []
                break
            else:
                state["tags"] = raw_tags_text.split()
                break
    else:
        state["tags"] = []

    # 5. 添加订阅
    try:
        await config.add_subscribe(
            user=target_user_info,
            target=cast("Target", state["id"]),
            target_name=cast(str, state["name"]),
            platform_name=state["platform"],
            cats=state.get("cats", []),
            tags=state.get("tags", []),
        )
    except SubscribeDupException:
        await add_sub_command.finish(f"添加 {state['name']} 失败: 已存在该订阅")
    except Exception as e:
        await add_sub_command.finish(f"添加 {state['name']} 失败: {e}")
    await add_sub_command.finish(f"添加 {state['name']} 成功")
