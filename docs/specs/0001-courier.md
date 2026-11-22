# courier — 运输内核

零 NoneBot 依赖（[ADR 0001](../adr/0001-courier-has-no-nonebot-dependency.md)）。只依赖 `anyio`、`sqlalchemy`（Core）。

## 1. 职责与非职责

**职责：** 接收「包裹 + 地址」，按资源划分信道，以单 worker 串行执行站点，统一结算每次执行，直到包裹终结或进入回收站；保证已提交的运输状态活过进程重启。

**非职责：** 不认识消息内容、社交平台、聊天平台；不做抓取/渲染/发送策略；不加载业务配置；不依赖任何 web 框架；不解释 Renderer 的内部技术或凭证内容。

## 2. 概念

| 概念 | 定义 |
|---|---|
| 地址 | 站点标识，字符串。标识**哪一类处理**，不标识**哪一个对象** |
| 包裹 | 一次投递的完整单位，含稳定的执行身份与血缘 |
| 面单 | 当前目的地与投递状态，不含途经链 |
| 投递凭据 | 状态、途经地址链、每站尝试次数、`next_attempt_at` 与最后错误 |
| 信道 | 按**资源键**划分的运输通道，一行调度投影 |
| 资源键 | 入队时由包裹算出并随包裹冻结的不透明字符串，决定共享顺序与节流的边界 |
| 站点 | 地址对应的处理函数 |
| 回收站 | 地址 `dead-letter` 上的内建终态处理；持久死信记录不依赖可替换的通知逻辑 |

## 3. 包裹与投递凭据

```python
Parcel {
  id          : str          # 确定性幂等键，不是随机值
  content_hash: str          # 业务内容摘要，不含执行血缘与调度字段
  parent_id   : str | None   # 直接来源，供审计
  root_id     : str          # 后代预算根；新预算根的 root_id 是自己的 id
  retry_of    : str | None   # 人工重投来源的死信包裹
  generation  : int          # 自动重试不增加，人工重投增加
  address     : str          # 当前目的地
  kind        : str          # 不透明标签，词汇归宿主
  payload     : 不透明        # courier 不解释，但必须可 JSON 往返
  metadata    : dict         # 随行数据，不得放运行时对象
  created_at  : datetime
  receipt     : Receipt
}

Receipt {
  status        : DELIVERING | DELIVERED | DEAD | CANCELLED | DROPPED
  route         : list[str]              # 已途经地址，供间接循环检测
  attempts      : dict[address, int]     # 每站独立预算
  held          : bool         # 暂停等待，不是终态，不占用活动 head
  attempt_in_progress : bool   # 已开始但尚未结算的执行
  outcome_unknown     : bool   # 外部副作用可能已发生但结果不可知
  next_attempt_at
  last_error
  last_error_kind
}
```

**硬约束：整条包裹必须能 `json` 往返。** 事件、锁、连接、task、client、文件句柄与任何其他运行时对象都不许进入包裹。文件只能以符合 bison 产物协议的持久引用出现。

状态含义：

- `DELIVERING`：排队、执行或 `held` 暂停等待中，尚未产生终态。
- `DELIVERED`：本阶段已经正常结算。
- `DEAD`：自动运输终止，保留审计；不直接复活。
- `CANCELLED`：因源、订阅或目的地被删除等管理动作，在产生外部副作用前取消。
- `DROPPED`：被明确的容量策略放弃；不是处理异常，也不是管理员取消。

## 4. 身份、血缘与冲突

- 子包裹默认由 `(父包裹 id, 目标地址, 显式变异维度)` 派生确定性 id。站点必须为每个输出提供稳定且互不相同的变异维度。
- 宿主可以在业务身份发生变化时开启新预算根：子包裹仍保留 `parent_id`，但 `root_id` 改为自己的 id。bison 的每个 Report 都这样脱离轮询预算根。
- **轮询执行身份不能直接成为后续内容的去重身份。** bison 必须让稳定内容身份进入 Report 及后续 id，规则见 [bison §3](./0002-bison.md)。
- `content_hash` 由输出站点用稳定、可版本化的算法计算，只覆盖业务内容。`parent_id`、轮询 id、`root_id`、resource、Receipt、调度时间与配置快照存储位置等执行元数据不得进入；会影响实际投递语义的配置值必须已经体现在业务载荷或 id 中。
- Store 重复写入同一 id 且 `content_hash` 相同，是幂等成功，不重复占用后代预算；首次写入的 `parent_id` 等审计字段保持不变，后续重放不改写血缘。同一 id 但摘要不同是冲突错误，**不得用 `ON CONFLICT DO NOTHING` 静默保留旧值**。
- 幂等记录的保留期不得短于任何合法重试、补抓或人工重投仍可能引用它的期间。

