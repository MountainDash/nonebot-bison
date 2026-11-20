# bison — 业务应用

依赖 NoneBot（[ADR 0001](../adr/0001-courier-has-no-nonebot-dependency.md) 的理由不适用于 bison 的任何部分：渲染器与发送器本质上依赖 NoneBot 插件）。

## 1. 组件模型

四类组件，一个通用适配器。组件作者**不写任何 courier 概念**（面单、地址、资源键、`next_attempt_at`）。

```python
class Component[In, Out](ABC):
    kind: ClassVar[str]                  # 声明的产出/接受标签
    config_model: type[BaseModel]        # 声明的配置 schema
    async def run(self, item: In, ctx) -> Out: ...
```

依赖用类型标注声明，由 [ADR 0003](../adr/0003-di-open-vocabulary-closed-mechanism.md) 的注入器解析。

**「新增一个平台 ≈ 100 行」这条心智模型不能退化。** 判据：写一个最简单的抓取器，作者只写一个类 + 一个 `run`。

## 2. 四类组件

| 组件 | 输入 | 输出 |
|---|---|---|
| **抓取器 (Fetcher)** | 源 + 抓取参数 | 原始产出 `RawPost` 列表 |
| **解析器 (Parser)** | `RawPost` | 报文 `Report`（固定核心字段，见 §3） |
| **富化器 (Enricher)** | `(Report, RawPost)` | `Report`，**只能新增** |
| **渲染器 (Renderer)** | `Report` + 风格 | 渲染产物（中立内容，[ADR 0007](../adr/0007-rendered-content-is-transport-neutral.md)） |
| **发送器 (Sender)** | 渲染产物 + 目的地 | 投递结果 |

抓取器另外负责**订阅输入解析**（把用户输入变成源）与**源名字查询**——只有它知道该平台的 URL / ID 形态。

### 报文与富化

```python
class Report(BaseModel):        # 核心字段，谁都不能改
    source_id, post_id, posted_at, url, author, title, text, media
    extra: dict[str, Any]       # 富化器唯一能写的地方

class Enricher(Component[tuple[Report, RawPost], Report]):
    adds: frozenset[str]        # 它会写哪些 extra 键
    required: bool = False      # 失败是致命还是可跳过
```

四条启动期校验：`adds` 与核心字段重名 → 报错；同一源上两个富化器的 `adds` 相交 → 报错；运行时写入的键必须 ⊆ `adds`；`required=False` 的富化器失败只记 `extra["_enricher_errors"]` 并继续。

**理由：** 一个可选的富化器（翻译、头像、直链）不应该有能力让整条动态发不出去。旧代码里一条 `JSONDecodeError` 杀掉整个抓取周期，就是缺这条区分。

### 渲染产物

有序块序列，最小集合：文本、图片引用、可选提及/回复/附件。**发送器负责翻译**成 SAA 的 `MessageSegmentFactory` 或 Alconna 的 `UniMessage`，并声明自己的能力集；不支持的内容按 §9 降级。

## 3. 流水线与站点映射

```
源调度到期
  → 站 fetch:<fetcher>   [resource = host#凭证]
      抓取 → 解析 → 富化 → 按渲染风格分组 → post_many
  → 站 render:<renderer> [resource = renderer:<id>]
      渲染一次，产出渲染产物 → post_many，每个目的地一个包裹
  → 站 send:<sender>     [resource = destination:<id>]
      翻译成平台消息并发出去
```

**解析与富化在抓取站内同步执行，不单独成站。** 它们是纯函数、无外部 IO、失败应连带抓取一起归因；拆成独立站点会让每条动态多一次信道往返，只换来更长的失败链。组件仍然是独立的（作者分开写、注册分开注册）。

**渲染与发送是独立站点**，因为它们是昂贵或不可逆的步骤：渲染要浏览器，发送一出去就收不回。

### 站点边界判据

站点边界由两条之一决定：**扇出基数变化**，或**独立的对外资源约束**。两者都不满足的阶段就内联。

| 阶段 | 扇出 | 对外资源 | 归属 |
|---|---|---|---|
| 抓取 | 1 源 → N 条动态 | 上游 host + 凭证 | **站点** |
| 解析 | 1:1 | 默认无；声明 `external` 则有 | 内联（默认）/ 站点（`external`） |
| 富化 | 1:1 | 默认无；声明 `external` 则有 | 内联（默认）/ 站点（`external`） |
| 渲染 | 1 条 → N 个风格 | 浏览器 | **站点** |
| 发送 | 1 → N 个目的地 | 聊天平台 + 目的地 | **站点** |

