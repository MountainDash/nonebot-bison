from .card_post import CardPost as CardPost
from .plain_post import BasePost as BasePost
from .plain_post import PlainPost as PlainPost

Post = BasePost | PlainPost | CardPost
