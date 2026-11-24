# bison — 业务应用

依赖 NoneBot（[ADR 0001](../adr/0001-courier-has-no-nonebot-dependency.md)）。bison 负责业务身份、组件装配、抓取补发、订阅生命周期、配置、渲染与发送；courier 只负责通用运输。

## 1. 组件模型

**五类组件，一个通用适配器。** 组件作者不写 courier 的面单、地址、资源键、血缘或 `next_attempt_at`。

```python
class Component[In, Out](ABC):
    kind: ClassVar[str]
    config_model: type[BaseModel]
    async def run(self, item: In, ctx) -> Out: ...
```

依赖用类型标注声明，由 [ADR 0003](../adr/0003-di-open-vocabulary-closed-mechanism.md) 的注入器解析。组件执行必须可取消；组件拥有并清理自己创建的 client、页面、进程或其他资源，通用流水线不需要知道这些资源的具体类型。

「新增一个平台 ≈ 100 行」仍是心智模型：最简单的抓取器只写一个类 + 一个 `run`，默认链路完成其余工作。

## 2. 五类组件与报文

| 组件 | 输入 | 输出 |
|---|---|---|
| **抓取器 (Fetcher)** | 源 + 抓取参数 + 补抓游标 | 原始产出 `RawPost` 列表与下一轮调度信息 |
| **解析器 (Parser)** | `RawPost` | `Report` |
| **富化器 (Enricher)** | `(Report, RawPost)` | `Report`，只能新增 `extra` |
| **渲染器 (Renderer)** | `Report` + 解析后配置 + 能力变体 | 中立 `RenderedContent` |
| **发送器 (Sender)** | `RenderedContent` + 目的地 | 投递结果 |

`RawPost`、`Report`、执行计划与配置快照全部必须满足 Parcel 的 JSON 往返约束。

```python
class Report(BaseModel):
    source_id, post_id, content_revision
    posted_at, url, author, title, text, media
    extra: dict[str, Any]       # 仅 Enricher 业务扩展可写
```

系统错误、降级、路由与投递信息使用独立的系统命名空间和结构化事件，不写入 `extra`，也不占用 Enricher 的 `adds`。

```python
class Enricher(Component[tuple[Report, RawPost], Report]):
    adds: frozenset[str]
    required: bool = False
```

启动校验：`adds` 不得与核心字段或系统命名空间冲突；同一源上的 `adds` 不得相交；运行时写键必须是 `adds` 子集。多个 Enricher 的执行顺序来自源配置，而非插件加载顺序。

## 3. 内容身份、订阅身份与投递身份

三种身份不得混用：

1. **轮询身份**：`(source_id, scheduled_slot)`，只对齐一次调度执行及其崩溃重放。
2. **内容身份**：`(source_id, post_id, content_revision)`，是 Report 的稳定业务身份，不继承轮询 id。
3. **投递身份**：在内容身份上加入订阅、渲染计划、目的地与投递代，保证重放安全，同时允许同一内容合法发往不同订阅。

Fetcher 优先使用上游编辑版本作为 `content_revision`；上游没有版本时，使用规范化原始内容的摘要。规范化规则必须确定且可版本化，排除抓取时间、请求 id 等易变字段；无法提供稳定内容身份的 Fetcher 不得接入。内容未变时重复轮询得到同一 Report id；内容编辑形成新 revision，而不是同 id 不同 payload。相同内容身份却得到不同摘要是冲突错误。

每个 Report 是新的后代预算根，但保留指向轮询包裹的 `parent_id`。Report 的 `content_hash` 只覆盖稳定业务内容，不包含 `parent_id` 或轮询 id；跨轮询幂等重放保留首次 parent 作为审计。抓取批大小单独受限，不把整次轮询的所有动态塞进一个默认预算。

渲染包裹可以按相同渲染计划聚合多个订阅；发送包裹必须显式携带 `subscription_id`、`destination_id` 与统一的 `effective_revision`。新订阅默认不补历史：轮询扇出使用当时的订阅集合快照，崩溃重放不得把后来新增的订阅偷偷加入。