`route` 在每个新地址执行前追加。重试当前地址不重复追加；返回任何已经出现在 `route` 中的地址都构成循环，包括 `A → B → A`，以 `routing` 进死信。人工重投是新一代，重置当前执行路线，但通过 `retry_of` 保留完整审计关系。

## 5. 注册与依赖注入

```python
register(address, station, *, channel, resource, kind, side_effecting=False)
```

- `address`、`kind` 与 `resource` 必须显式给出。`resource` 是 `Parcel -> str` 选择器，不是注册期固定资源值。
- `channel` 是站点声明的资源画像名称，供装配校验与 inspect 使用；实际信道键仍是入队时算出的 `resource`。`side_effecting=True` 表示调用可能产生不可撤回的外部结果，发送站必须声明。
- 一条信道可以承载多个地址的包裹，实现不得假设「信道 ↔ 地址」一一对应。
- `register()` 在 `run()` 或宿主组合调度启动后直接抛 `RuntimeError`。

启动期一次性校验，失败时列出全部缺失项并拒绝启动：

1. 每个地址有站点且无重复注册，每个 `(address, kind)` 组合有效。
2. 每个 `kind` 至少有一个可处理它的站点。
3. 每个站点的依赖都能被注入器满足。
4. 配置中的组件名都已注册，且每个源的抓取器 + 解析器配对成立。
5. 声明共享同一资源画像的站点必须使用一致的资源级 pacing；不同画像应拆站点，不能用源轮询间隔冒充资源限流。
6. `dead-letter` 的内建持久终态处理存在；通知观察者可替换，但不能替换耐久记录。DI 见 [ADR 0003](../adr/0003-di-open-vocabulary-closed-mechanism.md)，可满足性在注册或准备期校验，运行期注册表只读。

## 6. 信道与执行模型

```python
lane {
  resource             : str
  head                 : parcel_id | null
  resource_available_at: timestamp   # 跨 head 的资源节奏/风控状态，独立持久化
  next_attempt_at      : timestamp   # max(head Receipt, resource_available_at) 的缓存
  attempt_count        : int         # 当前 head 的投影，换 head 即重建
  last_error
  last_error_kind
}
```

包裹表按 `(resource, seq)` 保序。lane 的 `head` 指向最老的**非 held** 未结算包裹；held 包裹保持原 seq 与 `DELIVERING`，恢复后按原顺序重新参与，但不阻塞同目的地的其他订阅。`head`、尝试计数与 head 错误是可重建投影；`resource_available_at` 是属于资源本身的持久事实，即使 lane 暂时为空也不能随换 head 或重建而清零。实际到期时间取 `max(head.receipt.next_attempt_at, resource_available_at)`，`next_attempt_at` 只是这个结果的调度缓存。

**当前只支持一个 worker。** 不开放 `worker_count > 1`，因此不存在两个执行者同时取同一 head 的路径。未来若开放多 worker，必须先另立 ADR，定义数据库原子 claim、owner、lease、崩溃 reclaim 与 fencing；仅限制「取 head」不构成占用。

执行分为两个角色：

- **调度器**：计算最早到期项、接收唤醒、选择下一条到期信道，不直接执行站点。
- **唯一 worker**：先用一个短事务把 head 标记为 `attempt_in_progress`，再执行站点并调用统一结算；标记失败不得调用站点。该标记只用于恢复与竞态审计，不是多 worker lease。站点有有限执行超时，可取消；取消后必须等待任务真正结束。

到期信道采用公平轮转，不能让持续可到期的信道饿死其他信道。承诺是「失败或卡住不得造成其他信道的**无界**阻塞」，不是物理执行上「跨信道永不等待」。

