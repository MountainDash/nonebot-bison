# 实施计划

依据：[设计规格](specs/README.md)、[词汇表](../GLOSSARY.md)、[ADR](adr/)。

> 本文件只描述拟实施的 PR、验收口径与停损条件，不记录任何完成状态。PR 是否合并、里程碑是否打 tag、验收是否通过，都以实际执行结果为准。

## 全局规则

前五次 courier 尝试的死法是同一个：**一次吃掉全部，写一天，推上去，停**。以下规则直接针对它：

1. **每个里程碑结束时系统必须是能跑的。** 没有「中间态不可运行」的里程碑。
2. **每个里程碑结束时必须 commit + tag + 可运行 + 测试通过。** 里程碑之间的工作区不留给下一个人。
3. **任一里程碑不超过 1.5 周。** 超过就说明它该拆，不是说明它难。
4. **不引入未被规格要求的依赖。** 规格允许 `anyio` + `sqlalchemy`(Core) + `pydantic` + `arclet-letoderea`（0.22.x 及其锁定传递依赖），其它依赖仍须先改规格与 ADR。
5. **里程碑顺序是依赖顺序，不是优先级。** 后续网页与迁移不能反过来迫使内核补语义。
6. **每个里程碑拆成一个链式 PR 栈**。栈内一个 PR 只做一件事，默认约 400 行实质变更（不含测试、fixture、生成物/锁文件、纯 import/export 与纯格式调整），合并后主干测试全绿。
7. **测试与实现在同一个 PR 里。** 不允许「先实现、后补测」，也不允许「最后来一个测试 PR 收口」；唯一的测试集中补充点是里程碑验收 PR，它不得夹带实现。
8. **行数只提醒 review 成本，不是机械闸门。** 一个理由且可独立 review 的 PR 超预算时在描述中说明；含两个理由才必须拆。不得用排除测试、挪动逻辑到 import/export、删除必要说明或牺牲可读性来凑数。

## 统一交付与验收口径

详细语义以三份规格与 ADR 为权威，本计划只引用验收所需规则，不再复制完整定义：

- **交付**：at-least-once，无未报告损失；唯一重复例外是 timeout/disconnect/crash 导致的 `outcome_unknown`，按原投递代重入。
- **终态与重投**：`DEAD / DROPPED / CANCELLED` 不得混算；重投以 `retry_of / requeue_from / generation` 创建新预算根，按计划选择接入点并处理 artifact。
- **顺序**：只承诺同一 Source、Subscription、`effective_revision` 内保序；扇出必须有序，in-flight 或结果不可知的发送不得误取消、误丢弃。
- **身份**：轮询、稳定内容身份与独立游标分离；`content_hash` 排除执行血缘，同 ID 不同内容不得静默吞掉。
- **资源**：resource 入队计算并冻结且不含 secret；`resource_available_at` 跨 head/重启保留；轮换只影响新根，重投才重算存量资源。
- **调度**：`merge_pending + next_poll_at` 同事务；成功、DEAD、删除 CANCELLED 与暂停 CANCELLED 分别处理，任何路径不形成扫描热循环。
- **事务**：统一 settle；业务校验拒绝提交父 DEAD，存储失败全回滚；bison/courier 可共享 transaction 但不 join，外部副作用在事务外。
- **运行与迁移**：p95 使用条件口径，通知区分生成/尝试/送达；`cutover_watermark` 与 `migration_skipped` 独立于运行游标和投递历史。
- **权限与耐久**：对象级 ACL 与全出口脱敏为上线门槛；数据库参数属于部署档案，更换 Store 必须重跑恢复矩阵。

## PR 切片

### 栈与链

**一个里程碑 = 一个栈。** 栈内 PR 逐层相接：每一层的 base 是下一层的分支，栈底指向 `main`。栈底合并后，下一层改指向 `main`。

不按所有里程碑建立一条长链，原因是 review 疲劳、级联 rebase 成本与停损形状。按里程碑分栈，最坏情况也只是停在当前栈中间，已合并的主干仍然可运行、可测试。

**合栈时机：** 栈内每层各自 review 与合并；整个栈在里程碑验收通过后合完并打 tag（`m0`…`m6`）。tag 是实际完成后的动作，本文件不预设其已经存在。

### PR 判据

一个改动够格成为一个 PR，当且仅当它能在**不读其他 PR 的情况下被单独 review**，且满足：

