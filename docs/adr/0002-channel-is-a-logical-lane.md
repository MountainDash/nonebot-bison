# 信道是逻辑车道，顺序由「单在途」保证

courier 不提供传输级全序，也不实现序列号、Resequencer 或乱序窗口。顺序来自一条结构性约束：**同一信道上同时至多一个包裹在途**。信道是一行状态（head 包裹、`next_attempt_at`、`attempt_count`），不是任务或队列对象；物理资源是一个固定大小的 worker 池，按最早到期的信道取活。

## Considered Options

- **序列号 + Resequencer**：需要额外的超时策略，而在超时那一刻必须在「乱序发出」与「阻塞车队」之间二选一（Camel 与 Spring Integration 都把这个选择暴露成配置项）。
- **单全局队列**（现状）：跨目的地队头阻塞，即 [#678](https://github.com/MountainDash/nonebot-bison/issues/678) 的成因 —— 一个群坏掉，所有群排队。
- **每目的地一个 task + 队列对象**：语义相同，但物理开销随目的地数增长，且队列状态不在存储里，既不能活过重启（[#635](https://github.com/MountainDash/nonebot-bison/issues/635)）也不能被 inspect。

## Consequences

- 顺序不是被「解决」的，是被「排除」的：车队宽度为 1，乱序没有入口，因此 Resequencer、序列号、乱序窗口一并消失。
- 失败必须原地重试（只推后该信道的 `next_attempt_at`）。跳到队尾会把「下播」发在「开播」之前。
- 跨信道永不互相等待，因此「目的地内阻塞」是正确的，「跨目的地阻塞」是 bug —— 这条区分是整个设计的支点。
- 队列必须落表（要活过重启），而一旦落表，信道的成本就降到一行数据，于是「每目的地一条信道」不再浪费。
