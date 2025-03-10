---
prev: /usage/install
next: /usage/
---

# :package: Bison 的第一个包裹

本节将教你如何开始使用 Bison 进行基础的使用，
默认你已经完成了[**安装**](/usage/install.md)并且已经成功启动了 Bison

如果你想要了解更详细的内容，请前往[详细配置](/usage)

## :wrench: 骑行前检查

首先，我们需要检查一下 Bison 的配置是否正确

在最基础的使用情况下，我们只需要关注少数几个配置的内容：

1. `COMMAND_START`  
   这个配置是 Bison 的命令前缀，如果你的配置中没有设置，那么默认是`''`，也就是没有前缀  
   在本节中，我们假设`COMMAND_START`设置中包含`'/'`，也就是说，我们的命令前缀是`/`  
   例如：`COMMAND_START=['', '/']`
2. `BISON_TO_ME`  
   是否需要 @Bot 或使用 Bot 的 Nickname 来触发 Bison，默认为`True`  
   例如：
   - `BISON_TO_ME=True`  
     `@Bot /help`
   - `BISON_TO_ME=False`  
     `/help`
3. `BISON_USE_PIC`  
   将文字渲染成图片后进行发送，多用于规避风控，默认为`False`
4. `BISON_USE_PIC_MERGE`: 是否启用多图片时合并转发（仅限群）

   - `0`: 不启用 (默认)
   - `1`: 首条消息单独发送，剩余图片合并转发
   - `2`: 所有消息全部合并转发

   ::: details BISON_USE_PIC_MERGE 配置项示例

   - 当`BISON_USE_PIC_MERGE=1`时：
     ![simple1](/images/forward-msg-simple1.png)
   - 当`BISON_USE_PIC_MERGE=2`时：
     ![simple1](/images/forward-msg-simple2.png)

   :::
   ::: warning
   选择模式`1`时，可能会因为待推送图片过大/过多而导致文字消息与合并转发图片消息推送间隔过大，请谨慎考虑开启。  
   可以考虑选择模式`2`，使图文消息一同合并转发，但可能会使消息推送延迟过长
   :::

---

::: tip 如何进行合理的配置？