- **一个理由**：标题能写成一句「为了 X 而 Y」，不需要「顺便」。
- **默认约 400 行实质变更**。纯 import/export、空行、纯格式调整与不承载新语义的注释/docstring 不计；超预算仍可独立 review 时在描述中说明，含两个理由才必须拆。
- **主干保持可运行**：合并后 `uv run pytest` 全绿；M3 之后还要求 bison 能启动。
- **行为变化必带测试**：courier 的每个 PR 至少新增或修改一个行为测试。
- **决策变化必带文档**：若 PR 改变已记录的决策，ADR / GLOSSARY 在同一个 PR 更新。
- **三道静态门**：`ruff check`、`ruff format --check`、`basedpyright` 与测试在同 PR 通过。

M3 之前「可运行」只要求 workspace 测试全绿；M3 之后要求 bot 能启动。未接线的代码以「已实现但未注册」进入主干，不影响运行。

### PR 清单

| PR | 内容 | 依赖 |
|---|---|---|
| **M0 — 工程地基** | | |
| 0 | 为建立文档基线清空 `main` 旧文件，只保留 `AGENTS.md`、`GLOSSARY.md` 与 `docs/` | — |
| 1 | 为统一验证入口建立 uv workspace 与 CI（pytest / ruff / format / basedpyright） | 0 |
| 2a | 为解耦匹配与启动校验建立不可变 BindingPlan、BindingBackend、ValidationBackend、严格图校验及契约测试 | 1 |
| 2b | 为复用公开执行机制实现实例化 DependencyDispatcher、letoderea Subscriber 适配、singleton 与冻结测试 | 2a |
| 3 | 为固定存储边界定义 `Store` Protocol、外部事务参与接口、`settle` / `parcel_status` 签名及零 NoneBot 依赖测试 | 1 |
| **M1 — courier 内存语义闭环** | | |
| 4 | 为可恢复追踪定义 `Parcel` / `Receipt`、业务 `content_hash`、lineage、路由历史、`held / attempt_in_progress / outcome_unknown`、五种状态与 JSON 往返 | 2b,3 |
| 5 | 为按包裹冻结资源实现内存 Store、resource selector、入队幂等及同 ID 冲突检测 | 4 |
| 6 | 为消除父子状态分叉实现统一内存 `settle`、lane 调度投影及业务拒绝提交父 DEAD/存储故障全回滚分路 | 5 |
| 7 | 为有界进度实现单 worker、`attempt_in_progress` 短事务、调度/执行分离、公平选择、站点超时、跨 head 的 `resource_available_at` 与可注入时钟 | 6 |
| 8 | 为统一失败终态实现精确重试、错误分类、死信记录及以 `retry_of / requeue_from / generation` 关联原死信的新预算根重投 | 7 |
| 9 | 为可重入扇出实现有序 `post_many`、稳定派生 ID、原子去重与逐输出业务校验 | 8 |
| 10 | 为限制乘性路由实现可重设预算根、原子额度预留、直接与间接循环检测 | 9 |
| 11 | 为安全停止实现 `close()` 状态机、closing 拒绝 `post()` 与 cancel-and-await | 10 |
| **M2 — SQLite 持久化与恢复** | | |
| 12 | 为持久化全部状态建立含 `resource_available_at` 的 parcels / lanes / dead_letters / 版本表、索引与手写 DDL | 11 |
| 13 | 为保持内存语义实现 SQLAlchemy Core Store 与统一事务 `settle` | 12 |
| 14 | 为验证崩溃原子性建立故障注入工具并把 M1 语义套件切换到 SQLite | 13 |
| 15 | 为明确 SQLite 耐久边界建立部署档案（WAL、`synchronous=FULL`、busy timeout、短事务）及恢复测试 | 14 |
| 16 | 为无跨 schema join 的对账实现批量 `parcel_status`，以及保留 `resource_available_at` 的 lane 重建测试 | 15 |
| **M3 — 可恢复的 RSS 垂直切片** | | |
| 17 | 为隔离组件契约建立 `Component`、通用适配器、注册中心与组件资源所有权 | 16 |
| 18 | 为冻结自然身份建立 Source / Destination / Subscription / Credential 模型、游标字段、初始 `effective_revision` 快照与唯一约束 | 17 |
| 19 | 为统一生产与消费建立单组合调度器、跨 schema 同事务入队、提交后唤醒、Source 暂停恢复，以及 `merge_pending + next_poll_at` 事务与成功/DEAD/CANCELLED/暂停消费规则 | 18 |
| 20 | 为阻止跨轮询重复实现稳定内容身份、每 Report 新预算根、独立游标、排除执行字段的业务 `content_hash`、首次 parent 保留及游标同事务 settle | 19 |
| 21 | 为接入真实来源实现 RSS Fetcher、最新快照补抓能力与可审计补抓缺口 | 20 |
| 22 | 为提供无卡片兜底实现直通 Parser、`basic`（文字 + 动态原生媒体）与最终纯文本变体 | 21 |
| 23 | 为崩溃安全发布产物实现内容寻址临时文件、原子 rename、artifact/ref 与同事务子包裹 | 22 |
| 24 | 为回收产物实现基于 `parcel_status` 的周期对账、live ref 保留、孤儿宽限、容量背压与缺失告警 | 23 |
| 25 | 为完成端到端投递实现 SAA Sender、按目的地有序扇出、发送前状态校验、Destination 暂停恢复唤醒及 timeout/disconnect/crash 的 `outcome_unknown` | 24 |
| 26 | 为限制恢复积压实现目的地 24h/200、仅选择未执行项的保留最新/`DROPPED`、执行中与提交中临时容量余量、竞态防护与恢复后聚合摘要 | 25 |
| 27 | 为接入宿主实现启动校验、固定关闭资源顺序与首版 inspect 数据投影 | 26 |
| 28 | 为验证最小可用形态执行 M3 端到端与恢复验收（只补验收，不夹带实现） | 27 |
| **M4 — 配置、组件生态与降级** | | |
| 29 | 为消除配置作用域冲突实现组件 schema 与 Fetch/Parser/Enricher/Renderer 的覆盖矩阵 | 28 |
| 30 | 为启动期暴露装配错误实现配置定位、未知组件报错、Sender/Adapter 兼容校验与 schema 注册 | 29 |
| 31 | 为控制在途变更实现由 Source/Subscription/Destination/组件默认与能力版本合成的 `effective_revision`、自然身份不可变、成员级暂停删除及 in-flight/outcome_unknown 取消保护 | 30 |
| 32 | 为接续 external 组件实现每源有序执行计划、`plan_id / step / source_revision`、下游 `effective_revision` 与 RawPost/Report JSON 路由 | 31 |
| 33 | 为隔离富化失败实现 Enricher 顺序、`adds / required`、独立系统错误事件及失败后下一跳 | 32 |
| 34 | 为按能力复用渲染实现 render plan、能力变体分组、共享成员暂停/删除时 held 拆分且其他成员继续，以及原站点内指定风格→basic→纯文本降级 | 33 |
| 35 | 为开放第三方接入实现专线包契约（含 Enricher 类别）、API 版本校验与装配规则 | 34 |
| 36 | 为证明扩展边界接入第二个独立 Fetcher 并执行 M4 验收 | 35 |
| **M5 — 显式迁移与切流** | | |
| 37 | 为区分全新与接管实现迁移 CLI、显式 fresh/takeover 模式及源/目标 DSN 前置检查 | 36 |
| 38 | 为保护旧库实现一致只读快照、确定性身份映射与脱敏 `--dry-run` 报告 | 37 |
| 39 | 为中断续跑实现分批写入、幂等 upsert、checkpoint 与最终标记最后提交 | 38 |
| 40 | 为界定接管窗口实现停旧 bot、独立 `cutover_watermark`、`observed / migration_skipped` 审计、与运行游标隔离的首轮边界，以及迟到旧动态无法判断先后时的逐源 gap | 39 |
| 41 | 为切换基础设施实现 datastore→orm、目标 schema version 与接管完成启动门禁 | 40 |
| 42 | 为验证真实接管执行旧库备份迁移、kill 重跑、切流与缺口验收（只补验收） | 41 |
| **M6 — 运维、权限与网页** | | |
| 43 | 为解释全部出口实现结构化事件与扩充指标（发送、延迟、缺口、丢弃、artifact、重投、心跳、关闭） | 36 |
| 44 | 为持久呈现运行事实扩展 inspect 的缺口、`DROPPED`、重投、artifact/GC 与降级投影 | 43 |
| 45 | 为阻止跨群越权实现 JWT 对象级 ACL、默认拒绝矩阵、安全审计与全出口脱敏 | 44 |
| 46 | 为提供受控读接口挂载同进程网页与按权限过滤的 inspect API | 45 |
| 47 | 为提供幂等管理动作实现暂停/恢复、超管刷新名字与重投 API：以 `retry_of` 创建新预算根，按计划选择 `requeue_from`，共享死信逐成员过滤，且仅复用旧 artifact 时立即复制 ref | 46 |
| 48 | 为区分通知事实与送达实现持久红点、best-effort 私聊、去重聚合及失败记录 | 47 |
| 49 | 为呈现运维工作流实现信道/死信/缺口/丢弃页面与三个管理动作；更大前端改动另拆 PR | 48 |
| 50 | 为验证上线运维面执行越权反例、脱敏、SLO、通知与 M6 验收（只补验收） | 49 |

