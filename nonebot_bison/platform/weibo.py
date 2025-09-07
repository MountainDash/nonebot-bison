from datetime import datetime
import json
import re
from typing import Any, ClassVar
from typing_extensions import override
from urllib.parse import unquote

from bs4 import BeautifulSoup as bs
from httpx import AsyncClient
from lxml.etree import HTML
from nonebot.log import logger
from yarl import URL

from nonebot_bison.post import Post
from nonebot_bison.types import ApiError, Category, RawPost, Tag, Target
from nonebot_bison.utils import http_client, text_fletten
from nonebot_bison.utils.site import CookieClientManager, Site

from .platform import NewMessage

_HEADER = {
    "accept": (
        "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,"
        "*/*;q=0.8,application/signed-exchange;v=b3;q=0.9"
    ),
    "accept-language": "zh-CN,zh;q=0.9",
    "authority": "m.weibo.cn",
    "cache-control": "max-age=0",
    "sec-fetch-dest": "empty",
    "sec-fetch-mode": "same-origin",
    "sec-fetch-site": "same-origin",
    "upgrade-insecure-requests": "1",
    "user-agent": (
        "Mozilla/5.0 (Linux; Android 6.0; Nexus 5 Build/MRA58N) "
        "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/89.0.4389.72 "
        "Mobile Safari/537.36"
    ),
}


class WeiboClientManager(CookieClientManager):
    _site_name = "weibo.com"

    async def _get_current_user_name(self, cookies: dict) -> str:
        url = "https://m.weibo.cn/setup/nick/detail"
        async with http_client() as client:
            r = await client.get(url, headers=_HEADER, cookies=cookies)
            data = json.loads(r.text)
            name = data["data"]["user"]["screen_name"]
            return name

    @override
    async def get_cookie_name(self, content: str) -> str:
        """从cookie内容中获取cookie的友好名字，添加cookie时调用，持久化在数据库中"""
        name = await self._get_current_user_name(json.loads(content))

        return text_fletten(f"weibo: [{name[:10]}]")

    @override
    async def get_client(self, target: Target | None) -> AsyncClient:
        client = await super().get_client(target)

        if len(client.cookies) == 0:
            client.cookies.update({"dummycookie": "1"})

        return client

    @classmethod
    async def get_query_name_client(cls) -> AsyncClient:
        client = http_client()

        if len(client.cookies) == 0:
            client.cookies.update({"dummycookie": "1"})

        return client


class WeiboSite(Site):
    name = "weibo.com"
    schedule_type = "interval"
    schedule_setting: ClassVar[dict] = {"seconds": 10}
    client_mgr = WeiboClientManager


