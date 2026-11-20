# 依赖注入：开放词汇，封闭机制

courier 自研约 70 行注入器（[原型](../research/prior-art/courier_di.py)）：站点用类型标注声明依赖，宿主与插件用 `register(key, factory)` 注册 provider，键是一个类型或 `Annotated[T, marker]`。**注入方式只有一种**（读签名 + 查注册表），**可注入的类型集合完全开放** —— 下游插件注册任意新类型不需要改 courier。

## Considered Options

- **复用 NoneBot 的 `Dependent`**：被 [ADR 0001](./0001-courier-has-no-nonebot-dependency.md) 否掉。
- **第三方 DI 库**（`injector` / `punq` / `dependency-injector` / `wireup`）：它们解决的是作用域与生命周期，而 courier 只需要「按类型或 marker 取一个实例」。
- **照抄 Entari（实际是 `arclet-letoderea` 的分发器 DI）**：provider 是带 `validate()` 谓词的有序列表，「返回 `None` 表示不是我的」，三套并存的注册入口（`global_providers` / `Scope.providers` / dispatcher providers）加上按参数名兜底查找，引擎约 350 行；且缺 provider 要到**首次调用**才报 `UnresolvedRequirement`，互相 `Depends` 会炸成裸 `RecursionError`。只有「零参 async provider + `Annotated` 键 + 派生 provider」这三件事值得抄。

## Consequences

- 可满足性在 **`register()` / 装饰期**校验，不是首次调用 —— 启动就炸，而不是半夜第一次投递才炸。
- 重复注册同一个键**直接报错**。Entari 在这里是静默的（两个 provider 都进列表，先到先得），而「两个插件抢同一个类型」是下游生态里最常见的事故。
- 注册表是启动期单线程单次写入的模块级 dict，运行时只读。
- `@inject` 在装饰期解析出的依赖清单**就是 inspect 的数据源**：每个站点「需要什么」在注册那一刻已是已知数据，不需要另一个子系统。