### PR 检查清单

每个 PR 描述里必须有：

- [ ] 一行「为什么」：为了 X 而 Y
- [ ] 一行「怎么验证」：跑哪个测试 / 点哪个界面
- [ ] 是否改变已发布的接口？（改了就说明有兼容问题）
- [ ] 是否改变已记录的决策？（改了就在同一 PR 更新 ADR / GLOSSARY）
- [ ] 实质 diff 是否约 400 行以内；超出是否仍为一个理由、可独立 review 且已说明
- [ ] 行为测试是否与实现同 PR，且没有借用后续 PR 才能通过的语义

## 里程碑

### M0 — 工程地基（2–3 天）

**产出**

- uv workspace：`packages/courier`、`packages/bison`。
- 实例化 DependencyDispatcher、letoderea adapter、可插拔 BindingBackend / ValidationBackend 与 Store Protocol。
- 四道验证门：测试、ruff、format、basedpyright。

**验收**

- `uv run pytest` 全绿，三道静态门全绿。
- 干净子进程 import DI 后不含 `nonebot`、Entari、launart 或 Satori。
- DI 覆盖 singleton/transient、精确 marker、重复键、乱序注册、全量缺项、直接/间接环、后端替换、校验零 factory 调用及冻结后拒绝写入。
- Store 签名能表达统一 settle、宿主事务参与和批量状态对账，不含 SQLite 专属参数。

