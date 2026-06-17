---
name: generic-issue-log-analysis
description: 分析当前仓库或用户明确指定的公开 GitHub issue（完整 URL 或 `#1234`）。优先读取 issue 正文和评论，按需下载日志包、截图、配置导出和崩溃转储，建立时间线后结合仓库代码、文档和必要的上游依赖判断根因，并给出修复建议或下一步排查建议。
---

# Generic Issue Log Analysis

## Scope

- 默认把 `#1234` 视为当前仓库 issue。
- 如果用户给了完整 issue URL，则以该 URL 为准。
- 只分析可以直接访问的公开 issue、评论、截图和附件。
- 如果缺少日志、现场图、配置导出或崩溃信息，要先明确说明证据不足，再基于现有材料给出初步判断。
- 如果问题依赖私有环境、外部服务或用户本地状态，而仓库内证据不足，要明确列出还缺哪些材料。

## Workflow

1. 规范化输入。

   - `#1234` 视为当前仓库 issue。
   - 完整 issue URL 以 URL 为准。
   - 如果用户给的是模糊描述，先在 issue 文本里定位编号、链接或关键上下文。

2. 获取 issue 内容。

   - 读取正文和评论。
   - 提取这些信息：Bison 版本、NoneBot 版本、Python 版本、部署方式（Docker / pip 安装 / 源码运行）、平台（微博/B站/RSS/明日方舟等）、任务或订阅、预期行为、实际行为、复现步骤、维护者评论、附件链接。
   - 如果维护者、机器人或其他评论已经给出结论，不要直接照抄；仍要用日志、代码和文档自行验证。

3. 提取附件和现场证据。

   - 优先关注 Bison 运行日志、NoneBot 控制台输出、截图、配置导出（如 `.env`、`docker.env`、`bison_config`）、崩溃转储、浏览器截图（playwright 相关问题）、平台订阅配置导出。
   - 不要假定附件命名固定；留意 `log`、`report`、`debug`、`crash`、`dump`、`config`、`trace`、`screenshot`、`bison.log`、`nonebot.log` 等关键词。
   - 如果同一个 issue 有多份日志，先看最新一次复现；如果 issue 在对比不同版本、不同环境或不同平台，再补看旧样本。

4. 下载并解压附件。

   - 二进制附件不要只靠网页抓取工具直接分析，应先下载到工作区临时目录，例如 `.cache/issue-logs/issue-<number>/`。
   - 解压后先列目录，不要假定内部结构固定。
   - 只读取和结论直接相关的文件，不要把整份大日志、整份配置或整个转储内容直接塞进回复。

5. 建立时间线。

   - 先从 issue 文本确定“用户认为出问题的时刻”和复现条件（如添加特定订阅、特定时间段没有收到推送）。
   - 再把 NoneBot 日志、Bison 调度日志、爬取日志、推送日志、配置快照和崩溃信息串成一条时间线。
   - 优先锁定这次复现对应的 `sub_id`、`platform`、`target`、用户 ID、群号、时间戳或其他稳定标识，再追踪细节。

6. 回溯到代码和文档。

   - 先看仓库里的 docs 目录下的文档、README、FAQ。
   - 再看相关模块：`platform/`（各平台爬取逻辑）、`scheduler/`（调度器）、`send.py`（推送队列）、`sub_manager.py`（订阅管理）、`plugin_config.py`（配置项）。
   - 如果问题明显落在 NoneBot2 框架、`nonebot-plugin-saa`、`nonebot-plugin-apscheduler`、`nonebot-plugin-datastore` 或下游 QQ 客户端，再按需查看相关仓库或文档。
   - 只看真正相关的模块，不要为了“完整”而把整个依赖栈都扫一遍。