**游标与去重键都不能替代对方：** 去重防止重复，游标决定补抓从哪里继续。运行期游标只在对应内容已经成为耐久运输包裹或耐久死信后推进，并与这些写入共享事务。解析或富化死信已经被显式记录，因此不构成静默跳过。

迁移是独立例外，不违反这条不变量：`cutover_watermark` 记录真实观察快照，`source_post` 用 `observed / migration_skipped / handed_off` 等观察状态抑制首轮重复；它们不是运行游标，也不是 `DELIVERED` 或 `DEAD` 历史。只有能证明晚于切流高水位的内容才补发；无法判断先后的迟到旧内容形成补抓缺口，不能因“不在快照里”就冒充新内容。

## 4. 流水线与执行计划

默认逻辑链路：

```text
Source 到期
  → fetch:<fetcher>       [resource = host#opaque_credential_id]
  → 每帖执行计划：parse → enrichers
  → 按有效渲染计划分组
  → render:<renderer>     [resource = renderer:<id>]
  → 按订阅与目的地扇出
  → send:<sender>         [resource = destination:<id>]
```

连续 inline 阶段合并执行；扇出基数变化或存在独立外部资源约束时建立站点。默认仍只有 fetch、render、send 三类站点，但 external Parser/Enricher 会按执行计划增加站点。

启动装配时，每个源生成不可变的有序执行计划：

```python
{
  plan_id,
  source_revision,
  steps: [
    {kind: "parser" | "enricher", component_id, external, config_snapshot},
    ...
  ],
}
```

包裹携带 `plan_id + step + source_revision`，下游订阅快照再组合成统一的 `effective_revision`。每个 external 站点成功后推进到下一步；连续 inline 后缀并入当前站点。`RawPost` 与当前 `Report` 随计划一起持久化，因此重启后可以从失败步骤继续，而不是重抓，也为人工重投保留必要接入点。

失败规则：

- 每条 RawPost 独立 try/except，一条坏数据不得中断整批。
- Parser 确定性失败：当前帖死信，绝不重试抓取。
- `required=False` 的 inline Enricher 失败：记录系统错误并立即继续。
- `required=False` 的 external Enricher：先消耗自己的瞬态重试预算，耗尽后记录并继续下一跳。
- `required=True`：可重试错误消耗预算，耗尽或永久失败后当前帖死信。
- 任一后续阶段失败不得重新执行 fetch。

站点边界判据不变：扇出基数变化或独立外部资源约束。渲染与发送独立，是因为它们可能昂贵或不可逆；纯解析与富化默认内联，避免无收益的往返。

## 5. 扇出与顺序

- Fetcher 必须返回有确定顺序的批次；通常按 `(posted_at, post_id)` 排序。禁止无序集合决定发送顺序。
- 一次源只抓取一次；过滤在订阅扇出前按各订阅快照分别求值。
- 同一有效渲染计划只渲染一次，然后按订阅/目的地扇出；不同计划可以产生不同内容变体。
- 最终顺序只承诺：**同一 Source、同一 Subscription、同一 `effective_revision` 内的内容保序**。不同源之间只有目的地信道的到达 FIFO，不承诺按 `posted_at` 全序。
- 渲染降级在原渲染站点内完成并直接产生发送包裹，不另开一条可能让后续内容超车的降级信道。

`effective_revision` 不同的内容不承诺跨代际顺序；配置修改只影响新内容，见 §6。

## 6. 数据模型与生命周期

指示性模型如下，确切列类型与命名属于实现：