---

### M1 — courier 内存语义闭环（5–7 天）

**产出**

- 可 JSON 往返的 Parcel/Receipt：`content_hash / root_id / parent_id / route / retry_of / generation`、`held / attempt_in_progress / outcome_unknown` 及明确状态；`requeue_from` 是宿主选择的接入点，业务 `effective_revision` 由 bison 在 M4 合成并放入执行计划与载荷，不进入 courier 通用词汇。
- `DELIVERING / DELIVERED / DEAD / CANCELLED / DROPPED`；后两种在内存模型中先定义，业务触发分别在 M3/M4 接线。
- 单 worker、调度与执行分离、超时取消、公平轮转、统一 settle；`resource_available_at` 独立于 head 保存资源级等待。
- 每站总计最多 3 次调用，退避 5s/30s；`Retry-After` 与 jitter 不互相绕过。
- 有序扇出、稳定 ID、可重设预算根（默认每个根 1000）、路由历史、原子预算与循环检测；Report 到预算根的映射在 M3，整次轮询不共用单笔内容预算。
- 统一 settle 区分业务校验拒绝与存储故障：前者不写子包裹但提交父 DEAD，后者全回滚且父不 DEAD。
- 内存死信记录的新代重投语义；原死信只能重投一次，持久化在 M2 验收。

**验收（全部无数据库）**

1. **模型往返**：全部字段和五种状态可 JSON 往返，运行时事件、锁、连接不能进入包裹。
2. **顺序**：同一 lane 的 A/B/C 按序 settle；无序扇出被拒绝；同一有序业务路径的下游顺序不被中转破坏，Source/Subscription/`effective_revision` 的端到端验收在 M3/M4。
3. **隔离**：X 连续退避时 Y 正常推进；X 站点卡住时在声明超时内取消，Y 随后取得有界进度。
4. **统一 settle**：对 `None`、单子、多子、重试、死信分别注入失败，父 Receipt、head、子行与调度状态不出现分叉；业务校验拒绝提交父 DEAD，存储异常全回滚且父不得 DEAD。
5. **重试**：总调用 3 次，退避为 5s/30s；`Retry-After` 取较大者，jitter 不低于它。
6. **错误分类**：`permanent`、地址/kind `routing`、预算超限立即死信；`credential` 不盲目重试；只有 `transient` 消耗自动预算。
7. **死信重投**：原行保持 `DEAD`，重投产生新 ID、新预算根与 `retry_of / requeue_from / generation`；并发重投只有一个新代，原记录指向它。
8. **扇出原子性**：第 7 个输出无效时，全部子包裹不写但父 DEAD 正常提交；第 7 个子行存储写失败时，前 6 个与父 DEAD/settle 全部不可见。同父重跑不重复，同 ID 不同内容报冲突；业务游标的事务验收在 M3。
9. **循环**：直接自环与 `A→B→A` 都以 `routing` 死信；重试不会伪造路由历史。
10. **预算**：200 个合法订阅的多跳扇出不因默认预算误伤；超额整批不写且父死信，重试去重不重复扣额度。
11. **lane 投影**：换 head 后尝试计数来自新 Receipt；`resource_available_at` 不随 head 推进清零，实际到期取资源可用时间与 head `next_attempt_at` 的较晚者；held 保留原 seq 但不占活动 head，恢复后不超车。
12. **关闭**：closing 后 `post()` 报错；超时任务 cancel-and-await；重复 `close()` 安全。
13. **资源冻结**：resource 在入队时固定且不含 secret；换凭证只改变新根包裹的 lane，旧 head 不被静默迁移，重投才重新计算。