7. 区分 issue 当时环境和当前分支。

   - 先以 issue 文本、附件、配置快照和缓存资源还原用户当时的实际环境。
   - 再对照当前仓库代码，判断问题是当前仍存在，还是当时存在但现在可能已修复。
   - 如果 issue 很旧，或日志流程与当前主线明显不一致，必要时按对应 tag、release 或历史提交复核旧逻辑。
   - 输出给用户时，如果提到平台名、订阅名、配置项、按钮名、错误提示或日志前缀，先在仓库里搜索翻译 / 本地化文件，不要直接把 `t("...")`、`i18n.t("...")`、枚举名或内部 ID 当成最终展示文本。

8. 输出结论。

   - 明确区分“已证实的根因”“高概率怀疑点”“证据不足的待确认项”。
   - 给出能执行的下一步，例如修复方向、需要补充的材料、临时绕过方案、是否建议升级或回滚。

## Artifact Map

### Bison / NoneBot Runtime Logs

- 模块归属：Bison 核心运行时、NoneBot2 框架层。
- 最适合看：
  - 插件加载失败、数据库连接错误
  - 调度器启动状态
  - 配置读取问题（`plugin_config` 相关）
  - `bootstrap.py` 中的数据库迁移日志（alembic 版本检查）
- 典型日志特征：`nonebot-bison bootstrap done`、`[nonebot_bison]` 前缀的日志、`nonebot.log` 中的 ERROR 级别日志。

### Platform / Crawler Logs

- 模块归属：各平台爬取模块（`platform/` 目录），包括微博、Bilibili、B站直播、RSS、明日方舟、网易云音乐、FF14。
- 最适合看：
  - 订阅的特定平台爬取失败
  - Cookie 过期或无效
  - 平台风控导致返回空数据或错误页面
  - playwright 浏览器启动失败
  - HTTP 请求超时、代理配置问题
- 典型日志特征：`Fetching posts from platform xxx`、`Failed to fetch`、`Cookie expired`、`bison_use_browser` 相关日志。

### Scheduler Logs

- 模块归属：调度器模块（`scheduler/` 目录），基于 `nonebot-plugin-apscheduler`。
- 最适合看：
  - 定时任务是否按预期执行
  - 任务被跳过或延迟执行
  - 调度器未启动
  - 权重调度配置问题
- 典型日志特征：`Job xxx triggered`、`scheduler log level` 调整相关。

### Send / Queue Logs

- 模块归属：推送模块（`send.py`），使用 `nonebot-plugin-saa` 和队列机制。
- 最适合看：
  - 消息发送失败及重试次数
  - 队列积压
  - `ActionFailed` 异常（适配器层面）
  - 风控触发导致的发送失败
  - 图片合并转发配置问题（`bison_use_pic_merge`）
- 典型日志特征：`send msg failed, refresh bots`、`send msg err`、`QUEUE` 相关内容。

### Config Snapshots

- 模块归属：Bison 配置项（`plugin_config.py`、`.env`、`docker.env`、`bison_config`）。
- 重点关注配置项：
  - `bison_use_pic`：文本转图片风控防护
  - `bison_use_browser`：是否启用浏览器（playwright）
  - `bison_use_queue`：是否启用推送队列
  - `bison_proxy`：代理配置
  - `bison_ua`：User-Agent
  - `bison_resend_times`：推送失败重试次数
  - `bison_filter_log`：日志过滤
  - `bison_platform_theme`：平台主题映射
  - `bison_to_me`：是否 at 自己触发命令
- 最适合看：
  - issue 中描述的配置是否与实际生效配置一致
  - 配置项冲突或误设导致的异常行为

### Screenshots / QQ Client Logs

- 模块归属：QQ 客户端截图、Bison 管理后台截图、QQ 客户端日志（lagrange/napcat/...）。
- 最适合看：
  - 用户看到的实际推送样式
  - 后台管理界面报错
  - QQ 客户端是否正常接收消息
  - 风控提示截图
  - `connect open` 等 QQ 适配器连接日志

### Dumps / Crash Reports

