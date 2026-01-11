from datetime import timedelta

from nonebot import get_plugin_config
from nonebot.compat import PYDANTIC_V2
from pydantic import BaseModel, ConfigDict, Field


class MaxConcurrencyConfig(BaseModel):
    if PYDANTIC_V2:
        model_config = ConfigDict(populate_by_name=True)
    else:

        class Config:
            allow_population_by_field_name = True

    render_post: int = Field(default=5, description="渲染动态报文的最大并发数")
    send_message: int = Field(default=100, description="消息发送队列的最大缓存大小")
    resend_wait: timedelta = Field(default=timedelta(seconds=1.5), description="消息重试发送前的等待时间")


class Config(BaseModel):
    max_concurrency: MaxConcurrencyConfig = Field(default_factory=MaxConcurrencyConfig)
    send_use_queue: bool = True
    send_use_pic_merge: bool = True
    send_resend_times: int = 3

plugin_config = get_plugin_config(Config)