class Weibo(NewMessage):
    categories: ClassVar[dict[Category, str]] = {
        1: "转发",
        2: "视频",
        3: "图文",
        4: "文字",
    }
    enable_tag = True
    platform_name = "weibo"
    name = "新浪微博"
    enabled = True
    is_common = True
    site = WeiboSite
    has_target = True
    parse_target_promot = "请输入用户主页（包含数字UID）的链接"

    @classmethod
    async def get_target_name(cls, client: AsyncClient, target: Target) -> str | None:
        header = {
            "Referer": f"https://m.weibo.cn/u/{target}",
            "MWeibo-Pwa": "1",
            "X-Requested-With": "XMLHttpRequest",
            "sec-fetch-mode": "cors",
        }
        res = await client.get(f"https://m.weibo.cn/api/container/getIndex?type=uid&value={target}", headers=header)
        res_dict = json.loads(res.text)
        if res_dict.get("ok") == 1:
            return res_dict["data"]["userInfo"]["screen_name"]
        else:
            return None

    @classmethod
    async def parse_target(cls, target_text: str) -> Target:
        if re.match(r"\d+", target_text):
            return Target(target_text)
        elif match := re.match(r"(?:https?://)?weibo\.com/u/(\d+)", target_text):
            # 都2202年了应该不会有http了吧，不过还是防一手
            return Target(match.group(1))
        else:
            raise cls.ParseTargetException(prompt="正确格式:\n1. 用户数字UID\n2. https://weibo.com/u/xxxx")

    async def get_sub_list(self, target: Target) -> list[RawPost]:
        client = await self.ctx.get_client(target)
        header = {"Referer": f"https://m.weibo.cn/u/{target}", "MWeibo-Pwa": "1", "X-Requested-With": "XMLHttpRequest"}
        # 获取 cookie 见 https://docs.rsshub.app/zh/deploy/config#%E5%BE%AE%E5%8D%9A
        params = {"containerid": "107603" + target}
        res = await client.get("https://m.weibo.cn/api/container/getIndex?", headers=header, params=params, timeout=4.0)
        res_data = json.loads(res.text)
        if not res_data["ok"] and res_data["msg"] != "这里还没有内容":
            raise ApiError(res.request.url)

        def custom_filter(d: RawPost) -> bool:
            return d["card_type"] == 9

        return list(filter(custom_filter, res_data["data"]["cards"]))

    def get_id(self, post: RawPost) -> Any:
        return post["mblog"]["id"]

    def filter_platform_custom(self, raw_post: RawPost) -> bool:
        return raw_post["card_type"] == 9

    def get_date(self, raw_post: RawPost) -> float:
        created_time = datetime.strptime(raw_post["mblog"]["created_at"], "%a %b %d %H:%M:%S %z %Y")
        return created_time.timestamp()

    def get_tags(self, raw_post: RawPost) -> list[Tag] | None:
        "Return Tag list of given RawPost"
        text = raw_post["mblog"]["text"]
        soup = bs(text, "html.parser")
        res = [
            x[1:-1]
            for x in filter(
                lambda s: s[0] == "#" and s[-1] == "#",
                (x.text for x in soup.find_all("span", class_="surl-text")),
            )
        ]
        super_topic_img = soup.find("img", src=re.compile(r"timeline_card_small_super_default"))
        if super_topic_img:
            try:
                res.append(super_topic_img.parent.parent.find("span", class_="surl-text").text + "超话")  # type: ignore
            except Exception:
                logger.info(f"super_topic extract error: {text}")
        return res

    def get_category(self, raw_post: RawPost) -> Category:
        if raw_post["mblog"].get("retweeted_status"):
            return Category(1)
        elif raw_post["mblog"].get("page_info") and raw_post["mblog"]["page_info"].get("type") == "video":
            return Category(2)
        elif raw_post["mblog"].get("pics"):
            return Category(3)
        else:
            return Category(4)

    def _get_text(self, raw_text: str) -> str:
        text = raw_text.replace("<br/>", "\n").replace("<br />", "\n")
        selector = HTML(text, parser=None)
        if selector is None:
            return text
        url_elems = selector.xpath("//a[@href]/span[@class='surl-text']")
        for br in selector.xpath("br"):
            br.tail = "\n" + br.tail
        for elem in url_elems:
            url = elem.getparent().get("href")
            if (
                not elem.text.startswith("#")
                and not elem.text.endswith("#")
                and (url.startswith("https://weibo.cn/sinaurl?u=") or url.startswith("https://video.weibo.com"))
            ):
                url = unquote(url.replace("https://weibo.cn/sinaurl?u=", ""))
                elem.text = f"{elem.text}( {url} )"
        return selector.xpath("string(.)")

    async def _get_long_weibo(self, weibo_id: str) -> dict:
        try:
            client = await self.ctx.get_client()
            weibo_info = await client.get(
                "https://m.weibo.cn/statuses/extend",
                params={"id": weibo_id},
                headers=_HEADER,
            )
            weibo_info = weibo_info.json()
            if not weibo_info or weibo_info["ok"] != 1:
                return {}
            return weibo_info["data"]
        except (KeyError, TimeoutError):
            logger.info(f"detail message error: https://m.weibo.cn/detail/{weibo_id}")
        return {}

    async def _parse_weibo(self, info: dict) -> Post:
        if info["isLongText"] or info["pic_num"] > 9:
            info["text"] = (await self._get_long_weibo(info["mid"]))["longTextContent"]
        parsed_text = self._get_text(info["text"])
        raw_pics_list = info.get("pics", [])
        pic_urls = [img["large"]["url"] for img in raw_pics_list]
        # 视频cover
        if "page_info" in info and info["page_info"].get("type") == "video":
            crop_url = info["page_info"]["page_pic"]["url"]
            pic_urls.append(
                f"{URL(crop_url).scheme}://{URL(crop_url).host}/large/{info['page_info']['page_pic']['pid']}"
            )
        pics = []
        for pic_url in pic_urls:
            async with http_client(headers={"referer": "https://weibo.com"}) as client:
                res = await client.get(pic_url)
                res.raise_for_status()
                pics.append(res.content)
        detail_url = f"https://weibo.com/{info['user']['id']}/{info['bid']}"
        return Post(
            self,
            content=parsed_text,
            url=detail_url,
            images=pics,
            nickname=info["user"]["screen_name"],
        )

    async def parse(self, raw_post: RawPost) -> Post:
        info = raw_post["mblog"]
        post = await self._parse_weibo(info)
        if "retweeted_status" in info:
            post.repost = await self._parse_weibo(info["retweeted_status"])
        return post