- 模块归属：Python 异常堆栈、playwright 崩溃信息、数据库损坏报告。
- 最适合看：
  - `TypeError: 'type' object is not subscriptable`（Python 版本不兼容）
  - `TypeError: __init__() got an unexpected keyword argument 'proxies'`（httpx 版本问题）
  - `ActionFailed` 等发送层异常

### Database / Subscription Exports

- 模块归属：订阅数据（`nonebot_plugin_datastore` 管理）、迁移脚本（`bootstrap.py`、`db_migration.py`）。
- 最适合看：
  - 订阅是否在数据库中正确存储
  - 数据库版本与代码版本是否匹配
  - 数据迁移是否成功执行
- 典型日志特征：`当前数据库版本：{t}，不是插件的版本，已跳过`、`未发现默认版本数据库，开始初始化`

## How To Filter Evidence

1. 先从 issue 文本拿到这些锚点：

   - Bison 版本、NoneBot 版本、Python 版本、部署方式
   - 平台（微博/B站/RSS/明日方舟等）
   - 订阅目标（uid、mid、用户 ID）
   - 用户说“出问题”的具体时间、发送的消息、期望收到但没收到的内容

2. 再从日志里找高价值信号：

   - `ERROR`、`WARNING`、`CRITICAL`
   - `Failed`、`Exception`、`ActionFailed`
   - `timeout`、`retry`
   - `bison_` 开头的配置项相关日志
   - `playwright`、`browser`、`cookie`
   - `queue`、`send`、`refresh_bots`
   - `sub_id`、`platform`、`target`、`group_id`、`user_id`

3. 先锁定“这一次复现”再下钻。

   - 一个日志包里通常会混有很多历史运行。
   - 如果 issue 文本说失败，但对应这次复现的任务最终成功，要明确写出“本次日志未复现用户描述的问题”。

4. 区分表象和根因。

   - 用户看到的“Bot 不理我”可能是命令前缀配置问题（`COMMAND_START`）。
   - 更高层的平台爬取失败可能是 Cookie 过期或平台风控。
   - 如果 send.py 层已经给出 `ActionFailed` 异常，应优先以该层为准，再回头解释用户看到的现象。

5. 回答时只保留关键片段。

   - 只摘足够支撑结论的少量证据。
   - 不要把整份日志、整段 issue 讨论或整份配置直接倾倒进回复。

## Common Patterns

- **Python 版本问题**：报错 `TypeError: 'type' object is not subscriptable` → Python 3.10 以下不支持语法，检查用户 Python 版本，建议升级到 3.10 或使用 Docker。

- **httpx 版本不兼容**：`TypeError: __init__() got an unexpected keyword argument 'proxies'` → httpx 0.28.0 之后不再支持 `proxies` 参数，需锁定 httpx 版本或修改代理配置代码。

- **Bot 不理我**：
  - 检查 `COMMAND_START` 环境变量是否设为 `[""]` 或正确前缀
  - 确认用户是群主或管理员
  - 检查 `bison_to_me` 配置决定是否需要 at bot

- **微博漏订阅**：微博平台风控更新，某些含特定关键词的微博获取不到 → 建议用户确认平台状态或使用其他平台。

- **无法使用后台管理页面**：
  - 确认 `HOST=0.0.0.0`（远程访问时）
  - 检查云服务器防火墙配置
  - 确认安装方式支持后台管理（使用 pypi 版本或 docker 版本）

- **playwright 浏览器相关**：`bison_use_browser=True` 但浏览器未安装或崩溃 → 检查 playwright 是否正确安装，Docker 镜像中是否包含浏览器。

- **数据库迁移问题**：日志显示“当前数据库版本：xxx，不是插件的版本，已跳过” → 数据库版本与插件版本不匹配，需要按文档执行迁移或清理重建。

- **维护者评论已经给出判断，但日志和代码证据并不支持**：以可验证证据为准，把维护者评论当成补强而不是唯一依据。