**停损条件**：统一 settle、顺序或隔离测试写不出来，停止业务开发，回改内核 ADR；不得用实现默契绕过。

---

### M2 — SQLite 持久化与恢复（4–6 天）

**产出**

- SQLAlchemy Core Store、完整 schema、手写版本迁移与内存语义复用；`resource_available_at` 持久化并跨 head/重启保留。
- 崩溃注入矩阵与批量 `parcel_status`。
- **SQLite 部署档案**：WAL、`synchronous=FULL`、busy timeout、短事务；这些参数不进入跨 Store 通用契约。

**验收**

1. M1 全部语义测试在 SQLite 上通过。
2. 在 settle 提交前后、子行写入中、死信写入中、源调度模拟事务中注入崩溃：状态原子，无未报告损失。
3. 分别注入平台可能已接受但本地结果不可知的 timeout、disconnect、crash：允许且只允许声明窗口内按原代重入；`attempt_in_progress` 标记后崩溃时，启动恢复事务先把 side-effecting 执行转为 `outcome_unknown` 并清除执行标记，提交前不得调用站点，恢复事务提交前后均不得重复清理或丢失 head。测试不得写成绝对「重启不重复」。
4. 未来的 `next_attempt_at` 与 `resource_available_at` 重启后仍按时执行；推进 head 不清除资源等待，执行中崩溃不伪造一次失败计数。
5. 重建 lane 不丢失 Receipt 中的退避、错误、尝试历史或独立 `resource_available_at`。
6. `parcel_status(ids)` 无需跨 schema join 即可支撑外部对账。
7. SQLite 部署档案验证已提交事务的恢复边界；进程 kill 测试不被表述为证明所有物理断电场景。

**停损条件**：任一 M1 语义在 SQLite 上变红，或崩溃矩阵出现父子分叉，不进入 M3。

---

### M3 — 可恢复的 RSS 垂直切片（7–10 天）

**产出**

- 单组合调度器：统一比较 Source 与 lane 到期项；Source 推后、抓取入队与提交后唤醒闭合。
- 每源 `merge_pending + next_poll_at` 同事务更新；成功、DEAD、CANCELLED、暂停/恢复分别消费或冻结合并标记，任何路径不形成热循环。
- 稳定内容身份、排除执行字段的业务 `content_hash`、首次 parent 保留、独立游标、初始 `effective_revision` 快照、最新快照能力与补抓缺口；完整合成规则在 M4 扩展。
- RSS → 直通 Parser → `basic`（文字 + 动态原生媒体）→ SAA；最终纯文本不依赖卡片渲染。
- 内容寻址 artifact、文件先发布后引用提交、周期状态对账、live ref 保护与容量背压。
- 发送 timeout/disconnect/crash 形成 `outcome_unknown`；send in-flight/outcome_unknown 不可直接取消或丢弃。
- 目的地 24h/200 保留最新，仅将未执行的最老排队项转为 `DROPPED`；为执行中/提交中预留临时容量余量并处理入队竞态，暂停仍计时计数。
- 固定关闭顺序：停止生产→停止取件→排干/取消→关闭组件资源→最后关闭 engine。

**验收**

