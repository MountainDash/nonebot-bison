from .base_post import BasePost as BasePost
from .plain_post import PlainPost as PlainPost

Post = BasePost | PlainPost
