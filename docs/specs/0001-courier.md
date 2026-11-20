# courier — 运输内核

零 NoneBot 依赖（[ADR 0001](../adr/0001-courier-has-no-nonebot-dependency.md)）。只依赖 `anyio`、`sqlalchemy`（Core）。

## 1. 职责与非职责

**职责：** 接收「包裹 + 地址」，按资源划分信道，串行地把包裹交给站点，直到终结或进入回收站；保证包裹活过重启。

**非职责：** 不认识消息内容、社交平台、聊天平台；不做抓取/渲染/发送策略；不加载配置；不依赖任何 web 框架。

## 2. 概念

| 概念 | 定义 |
|---|---|
| 地址 | 站点标识，字符串。标识**哪一类处理**，不标识**哪一个对象** |
| 包裹 | 一次投递的完整单位 |
| 面单 | 目的地（地址）与投递状态。**不含途经链** |
| 投递凭据 | 状态、每站尝试次数、`next_attempt_at`、最后一次错误 |
| 信道 | 按**资源键**划分的运输通道，一行状态 |
| 站点 | 地址对应的处理函数 |
| 回收站 | 地址 `dead-letter` 上的站点，内建兜底 |

**地址的粒度是本设计的地基：** `fetch:bilibili` 处理所有 B 站源，源是包裹里的参数。因此注册表可以在启动后冻结 —— 用户新增订阅产生的是新**对象**，不是新**处理类型**。

## 3. 包裹

```
Parcel {
  id        : str          # 幂等键；派生，不是随机
  address   : str          # 当前目的地
  kind      : str          # 不透明标签，词汇归宿主（"fetch" / "report" / "rendered" / "notice"）
  payload   : 不透明        # courier 不解释
  metadata  : dict         # 随行数据
  receipt   : Receipt
}

Receipt {
  status        : DELIVERING | DELIVERED | DEAD
  attempts      : dict[address, int]     # 每站一份，独立预算
  next_attempt_at, last_error, last_error_kind
}
```

**硬约束：整条包裹必须能 `json` 往返。** 上一版把 `anyio.Event` 塞进 receipt，从类型上堵死了持久化。事件与唤醒属于运行时，不属于数据。

## 4. 站点注册

```python
register(address, station, *, channel, resource, kind)
```

- `address` 与 `kind` 必须显式给出；`resource` 是**必需**参数（[ADR 0005](../adr/0005-resource-key-equals-station-granularity.md)）。
- 一条信道可以承载多个地址的包裹（同凭证的两个源落在同一信道）。
- `register()` 在 `run()` 之后调用**直接抛 `RuntimeError`**，不静默生效。

**启动期一次性校验**，失败时**列出全部缺失项**并拒绝启动：

1. 每个地址有站点，且无重复注册
2. 每个 `kind` 至少有一个可处理它的站点
3. 每个站点的依赖都能被注入器满足
4. 配置里出现的每个组件名都已注册
5. 每个源的抓取器 + 解析器配对成立
6. 回收站地址 `dead-letter` 存在（无则用内建兜底，见 §8）

## 5. 依赖注入

见 [ADR 0003](../adr/0003-di-open-vocabulary-closed-mechanism.md)。约 70 行：`register(key, factory)` / `@provider` / `@inject` / `call()`。

- 键是 `type` 或 `(type, marker)`（对应 `Annotated[T, marker]`）。
- **开放词汇：** 宿主与任何下游包都能注册任意类型。
- **封闭机制：** 注入方式只有一种（读签名 → 查注册表）。
- 可满足性在**装饰期**校验；`register()` 期递归校验 provider 自身的依赖。
- **重复注册同一个键直接报错**（Entari 在这里是静默的，我们不抄）。
- 注册表是启动期单线程单次写入的模块级 dict，运行时只读。
- `@inject` 解析出的依赖清单成为 inspect 的数据源。

## 6. 信道与调度循环

**信道是一行数据，不是一个任务。**

```
lane {
  resource        : str
  head            : parcel_id | null     # 队列里最老的未结算包裹 —— 这就是顺序保证
  next_attempt_at : timestamp
  attempt_count   : int
  last_error, last_error_kind
}
```

**队列本身是一张包裹表里按 `(resource, seq)` 有序的行**，信道行只持有 head 指针。所以「同一时刻只有一个在途」是「只允许取 head」的直接结果，不需要额外锁。信道行可以只在这一张表上重建（它是索引不是真相），但保留它可以让调度循环一次查询就选出下一条要跑的信道。

**循环语义：**

```
while running:
    wake.wait()            # post() 写入后置位，否则等到最早到期时间
    lane = 取 next_attempt_at 最早且已到期的非空信道
    parcel = load(lane.head)
    result = await station(parcel)
    推进 head / 设 next_attempt_at
```

