# SQLAlchemy Core、共享事务与后端耐久契约

courier 定义 `Store` Protocol，自带实现基于 SQLAlchemy 2.0 async **Core**（不用 ORM），`AsyncEngine` 由宿主注入。courier 与 bison 各自拥有自己的表和迁移，不共享 schema、互不 join；两者可以在同一个 SQLAlchemy connection/transaction 中完成一次业务原子写入。

**每次站点结果都必须统一原子结算。** 父 Receipt、信道 head 推进、全部子包裹与去重、下一跳或重试时间、终态与死信记录必须在同一事务中提交。业务校验拒绝时丢弃全部输出，但提交父 DEAD 与 head 推进；存储/系统失败才整体回滚并保持 head。网络请求、渲染和聊天发送等外部副作用不得放进这个数据库事务；运行时唤醒只能在提交成功后发出。

bison 的源调度、内容去重、游标推进与 courier 入队需要原子完成时，由 bison 开启事务并传入 connection，courier Store 参与而不接管该事务。共享事务不意味着共享表结构或跨 schema 查询。

## Considered Options

- **裸 `sqlite3` / `aiosqlite`**：少一个依赖，但会形成两套连接、事务与迁移基础设施。
- **SQLAlchemy ORM**：队列操作是少量显式 SQL，ORM 只带来 session 生命周期、身份映射与懒加载的样板。
- **只做内存实现**：直接丢失重启恢复能力。
- **各包独立提交**：会在父结算与子入队、游标推进与内容入队之间留下崩溃分叉。
- **把跨 schema join 当作组合方式**：破坏包边界；这里需要的是共同提交，不是关系查询。

## Consequences

- Store 的持久契约是**原子提交与声明的耐久性**，不包含某个数据库的 journal 参数。进程崩溃、提交前后崩溃与外部发送后未结算必须分别验收。
- 内建 SQLite 部署档案使用 WAL、`synchronous=FULL`、busy timeout 与短事务，并据此定义恢复测试。这些参数属于 SQLite，而不是 `Store` Protocol。
- 未来替换数据库或 Store 时，必须声明等价的原子性与耐久保证，并替换相应部署档案和崩溃验收；更换后端不自动意味着语义不变。
- 文件、渲染产物等外部资源不能只靠数据库事务获得一致性，必须有独立的发布与对账协议。
- 「零 NoneBot 依赖」（[ADR 0001](./0001-courier-has-no-nonebot-dependency.md)）不受影响；courier 的 schema 仍能独立迁移。
