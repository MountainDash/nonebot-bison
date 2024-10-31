---
prev: /usage/install
next: /dev/cookie
---

# 基本开发须知

## 语言以及工具

1. 本项目使用了`python3.10`的特性进行开发，所以请确保你的 Python 版本>=3.10
2. 本项目使用 poetry 进行依赖管理，请确保开发之前已经进行过`poetry install`，运行时在`poetry shell`的环境中进行运行
3. 本项目使用的 node 项目管理工具是 pnpm

::: tip 参考
可以参考[安装 - 直接运行](../usage/install.md#直接运行)中的内容
:::

## 前端

本项目使用了前端，如果单独 clone 仓库本身，里面是**不包含**编译过的前端的，请使用`pnpm i && pnpm build`进行前端的构建。

如果想要开发前端，推荐的步骤是：

1. 在`.env.dev`中添加`BISON_OUTER_URL`配置项

   ```env
   BISON_OUTER_URL="http://localhost:3000/bison/"
   ```

2. 运行 bot

   ```bash
   poetry run nb run
   ```

3. 运行前端：

   ```bash
   cd admin-frontend
   pnpm start
   ```

::: warning
请在开发前端的时候删除项目**根目录**中的`node_modules`，否则编译和运行的时候可能会出现奇怪的问题。
:::

## 文档

文档的相关部分在`docs`目录中，可以在项目根目录执行`pnpm docs:dev`预览文件更改效果。

## 代码格式

本项目使用了 pre-commit 来进行代码美化和格式化。在`poetry shell`状态下执行`pre-commit install`来安装 git hook，可自动在 commit 时
格式化代码。

## 适配新网站

本插件需要你的帮助！只需要会写简单的爬虫，就能给本插件适配新的网站。

::: danger
Nonebot 项目使用了全异步的处理方式，所以你需要对异步，Python asyncio 的机制有一定了解，当然，
依葫芦画瓢也是足够的
:::

## 基本概念

- `nonebot_bison.post`: 可以理解为推送内容，其中包含需要发送的文字，图片，链接，平台信息等，分为：
  - `nonebot_bison.post.Post`: 推送内容格式，传入需要发送的内容由 Theme 模块处理
  - 详细的介绍可参见[生成 bison 的推送文本](#生成-bison-的推送文本)
- `nonebot_bison.types.RawPost`: 从站点/平台中爬到的单条信息
- `nonebot_bison.types.Target`: 目标账号，Bilibili，微博等社交媒体中的账号
- `nonebot_bison.types.Category`: 信息分类，例如视频，动态，图文，文章等
- `nonebot_bison.types.Tag`: 信息标签，例如微博中的超话或者 hashtag
- `nonebot_bison.theme.Theme`: 用于渲染`nonebot_bison.post.Post`的模块，可以理解为一个模板引擎，生成可发送的消息

## 快速上手

上车！我们走

先明确需要适配的站点类型，先明确两个问题：

### 我要发送什么样的推送

- `nonebot_bison.platform.platform.NewMessage` 最常见的类型，每次爬虫向特定接口爬取一个消息列表，
  与之前爬取的信息对比，过滤出新的消息，再根据用户自定义的分类和标签进行过滤，最后处理消息，把
  处理过后的消息发送给用户  
   例如：微博，Bilibili
- `nonebot_bison.platform.platform.StatusChange` 每次爬虫获取一个状态，在状态改变时发布推送  
   例如：游戏开服提醒，主播上播提醒
- `nonebot_bison.platform.platform.SimplePost` 与`NewMessage`相似，但是不过滤之前发过的
  ，每次发送全部消息  
   例如：每日榜单定时发送

### 这个平台是否有账号的概念

- 有账号的概念  
   例如：B 站用户动态，微博用户动态，网易云电台更新
- 没有账号的概念  
  例如：游戏公告，教务处公告

## 实现方法

现在你需要在`nonebot_bison/platform`下新建一个 `.py` 文件，
在里面新建一个类，继承推送类型的基类，重载一些关键的函数，然后……就完成了~(??)~，不需要修改别的东西了。

### 不同类型 Platform 的实现适配以及逻辑

- `nonebot_bison.platform.platform.NewMessage`
  需要实现：

  - `async get_sub_list(Target) -> list[RawPost]`
  - `get_id(RawPost)`
  - `get_date(RawPost)` (可选)

  ::: details 大致流程

  1. 调用`get_sub_list`拿到 RawPost 列表
  2. 调用`get_id`判断是否重复，如果没有重复就说明是新的 RawPost
  3. 如果有`get_category`和`get_date`，则调用判断 RawPost 是否满足条件
  4. 调用`parse`生成正式推文
     :::

  参考[nonebot_bison.platform.Weibo](https://github.com/MountainDash/nonebot-bison/blob/v0.9.1/nonebot_bison/platform/weibo.py)

- `nonebot_bison.platform.platform.StatusChange`
  需要实现：

  - `async get_status(Target) -> Any`
  - `compare_status(Target, old_status, new_status) -> list[RawPost]`

  :::details 大致流程

  1. `get_status`获取当前状态
  2. 传入`compare_status`比较前状态
  3. 通过则进入`parser`生成 Post
     :::

  参考[nonenot_bison.platform.AkVersion](https://github.com/MountainDash/nonebot-bison/blob/v0.9.1/nonebot_bison/platform/arknights.py#L122)

- `nonebot_bison.platform.platform.SimplePost`
  需要实现：

  - `async get_sub_list(Target) -> list[RawPost]`
  - `get_date(RawPost)` (可选)

  ::: details 大致流程

  1. 调用`get_sub_list`拿到 RawPost 列表
  2. 如果有`get_category`和`get_date`，则调用判断 RawPost 是否满足条件
  3. 调用`parse`生成正式推文
     :::

### 公共方法/成员

任何一种订阅类型需要实现的方法/成员如下：

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
- `get_tags(RawPost) -> Optional[Collection[Tag]]` （可选）从 RawPost 中提取 Tag
- `get_category(RawPos) -> Optional[Category]` （可选）从 RawPost 中提取 Category
- `async parse(RawPost) -> Post` 将获取到的 RawPost 处理成 Post
- `async parse_target(str) -> Target` （可选）定制化处理传入用户输入的 Target 字符串，返回 Target（一般是把用户的主页链接解析为 Target），如果输入本身就是 Target，则直接返回 Target
- `parse_target_promot` （可选）在要求用户输入 Target 的时候显示的提示文字
- `default_theme` （可选）默认的渲染主题，如果用户没有指定渲染主题，则优先使用这个主题进行渲染，不显式覆盖则为`basic`
- `use_batch` （可选）是否使用批量获取，如果使用批量获取，那么会调用`batch_get_sub_list`，否则调用`get_sub_list`

### 特有的方法/成员

- `async get_sub_list(Target) -> list[RawPost]` 输入一个`Target`，输出一个`RawPost`的 list
  - 对于`nonebot_bison.platform.platform.NewMessage`  
    `get_sub_list(Target) -> list[RawPost]` 用于获取对应 Target 的 RawPost 列表，与上一次`get_sub_list`获取的列表比较，过滤出新的 RawPost
  - 对于`nonebot_bison.platform.platform.SimplePost`  
    `get_sub_list` 用于获取对应 Target 的 RawPost 列表，但不会与上次获取的结果进行比较，而是直接进行发送
- `async def batch_get_sub_list(list[Target]) -> list[list[RawPost]]` （可选）输入一个`Target`的 list，输出一个`RawPost`的 list 的 list，用于批量获取 RawPost
  - 其他类似`get_sub_list`，但是可以一次性获取多个 Target 的 RawPost
- `get_id(RawPost) -> Any` 输入一个`RawPost`，从`RawPost`中获取一个唯一的 ID，这个 ID 会用来判断这条`RawPost`是不是之前收到过
- `get_date(RawPost) -> Optional[int]` 输入一个`RawPost`，如果可以从`RawPost`中提取出发文的时间，返回发文时间的 timestamp，否则返回`None`
- `async get_status(Target) -> Any`
  - 对于`nonebot_bison.platform.platform.StatusChange`  
    `get_status`用于获取对应 Target 当前的状态，随后将获取的状态作为参数`new_status`传入`compare_status`中
- `compare_status(self, target: Target, old_status, new_status) -> list[RawPost]`
  - 对于`nonebot_bison.platform.platform.StatusChange`  
    `compare_status` 用于比较储存的`old_status`与新传入的`new_status`，并返回发生变更的 RawPost 列表

### 单元测试

当然我们非常希望你对自己适配的平台写一些单元测试

你可以参照`tests/platforms/test_*.py`中的内容对单元测试进行编写。

为保证多次运行测试的一致性，可以 mock http 的响应，测试的内容应包括[获取 RawPost](https://github.com/MountainDash/nonebot-bison/blob/v0.9.1/tests/platforms/test_weibo.py#L43)，处理成 Post
，测试分类以及提取 tag 等，当然最好和 rsshub 做一个交叉验证。

## 一些例子

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
      #获取 Target 对应的用户名
      ...
    async def get_sub_list(self, target: Target) -> list[RawPost]:
      #获取对应 Target 的 RawPost 列表，会与上一次 get_sub_list 获取的列表比较，过滤出新的 RawPost
      ...
    def get_id(self, post: RawPost) -> Any:
      #获取可以标识每个 Rawpost 的，不与之前 RawPost 重复的 id，用于过滤出新的 RawPost
      ...
    def get_date(self, raw_post: RawPost) -> float:
      #获取 RawPost 的发布时间，若 bot 过滤出的新 RawPost 发布时间与当前时间差超过 2 小时，该 RawPost 将被忽略，可以返回 None
      ...
    def get_tags(self, raw_post: RawPost) -> Optional[list[Tag]]:
      #获取RawPost中包含的微博话题（#xxx#中的内容）
      ...
    def get_category(self, raw_post: RawPost) -> Category:
      #获取该 RawPost 在该类定义 categories 的具体分类 (转发？视频？图文？...？)
      ...
    async def parse(self, raw_post: RawPost) -> Post:
      #将需要 bot 推送的 RawPost 处理成正式推送的 Post
      ...
```

## 生成 bison 的推送文本

### 什么是`nonebot_bison.post`

可以认为`nonebot_bison.post`是最终要交付给 bison 的 Theme 模块渲染，最终推送到群内的内容。

`parse`函数的工作就是将`nonebot_bison.types.RawPost`中的数据相应传入`nonebot_bison.post.Post`中

经过`parse`函数处理过后的报文应该返回属于`nonebot_bison.post`下的某个类。

目前 bison 所支持的类有：

- `nonebot_bison.post.Post`

### 什么是`nonebot_bison.post.Post`

最通用的 Post，理论上包含所有常用的数据

```python
class Post(AbstractPost):
    platform: "Platform"
    """来源平台"""
    content: str
    """文本内容"""
    title: str | None = None
    """标题"""
    images: list[str | bytes | Path | BytesIO] | None = None
    """图片列表"""
    timestamp: int | None = None
    """发布/获取时间戳"""
    url: str | None = None
    """来源链接"""
    avatar: str | bytes | Path | BytesIO | None = None
    """发布者头像"""
    nickname: str | None = None
    """发布者昵称"""
    description: str | None = None
    """发布者个性签名等"""
    repost: "Post | None" = None
    """转发的 Post"""
```

额外参数 (AbstractPost)：

- 使用`compress`参数将所有消息压缩为一条进行发送。
- 使用`extra_msg`可以携带额外的消息进行发送。
  可参考[Post 的用法](https://github.com/MountainDash/nonebot-bison/blob/v0.9.1/nonebot_bison/platform/arknights.py#L240)

## 制作主题

### 什么是主题

主题是用于渲染`nonebot_bison.post.Post`的模块，可以理解为一个模板引擎，生成可发送的消息。

RawPost 通过`Platform.parse`函数处理成 Post，然后通过`Theme.render`函数渲染成可发送的消息。

### 主题的注册

Bison 在启动时会尝试注册所有在`nonebot_bison/theme/themes`下的主题，如果你的主题在这个目录下，并指定了 `__theme_meta__`，那么它会被自动注册。

若配置项`BISON_USE_BROWSER=false`，则在注册的主题需要浏览器渲染，即`need_browser`字段为`True`时，会发出注册警告

同时，你也可以手动调用`nonebot_bison.theme.theme_manager.register`来注册主题

::: tip 另一种加载方式
理论上你自己的 Theme 可以创建在别的位置，甚至作为一个插件
这样的话想要注册这个 Theme，就需要在插件里这样做：

```python
from nonebot_bison.theme import theme_manager
from .path.to.your.theme import ATheme

theme_manager.register(ATheme())
```

:::

### 主题的实现

主题需要继承`nonebot_bison.theme.Theme`，并实现`render`函数

在某个 Platform 获取到 Post 之后，会根据 主题渲染规则，将 Post 传入对应的 Theme 中，然后调用`render`函数，将 Post 渲染成可发送的消息。

::: info 主题渲染规则

```python
def get_priority_themes(self) -> list[str]:
    """获取渲染所使用的 theme 名列表，按照优先级排序"""
    themes_by_priority: list[str] = []
    # 最先使用用户指定的 theme
    if user_theme := self.get_config_theme():
        themes_by_priority.append(user_theme)
    # 然后使用平台默认的 theme
    if self.platform.default_theme not in themes_by_priority:
        themes_by_priority.append(self.platform.default_theme)
    # 最后使用最基础的 theme
    if "basic" not in themes_by_priority:
        themes_by_priority.append("basic")
    return themes_by_priority
```

:::

在获取到可渲染的主题列表后，会按照列表中的顺序依次调用`render`函数。

如果某个主题渲染失败，会继续调用下一个主题，直到渲染成功或者没有主题可用。

### 例子

想要创建一个主题，首先需要在`nonebot_bison/theme/themes`目录下创建一个新的目录，比如`mytheme`

然后在`mytheme`目录下创建一个`__init__.py`文件

接下来创建一个`build.py`文件，用于生成主题

在文件中写入：

```python
from typing import TYPE_CHECKING, Literal

from nonebot_bison.theme import Theme
if TYPE_CHECKING:
    from nonebot_bison.post import Post

class MyTheme(Theme):
    name: Literal["mytheme"] = "mytheme"

    # 可选，该主题渲染是否需要浏览器
    # need_browser: bool = ...

    async def render(self, post: "Post") -> list[MessageSegmentFactory]:
        ...
```

在`render`函数中，将传入的 post 中的数据用你所希望的方式渲染成 MessageSegmentFactory，就完成了一个主题的制作

然后在`__init__.py`中注册这个主题：

```python
from .build import MyTheme

__theme_meta__ = MyTheme()
```

这样就完成了一个主题的创建，Bison 会在启动时自动加载这个主题。
