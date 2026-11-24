# 依赖注入：letoderea 执行器，分发与验证解耦

courier 直接使用 `arclet-letoderea` 的 `Provider / ProviderFactory / Depend / Subscriber` 公开机制，但**不让它承担完整容器职责**。实例化的 `DependencyDispatcher` 拥有注册表、不可变 `BindingPlan`、singleton、依赖图、冻结与运行期调用；不保留旧模块级 DI 或兼容入口。

## 两种后端，两种问题

**BindingBackend** 回答「哪些 Provider 匹配这个参数」。默认严格键后端只接受类型或 `Annotated[T, marker]` 的精确键；可选 Entari 后端适配 `Provider.validate` / `ProviderFactory`，处理更复杂的注解。ProviderFactory 生成的实例固定在 BindingPlan 中，校验与执行不得生成两次。

**ValidationBackend** 回答「整个声明图是否可满足」。它只读 RegistrySnapshot 与 BindingPlan，聚合并返回缺失、同优先级歧义、直接/间接环等问题，不调用 factory、不接触 Parcel。默认严格图实现必须覆盖所有根与所有可达 fallback。替换后端必须通过同一组行为契约，不能静默放宽仓库底线。

二者与执行器消费**同一份 BindingPlan**，不得各自计算一套匹配结果。`Prepared.needs` 的替代数据来自该计划，继续作为 inspect 数据源。

## 装配与执行

```text
创建 DependencyDispatcher
→ 注册全部 Provider（允许 forward declaration）
→ prepare 全部站点，生成 BindingPlan
→ ValidationBackend 一次聚合全部问题
→ 无错误后构造 Subscriber 并冻结
→ 运行期只通过 Subscriber.handle 与 Dispatcher resolve 调用
```

严格键重复注册立即报错。缺项与环在启动校验期一次性报告，不再要求「依赖先于使用方注册」。冻结后禁止注册、替换后端或重绑定。校验失败不得执行 factory、创建资源或部分冻结。

letoderea 的 `record` 只缓存 Provider 选择，不是 singleton。singleton/transient 与并发构造由 Dispatcher 管理；singleton 不得捕获单次调用上下文，factory 异常不得发布半初始化值。资源仍由宿主拥有，除非另有明确生命周期协议。

## 不复用的上游语义

- 不引入 Entari、launart、Satori，不使用 `Scope` / `publish` / `dispatch` 作为站点 worker。
- 不使用 `global_providers`、隐式参数名上下文覆盖、字符串 marker=context key、`skip_req_missing`、运行期 `_recompile` 或私有 `_compile`。
- 严格键优先；谓词候选只来自显式启用的后端。同优先级歧义启动失败，不静默先到先得。
- keyed factory 返回 `None` 是合法值；原生谓词 Provider 的 `None=decline` 仅留在该后端内，两种语义不得混用。
- `Subscriber.handle` 只接收显式调用上下文。构造时审计实际 candidates，防止宿主全局 Provider 污染。

## Considered Options

- **继续自研单体 DI**：签名解析、匹配、图校验、执行和缓存耦在一个模块，无法替换验证策略，也要求注册顺序碰巧正确。
- **完整采用 Entari / letoderea 事件系统**：会同时引入全局注册、事件异常分发、隐式上下文与不符合仓库要求的冲突语义。
- **复用 NoneBot `Dependent`**：仍被 [ADR 0001](./0001-courier-has-no-nonebot-dependency.md) 排除。
- **只借思想、不依赖 letoderea**：需要重新维护参数编译与调用细节；本次目标正是在严格边界内复用这些机制。

## Consequences

- `courier` 新增直接运行时依赖 `arclet-letoderea>=0.22.1,<0.23`，其传递依赖为 `tarina` 与 `typing-extensions`；不引入 Entari 的完整依赖树。依赖白名单、规格与锁文件必须同步更新。
- letoderea 仍是 0.x Beta，只能通过 adapter 使用公开 API，并以契约测试锁定 0.22.x 集成面；不得向其私有编译函数或 monkeypatch 迁移复杂度。
- 新项目没有已发布 DI 消费者，**不做旧 API 兼容层**。旧 `reset_registry()`、模块级默认 registry 与实现细节测试直接删除，调用方和行为测试重写。
- 启动校验证明声明图的结构可满足性，不证明外部服务健康，也不保证原生谓词 Provider 运行时一定不 decline；运行期解析错误必须保留站点、参数与依赖链，取消继续传播。
- [Entari / letoderea 调研](../research/prior-art/entari-di.md)记录机制来源；本 ADR 记录本项目实际保留与拒绝的语义。
