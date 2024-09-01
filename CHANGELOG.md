# Change Log

## 最近更新

### Bug 修复

- 无权限用户尝试添加订阅时返回提示信息 [@suyiiyii](https://github.com/suyiiyii) ([#617](https://github.com/MountainDash/nonebot-bison/pull/617))
- B站请求策略阶段行为优化 [@AzideCupric](https://github.com/AzideCupric) ([#610](https://github.com/MountainDash/nonebot-bison/pull/610))
- Rss 不再删除格式化字符 [@suyiiyii](https://github.com/suyiiyii) ([#615](https://github.com/MountainDash/nonebot-bison/pull/615))
- forbid adding platform that needs browser in no-browser env [@felinae98](https://github.com/felinae98) ([#609](https://github.com/MountainDash/nonebot-bison/pull/609))
- 修正项目的代码警告 [@AzideCupric](https://github.com/AzideCupric) ([#614](https://github.com/MountainDash/nonebot-bison/pull/614))
- 修复 anonymous_site() 无法正确工作的问题 [@felinae98](https://github.com/felinae98) ([#606](https://github.com/MountainDash/nonebot-bison/pull/606))

## v0.9.3

### 新功能

- 适配小刻食堂平台 [@AzideCupric](https://github.com/AzideCupric) ([#379](https://github.com/MountainDash/nonebot-bison/pull/379))
- refactor client getting logic in platform config [@felinae98](https://github.com/felinae98) ([#544](https://github.com/MountainDash/nonebot-bison/pull/544))
- ParseTargetException可以携带prompt参数 [@AzideCupric](https://github.com/AzideCupric) ([#479](https://github.com/MountainDash/nonebot-bison/pull/479))
- 为 scheduler config 添加 require_browser 属性 [@felinae98](https://github.com/felinae98) ([#542](https://github.com/MountainDash/nonebot-bison/pull/542))
- 将 bison_theme_use_browser 更名为 bison_use_browser  [@felinae98](https://github.com/felinae98) ([#540](https://github.com/MountainDash/nonebot-bison/pull/540))

### Bug 修复

- Bilibili调度新增回避策略 [@AzideCupric](https://github.com/AzideCupric) ([#573](https://github.com/MountainDash/nonebot-bison/pull/573))
- 实现 `Post.content` 相关扩展协议 [@GuGuMur](https://github.com/GuGuMur) ([#553](https://github.com/MountainDash/nonebot-bison/pull/553))
- fix config alias err [@felinae98](https://github.com/felinae98) ([#580](https://github.com/MountainDash/nonebot-bison/pull/580))
- 插入新的Schedulable时应传入use_batch参数 [@AzideCupric](https://github.com/AzideCupric) ([#594](https://github.com/MountainDash/nonebot-bison/pull/594))
- 查询订阅时提示不存在的平台 [@suyiiyii](https://github.com/suyiiyii) ([#584](https://github.com/MountainDash/nonebot-bison/pull/584))
- B站蹲饼修复 [@AzideCupric](https://github.com/AzideCupric) ([#525](https://github.com/MountainDash/nonebot-bison/pull/525))
- 🐛 补充主题渲染时遗漏的转发推文中的图片 [@AzideCupric](https://github.com/AzideCupric) ([#554](https://github.com/MountainDash/nonebot-bison/pull/554))

### 文档

- 📝 更新 README [@KomoriDev](https://github.com/KomoriDev) ([#583](https://github.com/MountainDash/nonebot-bison/pull/583))
- 💄 更新 favicon [@KomoriDev](https://github.com/KomoriDev) ([#585](https://github.com/MountainDash/nonebot-bison/pull/585))
- 修复前端开发部分文档的问题 [@changsun20](https://github.com/changsun20) ([#552](https://github.com/MountainDash/nonebot-bison/pull/552))

## v0.9.2

### 新功能

- 更详细的微博 [@LambdaYH](https://github.com/LambdaYH) ([#504](https://github.com/MountainDash/nonebot-bison/pull/504))
- 独立 bilibili-live 的 SchedConf [@AzideCupric](https://github.com/AzideCupric) ([#473](https://github.com/MountainDash/nonebot-bison/pull/473))
- 使用 yarl.URL 拼接 outer_url [@AzideCupric](https://github.com/AzideCupric) ([#496](https://github.com/MountainDash/nonebot-bison/pull/496))

### Bug 修复

- 为B站动态API建立model，转发动态放入repost字段 [@AzideCupric](https://github.com/AzideCupric) ([#507](https://github.com/MountainDash/nonebot-bison/pull/507))
- Arknights 公告分类 过滤不可访问的 URL [@AzideCupric](https://github.com/AzideCupric) ([#495](https://github.com/MountainDash/nonebot-bison/pull/495))
- 为各主题补全 repost 的渲染 [@AzideCupric](https://github.com/AzideCupric) ([#505](https://github.com/MountainDash/nonebot-bison/pull/505))

### 文档

- 文档迁移到 vuepress hope 主题 [@dependabot](https://github.com/dependabot) ([#490](https://github.com/MountainDash/nonebot-bison/pull/490))

## v0.9.1

### Bug 修复

- 修复后台管理界面无法获取群信息的问题 [@he0119](https://github.com/he0119) ([#486](https://github.com/MountainDash/nonebot-bison/pull/486))

### 文档

- 更新文档以适配 pyd2 的用法 [@felinae98](https://github.com/felinae98) ([#485](https://github.com/MountainDash/nonebot-bison/pull/485))

## v0.9.0

### 破坏性变更

- 移除 mcbbsnews platform [@AzideCupric](https://github.com/AzideCupric) ([#477](https://github.com/MountainDash/nonebot-bison/pull/477))

### 新功能

- 适配 Pydantic V2 [@he0119](https://github.com/he0119) ([#484](https://github.com/MountainDash/nonebot-bison/pull/484))
- Theme 功能添加 [@AzideCupric](https://github.com/AzideCupric) ([#400](https://github.com/MountainDash/nonebot-bison/pull/400))
- 调整 Dockerfile 以及 Bison 的运行方式 [@AzideCupric](https://github.com/AzideCupric) ([#447](https://github.com/MountainDash/nonebot-bison/pull/447))
- BISON_OUTER_URL 配置改进 [@SherkeyXD](https://github.com/SherkeyXD) ([#405](https://github.com/MountainDash/nonebot-bison/pull/405))

### Bug 修复

- 修复 Arknights Platform 的时间判断和标题显示 [@AzideCupric](https://github.com/AzideCupric) ([#481](https://github.com/MountainDash/nonebot-bison/pull/481))

## v0.8.2

### 新功能

- 提供批量 api 接口 [@felinae98](https://github.com/felinae98) ([#290](https://github.com/MountainDash/nonebot-bison/pull/290))
- 适配明日方舟新版公告栏API [@GuGuMur](https://github.com/GuGuMur) ([#305](https://github.com/MountainDash/nonebot-bison/pull/305))

### Bug 修复

- 处理topic_info字段缺失的问题 [@AzideCupric](https://github.com/AzideCupric) ([#354](https://github.com/MountainDash/nonebot-bison/pull/354))
- 修复无法正常判断 FastAPI 是否存在的问题 [@KomoriDev](https://github.com/KomoriDev) ([#350](https://github.com/MountainDash/nonebot-bison/pull/350))
- 适配 SAA 0.3 [@he0119](https://github.com/he0119) ([#349](https://github.com/MountainDash/nonebot-bison/pull/349))
- 修复文本相似度函数除0报错 [@UKMeng](https://github.com/UKMeng) ([#302](https://github.com/MountainDash/nonebot-bison/pull/302))
- 修正明日方舟游戏信息的模板与图片渲染 [@GuGuMur](https://github.com/GuGuMur) ([#306](https://github.com/MountainDash/nonebot-bison/pull/306))

## v0.8.0

### 破坏性变更

- 使用 saa 代替所有发送 [@felinae98](https://github.com/felinae98) ([#219](https://github.com/felinae98/nonebot-bison/pull/219))

### 新功能

- 优化 RSS 推送的内容 [@UKMeng](https://github.com/UKMeng) ([#259](https://github.com/felinae98/nonebot-bison/pull/259))
- 支持 nb2.0.0 并更新 metadata [@AzideCupric](https://github.com/AzideCupric) ([#274](https://github.com/felinae98/nonebot-bison/pull/274))
- 移除交互式管理中的 ob11 [@felinae98](https://github.com/felinae98) ([#268](https://github.com/felinae98/nonebot-bison/pull/268))

### Bug 修复

- 修复 bilibili 推送的一些格式错误 [@UKMeng](https://github.com/UKMeng) ([#263](https://github.com/felinae98/nonebot-bison/pull/263))
- 修复B站订阅没有动态或者B站直播订阅没有直播间的用户时轮询报错的问题 [@AzideCupric](https://github.com/AzideCupric) ([#273](https://github.com/felinae98/nonebot-bison/pull/273))
- 在 Postgresql 下，user_target 字段使用 jsonb 代替 json [@LambdaYH](https://github.com/LambdaYH) ([#271](https://github.com/felinae98/nonebot-bison/pull/271))

## v0.7.3

### Bug 修复

- 更换获取B站用户名的 api [@UKMeng](https://github.com/UKMeng) ([#261](https://github.com/felinae98/nonebot-bison/pull/261))
- 修复 ff14 公告链接 [@LambdaYH](https://github.com/LambdaYH) ([#257](https://github.com/felinae98/nonebot-bison/pull/257))

## v0.7.2

### 新功能

- 开播提醒推送的图片改为使用直播间封面 [@AzideCupric](https://github.com/AzideCupric) ([#249](https://github.com/felinae98/nonebot-bison/pull/249))
- 可以关闭日志中的网络报错 [@felinae98](https://github.com/felinae98) ([#227](https://github.com/felinae98/nonebot-bison/pull/227))
- 调整 bilibili 网络报错 [@felinae98](https://github.com/felinae98) ([#223](https://github.com/felinae98/nonebot-bison/pull/223))
- 调整 scheduler log level [@felinae98](https://github.com/felinae98) ([#222](https://github.com/felinae98/nonebot-bison/pull/222))

### Bug 修复

- 修复订阅 RSS 时，输入链接被转义的问题 [@LambdaYH](https://github.com/LambdaYH) ([#238](https://github.com/felinae98/nonebot-bison/pull/238))
- 解决添加Blibili订阅时，获取用户名时的报错 [@UKMeng](https://github.com/UKMeng) ([#248](https://github.com/felinae98/nonebot-bison/pull/248))
- 在未安装 fastapi 时不加载 webui [@felinae98](https://github.com/felinae98) ([#221](https://github.com/felinae98/nonebot-bison/pull/221))

### 文档

- 拆分部署与使用，添加简单使用章节 [@AzideCupric](https://github.com/AzideCupric) ([#252](https://github.com/felinae98/nonebot-bison/pull/252))
- 在文档和log中强调bison启动时和配置里的网站不能直接访问，并优化部分文档的表达 [@AzideCupric](https://github.com/AzideCupric) ([#235](https://github.com/felinae98/nonebot-bison/pull/235))
- 修复文档中指向的nonebot2文档url [@SherkeyXD](https://github.com/SherkeyXD) ([#231](https://github.com/felinae98/nonebot-bison/pull/231))

## v0.7.1

### 新功能

- 通过 nb-cli 实现数据库一键导入导出 [@AzideCupric](https://github.com/AzideCupric) ([#210](https://github.com/felinae98/nonebot-bison/pull/210))
- 调整群内订阅命令回复文本的位置，为`后台管理`命令添加别名`管理后台` [@AzideCupric](https://github.com/AzideCupric) ([#198](https://github.com/felinae98/nonebot-bison/pull/198))
- 解决使用队列发送时产生大量日志的问题 [@felinae98](https://github.com/felinae98) ([#185](https://github.com/felinae98/nonebot-bison/pull/185))

### Bug 修复

- 修复使用 PostgreSQL 时迁移脚本的报错 [@he0119](https://github.com/he0119) ([#200](https://github.com/felinae98/nonebot-bison/pull/200))

### 杂项

- 又切换回 sqlalchemy，但是 2.0 [@felinae98](https://github.com/felinae98) ([#206](https://github.com/felinae98/nonebot-bison/pull/206))
- 修改 nonebot_bison 项目结构 [@he0119](https://github.com/he0119) ([#211](https://github.com/felinae98/nonebot-bison/pull/211))

## v0.7.0

### 破坏性变更

- 适配最新的 DataStore 插件，并切换模型为 SQLModel [@he0119](https://github.com/he0119) ([#178](https://github.com/felinae98/nonebot-bison/pull/178))

### 新功能

- 适配 Nonebot 插件元数据 [@he0119](https://github.com/he0119) ([#184](https://github.com/felinae98/nonebot-bison/pull/184))
- 支持连接多个机器人 [@he0119](https://github.com/he0119) ([#179](https://github.com/felinae98/nonebot-bison/pull/179))

### Bug 修复

- 修复“订阅帐号可以被修改”的 bug , 实际上不可以修改 [@felinae98](https://github.com/felinae98) ([#169](https://github.com/felinae98/nonebot-bison/pull/169))

### 杂项

添加打上 test-render 的标签后进行带 render 标记测试的功能 [@AzideCupric](https://github.com/AzideCupric) ([#176](https://github.com/felinae98/nonebot-bison/pull/176))

## v0.6.3

### 新功能

- 适配 python3.11 [@felinae98](https://github.com/felinae98) ([#133](https://github.com/felinae98/nonebot-bison/pull/133))
- 添加记录 api 错误发生时 http 请求的方法 [@felinae98](https://github.com/felinae98) ([#152](https://github.com/felinae98/nonebot-bison/pull/152))

### Bug 修复

- 修复后台无法删除 RSS 订阅的问题 [@felinae98](https://github.com/felinae98) ([#154](https://github.com/felinae98/nonebot-bison/pull/154))
- 修正一些错误的api [@AzideCupric](https://github.com/AzideCupric) ([#151](https://github.com/felinae98/nonebot-bison/pull/151))

## v0.6.2

### 新功能

- 更换哔哩哔哩直播使用的api，添加直播间标题修改时推送直播间的功能 [@AzideCupric](https://github.com/AzideCupric) ([#128](https://github.com/felinae98/nonebot-bison/pull/128))
- 前端适配移动端设备 [@felinae98](https://github.com/felinae98) ([#124](https://github.com/felinae98/nonebot-bison/pull/124))
- 由 scheduler 提供 http client [@felinae98](https://github.com/felinae98) ([#126](https://github.com/felinae98/nonebot-bison/pull/126))
- 调整调度器 api [@felinae98](https://github.com/felinae98) ([#125](https://github.com/felinae98/nonebot-bison/pull/125))

### Bug 修复

- download weibo pics in `parse` [@felinae98](https://github.com/felinae98) ([#147](https://github.com/felinae98/nonebot-bison/pull/147))
- 修复前端两次点击编辑不能正确显示的问题 [@felinae98](https://github.com/felinae98) ([#131](https://github.com/felinae98/nonebot-bison/pull/131))

## v0.6.1

### Bug 修复

- 修复前端 title [@felinae98](https://github.com/felinae98) ([#121](https://github.com/felinae98/nonebot-bison/pull/121))
- 使用新的文件来标志 legacy db 已弃用 [@felinae98](https://github.com/felinae98) ([#120](https://github.com/felinae98/nonebot-bison/pull/120))
- 修复添加按钮没反应 [@felinae98](https://github.com/felinae98) ([#119](https://github.com/felinae98/nonebot-bison/pull/119))
- 修复前端面包屑错误 [@felinae98](https://github.com/felinae98) ([#118](https://github.com/felinae98/nonebot-bison/pull/118))

## v0.6.0

### 破坏性更新

- 弃用 tinydb，使用 sqlite 作为数据库（届时将自动迁移数据库，可能存在失败的情况）
- 放弃对 Python3.9 的支持
- 重写前端

### 新功能

- 使用了新的调度器

### Bug 修复

- 处理「添加重复订阅」异常 [@felinae98](https://github.com/felinae98) ([#115](https://github.com/felinae98/nonebot-bison/pull/115))

## v0.5.5

### 新功能

- 添加屏蔽特定 tag 的功能 [@AzideCupric](https://github.com/AzideCupric) ([#101](https://github.com/felinae98/nonebot-bison/pull/101))
- 临时解决 bilibili 的反爬机制 [@felinae98](https://github.com/felinae98) ([#110](https://github.com/felinae98/nonebot-bison/pull/110))
- 在 StatusChange 中提供了如果 api 返回错误不更新 status 的方法 [@felinae98](https://github.com/felinae98) ([#96](https://github.com/felinae98/nonebot-bison/pull/96))
- 添加 CustomPost [@felinae98](https://github.com/felinae98) ([#81](https://github.com/felinae98/nonebot-bison/pull/81))

### Bug 修复

- 修复 bilibili-live 中获取状态错误后产生的错误行为 [@felinae98](https://github.com/felinae98) ([#111](https://github.com/felinae98/nonebot-bison/pull/111))

## v0.5.4

### 新功能

- 增加 rss 对 media_content 中图片的支持 [@felinae98](https://github.com/felinae98) ([#87](https://github.com/felinae98/nonebot-bison/pull/87))
- 添加新的订阅平台 mcbbsnews [@AzideCupric](https://github.com/AzideCupric) ([#84](https://github.com/felinae98/nonebot-bison/pull/84))
- 添加 bilibili 开播提醒 [@Sichongzou](https://github.com/Sichongzou) ([#60](https://github.com/felinae98/nonebot-bison/pull/60))
- 添加 User-Agent 配置 [@felinae98](https://github.com/felinae98) ([#78](https://github.com/felinae98/nonebot-bison/pull/78))
- 增加代理设置 [@felinae98](https://github.com/felinae98) ([#71](https://github.com/felinae98/nonebot-bison/pull/71))
- 增加 Parse Target 功能 [@felinae98](https://github.com/felinae98) ([#72](https://github.com/felinae98/nonebot-bison/pull/72))

### Bug 修复

- 捕获 JSONDecodeError [@felinae98](https://github.com/felinae98) ([#82](https://github.com/felinae98/nonebot-bison/pull/82))
- 捕获 SSL 异常 [@felinae98](https://github.com/felinae98) ([#75](https://github.com/felinae98/nonebot-bison/pull/75))

### 文档

- 完善开发文档 [@AzideCupric](https://github.com/AzideCupric) ([#80](https://github.com/felinae98/nonebot-bison/pull/80))

## v0.5.3

- on_command 设置 block=True (#63) @MeetWq
- 修复 issue#51 存在的问题并修改相应的单元测试 (#52) @AzideCupric
- 增添关于添加订阅命令中中止订阅的相关文档 (#45) @AzideCupric

### Bug 修复

- 修复#66 (#69) @felinae98

## [0.5.2]

- 修复了微博获取全文时接口失效的问题
- 修复了 bilibili 空列表时的报错

## [0.5.1]

- 使用了新的在私聊中进行群管理的方式：从`管理-*`替换为`群管理`命令
- 默认关闭自动重发功能
- 添加了 [推送消息合并转发功能](https://nonebot-bison.vercel.app/usage/#%E9%85%8D%E7%BD%AE)
- 添加了`添加订阅`命令事件的中途取消功能
- 优化了`添加订阅`命令的聊天处理逻辑

## [0.5.0]

- 添加了 FF14
- 去掉了自己维护的 playwright，转向[nonebot-plugin-htmlrender](https://github.com/kexue-z/nonebot-plugin-htmlrender)
- 支持了 nonebot 2.0.0beta

## [0.4.4]

- 又双叒叕重构了一下
- 修复了 Docker 中 Playwright 下载的浏览器版本不正确问题
- 加入了猴子补丁，使 Windows 里能运行 Playwright

## [0.4.3]

- 使用 playwright 替换 pypeteer（大概能修复渲染失败图片之后 CPU 跑满的问题）
- 增加了 help 插件`nonebot-plugin-help`
- 修复 playwright 漏内存的问题
- 增加过滤 nonebot 日志功能
- 前端可以刷新了（之前居然不可以）
- 在镜像里塞进了浏览器（导致镜像体积起飞）

## [0.4.2]

并没有做什么只是为了修复前端文件没有正确打包的问题开了个新的版本号
推上 pypi

## [0.4.1] - 2021-11-31

- 加入了管理后台

## [0.4.0] - 2021-11-18

- 项目更名为 nonebot-bison

## [0.3.3] - 2021-09-28

- 修复了微博获取全文时接口失效的问题
- 修复了 bilibili 空列表时的报错
- 修复拼图问题

## [0.3.2] - 2021-09-28

- 增加 NoTargetGroup
- 增加 1x3 拼图的支持
- 增加网易云

## [0.3.1] - 2021-07-10

- 修复不发送来源
- 发送 RSS 订阅的 title
- 修复浏览器渲染问题

## [0.3.0] - 2021-07-06

- 微博 tag 支持
- 修复 bug
- 增加微博超话和纯文字支持
- 更改浏览器配置
- 将“来源”移动到文末
- 使用组合来构建新的 platform，新增状态改变类型订阅

## [0.2.11] - 2021-06-17

- 增加了简单的单元测试
- 增加了管理员直接管理订阅的能力
