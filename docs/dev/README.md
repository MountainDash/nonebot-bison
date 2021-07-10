---
sidebar: auto
---
# 开发指南
本插件需要你的帮助！只需要会写简单的爬虫，就能给本插件适配新的网站。

## 基本概念
* `nonebot_hk_reporter.post.Post`: 可以理解为推送内容，其中包含需要发送的文字，图片，链接，平台信息等
* `nonebot_hk_reporter.types.RawPost`: 从站点/平台中爬到的单条信息
* `nonebot_hk_reporter.types.Target`: 目标账号，Bilibili，微博等社交媒体中的账号
* `nonebot_hk_reporter.types.Category`: 信息分类，例如视频，动态，图文，文章等
* `nonebot_hk_reporter.types.Tag`: 信息标签，例如微博中的超话或者hashtag

## 快速上手
上车！我们走

先明确需要适配的站点类型，先明确两个问题：
#### 我要发送什么样的推送
* `nonebot_hk_reporter.platform.platform.NewMessage` 最常见的类型，每次爬虫向特定接口爬取一个消息列表，
    与之前爬取的信息对比，过滤出新的消息，再根据用户自定义的分类和标签进行过滤，最后处理消息，把
    处理过后的消息发送给用户  
    例如：微博，Bilibili
* `nonebot_hk_reporter.platform.platform.StatusChange` 每次爬虫获取一个状态，在状态改变时发布推送  
    例如：游戏开服提醒，主播上播提醒
* `nonebot_hk_reporter.platform.platform.SimplePost` 与`NewMessage`相似，但是不过滤新的消息
    ，每次发送全部消息  
    例如：每日榜单定时发送
#### 这个平台是否有账号的概念
* `nonebot_hk_reporter.platform.platform.TargetMixin` 有账号的概念  
    例如：Bilibili用户，微博用户
* `nonebot_hk_reporter.platform.platform.NoTargetMixin` 没有账号的概念  
    例如：游戏公告，教务处公告

现在你已经选择了两个类，现在你需要在`src/plugins/nonebot_hk_reporter/platform`下新建一个py文件，
在里面新建一个类，继承你刚刚选择的两个类，重载一些关键的函数，然后……就完成了，不需要修改别的东西了。

例如要适配微博，微博有账号，并且我希望bot搬运新的消息，所以微博的类应该这样定义：
```python
class Weibo(NewMessage, TargetMixin):
    ...
```

当然我们非常希望你对自己适配的平台写一些单元测试，你可以模仿`tests/platforms/test_*.py`中的内容写
一些单元测试。为保证多次运行测试的一致性，可以mock http的响应，测试的内容包括获取RawPost，处理成Post
，测试分类以及提取tag等，当然最好和rsshub做一个交叉验证。

::: danger
Nonebot项目使用了全异步的处理方式，所以你需要对异步，Python asyncio的机制有一定了解，当然，
依葫芦画瓢也是足够的
:::

## 类的方法与成员变量
## 方法与变量的定义