- **issue 文本说“失败 / 卡死”，但对应复现日志最终成功**：先明确“本次日志没有复现出用户描述的问题”，再区分是用户补错了日志，还是代码里确实存在脆弱点但这次没触发。

- **用户日志里的流程与当前主线代码明显不一致**：先确认 issue 当时的版本、tag 或 release，不要用当前主线直接否定旧版本问题。

- **配置快照和实际运行日志不一致**：不要立刻认定是用户表述错误，先确认配置是否在复现后又被修改、是否有多个配置文件、是否存在缓存或导出时机差异。

- **日志显示截图、诊断包或转储已保存，但附件里没有对应文件**：把“缺失的关键证据”单独写出来，不要假装已经验证过那部分现场。

## Correlating With Code

**核心原则：先用日志证据定位到具体模块和操作，再阅读对应代码。严禁未看证据直接猜测代码问题。**

### Phase 1: 确认证据指向

在阅读任何代码之前，先用证据回答以下问题：

1. **错误发生在哪个层级？**
   - NoneBot2 框架层（启动失败、命令不响应、适配器报错）
   - Bison 调度层（定时任务未触发、权重调度异常）
   - 平台爬取层（某个平台的所有订阅都失败）
   - 推送层（消息发送失败、队列积压）
   - 数据库层（迁移失败、读写错误）

2. **错误的直接表现是什么？**
   - 从日志中提取精确的错误信息（`ERROR`、`Exception`、`ActionFailed`）
   - 从 issue 描述中提取用户看到的现象（"Bot 没反应"、"收不到某条微博"）

3. **问题是否可稳定复现？**
   - 日志中是否包含同一次复现的完整流程？
   - 如果日志中未复现用户描述的问题，**先明确说明证据不足，不要强行关联代码**

### Phase 2: 定位到具体代码模块

根据 Phase 1 的结论，按以下优先级阅读文档和代码：