courier 可独立运行，也必须向宿主暴露单步调度、到期时间与唤醒接口。bison 用这些接口组成唯一的源 + 信道调度循环；不得各起一个扫描循环。

`post()` 在事务提交后唤醒调度器。回滚不得唤醒一个指向不存在包裹的执行。

## 7. 站点执行与统一结算

站点返回值保持 `Parcel | Iterable[Parcel] | None`；批量输出必须是有序序列，禁止以 `set` 等无序容器决定投递顺序。需要显式延期或分类错误时使用结构化结果/异常，不把业务控制流编码进 payload。

站点执行、网络请求、渲染与外部发送均在数据库事务外完成。每次返回后只经过一个 `settle` 边界。正常输出的以下写入在**同一事务**完成：

1. 写入全部新子包裹，或记录幂等重放。
2. 更新父 Receipt 与状态。
3. 推进 head，按下一 Receipt 与持久 `resource_available_at` 重建调度缓存；无下一 head 则清空 head。
4. 写入重试、显式延期、`DELIVERED`、`DEAD`、`CANCELLED` 或 `DROPPED` 的终态记录。
5. 更新与本次运输直接相关的资源调度状态。

必须区分两类失败：

- **业务校验拒绝**：无效地址/kind、同 id 不同内容、循环或额度超限在写入子包裹前确定。丢弃全部输出，然后在**一个事务中提交**父 `DEAD`、耐久死信与 head 推进；不能随机保留前 N 个输出，也不能因拒绝输出而回滚父死信。
- **存储/系统失败**：写子行、父行、死信或调度状态的任一存储操作失败，整个事务回滚，head 不推进。若连父死信也无法写入，就保持原未结算状态，由有界退避和重启重入处理，不能伪造已经死信。

事务提交前崩溃会重入站点；提交后崩溃不重入。外部副作用与数据库提交不可能组成一个本地事务。

## 8. 重试、错误与 pacing

- 「每站 3 次」指总共最多调用三次：首次 + 两次重试，退避为 5s / 30s。
- `transient` 才消耗自动重试预算；`Retry-After` 与默认退避取较晚者。jitter 不得将执行时间提前到 `Retry-After` 以下。
- `permanent`、`routing`、`fanout_exceeded` 立即进死信。
- `credential` 表示当前凭证不可继续使用，不盲目打满预算；进死信并等待修复后人工重投。单纯限流必须归类为带 `Retry-After` 的 `transient`。
- 进程在站点执行中崩溃时，不伪造一次已记录失败；包裹按未结算状态重入，并接受外部副作用重复窗口。
- Receipt 是每站尝试历史的真源；lane 只投影当前 head 的计数与错误，换 head 时不得继承上一个包裹的预算。资源可用时间不属于某个 head，必须独立保留。

pacing 分三类，不得互相覆盖：

1. 源级轮询间隔只修改 bison 的 `source.next_poll_at`。
2. 资源级 `min_interval`、风控退避与资源相关 `Retry-After` 只修改该资源持久化的 `resource_available_at`。
3. 站点对单个包裹的显式延期与默认失败退避只修改该包裹的 Receipt。

成功路径使用资源画像声明的间隔与显式延期；失败路径使用重试公式。统一 jitter 由 courier 施加并受配置夹紧，但任何夹紧都不得违反上游 `Retry-After`。

## 9. 扇出与后代预算

三条硬约束：

1. **原子写入与结算。** 全部子包裹、去重、父结算和 head 推进使用 §7 的同一事务。
2. **确定性 id 与冲突检查。** 同父重跑不重复，同 id 不同内容不静默吞掉。
3. **按根累计的后代预算。** 默认每个预算根 1000 个实际新后代；fetch 批次另有限额，bison 让每个 Report 成为新预算根，因此合法的多跳订阅不会被整次轮询的总预算误伤。

额度在写入新子包裹时原子预留；幂等重放不重复扣减。超限整批回滚，父包裹以 `fanout_exceeded` 进死信。预算根计数在可能重放的整个期间持久保存，不能随单个 head 推进而消失。

## 10. 回收站

