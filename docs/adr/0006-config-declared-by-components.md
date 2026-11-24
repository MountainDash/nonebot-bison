# 配置由组件声明，覆盖范围由组件角色决定

bison 的配置系统是 **bison 内部的一个模块**，不是一个包。它读取 toml，由各组件声明自己的 pydantic 模型，loader 按组件 id 组装并校验。凭证是数据而不是配置，留在存储中；配置只描述使用哪个凭证以及如何轮换。

配置不能对所有组件笼统支持三层覆盖：一个源只抓取、解析和富化一次，因此这些阶段不能接受互相冲突的订阅级配置。允许的范围如下。

| 组件 | 组件默认 | 源级覆盖 | 订阅级覆盖 |
|---|---:|---:|---:|
| Fetcher | 是 | 是 | 否 |
| Parser | 是 | 是 | 否 |
| Enricher | 是 | 是 | 否 |
| Renderer | 是 | 是 | 是 |
| Sender | 是 | 否 | 否 |

目的地不是新的配置层，只选择 `sender`。sender 与 destination.adapter 不兼容是启动期装配错误，不是运行时内容降级。

**为什么不分包**：包边界应由依赖集合与发布节奏决定。配置系统与注册中心互相咬合，且没有第二个消费者或独立发布需求，拆包只会制造额外边界。

## Considered Options

- **一个全局配置模型、所有字段平铺**：加一个平台就增加全局字段，配置与组件无法各自演进。
- **每个组件自己读文件**：校验时机分散，拼错组件名会被静默忽略。
- **所有组件都支持订阅级覆盖**：与「一个源只抓取、解析、富化一次」直接冲突。
- **独立的配置包**：没有独立依赖或消费者，只会增加 `config → registry` 的跨包耦合。

## Consequences

- 校验失败必须定位到组件、配置段与行；未注册的组件名必须报错。配置 schema 进入注册中心，供表单与 inspect 使用。
- Source 执行计划、Subscription、Destination 与相关组件默认/能力版本共同形成不可变 **effective_revision**。修改 Subscription 的 filter、renderer 或渲染配置只影响新内容；修改 Source 的 Parser/Enricher 等配置产生新执行计划 revision；修改共享 Destination.sender 或相关默认/能力版本会改变所有受影响订阅的 effective_revision。已在运输中的包裹继续使用原快照。
- Renderer 的完整解析后配置必须进入渲染计划、分组与缓存身份，不能只按 `renderer_id` 合并。顺序代际、执行计划和发送包裹引用同一 effective_revision。人工重投属于新投递代，重新计算当前 effective_revision 并据此选择重进阶段。
- Source 的 `(line, fetcher, platform_key)` 与 Destination 的 `(adapter, native_id)` 是自然身份，不是可编辑配置；变更它们必须新建对象，目的地自然身份必须唯一。
- 目的地级任意配置仍不做；不同群的风格需求由订阅级 Renderer 配置表达。