| 表 | 关键字段与不变量 |
|---|---|
| **source** | `id`、`line`、`fetcher_id`、`platform_key`、`display_name*`、`interval`、`next_poll_at`、`merge_pending`、`cursor`、`revision`、`enabled` |
| **destination** | `id`、`adapter`、`native_id`、`sender`、`revision`、`paused` |
| **subscription** | `id`、`source_id`、`destination_id`、`renderer_id`、`filters`、`config`、`revision`、`paused`、`created_at` |
| **source_post** | `source_id`、`post_id`、`content_revision`、内容摘要、观察状态、首次见到时间 |
| **execution_plan** | `plan_id`、源、`source_revision`、有序步骤与配置快照 |
| **cutover_watermark** | 接管源、真实观察高水位、切流时间、快照内容与缺口状态 |
| **credential** | 随机不透明 `id`、`host`、`secret`、`cooldown_until`、`last_ok_at` |
| **artifact / artifact_ref** | 内容摘要、持久位置、Parcel 引用与对账状态，见运行规格 |

自然身份规则：

- Source 的 `(line, fetcher_id, platform_key)` 唯一且创建后不可变；换账号必须新建 Source。
- Destination 的 `(adapter, native_id)` 唯一且创建后不可变；换真实聊天位置必须新建 Destination。
- 名字是展示缓存：TTL 7 天、可手动刷新；取不到名字不得阻断订阅。
- 删除后重建使用新对象 id，不继承旧对象的身份、游标或订阅关系。

变更规则：

- `effective_revision` 由 Source 执行计划 revision、Subscription revision、Destination revision，以及相关组件默认配置与能力版本共同计算。执行计划、订阅快照、渲染计划和发送包裹必须引用同一个有效代际。
- 修改 Subscription 的 filter、renderer 或渲染配置产生新 subscription revision；修改 Source 的 Parser/Enricher 等配置产生新执行计划 revision；修改 Destination.sender 或相关组件默认/能力版本会改变所有受影响订阅的 effective_revision。它们只影响新内容，旧包裹继续按原快照执行。
- 暂停 Source：不再产生新轮询；尚未开始的 queued fetch 转为 `CANCELLED`，in-flight fetch 及其已经产生的下游继续。`merge_pending` 保留到恢复后至多补一次。
- 暂停 Subscription：只处理目标成员。共享渲染包裹中的其他成员照常扇出；目标成员的发送包裹以 `held` 保存，不占目的地活动 head，恢复后按原 seq 唤醒。
- 暂停 Destination：该目的地的未执行发送全部 held，其他目的地不受影响；恢复时统一唤醒。
- 删除 Source、Subscription 或 Destination：按成员取消未执行且结果可知的后代，共享渲染中的其他成员不得连带取消。`CANCELLED` 不是故障死信，artifact 引用随终态对账释放。
- 正在执行或 `outcome_unknown` 的发送不得直接取消；先按实际结果结算。已经由平台接受或结果不可知的内容保留相应审计，删除只阻止新的后代，不篡改历史。

## 7. 组合调度、轮询合并与补抓

**bison 拥有唯一调度循环。** 它通过 courier 的单步调度与到期接口比较两类时间：

| 到期项 | 真相 | 到期后做什么 |
|---|---|---|
| `source.next_poll_at` | bison source 表 | 入队一个抓取包裹 |
| `Receipt.next_attempt_at` | courier，投影到 lane | 让唯一 worker 执行 head |

调度器不直接等待站点；worker 执行期间，调度器仍能接收唤醒和处理数据库调度。源生产与 courier 消费不得各开一个扫描循环。

推后 `next_poll_at` 与入队抓取包裹共享事务。事务内「先入队、再推后」只是固定写法，不提供额外崩溃保证；真正保证来自同一提交点、确定性轮询 id 与提交后唤醒。

**每个 Source 至多一个未开始的抓取包裹。** 到期时发现已有 queued/in-flight，必须在一个事务中设置 `merge_pending=True` 并按源规则推后 `next_poll_at`，不碰内容游标；这样调度器不会反复选择同一个已经到期的 Source。

当前 fetch 成功结算时，若 Source 仍 enabled 且 `merge_pending=True`，在同一事务中消费标记、入队至多一个合并轮询并写下一轮 `next_poll_at`；资源 `resource_available_at` 仍然生效。fetch 自身 `DEAD` 清除合并标记且不自动紧跟补抓，只按正常 `next_poll_at` 等待；删除导致的 `CANCELLED` 同样清除。暂停导致的 queued fetch `CANCELLED` 不复活该包裹，但 Source 保留并冻结合并标记，恢复后至多补一次。被合并的旧轮询不推进内容游标，也不代表真实抓取；合并只防请求风暴与扫描热循环，不是历史补抓算法。