**所以默认是三个站点，但只要有一个解析器或富化器声明 `external = True`，就自动多出一个站点。** 这不是全局开关，是按组件的 —— 大多数解析器是纯的，只有少数（微博长文要二次请求、B 站 OPUS 要额外接口）需要独立的重试与限流。

### 站内失败隔离（规格要求）

1. **per-post try/except。** 一条坏数据不得中断整批。旧代码里一条 `JSONDecodeError` 杀掉整个抓取周期（#632）就是缺这一条。
2. **确定性失败不重试上游。** 无外部 IO 的解析器/富化器失败是**确定性**失败（同样的输入会同样失败），因此该条直接进死信，**不得重试抓取** —— 重试只会白打上游请求，在风控环境下是真实伤害。这一条消除了内联方案最大的归因问题。
3. **`external` 组件必须声明资源键**（它的 host）。启动期校验：声明了 `external` 却没有对应的站点地址 → 报错。

**扇出点**（一次抓取 → 一次渲染 → N 次发送）：渲染包裹携带「需要它的目的地列表」，渲染完成后按目的地扇出。这样同一张卡片只渲染一次，而目的地之间互不阻塞。

## 4. 装配规则

默认按类型配对，冲突或需要时显式覆盖：

- 解析器声明它接受的 `RawPost` 类型；一个类型只有一个解析器时自动配对。
- 一个类型有多个候选 → **启动期报错**，要求在源配置里显式指定。
- 发送器是 1:N 配对（所有发送器都接受 `rendered`），不能用类型决定，因此走**目的地上的 `sender` 字段**，默认 `saa`。
- 装配失败一律在启动期报错，列全部缺失项。

## 5. 默认链路

只写一个抓取器就能跑：

```
抓取器 → 内建直通解析器（标题/正文/链接直接映射）→ 内建 basic 渲染器 → 发送器
```

解析器只在需要额外信息时才写。这是「100 行一个平台」的具体保证。

## 6. 数据模型（指示性，列名待定）

| 表 | 关键字段 |
|---|---|
| **source** | `id`、`line`（专线）、`fetcher_id`、`platform_key`、`display_name`、`display_name_at`、`interval`、`enabled` |
| **destination** | `id`、`adapter`、`native_id`、`sender`（默认 `saa`）、`paused` |
| **subscription** | `id`、`source_id`、`destination_id`、`renderer_id`、`filters`、`created_at` |
| **credential** | `id`、`host`、`secret`、`cooldown_until`、`last_ok_at` |

**身份规则：**

- 源的身份 = `(专线, 抓取器, 平台侧标识)`。**名字永远不是身份。**
- 订阅 = 源 × 目的地 × 渲染风格 × 过滤。目的地不重复存（`destination` 独立一张表），否则会出现旧代码里「按序列化 JSON 相等查找用户」那类重复行。
- 名字是展示缓存：TTL 7 天、可手动刷新、**取不到名字不得阻断订阅**（用平台侧 id 占位）。

## 7. 抓取调度

**一个循环，两类到期项：**

| 到期项 | 存在哪 | 到期后做什么 |
|---|---|---|
| 源的 `next_poll_at` | `source` 表 | 生成一个抓取包裹，入该源的**资源信道** |
| 信道的 `next_attempt_at` | 信道行 | 取 head 投递 |

两者都是「最早到期先跑」，但不能合并成一张表：源是**周期性生产**（一行一个源），信道是**队列消费**（一行一个资源，多源共享）。合并会让「多源共享一个凭证」时无法表达各自的轮询间隔。

**这不是妥协，是语义更准确。** 两种时间语义不同：源级覆盖（「这个源已完结，一天后再看」「直播中，5 秒后再看」）只该影响那个源；信道级节流（凭证风控、发送间隔）才该影响整条信道。混在一张表里，源级覆盖会泄漏成信道级覆盖 —— 一个源的「已完结」会把共用同一 cookie 的另一个源一起冻住。

**原子性与恢复：** 两张表在同一个库里，所以「推后 `next_poll_at` + 入队抓取包裹」在**一个事务**里完成，不损失原子性。顺序是**先入队、再推后**：崩溃只会导致下一轮重复生成一个抓取包裹（重复抓取，去重键会拦住重复投递），不会导致漏抓 —— 符合「不丢 > 不重」。取出包裹时再校验源仍然存在且启用（源可能已被暂停或删除）。

**必须是一个循环，不是两个。** 两个独立的到期扫描循环（一个跑源、一个跑信道）在 SQLite 单写者下会互相阻塞，且「谁先」不确定。正确形状是一个循环取两处的「最早到期」候选，取最小值。