进入回收站是一个数据库状态迁移：原包裹 `DEAD`、耐久死信记录与 head 推进必须同事务完成。每条死信至少携带：

- `stage`、`attempt_count`、`last_error`、`last_error_kind`；
- 原包裹 id、血缘、当前地址与路线游标；
- 可安全展示的上下文；secret 与凭证原文不得进入。

可替换的回收站观察者负责通知或额外投影，不能删除内建耐久记录。观察者失败只记日志和指标，不再生成新死信，也不改变原包裹已经持久化的 `DEAD`。若数据库本身不可用，结算不提交、head 不推进；调度器使用有界本地退避避免热循环并主动告警。

## 11. 存储与事务组合

见 [ADR 0004](../adr/0004-store-sqlalchemy-core.md)。

`Store` 负责入队、取 head、统一结算、状态查询、调度投影、死信与统计。自带实现基于 SQLAlchemy 2.0 async **Core**，`AsyncEngine` 由宿主注入。

courier 拥有自己的表与迁移，bison 拥有自己的表与迁移；双方共用 engine，**绝不跨 schema join**。但 bison 可以开启一个 SQLAlchemy 事务，把 connection 显式传给 Store，使以下业务写入与运输写入共享提交点：

- 推后 `next_poll_at` + 入队抓取包裹；内容去重/游标推进 + 内容子包裹入队 + 父结算；artifact 引用 + 发送包裹入队 + 父结算。

connection 只作为方法参数存在，绝不进入 Parcel。事务由 bison 开启与提交，courier 不在嵌套边界偷偷提交。

存储契约只规定原子性、已提交状态的耐久性与恢复语义。WAL、`synchronous=FULL`、busy timeout 等属于 [运行规格](./0003-operations.md)的 SQLite 部署档案，不进入 `Store` Protocol。

## 12. inspect、状态查询与事件

**纯数据出口：`inspect() -> dict`。** courier 不依赖任何 web 框架；bison 负责授权、脱敏并变成 HTTP 与对话命令。

至少包含：

```python
{
  "stations": [{"address", "kind", "channel", "needs"}],
  "channels": [{"resource", "head_age_seconds", "attempt_count", "held_count", "resource_available_at",
                "next_attempt_at", "last_error_kind", "outcome_unknown"}],
  "dead_letters": {"count_by_reason_kind", "recent"}, "terminal_counts": {"delivered", "cancelled", "dropped"},
  "scheduler": {"last_progress_at", "worker_state"}, "config": {"..."},
}
```

`resource` 必须是不透明标识。bison 在出口重新脱敏，不能把这里的 `config` 自动等同于可公开配置。

`parcel_status(ids)` 提供批量状态对账，供 bison GC 使用，避免跨 schema join。运输事件可用于指标和日志，但 GC 的正确性不得依赖事件零丢失；周期状态对账才是兜底。

## 13. 启动与关闭

启动时先加载并校验全部注册，再执行**中断恢复事务**，最后启动宿主组合调度；此时注册表冻结。

恢复事务必须处理所有遗留 `attempt_in_progress=True`：

- `side_effecting=True` 的站点写入 `outcome_unknown=True`；其他站点只记录中断执行，不伪造外部未知结果。
- 随后清除 `attempt_in_progress`，保留原 Receipt 计数、head、路由与退避，让包裹重新参与调度。

恢复事务提交前不得调用任何站点。进程无法在崩溃当时主动写 `outcome_unknown`，所以启动恢复是该状态迁移的必要组成部分，不是可选清理。

`close()`：

1. 标记 closing，拒绝新的 `post()` 与重投，停止取新 head 并唤醒调度器。
2. 给在途站点有限排干时间；超时则 cancel-and-await。
3. 等 worker 真正退出后才返回，由 bison 继续关闭组件资源和 engine。

重复 `close()` 幂等。未结算包裹留在表中，重启继续；不能留下 detached 站点任务。

## 14. 非目标

- 多进程 / 远程运输器、当前开放多 worker、多资源门控与运行时注册。
- 传输级全序、序列号、Resequencer 与乱序窗口。
- 认识浏览器、Cookie、社交动态或聊天平台等宿主概念。