1. **必读文档（优先于代码）**
   - [Bison 文档](https://nonebot-bison.netlify.app/)：了解整体架构和配置说明
   - README 和 FAQ：常见问题可能已有标准答案

2. **按错误类型定位代码**

   | 证据指向          | 优先阅读模块                              | 入口文件/关键函数                           |
   | ----------------- | ----------------------------------------- | ------------------------------------------- |
   | 插件启动/数据库问题 | `bootstrap.py`, `db_migration.py`         | 检查 alembic 版本、datastore 初始化          |
   | 命令不响应         | `__init__.py`, `matcher/`                 | 检查 `__usage__`、命令前缀匹配逻辑           |
   | 平台爬取失败       | `platform/<平台名>.py`                    | 定位 `fetch` 方法、cookie 处理、浏览器调用    |
   | 调度未触发         | `scheduler/`                              | 检查 `nonebot-plugin-apscheduler` 的 job 定义 |
   | 推送失败           | `send.py`                                 | 定位 `send_msg`、`refresh_bots`、队列逻辑      |
   | 配置不生效         | `plugin_config.py` + 用户的 `.env` 快照    | 对比配置项默认值和用户实际值                 |
   | 数据库读写异常     | `sub_manager.py` + datastore 模型定义      | 检查订阅 CRUD 操作的 SQL 和错误处理           |

### Phase 3: 深度分析（证据链驱动）

如果 Phase 2 初步定位后仍未找到根因，按以下步骤深入：

1. **建立症状到代码的追溯链**
   - 从用户看到的错误信息或异常堆栈的**最底层**开始
   - 向上追溯调用链，直到找到**数据/状态的原始来源**
   - 示例流程：`用户看到"发送失败"` → `send.py 中的 ActionFailed` → `适配器返回的错误码` → `SAA 的 send 方法` → `调用时的参数（bot_id, group_id）`

2. **逐层验证，不要跳跃**
   - 在每层边界确认：**输入是什么？输出是什么？哪个环节产生了偏差？**
   - 可以假想添加日志来验证中间状态（如"如果在这里加一行日志打印 xxx，应该能看到 yyy"）

3. **对比正常场景**
   - 找到同一个模块中**正常工作**的订阅或操作
   - 对比正常和异常场景的差异：参数不同？配置不同？数据状态不同？

4. **当需要回溯多组件调用链时**
   - 使用 `root-cause-tracing.md` 中描述的回溯方法
   - 明确记录每一步的证据，形成可验证的链条

### Phase 4: 代码证据的输出格式

当需要引用具体代码行时，必须满足以下要求：

- **统一使用远端 GitHub blob 行号链接**，格式：
  `https://github.com/MountainDash/nonebot-bison/blob/<commit>/<path>#L14-L20`
- `<commit>` 必须是本次分析实际依据的代码版本：
  - 默认使用当前检出的 `HEAD`（主分支 main）
  - 如果为了复核旧 issue 切到了某个 tag/commit，就使用那个版本解析后的 SHA
- **禁止**使用本地路径加行号（如 `src/platform/weibo.py:127`）
- **禁止**使用不带行号的模糊引用（如"参考 send.py 中的发送逻辑"）

### 依赖组件的代码查阅

如果问题指向 NoneBot2 框架或上游依赖，遵循同样原则：

- NoneBot2：[https://github.com/nonebot/nonebot2](https://github.com/nonebot/nonebot2)
- nonebot-plugin-saa：[https://github.com/nonebot/plugin-saa](https://github.com/nonebot/plugin-saa)
- nonebot-plugin-apscheduler、nonebot-plugin-datastore 等

引用时同样使用远端 GitHub blob 链接，并标注对应 commit SHA。

### 常见错误模式（避免）

| ❌ 错误做法                                      | ✅ 正确做法                                      |
| ----------------------------------------------- | ----------------------------------------------- |
| 看到 issue 描述后直接猜测"可能是 xxx 模块的问题" | 先用日志证据确认错误发生在哪个模块               |
| 引用代码时写"参考 send.py 第 120 行"              | 给出完整的 GitHub blob 链接                      |
| 只看一个模块的代码就下结论                       | 追溯完整调用链，验证每层的输入输出               |
| 用当前分支代码分析旧 issue                       | 确认 issue 当时的版本，使用对应 commit 的代码     |
| 跳跃式归因："可能是代理配置问题"（未验证）        | 逐层排除：先确认请求是否发出 → 确认响应内容 → 定位 |

## Localized Copy

- Bison 项目主要是中文用户，用户可见文案包括“添加订阅”“查询订阅”“删除订阅”等内置命令响应，以及各平台的推送消息格式。
- 总结任务、入口、设置项、按钮、错误提示、日志前缀等用户可见文案时，先在仓库里主动搜索翻译 / 本地化文件。
- 优先搜索这些常见目录、文件名和关键词：
  - `nonebot_bison/` 目录下的 Python 文件中的中文字符串
  - `admin-frontend/` 中的中文界面文案
- 再从实际代码调用反查：
  - `__usage__` 变量（定义在 `__init__.py`）
  - 命令处理器中的返回消息字符串
  - 各平台格式化消息的模板
- 查找顺序建议：
  - 先从 issue 中的报错日志、截图里的 UI 文案提取关键词
  - 再在代码中搜索对应字符串
  - 如果配置或日志里带有用户自定义名称（订阅 ID、自定义平台名），输出时优先保留用户自定义名称
  - 如果仓库里确实找不到对应文案，要明确说明“未找到对应文案定义”，再退回原始 key、英文字符串或内部 ID

## Linking Code Evidence

- 如果要指向具体代码行，不要写本地路径加行号，也不要写绝对路径。
- 统一给出对应仓库的远端 GitHub `blob` 行号链接，用尖括号包裹。
- 链接格式：
  - `https://github.com/MountainDash/nonebot-bison/blob/<commit>/<path>#L14-L20`
- `<commit>` 必须是本次分析实际依据的代码版本：
  - 默认使用当前检出的 `HEAD`（主分支 main）
  - 如果为了复核旧 issue 切到了某个 tag / commit，就使用那个版本解析后的 SHA
- 如果引用的是 NoneBot2 或上游依赖，使用对应仓库的链接：
  - NoneBot2：`https://github.com/nonebot/nonebot2/blob/<commit>/<path>#L...`
  - nonebot-plugin-saa：`https://github.com/nonebot/plugin-saa/blob/<commit>/<path>#L...`
- 如果引用的是文档、配置样例或资源定义，也尽量给对应远端链接，而不是本地路径。

## Output Format

最终回答用这个结构：

```markdown
## Issue 概要

- issue：`#1234`
- Bison 版本 / NoneBot 版本 / Python 版本 / 部署方式：
- 平台 / 订阅目标：
- 关键配置项：重点关注 `bison_use_browser`、`bison_proxy`、`bison_use_queue`、`bison_resend_times`、`COMMAND_START` 等
- 关键提示 / 报错文案：
- 用户现象：

## 附件概览

- 实际可读文件：
- 缺失或未上传的证据：

## 关键证据

<details><summary>点击此处展开</summary>

- issue 正文 / 评论：
- Bison / NoneBot 日志：
- 平台爬取日志：
- 调度器日志：
- 推送队列日志：
- 配置快照：
- 现场图 / QQ 客户端截图：
- 代码依据：如需指向具体实现，直接附远端 GitHub 行号链接

</details>

## 根因判断

- 直接结论：
- 证据链：
- 当前主线是否可能已修复：

## 修复方案

1. 代码 / 配置 / 环境层修复
2. 需要补充的测试、日志或截图
3. 如问题属于不支持场景或平台风控，应如何调整预期或改进提示

## 给用户的建议

- 用户现在可以直接尝试的动作（检查配置、更新版本、更换部署方式、检查 Cookie）
- 是否建议升级 Bison 版本 / NoneBot 版本 / Python 版本
- 是否有临时绕过方案（关闭某些配置、切换平台、使用代理）
- 是否参考官方文档中的已知 [FAQ](https://nonebot-bison.netlify.app/usage/)

## 给修复 AI 的建议（可复制）

<details><summary>点击此处展开</summary>

~~~text
现象：
[一句话描述用户可见的问题]

关键证据：
[粘贴原始日志、堆栈、监控截图中的关键文本]

可能相关线索（待验证）：
[根据日志/现象推测的可能方向，不保证准确，供参考]
~~~

</details>

## 置信度

- 高 / 中 / 低
- 还缺什么证据
```

## Reminders

- 不要只看一个日志文件下结论。
- 不要把 issue 评论、机器人提示或维护者判断当成唯一证据。
- 不要把当前分支代码直接当成 issue 当时的真实环境。
- 日志和截图冲突时，优先解释冲突，再决定更可信的证据链。
- 如果问题本身没有在当前日志中复现，要明确写“证据未复现”，不要硬凑结论。
- 如果 issue 版本较旧，要明确区分“当时的根因”和“当前主线是否已修复”。
- 如果回答里出现命令名（如“添加订阅”）、设置项名（`bison_use_browser`）、按钮名，优先先在代码中确认对应文案和配置项。
- 如果回答里引用了具体代码行，直接给远端 GitHub `blob` 行号链接，用尖括号包裹，不要给本地路径加行号。
- 如果证据表明问题已在新版本修复，明确建议升级；如果怀疑安装包、资源文件或配置损坏，明确建议重建；如果判断为真实代码缺陷且暂无 workaround，明确建议等待修复。
- 特别关注 Bison 已知的常见问题模式：Python 版本兼容、httpx 版本、命令前缀配置、微博风控、playwright 浏览器、数据库迁移、代理配置。
