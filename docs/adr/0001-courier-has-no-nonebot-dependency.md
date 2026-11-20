# courier 不依赖 NoneBot

courier 作为独立包发布，不 import nonebot，仅依赖 anyio 与一个存储抽象；所有 NoneBot 侧的适配（插件加载、Bot 获取、配置来源、调度宿主）留在 bison 里。代价是 NoneBot 现成的 `Dependent` 依赖注入、`require()` 插件加载与 `PluginMetadata` 都得自己实现一份，收益是 courier 能在非 NoneBot 宿主里运行：单元测试、独立守护进程、以及将来把抓取与推送拆到不同机器的分布式运输器。

## Considered Options

- **直接复用 nonebot 的 `Dependent` 与插件系统**：省下自研 DI 的成本，但 courier 从此只能在 NoneBot 进程里活，第二条实现路径（分布式）被结构性堵死。
- **零依赖**（采纳）：多付一次自研成本，换取宿主无关。

## Consequences

需要自建三样东西：最小依赖注入、注册中心、inspect 出口。三者都必须足够小，否则 courier 会从「组件」变成「框架」—— 这正是 `feat/courier2` 那一版 856 行里 269 行是 `param.py` 的原因。