1. 在真实 NoneBot 测试宿主中，一个 RSS Source 向一个群端到端投递。
2. 同一 `post_id` 跨不同轮询再次出现时不重复发送；业务 `content_hash` 排除 parent/轮询/resource 等执行字段，去重后保留首次 parent；同 ID 不同内容不被静默吞掉，新订阅默认不补历史。
3. 停机 30 分钟后，上游仍可枚举的更新被补发；构造超出 RSS 快照容量的场景时，产生包含 Source 与时间范围的补抓缺口，不宣称绝对「停机不丢」。
4. 连续产生多个过期轮询时只执行一次合并抓取；`merge_pending + next_poll_at` 在提交前后崩溃不分裂。成功且未暂停至多补一次，DEAD 与删除 CANCELLED 后按正常间隔等待并清空标记；暂停导致的 CANCELLED 包裹不复活，但标记冻结且恢复只补一次；连续失败与暂停/恢复测试均不出现热循环。
5. 游标、去重、子包裹与父 settle 同事务；在提交前后崩溃不会出现「先去重后漏发」或无法解释的重复。
6. 一个目的地错误 ID 或发送卡住时，在超时与重试边界内另一个目的地继续推进；同 Source/Subscription/初始 `effective_revision` 的顺序保持。分别注入 ambiguous send 的 timeout、disconnect、crash，平台可能已接受但本地结果不可知时进入 `outcome_unknown` 并按原代重入，不直接 DELIVERED/CANCELLED/DROPPED。
7. 文件发布后、DB 提交前崩溃只留下可按宽限清理的孤儿；正常路径没有悬空引用。
8. 暂停超过 7 天或死信等待重投时 live ref 不被年龄/LRU 删除；容量满且全为 live ref 时背压并告警；live 文件缺失形成 `artifact_missing` 事故。
9. 第 201 条积压只把尚未开始执行的最老排队项转为 `DROPPED`，保留最新 200 条并记录 Source/Subscription/Destination/时间范围；send in-flight 与 `outcome_unknown` 不被选中。并发入队、开始执行与溢出扫描交错时，临时容量余量避免越界误删，条件状态迁移保证竞态安全；故障目的地不被强制发送提示。
10. 恢复目的地会唤醒等待；`DROPPED` 与 `DEAD` 分别统计，预先定义的 `CANCELLED` 不被误计为处理故障；业务删除触发在 M4 验收。
11. 关闭期间没有 detached 站点任务，engine 最后关闭，closing 后生产与 `post()` 被拒绝；启动中途失败按相反顺序释放已创建资源。
12. 条件 SLO 的测试样本只含在线、非暂停、非补发、首次成功投递；其他样本有独立延迟数据。

**到此为止的计划状态**：形成最小可恢复业务闭环；不得据此声称已经替代任何真实旧部署。

---

### M4 — 配置、组件生态与降级（7–10 天）

**产出**

- 配置矩阵：Fetcher/Parser/Enricher 仅组件默认与 Source 覆盖；Renderer 可到 Subscription；Destination 只选择 Sender，不引入任意目的地配置。
- 统一 `effective_revision`：由 Source 执行计划、Subscription 配置、Destination sender/能力、组件默认配置及组件实现/能力版本合成；完整解析后 Renderer 配置与降级变体进入 render plan、分组、缓存与投递身份。
- `effective_revision` 与快照：修改只影响新内容，旧包裹按旧快照；自然身份不可变；send in-flight/outcome_unknown 不直接 CANCELLED。
- 每源有序执行计划：inline 阶段合并，external 独立成站，`plan_id / step / source_revision` 与下游 `effective_revision` 明确下一跳。
- 共享渲染按成员处理暂停/删除：暂停成员转 held，删除成员仅取消自身未执行后代，其他成员继续渲染/发送；held 不堵共享 render 或同一 Destination 的其他 Subscription。
- Enricher 顺序与错误规则；可选 external 重试耗尽后继续，必需 external 重试耗尽后死信；任何后续失败不重抓。
- 渲染降级在原站点内完成：可重试失败耗尽后进入 `basic`；`basic` 输出文字与原生媒体，不可用或 Sender 不支持媒体时进入最终纯文本。核心不认识浏览器，具体 Renderer 自行清理资源。
- 专线包含 Enricher 类别与 API 版本契约。

**验收**

1. 两个 Subscription 不能声明冲突的 Fetch/Parser/Enricher 覆盖；分别修改 Source 计划、Subscription、Destination sender/能力、组件默认与组件实现/能力版本，均产生新的 `effective_revision`；Renderer 的合法 Subscription 覆盖进入不同 render plan。
2. 同 ID 不同渲染配置不复用旧 artifact；Sender/Adapter 不兼容在启动期报错；重投比较使用同一份 `effective_revision` 与计划快照。
3. 修改配置不 retroactively 改写旧包裹；删除 Source/Subscription/Destination 只取消未产生外部副作用且未开始发送的后代，send in-flight/outcome_unknown 等待明确结果，不直接 CANCELLED；恢复暂停能唤醒。
4. external Parser 第 N 帖失败只影响该帖；optional external Enricher 耗尽后继续下一跳，required 失败后死信；所有场景均不重新 Fetch。
5. 同一 render plan 只渲染一次；不同 Sender 能力使用不同变体，不静默丢内容块。共享成员之一暂停时仅该成员 held，其他成员继续；成员删除不取消其他成员，held 不堵 Destination 的其他 Subscription。
6. 模拟超时型 Renderer：先按预算重试，耗尽后在原站点降级到 `basic`；原生媒体可用时保留，媒体不可用或 Sender 不支持时最终发纯文本。
7. 关闭导致的取消不触发降级；纯文本也失败才死信；后续动态不能借另一 renderer lane 超车。
8. 第二个 Fetcher 作为独立专线接入，不改核心；缺少 `bison_api_version` 或版本不匹配拒绝启动。
9. 对可分页/可游标 Fetcher 验证从最后成功游标持续补抓，直到追上当前位置或触及显式上限；游标推进仍与内容 settle 同事务。

