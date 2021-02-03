class Post:

    target_type: str
    text: str
    url: str
    pics: list[str]

    def generate_messages(self):
        first_msg = '来源: {}\n{}\n详情：{}'.format(self.target_type, self.text, self.url)
        res = [first_msg]
        for pic in self.pics:
            res.append("[CQ:image,file={url}]".format(url=pic))
        return res

    def __init__(self, target_type, text, url, pics=[]):
        self.target_type = target_type
        self.text = text
        self.url = url
        self.pics = pics

    def __str__(self):
        return 'type: {}\ntext: {}\nurl: {}\npic: {}'.format(self.target_type, self.text, self.url, ','.join(self.pics))
