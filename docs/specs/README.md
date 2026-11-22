# MountainDash Logistics — 设计规格

本文档集把 2026-11-20 那场设计对话的结论固化成规格。术语以 [GLOSSARY.md](../../GLOSSARY.md) 为准，难以逆转的决定以 [docs/adr/](../adr/) 为准；本目录只负责**把它们连成一个可实施的系统**。

## 这是什么

从 0 重建 MountainDash Logistics（原 `nonebot-bison`）：把社交媒体上的动态搬运到聊天平台。系统由两个包组成：

- **courier** —— 运输内核。知道地址、包裹、面单、信道、站点、回收站。不知道消息、社交平台、聊天平台。
- **bison** —— 业务应用。抓取器、解析器、富化器、渲染器、发送器五类组件，加上调度、订阅、配置、存储、网页与对话。

## 范围

覆盖重建后的架构形状与全部已决议的行为约束。

**非目标：**

- 多进程 / 分布式运输器（只保留接口形状，不实现）
- 当前开放多 worker（未来需求成立时须先补原子 claim 决策）
- Prometheus 之外的可观测后端
- 目的地级配置
- 兼容旧版插件作者 API
- 兼容旧版 admin 前端的 API 形状

## 约束基线

这些数字决定了所有取舍，其它任何"为了性能"的论证都要先过这一关：

| 指标 | 目标值 |
|---|---|
| 源 | ~10 |
| 订阅 | ~200 |
| 目的地（群 + 私聊） | ~50 |
| 消息量 | < 500 条/天（≈ 每 173 秒一条） |
| 端到端延迟 | 条件口径 p95 < 90 秒（在线、非暂停、非补发、首次尝试成功；见运行规格 §3.2） |
| 单条体积 | ≤ 9 张图 |

**推论（写进规格，不是建议）：任何以吞吐为理由的设计决定都是错的。** 单进程、SQLite、一个 worker 都绰绰有余。真正的约束是正确性、可扩展性与运维可理解性。

## 决策索引

| # | 决策 | 位置 |
|---|---|---|
| 0001 | courier 零 NoneBot 依赖 | [ADR](../adr/0001-courier-has-no-nonebot-dependency.md) |
| 0002 | 信道是逻辑车道，顺序由「单在途」保证；不引入序列号与 Resequencer | [ADR](../adr/0002-channel-is-a-logical-lane.md) |
| 0003 | 依赖注入：letoderea 执行器，分发与验证解耦 | [ADR](../adr/0003-di-open-vocabulary-closed-mechanism.md) |
| 0004 | 存储用 SQLAlchemy Core，engine 由宿主注入，不共享 schema | [ADR](../adr/0004-store-sqlalchemy-core.md) |
| 0005 | 信道按资源划分，资源粒度等于站点粒度 | [ADR](../adr/0005-resource-key-equals-station-granularity.md) |
| 0006 | 配置由组件声明 schema，配置系统不单独成包 | [ADR](../adr/0006-config-declared-by-components.md) |
| 0007 | 渲染产物与传输无关，渲染计划包含能力变体与可见降级 | [ADR](../adr/0007-rendered-content-is-transport-neutral.md) |
| 0008 | 带显式例外的 at-least-once：无未报告损失，不承诺绝对零重复 | [ADR](../adr/0008-at-least-once-with-explicit-losses.md) |

其余只活在这场对话里的决定，全部写进了三份规格：

| 文件 | 内容 |
|---|---|
| [0001-courier.md](./0001-courier.md) | 内核：包裹、信道、站点、DI、存储、扇出、语义 |
| [0002-bison.md](./0002-bison.md) | 应用：组件模型、装配、源与订阅、配置、对话 |
| [0003-operations.md](./0003-operations.md) | 运行：启动、关闭、网页、可观测、迁移、容量 |

实施顺序见 [PLAN.md](../PLAN.md)：七个里程碑，每个都以「可运行」结束。

## 待定（属于实现，不属于决策）

- 面单与信道表的确切列类型与命名
- 对话命令的具体语法
- 指标标签的维度命名
- 除内建 `basic` 与最终纯文本外，首批交付哪些可选风格渲染器
- 网页前端复用程度（需先审计旧 SPA）

## 研究依据

三份调研报告在 [docs/research/](../research/)：旧 bison 的技术考古、NoneBot 生态约束、courier 的先例（EIP / AMQP / Kafka / Erlang / Spark / 调度器 / durable execution）。