**停损条件**：第二个 Fetcher 需要修改核心才能接入，或 external 失败必须重抓才能续跑，停止扩展并重审站点边界。

---

### M5 — 显式迁移与切流（5–7 天）

**产出**

- 同一迁移实现提供 `nb bison-migrate` 与 `python -m bison_migrate`。
- 显式 fresh/takeover、旧/新 DSN、只读一致快照、脱敏 dry-run。
- 确定性映射、批次 checkpoint、幂等重跑、最终标记最后写入。
- 独立 `cutover_watermark` 与 `observed / migration_skipped` 审计，不写入或伪造运行游标；真实首轮静默边界、迟到旧动态歧义 gap、逐源补抓缺口与启动门禁。

**验收**

1. 全新安装无旧表可以启动；takeover 未完成或目标 schema version 不符时拒绝启动。旧库位于另一文件时不会被误判为全新安装。
2. dry-run 不写目标、不打印 secret；真实旧库及 WAL/SHM 通过一致快照读取，原文件逐字节不变。
3. 每批迁移中途 kill 后可从 checkpoint 重跑，旧主键不会映射出重复新对象；最终完成标记只在全部校验后写入。
4. 正式切流前要求旧 bot 停止；`cutover_watermark` 获取失败时不得静默完成接管。水印只记录真实观察及 `observed / migration_skipped`，不写成 Source 运行游标。
5. 首轮只静默水印中标记 `migration_skipped` 的内容；切流后可枚举内容补发，不可枚举内容逐源报告缺口。迟到的旧动态若无法可靠判断在 cutover 前或后出现，必须记 gap，不得凭文件时间或当前抓取顺序伪造先后、游标或历史。
6. 用真实旧库备份逐项核对 Source、Destination、Subscription、Credential；凭证只比较结果，不展示明文。
7. 迁移截断、`observed / migration_skipped` 数量、迟到旧动态歧义和补抓缺口均有管理员确认与持久报告，完成定义不使用绝对「无漏发」。

**停损条件**：任一数据对不上、原件发生变化、kill 重跑出现重复或缺口无法解释，不发布，继续在 dry-run/快照环境修复。

---

### M6 — 运维、权限与网页（7–10 天）

**产出**

- 在既有六项指标外补充 `send_outcome`、条件端到端延迟、补抓缺口、积压丢弃、artifact 缺失/GC/背压、重投、调度心跳与关闭结果。
- 结构化日志携带 root/parcel/source/subscription/destination/不透明 resource，不携带 secret。
- 对象级 ACL、默认拒绝、安全审计、全出口脱敏与按权限过滤的 inspect。
- 暂停/恢复、超管刷新 Source 名字、新代重投三个受控写操作；重投以 `retry_of` 创建新预算根，记录 `requeue_from` 并比较原/当前 `effective_revision` 与执行计划，send 死信在 Renderer 或渲染计划变化时回 render，只有复用旧 artifact 才立即复制 ref。
- 持久红点与 best-effort 私聊通知；信道、死信、缺口、丢弃和管理动作页面。

**验收**

1. A 群管理员不能读取、暂停或重投 B 群对象；共享上游死信、channels、components、resource 与配置仅超管可见。
2. 未授权对象按不可见处理并留下安全审计；非白名单写操作按授权矩阵拒绝，正常 GET 不被笼统写成「其余全部 403」。
3. resource、inspect、日志、异常、死信、指标和 dry-run 均不泄漏 cookie/token；数据库文件与备份按高敏边界保护。
4. 重投创建带 `retry_of / requeue_from` 的新预算根与新代，并发点击只成功一次；Parser/Enricher 计划未变时从原失败 step 续跑且不重新 Fetch，计划变化时进入最早变化 step；send 死信的 Renderer 或渲染计划已变时回 render。仅复用旧 artifact 的路径立即复制 ref，回 render 的路径不提前复制；共享上游死信过滤无权限/已删除成员并采用全组最早必要接入点。暂停/恢复幂等，只有超管能刷新共享 Source 名字。
5. 指标能计算确认口径下的 p95，并分别呈现重试、补抓、暂停、积压和降级，不通过删样本美化结果。
6. 每次 `DROPPED`、补抓缺口、artifact 缺失、GC 背压与人工重投均可从 inspect 解释。
7. 死信通知分别记录已生成、已尝试、已确认送达；私聊失败不递归死信，持久红点仍存在。
8. 页面能完成三个管理动作，所有共享对象和写操作均重新经过服务端鉴权。