Fetcher 必须声明补抓能力：

- **可分页/可游标**：从最后成功游标补到当前位置，或触及明确的补抓上限。
- **仅最新快照**：恢复后合并抓取一次，以稳定内容身份去重；若最后已见内容已消失、列表达到上限或时间范围不能覆盖，则记录补抓缺口。

补抓缺口包含 Source、时间区间与可确定的数量；数量无法确定时明确为未知。缺口进入 inspect、日志与指标，不伪装成死信，也不计入成功补发。对仅最新快照的 Fetcher，只能承诺「上游仍可枚举的更新不丢」。

源级间隔、「直播中」「已完结」等只修改 `next_poll_at`；host/凭证风控只修改对应资源持久化的 `resource_available_at`，二者不得互相覆盖。

## 8. 凭证与资源

凭证是数据，不是配置：

| 职责 | 归属 |
|---|---|
| 存取、选择、轮换、冷却 | bison provider |
| 请求装饰 | Fetcher 自己的 client 工厂 |
| 凭证级节流 | `host#opaque_credential_id` 资源键 |

凭证 id 是随机不透明标识，不是 secret、Cookie 或可逆指纹。secret 不进入 Parcel、resource、日志、异常、死信、inspect、指标或迁移报告。

资源键在入队时从包裹计算并冻结。轮换默认只影响新根包裹；旧包裹留在原信道。需要让旧内容改用新凭证时，通过人工重投创建新代并重新计算资源，不能原地修改一个已排队包裹的 lane。

人工重投使用当前有效配置、当前凭证和当前组件实现，保留原内容与自然身份，并根据当前计划选择**最早必要接入点**：

| 原死信与当前计划 | `requeue_from` 与 artifact 规则 |
|---|---|
| fetch 失败，没有可用内容快照 | 从 fetch 重进，不涉及 artifact |
| Parser/Enricher 死信 | 计划不变时从持久 RawPost 进入原失败 step；计划变化时进入最早变化 step；必要 RawPost 缺失则可见拒绝 |
| render 失败，或 send 失败但渲染计划已变化 | 从持久 Report 重进 render；重投时不预建 artifact_ref，正常发布后再建 |
| send 失败，当前渲染计划仍兼容原 artifact 且文件存在 | 从 send 重进，并在重投事务中建立新 artifact_ref |

Sender 或凭证变化但渲染计划仍兼容时可以复用 artifact；Renderer 配置、实现版本或 Sender 能力变体变化必须退回 render。重投创建新预算根，原死信条件记录 `requeued_to`，重复请求得到同一接入点与同一新代。必要 RawPost、Report 或 artifact 已缺失时明确拒绝，不伪造可恢复性。

共享上游死信按原订阅集合快照逐成员过滤：已删除或无权限的成员排除，其余成员按当前计划重新分组；只有没有任何可重投成员时才整体拒绝。整组采用所有合格成员中**最早的必要接入点**，保证一次重投只有一个新预算根，之后再走正常分组；只有整组都能直接复用旧 artifact 时才从 send 重投。

artifact 兼容性比较实际影响产物的 Renderer 配置、实现版本、内容变体与 Sender 能力，而不是仅比较 revision 字符串是否相等。直接复用旧 artifact 时，新 ref 建立后才能释放旧 ref；退回 render 的新代不再引用旧产物，旧 ref 可在重投提交后对账释放。

## 9. 渲染计划、能力与降级

渲染产物是与传输无关的有序块序列：文本、图片引用、可选提及/回复/附件。Sender 声明能力并翻译成具体平台消息。

每个订阅在渲染前计算有效计划：

```text
内容身份与 effective_revision
+ renderer_id
+ 完整解析后配置
+ Renderer 声明的实现版本
+ Sender 能力集
+ 目标变体与降级链
```

