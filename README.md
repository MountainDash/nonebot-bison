<div align="center">
<h1>Bison </br>通用订阅推送插件</h1>

[![pypi](https://badgen.net/pypi/v/nonebot-bison)](https://pypi.org/project/nonebot-bison/)
[![license](https://img.shields.io/github/license/felinae98/nonebot-bison)](https://github.com/felinae98/nonebot-bison/blob/main/LICENSE)
[![felinae98](https://circleci.com/gh/felinae98/nonebot-bison.svg?style=shield)](https://circleci.com/gh/felinae98/nonebot-bison)
[![docker](https://img.shields.io/docker/image-size/felinae98/nonebot-bison)](https://hub.docker.com/r/felinae98/nonebot-bison)
[![codecov](https://codecov.io/gh/felinae98/nonebot-bison/branch/main/graph/badge.svg?token=QCFIODJOOA)](https://codecov.io/gh/felinae98/nonebot-bison)
[![qq group](https://img.shields.io/badge/QQ%E7%BE%A4-868610060-orange)](https://qm.qq.com/cgi-bin/qm/qr?k=pXYMGB_e8b6so3QTqgeV6lkKDtEeYE4f&jump_from=webapi)

[文档](https://nonebot-bison.vercel.app)|[开发文档](https://nonebot-bison.vercel.app/dev)

</div>

## 简介

一款自动爬取各种站点，社交平台更新动态，并将信息推送到 QQ 的机器人。
基于 [`NoneBot2`](https://github.com/nonebot/nonebot2) 开发（诞生于明日方舟的蹲饼活动）

<details>
<summary>本项目原名原名nonebot-hk-reporter</summary>

寓意本 Bot 要做全世界跑的最快的搬运机器人，后因名字过于暴力改名

</details>
本项目名称来源于明日方舟角色拜松——一名龙门的信使，曾经骑自行车追上骑摩托车的德克萨斯

支持的平台：

- 微博
- Bilibili
- RSS
- 明日方舟
  - 塞壬唱片新闻
  - 游戏内公告
  - 版本更新等通知
- 网易云音乐
  - 歌手发布新专辑
  - 电台更新

## 功能

- 定时爬取指定网站
- 通过图片发送文本，防止风控
- 使用队列限制发送频率
- 使用网页后台管理 Bot 订阅

## 使用方法

**!!注意，如果要使用后台管理功能请使用 pypi 版本或者 docker 版本，如果直接 clone 源代码
需要按下面方式进行 build**

```bash
cd ./admin-frontend
yarn && yarn build
```

可以使用 Docker，docker-compose，作为插件安装在 nonebot 中，或者直接运行  
参考[文档](https://nonebot-bison.vercel.app/usage/#%E4%BD%BF%E7%94%A8)

## FAQ

1. 报错`TypeError: 'type' object is not subscriptable`  
   本项目使用了 Python 3.9 的语法，请将 Python 版本升级到 3.9 及以上，推荐使用 docker 部署
2. bot 不理我  
   请确认自己是群主或者管理员，并且检查`COMMAND_START`环境变量是否设为`[""]`
3. 微博漏订阅了
   微博更新了新的风控措施，某些含有某些关键词的微博会获取不到。

## 参与开发

欢迎各种 PR，参与开发本插件很简单，只需要对相应平台完成几个接口的编写就行。你只需要一点简单的爬虫知识就行。

如果对整体框架有任何意见或者建议，欢迎 issue。

## 鸣谢

- [`go-cqhttp`](https://github.com/Mrs4s/go-cqhttp)：简单又完善的 cqhttp 实现
- [`NoneBot2`](https://github.com/nonebot/nonebot2)：超好用的开发框架
- [`HarukaBot`](https://github.com/SK-415/HarukaBot/): 借鉴了大体的实现思路
- [`rsshub`](https://github.com/DIYgod/RSSHub)：提供了大量的 api

## License

MIT
