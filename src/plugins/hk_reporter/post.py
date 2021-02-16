from dataclasses import dataclass, field
from .plugin_config import plugin_config
from .utils import parse_text

@dataclass
class Post:

    target_type: str
    text: str
    url: str
    pics: list[str] = field(default_factory=list)

    async def generate_messages(self):
        if plugin_config.hk_reporter_use_pic:
            text_msg = '来源: {}\n{}'.format(self.target_type, self.text)
            if self.target_type == 'rss':
                res = [await parse_text(text_msg)]
            else:
                res = [await parse_text(text_msg), self.url]
        else:
            first_msg = '来源: {}\n{}\n详情：{}'.format(self.target_type, self.text, self.url)
            res = [first_msg]
        for pic in self.pics:
            res.append("[CQ:image,file={url}]".format(url=pic))
        return res

    def __str__(self):
        return 'type: {}\ntext: {}\nurl: {}\npic: {}'.format(self.target_type, self.text[:50], self.url, ','.join(map(lambda x: 'b64img' if x.startswith('base64') else x, self.pics)))