只有完整计划相同的订阅才共享渲染。配置、内容或实现版本变化不得复用旧产物；同 id 不同内容必须报冲突。

**核心不识别 Renderer 的内部技术。** 某个 Renderer 是否使用浏览器、Canvas 或模板，不改变通用失败语义：

1. 可重试失败先消耗通用重试预算。
2. 重试耗尽，或遇到可降级的永久失败，在原渲染站点内进入 `basic`。
3. `basic` 输出**文字 + 动态原生图片/媒体**，不制作渲染卡片；无原生媒体时自然只有文字。
4. 原生媒体不可用或 Sender 不支持媒体时，退到内建最终纯文本。
5. 所有可用变体都失败才进死信。

组件必须响应取消并清理自己的资源。关闭导致的取消不降级，包裹等待重启。Sender 瞬态失败只重试发送，不改变内容；Sender 与 `destination.adapter` 不兼容属于启动期装配错误，不属于内容降级。

每次降级产生结构化事件，携带 `subscription / destination / renderer / sender / from / to / reason`，同时按订阅与目的地投影 24h 统计。静默丢弃内容块禁止。

## 10. 配置系统

见 [ADR 0006](../adr/0006-config-declared-by-components.md)。配置不再对所有组件笼统提供三层覆盖：

| 组件 | 组件默认 | Source 覆盖 | Subscription 覆盖 | 其他 |
|---|---:|---:|---:|---|
| Fetcher | ✓ | ✓ | — | 保证一个源只抓一次 |
| Parser | ✓ | ✓ | — | 保证一个内容只解析一次 |
| Enricher | ✓ | ✓ | — | 顺序与配置均属执行计划 |
| Renderer | ✓ | ✓ | ✓ | 解析后完整配置进入计划、缓存与 revision |
| Sender | ✓ | — | — | Destination 只选择 sender，不做任意目的地配置 |

凭证是数据。配置只描述使用哪个不透明凭证与轮换策略。

loader 按组件 id 组装 pydantic schema，错误定位到组件、配置段与行；未注册组件名必须报错。配置 schema 进注册中心，但 inspect 输出必须脱敏。

## 11. 专线与包名

**专线 (Dedicated Line)**：面向某个社交媒体、提供该链路上部分或全部组件的发行包。

```text
nonebot-bison                          核心
nonebot-bison-<社交媒体>                专线
nonebot-bison-<社交媒体>-<类别>-<名称>   该社交媒体的单类扩展
nonebot-bison-<类别>-<名称>             不绑定社交媒体的扩展
类别 ∈ {fetcher, parser, enricher, renderer, sender}
```

子包声明 `bison_api_version`，启动时校验；同时使用 pip 依赖约束管大版本。子包是普通 NoneBot 插件，由 `require()` / 插件列表加载，不使用 entry points 形成第二套发现机制。

## 12. 对话层

Alconna。命令式为主，交互式引导为辅：

- `bison sub add <源> [--style] [--to]` 覆盖大部分订阅。
- 不带参数时进入最短引导；状态机只服务新手场景。
- 人工从死信创建新投递代的命令统一称为**重投**，与自动重试区分。

## 13. 注册中心与 inspect

注册中心收集地址/站点、五类组件、依赖、配置 schema、执行计划、子包 API 版本与源配对。inspect 是注册中心 + courier 状态 + bison 业务状态的数据投影：

```python
{
  "stations": [...],
  "channels": [...],
  "dead_letters": [...],
  "components": [{"name", "kind", "needs", "config_schema", "adds"}],
  "sources": [{"id", "fetcher", "parser", "enrichers", "cursor", "catchup_gaps"}],
  "subscriptions": [{"id", "effective_revision", "renderer", "degradations_24h", "drops_24h"}],
  "artifacts": {"live_refs", "bytes", "missing", "backpressure"},
  "api_versions": {...},
}
```

这不是公开 API 的授权声明。网页与对话必须按运行规格的对象级权限矩阵过滤；全局信道、组件、共享死信、资源与配置不能因「有合法 JWT」就向所有群管理员开放。
