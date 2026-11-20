# courier 用 SQLAlchemy Core，engine 由宿主注入

courier 定义 `Store` Protocol（入队、取 head、推进、设 `next_attempt_at`、进回收站、列信道等约十个方法），自带实现基于 SQLAlchemy 2.0 async 的 **Core**（不用 ORM），`AsyncEngine` 由宿主注入。courier 拥有自己的三张表与其迁移，bison 拥有自己的表与迁移，两者共用基础设施但**不共享 schema，也不跨库 join**。

## Considered Options

- **裸 `sqlite3` / `aiosqlite`**：少一个依赖，但会和 bison 的 SQLAlchemy 形成两套连接、两套迁移，且 PG/MySQL 支持要重写。
- **SQLAlchemy ORM**：队列的查询是十条显式 SQL，ORM 在这里只带来 session 生命周期、身份映射与懒加载的样板。
- **只做内存实现**：直接丢掉 [#635](https://github.com/MountainDash/nonebot-bison/issues/635)（重启丢消息），而持久化正是信道必须落表的理由。

## Consequences

- 「零 NoneBot 依赖」（[ADR 0001](./0001-courier-has-no-nonebot-dependency.md)）依然成立 —— SQLAlchemy 不是 NoneBot。
- PostgreSQL / MySQL 几乎免费，但 courier 的 schema 必须能独立于 bison 迁移：bison 可以整体重装，courier 的表不能。
- `Store` Protocol 存在的意义是「将来可能有第二种实现」（分布式运输器），而不是「现在就要支持多种数据库」。
