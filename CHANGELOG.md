# Change Log

## 最近更新

### Bug 修复

- 修复“订阅帐号可以被修改”的bug, 实际上不可以修改 [@felinae98](https://github.com/felinae98) ([#169](https://github.com/felinae98/nonebot-bison/pull/169))

## v0.6.3

### 新功能

- 适配 python3.11 [@felinae98](https://github.com/felinae98) ([#133](https://github.com/felinae98/nonebot-bison/pull/133))
- 添加记录 api 错误发生时 http 请求的方法 [@felinae98](https://github.com/felinae98) ([#152](https://github.com/felinae98/nonebot-bison/pull/152))

### Bug 修复

- 修复后台无法删除 RSS 订阅的问题 [@felinae98](https://github.com/felinae98) ([#154](https://github.com/felinae98/nonebot-bison/pull/154))
- fix(bilibili-live): 修正一些错误的api [@AzideCupric](https://github.com/AzideCupric) ([#151](https://github.com/felinae98/nonebot-bison/pull/151))

## v0.6.2

### 新功能

- 更换哔哩哔哩直播使用的api，添加直播间标题修改时推送直播间的功能 [@AzideCupric](https://github.com/AzideCupric) ([#128](https://github.com/felinae98/nonebot-bison/pull/128))
- 前端适配移动端设备 [@felinae98](https://github.com/felinae98) ([#124](https://github.com/felinae98/nonebot-bison/pull/124))
- 由 scheduler 提供 http client [@felinae98](https://github.com/felinae98) ([#126](https://github.com/felinae98/nonebot-bison/pull/126))
- 调整调度器 api [@felinae98](https://github.com/felinae98) ([#125](https://github.com/felinae98/nonebot-bison/pull/125))

### Bug 修复

- :bug: download weibo pics in `parse` [@felinae98](https://github.com/felinae98) ([#147](https://github.com/felinae98/nonebot-bison/pull/147))
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

- feat (issue #67 ):添加屏蔽特定tag的功能 [@AzideCupric](https://github.com/AzideCupric) ([#101](https://github.com/felinae98/nonebot-bison/pull/101))
- feat: 临时解决 bilibili 的反爬机制 [@felinae98](https://github.com/felinae98) ([#110](https://github.com/felinae98/nonebot-bison/pull/110))
- 在StatusChange中提供了如果api返回错误不更新status的方法 [@felinae98](https://github.com/felinae98) ([#96](https://github.com/felinae98/nonebot-bison/pull/96))
- 添加 CustomPost [@felinae98](https://github.com/felinae98) ([#81](https://github.com/felinae98/nonebot-bison/pull/81))

### Bug 修复

- fix: 修复 bilibili-live 中获取状态错误后产生的错误行为 [@felinae98](https://github.com/felinae98) ([#111](https://github.com/felinae98/nonebot-bison/pull/111))

## v0.5.4

### 新功能

- 增加rss对media_content中图片的支持 [@felinae98](https://github.com/felinae98) ([#87](https://github.com/felinae98/nonebot-bison/pull/87))
- 添加新的订阅平台mcbbsnews [@AzideCupric](https://github.com/AzideCupric) ([#84](https://github.com/felinae98/nonebot-bison/pull/84))
- 添加bilibili开播提醒 [@Sichongzou](https://github.com/Sichongzou) ([#60](https://github.com/felinae98/nonebot-bison/pull/60))
- 添加User-Agent配置 [@felinae98](https://github.com/felinae98) ([#78](https://github.com/felinae98/nonebot-bison/pull/78))
- 增加代理设置 [@felinae98](https://github.com/felinae98) ([#71](https://github.com/felinae98/nonebot-bison/pull/71))
- 增加Parse Target功能 [@felinae98](https://github.com/felinae98) ([#72](https://github.com/felinae98/nonebot-bison/pull/72))

### Bug 修复

- 捕获 JSONDecodeError [@felinae98](https://github.com/felinae98) ([#82](https://github.com/felinae98/nonebot-bison/pull/82))
- 捕获SSL异常 [@felinae98](https://github.com/felinae98) ([#75](https://github.com/felinae98/nonebot-bison/pull/75))

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
