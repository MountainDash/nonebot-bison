from dataclasses import dataclass, field
from typing import Optional
from .plugin_config import plugin_config
from .utils import parse_text

@dataclass
class Post:

    target_type: str
    text: str
    url: Optional[str]
    target_name: Optional[str] = None
    compress: bool = False
    override_use_pic: Optional[bool] = None

    pics: list[str] = field(default_factory=list)

    def _use_pic(self):
        if not self.override_use_pic is None:
            return self.override_use_pic
        return plugin_config.hk_reporter_use_pic

    async def generate_messages(self):
        msgs = []
        text = '来源: {}'.format(self.target_type)
        if self.target_name:
            text += ' {}'.format(self.target_name)
        if self.text:
            text += ' \n{}'.format(self.text)
        if self._use_pic():
            msgs.append(await parse_text(text))
            if not self.target_type == 'rss' and self.url:
                msgs.append(self.url)
        else:
            if self.url:
                text += ' \n详情: {}'.format(self.url)
            msgs.append(text)
        for pic in self.pics:
            msgs.append("[CQ:image,file={url}]".format(url=pic))
        if self.compress:
            msgs = [''.join(msgs)]
        return msgs

    def __str__(self):
        return 'type: {}\nfrom: {}\ntext: {}\nurl: {}\npic: {}'.format(
                self.target_type,
                self.target_name,
                self.text,
                self.url,
                ', '.join(map(lambda x: 'b64img' if x.startswith('base64') else x, self.pics))
            )