- 物理资源是固定大小的 worker 池（默认 1，可配）。50 条信道 = 50 行 + 1 个 worker。
- `post()` 必须唤醒循环，否则新包裹要等到下一个 `next_attempt_at` 才被看见。
- 宿主必须用 `anyio` task group 之类的可取消机制承载循环，不能用裸 `asyncio.create_task`。

**pacing（节奏）由站点声明，不由 courier 决定：**

- 站点可声明 `min_interval`；courier 在推进 head 时用它设置 `next_attempt_at`。
- 站点可以在返回时给出「下次最早时间」（上游的 `Retry-After`、「已完结，一天后再看」、「直播中，5 秒后再看」）。
- **jitter 由 courier 统一加，站点不许自己随机**，否则夹紧逻辑会被绕过。

## 7. 投递语义

- **同一信道上同时至多一个包裹在途**（[ADR 0002](../adr/0002-channel-is-a-logical-lane.md)）。顺序不是被解决的，是被排除的。
- 失败**原地重试**，只推后该信道的 `next_attempt_at`。跳到队尾会把「下播」发在「开播」之前。
- 默认预算：每站 3 次，退避 5s / 30s / 2min，耗尽进回收站。
- **跨信道永不互相等待：** 目的地内阻塞是正确的，跨目的地阻塞是 bug。
- 站点的返回值：`Parcel | Iterable[Parcel] | None`。
  - `None` → 本次投递结束，包裹标记 DELIVERED
  - 返回相同地址的包裹 → 视为循环，进回收站（`reason_kind = routing`）
  - 返回其他包裹 → 继续投递

## 8. 回收站

- 地址 `dead-letter` 上是一个**可替换的站点**，但该地址**必须无条件存在**。默认实现是内建的「写表」站点。
- 每条死信必须带：`stage` / `attempt_count` / `last_error` / `last_error_kind` / 面单游标。没有前三项，事后无法区分「解析器坏了」和「这个群没了」。
- `last_error_kind` 至少要能区分：`transient`（等会再试）、`credential`（换凭证再试）、`permanent`（放弃）、`routing`（地址/kind 错误）、`fanout_exceeded`。
- **回收站自己失败时绝不能再进回收站**，只能落日志并计数。
- 回收站**不是**「发送前暂存区」。合法但暂时不能投递的包裹（等前置、目的地暂停）留在自己的信道上，靠 `next_attempt_at` 表达等待，不要送进回收站。

## 9. 一对多扇出

站点可以返回多个包裹。三条硬约束：

1. **原子写入。** `post_many()` 在**单个事务**里写入全部子包裹并把来源包裹标记完成。要么全进，要么全不进。
2. **确定性子包裹 id。** 由 `(父包裹 id, 目的地, 变异维度)` 派生，靠 `ON CONFLICT DO NOTHING` 吃掉重试产生的重复。用 `uuid4()` 会让重试把整个群刷两遍。
3. **后代总量预算**（默认 200）。一对多 + 中转可以乘性放大；超预算进回收站（`fanout_exceeded`）。仅靠跳数上限不够。

## 10. 存储

见 [ADR 0004](../adr/0004-store-sqlalchemy-core.md)。

`Store` Protocol 约十个方法：入队、取 head、推进、设 `next_attempt_at`、进回收站、列信道、统计、死信查询。自带实现基于 SQLAlchemy 2.0 async **Core**（不用 ORM），`AsyncEngine` 由宿主注入。

**courier 拥有自己的表与迁移，bison 拥有自己的，两者共用 engine 但绝不跨 schema join。**

## 11. inspect

**纯数据出口：`inspect() -> dict`。** courier 不依赖任何 web 框架；bison 负责把它变成 HTTP 与对话命令。

至少包含：

```
{
  stations: [{address, kind, channel, resource, needs: [...]}],
  channels: [{resource, head_age_seconds, attempt_count, next_attempt_at, last_error_kind}],
  dead_letters: {count_by_reason_kind, recent: [...]},
  config: {...}                      # 构造参数，只读快照
}
```

## 12. 关闭

`close()`：唤醒循环 → 停止取新包裹 → 给在途包裹短超时（默认 10s）排干 → 退出。超时未完成的**留在信道里**（`next_attempt_at` 已在表里），重启自然继续。

**已知且接受的窗口：** 「投递已发生、`mark_delivered` 之前进程死掉」会导致重启后重发一次。聊天平台没有幂等键，这个重复无法消除。500 条/天里偶尔重复一条，远好于丢一条。

## 13. 非目标

- 多进程 / 远程运输器（`Store` 与注册接口的形状已经为它留了口子，但现在不实现）
- 序列号、Resequencer、乱序窗口
- 多资源门控（一个站点同时等待多个资源）
- 运行时注册
