from dataclasses import dataclass, field
from typing import Optional
from .plugin_config import plugin_config
from .utils import parse_text

@dataclass
class Post:

    target_type: str
    text: str
    url: str
    target_name: Optional[str] = None
    show_text: bool = True
    pics: list[str] = field(default_factory=list)

    async def generate_messages(self):
        msgs = []
        if self.show_text:
            text = '来源: {}'.format(self.target_type)
            if self.target_name:
                text += '\n{}'.format(self.target_name)
            if self.text:
                text += '\n{}'.format(self.text)
            if plugin_config.hk_reporter_use_pic:
                msgs.append(await parse_text(text))
                if not self.target_type == 'rss':
                    msgs.append(self.url)
            else:
                text += '详情: {}'.format(self.url)
                msgs.append(text)
        for pic in self.pics:
            msgs.append("[CQ:image,file={url}]".format(url=pic))
        return msgs

    def __str__(self):
        return 'type: {}\ntext: {}\nurl: {}\npic: {}'.format(
                self.target_type,
                self.text,
                self.url,
                ', '.join(map(lambda x: 'b64img' if x.startswith('base64') else x, self.pics))
            )
