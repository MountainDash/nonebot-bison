import base64
import functools
import io

import httpx

http_args = {
    "proxies": None,
}
http_headers = {
    "user-agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/51.0.2704.103 Safari/537.36"
}


@functools.wraps(httpx.AsyncClient)
def http_client(*args, **kwargs):
    if headers := kwargs.get("headers"):
        new_headers = http_headers.copy()
        new_headers.update(headers)
        kwargs["headers"] = new_headers
    else:
        kwargs["headers"] = http_headers
    return httpx.AsyncClient(*args, **kwargs)


http_client = functools.partial(http_client, **http_args)

pic_urls = [
    "https://tvax4.sinaimg.cn/crop.0.0.756.756.180/006QZngZly8gdj05mufr9j30l00l0dq4.jpg?KID=imgbed,tva&Expires=1623930706&ssig=jbkVpwN%2BKp",
]


async def main():
    for pic_url in pic_urls:
        async with http_client(headers={"referer": "https://weibo.com"}) as client:
            res = await client.get(pic_url)
            res.raise_for_status()
            pic_base64 = base64.b64encode(res.content)
            print(pic_base64.decode("utf-8"))


if __name__ == "__main__":
    import asyncio

    asyncio.run(main())