**抓取间隔：** 默认由源声明的 `interval` 决定，抓取器可在一次抓取后返回覆盖值（`Retry-After`、已完结、直播中）。courier 统一加 jitter 并夹紧到 `[min, max]`。**抓取器不许自己随机**。

**200 个订阅不能变成 200 次抓取：** 抓取侧是扇出点。一个源被 N 个订阅关注，只抓一次，扇出 N 次。

## 8. 凭证

凭证是**数据**，不是配置（[ADR 0006](../adr/0006-config-declared-by-components.md)）。三件事拆开：

| 职责 | 归属 |
|---|---|
| 存取、选择、轮换、冷却 | bison 的注入 provider |
| 请求装饰（cookie / UA / Referer / 签名） | 抓取器自己的 client 工厂 |
| **凭证级节流** | 信道的资源键（`host#凭证`） |

资源键必须**从包裹内容算出**，不能是构造函数常量——否则换凭证不会换信道，旧凭证的退避会拖累新凭证。

## 9. 渲染降级与发送器能力

降级链：订阅指定的风格 → `basic` → 纯文本。发送器能力不足同样走降级。

**每一次降级必须可见：** 记 metric、记一条 `extra`、inspect 里能看到「这个订阅过去 24 小时降级了 37 次」。

静默降级比失败更糟：用户看到的是「怪东西」而不是「没东西」，于是既不会报错也不会改配置。

## 10. 配置系统

见 [ADR 0006](../adr/0006-config-declared-by-components.md)。

- 组件声明自己的 pydantic 模型，loader 按组件 id 组装并校验。
- 三层粒度：**组件默认 / 源级覆盖 / 订阅级覆盖**。不做目的地级。
- 校验失败报到「哪个组件的哪一段哪一行」；配置里出现未注册的组件名**必须报错**。
- 配置 schema 进注册中心 → 网页可自动生成表单、inspect 可显示「这个组件接受哪些配置项」。
- courier 不读配置：`CourierConfig(worker_count, retry_budget, default_pacing, ...)` 由 bison 构造后传入。

## 11. 专线与包名

**专线 (Dedicated Line)**：面向某个社交媒体、提供该链路上部分或全部组件的一个发行包。

```
nonebot-bison                          核心
nonebot-bison-<社交媒体>                专线
nonebot-bison-<社交媒体>-<类别>-<名称>   该社交媒体的单类扩展
nonebot-bison-<类别>-<名称>             不绑定社交媒体的扩展
类别 ∈ {fetcher, parser, renderer, sender}
```

例：`nonebot-bison-instagram`、`nonebot-bison-bilibili-renderer-arma`。

包名里不出现 `platform`（已在词汇表禁用）。专线是**概念**，不进入包名——第三段是什么，就决定了这个包是什么。

**子包契约：** 子包声明 `bison_api_version`，bison 启动时校验，不匹配拒绝加载并给出明确报错；同时用 pip 依赖约束管大版本。两者并用，因为「小版本改了一个抽象方法」这种破坏只会在运行时表现为神秘 TypeError。

**发现机制：** 子包是普通 NoneBot 插件，由 `require()` / 插件列表加载，`nb plugin install` 会自动登记。**不使用 entry points** —— 那会是第二套发现机制，并且绕开 NoneBot 的启用/禁用与元数据。

## 12. 对话层

Alconna。命令式为主，交互式引导为辅：

- 命令式：`bison sub add <源> [--style] [--to]`，大部分订阅压成一行。
- 交互式引导：不带参数时进入最短路径（选源 → 选目的地），其余全用参数。
- 状态机只为新手引导保留一种场景。旧代码的 abort / 超时 / 分页细节是「所有东西都靠对话问」的代价。

## 13. 注册中心与 inspect

注册中心收集：地址 → 站点（含 `channel` / `resource` / `kind`）、组件的依赖清单、组件的配置 schema、子包的 `bison_api_version`、源的抓取器/解析器配对。

**inspect 是注册中心 + courier 状态的数据投影**，同一份数据供网页与对话命令使用：

```
{
  stations: [...],                    # 来自 courier.inspect()
  channels: [...],                    # 来自 courier.inspect()
  dead_letters: {...},                # 来自 courier.inspect()
  components: [{name, kind, needs, config_schema, adds?}],
  sources: [{id, fetcher, parser, enrichers, report_fields}],
  subscriptions: [{source, destination, renderer, degradations_24h}],
  api_versions: {line: version},
}
```

`report_fields` 由「解析器核心字段 + 所有富化器的 `adds`」合成——用户能查「这个源的报文会有哪些字段、分别由谁加上」，零运行时成本。
