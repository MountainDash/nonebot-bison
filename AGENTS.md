# AGENTS.md

给在本仓库工作的 agent（和人类）的操作纪律。**设计决策的权威在 [docs/adr/](docs/adr/)，规格在 [docs/specs/](docs/specs/)，术语在 [GLOSSARY.md](GLOSSARY.md)。** 本文只记录「不随设计演进变化的工作方式」和「不许越过的硬约束」。

## 项目

从 0 重建 MountainDash Logistics（原 `nonebot-bison`）：把社交媒体动态搬到聊天平台。两个包：

- `packages/courier` —— 运输内核，**零 NoneBot 依赖**
- `packages/bison` —— 业务应用，依赖 NoneBot

## 开工前先读

1. [GLOSSARY.md](GLOSSARY.md) —— 用里面的词，不要用 `_Avoid_` 里的词
2. [docs/specs/README.md](docs/specs/README.md) —— 范围、非目标、约束基线
3. 你这次要改的那一块的 spec（[courier](docs/specs/0001-courier.md) / [bison](docs/specs/0002-bison.md) / [运行](docs/specs/0003-operations.md)）
4. [docs/PLAN.md](docs/PLAN.md) —— 当前在哪个里程碑、哪些事还不能做

## 硬约束（不可违反）

1. **`courier` 不 import nonebot。** 有测试守着（`import courier` 之后 `sys.modules` 里不能有 `nonebot`）。见 [ADR 0001](docs/adr/0001-courier-has-no-nonebot-dependency.md)。
2. **依赖白名单：`anyio`、`sqlalchemy`(Core)、`pydantic`。** 加任何其他运行时依赖都要先改规格与 ADR，不能顺手装。
3. **`Parcel` / `Receipt` 的全部字段必须能 `json` 往返。** 事件、锁、连接、任何运行时对象都不许进包裹。
4. **不做以吞吐为理由的优化。** 规模基线是 10 源 / 200 订阅 / 50 目的地 / <500 条每天（见 specs/README 的约束基线）。
5. **不跨 schema join。** courier 的表归 courier，bison 的表归 bison，共用 engine 但互不查询。
6. **迁移：绝不删旧表、绝不伪造历史、绝不伪造去重游标。**
7. **站点注册只能在 `run()` 之前。** `run()` 之后调用 `register()` 必须抛错，不得静默生效。
8. **测试与实现在同一个 PR 里。** 不允许「先实现后补测」，也不允许「最后来个测试 PR 收口」（唯一例外是里程碑验收 PR，见 PLAN）。
9. **决策变了就在同一个 PR 里改 ADR / GLOSSARY。** 落后的 ADR 比没有 ADR 更糟。
10. **代码必须过三道门：`ruff check`、`ruff format --check`、`basedpyright`（0 error 0 warning）。** 不许用「关了这条规则」代替修代码；要关某条规则，得在 `pyproject.toml` 里写明理由。

## 工作方式：链式 PR 栈

- **一个里程碑 = 一个栈**，栈内 PR 逐层相接（每层 base 是下一层的分支），栈底指向 `main`。
- **一个 PR 一个理由**，标题能写成「为了 X 而 Y」，不需要「顺便」。
- **≤ 400 行**（不含测试、fixture、生成物）。超了就是它有两个理由，拆。
- **合并后主干必须全绿**；M3 之后还要求 bison 能启动。未接线的代码以「已实现但未注册」进主干。
- **行为变化必带测试**：courier 的每个 PR 至少新增或修改一个行为测试。

PR 描述里必须有这五行：

- [ ] 为了 X 而 Y
- [ ] 怎么验证（跑哪个测试 / 点哪个界面）
- [ ] 是否改变已发布接口
- [ ] 是否改变已记录决策（是则同 PR 更新 ADR / GLOSSARY）
- [ ] diff ≤ 400 行（不含测试）

完整 PR 清单见 [PLAN.md](docs/PLAN.md)。

## 不可自主执行的操作

以下操作**必须先在对话中获得明确同意，且每次单独确认**：

- `git push`（任何分支，**包括更新已开 PR 的分支**）
- `gh pr create` / `gh pr merge` / 关闭或标记 PR
- `git push --force` / `--force-with-lease`
- 删除远端分支、修改远端地址、修改仓库设置
- 打 tag、发布到 PyPI

**允许自主执行：** 本地提交、本地测试、本地分支与 rebase。

**本地提交不等于可以推送。** 提交是为了让工作可回退、可 bisect；推送是对外可见的动作，由人决定时机。做完一个 PR 该停下来说「这一层已经就绪，要推吗」，而不是推完再汇报。

## 停损条件（宁可停，不要绕）

- **M1 的顺序或隔离语义测试写不出来** → 停，回改 [ADR 0002](docs/adr/0002-channel-is-a-logical-lane.md)，不写 bison。
- **M1 的语义测试在 SQLite 上有任何一条变红** → 不进 M3。
- **第二个抓取器要改核心才能接入** → 停，重看「站点边界判据」。
- **任一里程碑超过 1.5 周** → 强制拆，不例外。

## 不要做

| 不要 | 原因 |
|---|---|
| 多进程 / 分布式运输器 | 非目标，接口已留口子 |
| ORM（SQLAlchemy 只用 Core） | 队列查询是十条显式 SQL |
| Alembic（M2 之前） | 表稳定后再引 |
| entry points 发现子包 | 会是第二套发现机制 |
| 旧 admin 的 API 形状 | 16 条路由全绑旧模型 |
| 序列号 / Resequencer / 乱序窗口 | 已由「单在途」排除 |
| 运行时注册 | 地址标识处理类型，对象是数据 |
| 一次性吃掉多个里程碑 | 前五次的死法 |

## 目录

```
packages/courier/      内核
packages/bison/        应用
docs/specs/            规格（权威）
docs/adr/              决策（权威）
docs/research/         调研与考古（只读参考）
docs/PLAN.md           里程碑与 PR 清单
GLOSSARY.md            术语（权威）
```

## 验证

```bash
uv run pytest                    # 全部测试
uv run ruff check .              # 静态检查
uv run ruff format --check .     # 格式
uv run basedpyright              # 类型检查
```
