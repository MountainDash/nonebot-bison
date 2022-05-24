---
sidebar: auto
---

# 基本开发须知

## 语言以及工具

1. 本项目使用了`python3.9`的特性进行开发，所以请确保你的 Python 版本>=3.9
2. 本项目使用 poetry 进行依赖管理，请确保开发之前已经进行过`poetry install`，运行时在`poetry shell`的环境中进行运行
3. 本项目使用的 node 项目管理工具是 yarn

## 前端

本项目使用了前端，如果单独 clone 仓库本身，里面是**不包含**编译过的前端的，请使用`yarn && yarn build`进行前端的构建。
如果想要开发前端，推荐在`.env.dev`中加入`BISON_OUTER_URL="http://localhost:3000/bison/"`，然后分别运行 bot 和`yarn dev`
::: warning
请在开发前端的时候删除项目根目录中的`node_modules`，否则编译和运行的时候可能会出现奇怪的问题。
:::

## 文档

文档的相关部分在`docs`目录中，可以在项目根目录执行`yarn docs:dev`预览文件更改效果。

## 代码格式

本项目使用了 pre-commit 来进行代码美化和格式化。在`poetry shell`状态下执行`pre-commit install`来安装 git hook，可自动在 commit 时
格式化代码。

# 适配新网站

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
- `get_tags(RawPost) -> Optional[Collection[Tag]]` （可选） 从 RawPost 中提取 Tag
- `get_category(RawPos) -> Optional[Category]` （可选）从 RawPost 中提取 Category
- `async parse(RawPost) -> Post`将获取到的 RawPost 处理成 Post

不同订阅类型的需要分别实现的方法如下:

- `get_sub_list(Target) -> list[RawPost]`
  - 对于`nonebot_bison.platform.platform.NewMessage`
    - `get_sub_list(Target) -> list[RawPost]` 用于获取对应 Target 的 RawPost 列表，与上一次`get_sub_list`获取的列表比较，过滤出新的 RawPost
  - 对于`nonebot_bison.platform.platform.SimplePost`
    - `get_sub_list` 用于获取对应 Target 的 RawPost 列表，但不会与上次获取的结果进行比较，而是直接进行发送
- `get_status(Target) -> Any`
  - 对于`nonebot_bison.platform.platform.StatusChange`
    - `get_status`用于获取对应Target当前的状态，随后将获取的状态作为参数`new_status`传入`compare_status`中
- `compare_status(self, target: Target, old_status, new_status) -> list[RawPost]`  
  - 对于`nonebot_bison.platform.platform.StatusChange`
    - `compare_status` 用于比较储存的`old_status`与新传入的`new_status`，并返回发生变更的RawPost列表

#### 简要的处理流程

- `nonebot_bison.platform.platform.NewMessage`
  ::: details 大致流程
  1. 调用`get_sub_list`拿到 RawPost 列表
  2. 调用`get_id`判断是否重复，如果没有重复就说明是新的 RawPost
  3. 如果有`get_category`和`get_date`，则调用判断 RawPost 是否满足条件
  4. 调用`parse`生成正式推文
     :::
  - 参考[nonebot_bison.platform.Weibo](https://github.com/felinae98/nonebot-bison/blob/v0.5.3/src/plugins/nonebot_bison/platform/weibo.py)
- `nonebot_bison.platform.platform.StatusChange`
  :::details 大致流程
  1. `get_status`获取当前状态
  2. 传入`compare_status`比较前状态
  3. 通过则进入`parser`生成 Post
     :::
  - 参考[nonenot_bison.platform.AkVersion](https://github.com/felinae98/nonebot-bison/blob/v0.5.3/src/plugins/nonebot_bison/platform/arknights.py#L86)

#### 一些例子

例如要适配微博，我希望 bot 搬运新的消息，所以微博的类应该这样实现：

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

    async def get_target_name(self, target: Target) -> Optional[str]:
      #获取Target对应的用户名
      ...
    async def get_sub_list(self, target: Target) -> list[RawPost]:
      #获取对应Target的RawPost列表，会与上一次get_sub_list获取的列表比较，过滤出新的RawPost
      ...
    def get_id(self, post: RawPost) -> Any:
      #获取可以标识每个Rawpost的，不与之前RawPost重复的id，用于过滤出新的RawPost
      ...
    def get_date(self, raw_post: RawPost) -> float:
      #获取RawPost的发布时间，若bot过滤出的新RawPost发布时间与当前时间差超过2小时，该RawPost将被忽略，可以返回None
      ...
    def get_tags(self, raw_post: RawPost) -> Optional[list[Tag]]:
      #获取RawPost中包含的微博话题（#xxx#中的内容）
      ...
    def get_category(self, raw_post: RawPost) -> Category:
      #获取该RawPost在该类定义categories的具体分类(转发？视频？图文？...？)
      ...
    async def parse(self, raw_post: RawPost) -> Post:
      #将需要bot推送的RawPost处理成正式推送的Post
      ...
```

当然我们非常希望你对自己适配的平台写一些单元测试

你可以参照`tests/platforms/test_*.py`中的内容对单元测试进行编写。

为保证多次运行测试的一致性，可以 mock http 的响应，测试的内容应包括[获取 RawPost](https://github.com/felinae98/nonebot-bison/blob/v0.5.3/tests/platforms/test_weibo.py#L59)，处理成 Post
，测试分类以及提取 tag 等，当然最好和 rsshub 做一个交叉验证。

::: danger
Nonebot 项目使用了全异步的处理方式，所以你需要对异步，Python asyncio 的机制有一定了解，当然，
依葫芦画瓢也是足够的
:::

## 类的方法与成员变量

## 方法与变量的定义