---

## 依赖关系

```text
M0 ──> M1 ──> M2 ──> M3 ──> M4 ──> M5
                         └──────> M6（可与 M5 并行）
```

- M3 之前不得开始配置、迁移或网页代码，因为它们尚无可作用的真实业务对象。
- M6 从 M4 之后开始，避免 `effective_revision`、render plan 与权限对象尚未稳定就重写 API。
- M5 与 M6 可并行，但完成定义要求两者都通过真实验收。

## 明确不做

| 不做 | 原因 |
|---|---|
| 多进程 / 分布式运输器 | 非目标；当前也不开放多 worker，避免引入未验证的 claim/lease 复杂度 |
| 以吞吐为理由增加 worker 或优化查询 | 500 条/天不构成需求；只有确认口径下的延迟证据才能促使重审 |
| 把 SQLite WAL/FULL 等参数写进 Store 通用接口 | 它们只属于 SQLite 部署档案 |
| Alembic（M2 之前） | 先手写 DDL，表稳定后再引 |
| 旧 admin 的 API 形状 | 旧路由绑定旧模型，且不能表达新对象级权限 |
| entry points 发现子包 | 会形成第二套发现机制 |
| 多源类型齐上 | M3 只做 RSS，M4 再用第二 Fetcher 验证边界 |
| 浏览器概念进入 courier 或通用渲染降级 | 浏览器只是某个 Renderer 的实现能力，不是领域概念 |
| 原死信复活或重复重投 | 重投必须是保留血缘的新投递代 |
| 以「绝对无重复 / 无漏发」作为验收 | 正确目标是无未报告损失，以及只含明确窗口的 at-least-once |

## 风险与停损

| 风险 | 停损条件 |
|---|---|
| 内核语义无法写成状态机（M1） | settle、顺序、隔离、预算或循环任一验收无法成立 → 回改 ADR，不动 bison |
| 持久化后语义漂移（M2） | M1 任一测试在 SQLite 变红或崩溃矩阵分叉 → 不进入 M3 |
| 补抓能力被高估（M3） | 上游不可枚举却没有缺口报告 → 不验收「可恢复」 |
| artifact 生命周期破坏恢复（M3） | live ref 可被 TTL/LRU 删除或正常路径出现悬空引用 → 不进入 M4 |
| 组件形状不够用（M4） | 第二 Fetcher 改核心、external 续跑需重抓、降级破坏顺序 → 停并重审边界 |
| 迁移数据或切流窗口不明（M5） | 映射、checkpoint、`cutover_watermark`、`observed / migration_skipped`、迟到动态歧义或缺口任一项无法解释 → 不发布 |
| 网页只验功能不验权限（M6） | 任一跨群反例成功或任一出口泄漏 secret → 不上线 |
| 又开始大爆炸 | 任一里程碑超过 1.5 周，或 PR 含两个理由/无法独立 review → 强制拆分；物理行数不单独作为拆分理由 |

## 完成定义

同时满足以下条件，才可把项目称为「做完了」：

1. 一个真实旧部署经显式 cutover 接管并运行一周：**无未报告损失**；除「平台可能已经接受但本地结果不可知（timeout/disconnect/crash）」外无异常重复；迁移截断、`observed / migration_skipped`、迟到旧动态歧义、补抓缺口与积压丢弃均有记录和解释。
2. 第三方能写一个专线包接入，不需要读 courier 源码；external 失败不会迫使上游重抓。
3. 一个目的地坏掉只对其他目的地造成声明超时内的有界影响；死信、丢弃与通知失败均有持久事实可查。
4. 进程崩溃以及当前部署档案承诺的故障边界内，不发生未报告损失；更换 Store 后必须重跑等价恢复矩阵。
5. 在线、非暂停、非补发、首次成功样本达到 p95 < 90 秒；其他延迟群体独立可见。
6. 群管理员与超管权限经跨群反例验证，所有凭证出口脱敏，运维动作可审计。
7. 资源等待跨 head/重启不丢失，轮询合并无热循环；共享渲染成员暂停/删除不阻塞其他成员，send in-flight/outcome_unknown 不被误取消或误丢弃；重投按 `effective_revision` 与计划选择续跑阶段并正确复制或重建 artifact 引用。