- 如果要在在 nonebot 中配置需要的**Bison 配置项**，请参考[NoneBot 配置方式](https://v2.nonebot.dev/docs/appendices/config#dotenv-%E9%85%8D%E7%BD%AE%E6%96%87%E4%BB%B6)，在`.env`/`.env.*`文件中写入希望配置的 Bison 配置项
- 请注意，在`.env`/`.env.*`中添加的配置项 **不** 需要声明变量类型

:::

## :bike: 上车！

首先，我们需要给 Bison 指定一份"订单"，让他知道我们想要订阅什么，去哪里获取包裹
::: tip 不想在群里添加订阅？
可以，但下述操作要求你是`SUPERUSERS`中的一员

- 个人订阅  
  支持私聊添加仅对自己推送的订阅，流程同下
- 群组订阅  
  支持私聊给某个群聊添加订阅，请私聊 Bison 发送`群管理`命令，Bison 会给你发送一个群列表，你可以选择你想要添加订阅的群聊以及执行的命令，之后的流程同下
  :::
  ::: warning Bison 不理我？
  在本段中`COMMAND_START`设置中包含了`'/'`，Bot 的`NICKNAME="bison"`

- 如果出现 bot 不响应的问题，请先排查这个配置
- 尝试在命令前添加设置了的命令前缀，如`COMMAND_START=['!']`，则尝试使用`!添加订阅`
- `BISON_TO_ME`默认为`True`, 请在命令前 @Bot 或者添加 Bot 的 Nickname : `@Bot 添加订阅`
- Bison 只会响应群主/群管理/SUPERUSERS 的命令，请检查你的群权限等级
  :::

## :memo: 添加订阅

选择一个群聊作为 Bison 的客户，发送`添加订阅`命令，Bison 会开始订阅流程
![add sub](/images/add-sub.png)

## :card_file_box: 选择订阅的平台

Bison 会列出所支持的常用平台，你可以选择你想要订阅的平台，也可以回复`全部`来查看所有 Bison 支持的平台

在这里，我们选择`weibo`作为我们的订阅平台
![choose platform](/images/choose-platform.png)

## :pushpin: 给出需要订阅的目标

Bison 会要求你给出你想要订阅的目标，这个目标可以是一个 uid，也可以是特定格式的包含 uid 的链接
![uid parse](/images/uid-parse.png)
这里发送了包含有 uid 的链接  
:::tip
在`weibo`中该链接必须符合`https://weibo.com/u/<uid>`格式  
具体请以[各个平台的支持情况](/usage/#所支持平台的-uid)为准
:::
当然，你也可以直接向 Bison 发送 uid:`6279793937`

## :label: 选择需要订阅的类别

在给出需要订阅的目标后，Bison 会告诉你该 uid 所对应的用户名，你可以借此确认订阅是否正确。
接着，如果该平台支持多个类别，Bison 会要求你选择你想要订阅的类别
![choose category](/images/choose-category.png)
这里选择订阅明日方舟微博的`视频 图文 文字`类别，当该账号在微博发送了视频、图文、文字时，Bison 会将其派送到你的群聊中

## :bookmark: 选择需要特定订阅/屏蔽的话题 (tag)

::: tip 什么是话题 (tag)？
Tag 是社交平台中一种常见的功能，它用井号 (#) 作为前缀，标记关键词，方便用户搜索相关内容。
例如：`#明日方舟# #每日打卡#（微博、哔哩哔哩） #baracamp（推特）`

具体的过滤规则参见[Tag 的推送规则](/usage/#tag-的推送规则)
:::
![choose tag](/images/choose-tag.png)
这里选择不特定订阅也不屏蔽话题，即`全部标签`

## :tada: 订阅成功，开始派送！

订阅流程结束后，Bison 会告诉你订阅成功，并且会在群聊中发送一条订阅成功的消息（如上图）  
至此，你已经成功订阅了一个明日方舟微博账号，Bison 会在该账号发布新内容时将其派送到你的群聊中

## :mag: 查询订阅

你可以在任意时刻查询该群的订阅情况，只需要在群里向 Bison 发送`查询订阅`命令即可
![query sub](/images/list-sub.png)

## :wastebasket: 删除订阅

你可以在任意时刻删除该群的订阅，只需要在群里向 Bison 发送`删除订阅`命令即可
![delete sub](/images/del-sub.png)

## :globe_with_meridians: 使用网页管理订阅

Bison 提供了一个网页管理订阅的功能，即 WebUI，你可以在网页上查看、添加、删除订阅  
如果需要使用，请 **私聊** Bison 发送`后台管理`命令，Bison 会给你发送一个网页链接，在浏览器打开即可进入网页管理订阅的界面
::: tip 该命令无效？
`后台管理`命令仅对`SUPERUSERS`的私聊有效
:::
::: tip Bison 给出的链接无效？
Bison 所给的链接中的 ip 和 port 是`BISON_OUTER_URL`配置决定的，也就是说 Bison 本身不能获取服务器的 ip 与自身的 port，所以 Bison 给出的链接可能是无效的。你可以在`BISON_OUTER_URL`中设置你的服务器 ip 与 port，或者直接修改 Bison 给出的链接为正确的`http://<ip>:<port>/bison/...`来进入网页管理订阅的界面。

参见[详细介绍 - 配置](/usage/#配置)的`BISON_OUTER_URL`部分
:::
::: tip 认证失败？
:bug:
在浏览器输入网址进入网页时，第一次进入可能会出现 unauthorized，请再输入网址重新进入一次，而**不能**简单的刷新页面
:::

## :chart_with_upwards_trend: 监控

Bison 支持导出 Prometheus 格式的指标数据，并且提供了配套的 Grafana 面板进行可视化查看。

在默认情况下，指标导出会默认挂载在 "/metrics" 路径下，详细配置请参考插件 [nonebot-plugin-prometheus](https://github.com/suyiiyii/nonebot-plugin-prometheus?tab=readme-ov-file#%E9%85%8D%E7%BD%AE) 。

可视化面板可以在[dashboard.json](https://github.com/MountainDash/nonebot-bison/blob/main/docker/grafana-dashboard.json)找到。

如果你对 Prometheus 以及 Grafana 不是很熟悉，可以使用[docker-compose 部署-包括监控](/usage/install.md#docker-compose-部署-包括监控)提供的安装方式，快速上手体验。
