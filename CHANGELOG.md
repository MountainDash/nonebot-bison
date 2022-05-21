# Change Log

## 最近更新

- Add GitHub Actions (#65) @he0119
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
