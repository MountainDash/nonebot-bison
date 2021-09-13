<div align="center">
<h1>hk-reporter </br>通用订阅推送插件</h1>



[![pypi](https://badgen.net/pypi/v/nonebot-hk-reporter)](https://pypi.org/project/nonebot-hk-reporter/)
[![felinae98](https://circleci.com/gh/felinae98/nonebot-hk-reporter.svg?style=shield)](https://circleci.com/gh/felinae98/nonebot-hk-reporter)
[![qq group](https://img.shields.io/badge/QQ%E7%BE%A4-868610060-orange )](https://qm.qq.com/cgi-bin/qm/qr?k=pXYMGB_e8b6so3QTqgeV6lkKDtEeYE4f&jump_from=webapi)

[文档](https://nonebot-hk-reporter.vercel.app)|[开发文档](https://nonebot-hk-reporter.vercel.app/dev)
</div>

## 简介
一款自动爬取各种站点，社交平台更新动态，并将信息推送到QQ的机器人。基于 [`NoneBot2`](https://github.com/nonebot/nonebot2 ) 开发（诞生于明日方舟的蹲饼活动）


支持的平台：
* 微博
* B站
* RSS
* 明日方舟
  * 塞壬唱片新闻
  * 游戏内公告
  * 版本更新等通知
* 网易云音乐


## 功能
* 定时爬取指定网站
* 通过图片发送文本，防止风控
* 使用队列限制发送频率

## 使用方法
参考[文档](https://nonebot-hk-reporter.vercel.app/usage/#%E4%BD%BF%E7%94%A8)

## FAQ
1. 报错`TypeError: 'type' object is not subscriptable`  
    本项目使用了Python 3.9的语法，请将Python版本升级到3.9及以上，推荐使用docker部署
2. bot不理我  
    请确认自己是群主或者管理员，并且检查`COMMAND_START`环境变量是否设为`[""]`
3. 微博漏订阅了
    微博更新了新的风控措施，某些含有某些关键词的微博会获取不到。

## 参与开发
欢迎各种PR，参与开发本插件很简单，只需要对相应平台完成几个接口的编写就行。你只需要一点简单的爬虫知识就行。

如果对整体框架有任何意见或者建议，欢迎issue。

## 鸣谢
* [`go-cqhttp`](https://github.com/Mrs4s/go-cqhttp)：简单又完善的 cqhttp 实现
* [`NoneBot2`](https://github.com/nonebot/nonebot2)：超好用的开发框架
* [`HarukaBot`](https://github.com/SK-415/HarukaBot/): 借鉴了大体的实现思路
* [`rsshub`](https://github.com/DIYgod/RSSHub)：提供了大量的api

## License
MIT

