---
sidebar: auto
---

# 开发指南

本插件需要你的帮助！只需要会写简单的爬虫，就能给本插件适配新的网站。

## 基本概念

- `nonebot_bison.post.Post`: 可以理解为推送内容，其中包含需要发送的文字，图片，链接，平台信息等
- `nonebot_bison.types.RawPost`: 从站点/平台中爬到的单条信息
- `nonebot_bison.types.Target`: 目标账号，Bilibili，微博等社交媒体中的账号
- `nonebot_bison.types.Category`: 信息分类，例如视频，动态，图文，文章等
- `nonebot_bison.types.Tag`: 信息标签，例如微博中的超话或者 hashtag

## 快速上手

上车！我们走

先明确需要适配的站点类型，先明确两个问题：

#### 我要发送什么样的推送

- `nonebot_bison.platform.platform.NewMessage` 最常见的类型，每次爬虫向特定接口爬取一个消息列表，
  与之前爬取的信息对比，过滤出新的消息，再根据用户自定义的分类和标签进行过滤，最后处理消息，把
  处理过后的消息发送给用户  
   例如：微博，Bilibili
- `nonebot_bison.platform.platform.StatusChange` 每次爬虫获取一个状态，在状态改变时发布推送  
   例如：游戏开服提醒，主播上播提醒
- `nonebot_bison.platform.platform.SimplePost` 与`NewMessage`相似，但是不过滤新的消息
  ，每次发送全部消息  
   例如：每日榜单定时发送

#### 这个平台是否有账号的概念

- 有账号的概念  
   例如：B 站用户动态，微博用户动态，网易云电台更新
- 没有账号的概念  
  例如：游戏公告，教务处公告

现在你需要在`src/plugins/nonebot_bison/platform`下新建一个 py 文件，
在里面新建一个类，继承推送类型的基类，重载一些关键的函数，然后……就完成了，不需要修改别的东西了。

任何一种订阅类型需要实现的方法/字段如下：

- `schedule_type`, `schedule_kw` 调度的参数，本质是使用 apscheduler 的[trigger 参数](https://apscheduler.readthedocs.io/en/3.x/userguide.html?highlight=trigger#choosing-the-right-scheduler-job-store-s-executor-s-and-trigger-s)，`schedule_type`可以是`date`,`interval`和`cron`，
  `schedule_kw`是对应的参数，一个常见的配置是`schedule_type=interval`, `schedule_kw={'seconds':30}`
- `is_common` 是否常用，如果被标记为常用，那么和机器人交互式对话添加订阅时，会直接出现在选择列表中，否则
  需要输入`全部`才会出现。
- `enabled` 是否启用
- `name` 平台的正式名称，例如`微博`
- `has_target` 平台是否有“帐号”
- `category` 平台的发布内容分类，例如 B 站包括专栏，视频，图文动态，普通动态等，如果不包含分类功能则设为`{}`
- `enable_tag` 平台发布内容是否带 Tag，例如微博
- `platform_name` 唯一的，英文的识别标识，比如`weibo`
- `async get_target_name(Target) -> Optional[str]` 通常用于获取帐号的名称，如果平台没有帐号概念，可以直接返回平台的`name`
- `async parse(RawPost) -> Post`将获取到的 RawPost 处理成 Post
- `get_tags(RawPost) -> Optional[Collection[Tag]]` （可选） 从 RawPost 中提取 Tag
- `get_category(RawPos) -> Optional[Category]` （可选）从 RawPost 中提取 Category

例如要适配微博，我希望 bot 搬运新的消息，所以微博的类应该这样定义：

```python
class Weibo(NewMessage):

    categories = {
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
    schedule_type = "interval"
    schedule_kw = {"seconds": 3}
    has_target = True
```

当然我们非常希望你对自己适配的平台写一些单元测试，你可以模仿`tests/platforms/test_*.py`中的内容写
一些单元测试。为保证多次运行测试的一致性，可以 mock http 的响应，测试的内容包括获取 RawPost，处理成 Post
，测试分类以及提取 tag 等，当然最好和 rsshub 做一个交叉验证。

::: danger
Nonebot 项目使用了全异步的处理方式，所以你需要对异步，Python asyncio 的机制有一定了解，当然，
依葫芦画瓢也是足够的
:::

## 类的方法与成员变量

## 方法与变量的定义
