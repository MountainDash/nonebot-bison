# 峯驰物流 / MountainDash Logistics

一个把社交媒体上的动态搬运到聊天平台的系统。它的语言借用现实物流：动态被打包成包裹，沿信道运到各个站点，由站点决定继续转运还是交付给最终使用者。

## 语言

### 运输

**包裹 (Parcel)**:
一次投递的完整单位，由面单、载荷与随行信息组成，在站点之间流转。
_Avoid_: 消息, 任务, job, item

**面单 (Waybill)**:
贴在包裹上的投递凭据，写明当前目的地、投递状态与途经站点。
_Avoid_: 元数据, metadata, 路由表, roadmap, 标签

**载荷 (Payload)**:
包裹里真正被运送的内容，例如一份待发送的报文。物流不解释它是什么。
_Avoid_: 内容, body, data, 数据

**信道 (Channel)**:
包裹的运输通道，按目的地划分。同一信道内同时至多一个包裹在途，因此信道内的包裹按投递顺序交付；信道之间互不等待。
_Avoid_: 队列, queue, 管道, 车道, 流

**站点 (Station)**:
信道尽头的一处处理位置，接收包裹并决定把它转运、就地终结还是丢弃。
_Avoid_: 处理器, handler, 消费者, consumer, worker, 节点

**入口点 (Intake)**:
包裹进入物流的起点。抓取器产出的包裹从这里被投递。
_Avoid_: 入口, 生产者, producer, publisher

**中转站 (Relay Station)**:
处理后把包裹重新投入物流的站点。它可以调整载荷，也可以改面单上的目的地。
_Avoid_: 中间件, middleware, 处理器

**终点站 (Terminal Station)**:
把包裹交付给最终使用者的站点。包裹在此结束运输。
_Avoid_: 出口, sink, 消费者

**回收站 (Dead Letter Station)**:
接收无法投递或重试耗尽的包裹的站点。包裹进入回收站即终止运输。
_Avoid_: 死信队列, DLQ, 错误队列, 垃圾桶

**投递凭据 (Receipt)**:
随包裹同行的进度记录，包含投递状态与途经站点的地址链。
_Avoid_: 回执, ack, 状态

**地址 (Address)**:
面单上写的目的地标识，对应一个已注册的站点。
_Avoid_: 路由键, routing key, tag, 路径

### 业务

**源 (Source)**:
被监控的一个社交媒体账号或栏目。抓取器按源抓取内容。
_Avoid_: 目标, target, 平台账号, 订阅对象

**订阅 (Subscription)**:
一个目的地对若干源的关注关系，附带渲染风格等偏好。
_Avoid_: 关注, follow, 监听, 监听项

**目的地 (Destination)**:
最终接收内容的聊天位置，例如一个群或一个私聊。
_Avoid_: 目标, target, 用户, user, 会话, session

**抓取器 (Fetcher)**:
从某个社交媒体取得原始产出的组件。它自行声明抓取时机与所需的请求条件。
_Avoid_: 平台, platform, 爬虫, spider, 采集器

**解析器 (Parser)**:
把抓取器的原始产出整理成报文的组件。
_Avoid_: 处理器, 转换器

**报文 (Report)**:
解析器整理后得到、可以交给发送器发送的正式内容。
_Avoid_: 消息, post, 消息段, segment

**渲染器 (Renderer)**:
把报文渲染成特定格式（例如图片）的组件。
_Avoid_: 主题, theme, 模板, template, 样式

**渲染产物 (Rendered Content)**:
渲染器产出的、与传输方式无关的内容，由文本与图片等有序块组成，由发送器负责翻译成具体聊天平台的形式。
_Avoid_: 消息, MessageSegment, UniMessage, 消息段

**发送器 (Sender)**:
把渲染结果交给某个聊天平台的组件。
_Avoid_: 通道, adapter, 发送插件

**调度中心 (Dispatcher)**:
按抓取器声明的调度要求安排抓取时机的组件。
_Avoid_: 调度器, scheduler, 轮询器

**订阅器 (Subscriber)**:
处理用户订阅意图、把订阅登记到系统的组件。
_Avoid_: 订阅管理, sub_manager, 订阅服务

**专线 (Dedicated Line)**:
面向某一个社交媒体、提供该链路上的一部分或全部组件（抓取、解析、可选渲染与发送）的一个发行包。
_Avoid_: 平台, platform, 组件合集, 套件, 插件包

**注册中心 (Registry)**:
记录抓取器、解析器、渲染器、发送器与站点声明的清单，供调度、投递和查看使用。
_Avoid_: 插件系统, plugin manager, 管理器
