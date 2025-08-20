<!-- markdownlint-disable first-line-heading -->
<div align="center">
  <a href="https://v2.nonebot.dev/store">
    <img src="https://nonebot-bison.netlify.app/logo.svg" width="200" alt="logo">
  </a>
</div>

<div align="center">

# Bison

<!-- markdownlint-disable no-emphasis-as-heading -->

_✨ 通用订阅推送插件 ✨_

<a href="https://raw.githubusercontent.com/MountainDash/nonebot-bison/main/LICENSE">
    <img src="https://img.shields.io/github/license/MountainDash/nonebot-bison" alt="license">
</a>
<a href="https://pypi.python.org/pypi/nonebot-bison">
    <img src="https://img.shields.io/pypi/v/nonebot-bison?logo=python&logoColor=edb641" alt="pypi">
</a>
<img src="https://img.shields.io/badge/python-3.10+-blue?logo=python&logoColor=edb641" alt="python">
<a href="https://github.com/astral-sh/ruff">
    <img src="https://img.shields.io/endpoint?url=https://raw.githubusercontent.com/charliermarsh/ruff/main/assets/badge/v2.json" alt="ruff">
</a>
<br />
<a href="https://codecov.io/gh/MountainDash/nonebot-bison">
    <img src="https://codecov.io/gh/MountainDash/nonebot-bison/branch/main/graph/badge.svg?token=QCFIODJOOA" alt="codecov"/>
</a>
<a href="https://github.com/MountainDash/nonebot-bison/actions/workflows/main.yml.yml">
    <img src="https://github.com/MountainDash/nonebot-bison/actions/workflows/main.yml/badge.svg?branch=main&event=push" alt="action"/>
</a>
<a href="https://results.pre-commit.ci/latest/github/MountainDash/nonebot-bison/main">
    <img src="https://results.pre-commit.ci/badge/github/MountainDash/nonebot-bison/main.svg" alt="pre-commit" />
</a>
<a href="https://github.com/MountainDash/nonebot-bison/actions/workflows/ruff.yml">
    <img src="https://github.com/MountainDash/nonebot-bison/actions/workflows/ruff.yml/badge.svg?branch=main&event=push" alt="ruff">
</a>

<br />
<a href="https://nonebot-bison.netlify.app/" target="__blank">
    <strong>📖 官方文档</strong>
  </a>
  &nbsp;&nbsp;|&nbsp;&nbsp;
  <a href="https://nonebot-bison.netlify.app/usage/easy-use.html" target="__blank">
    <strong>🚀 快速开始</strong>
  </a>
  &nbsp;&nbsp;|&nbsp;&nbsp;
  <a href="https://qm.qq.com/q/7DH4H3hbaw" target="__blank">
    <strong>💬 讨论交流</strong>
  </a>

</div>

## 简介

一款自动爬取各种站点，社交平台更新动态，并将信息推送到 QQ 的机器人。
基于 [`NoneBot2`](https://github.com/nonebot/nonebot2) 开发（诞生于明日方舟的蹲饼活动）

<details>
<summary>本项目原名 nonebot-hk-reporter</summary>

寓意本 Bot 要做全世界跑的最快的搬运机器人，后因名字过于暴力改名

</details>
本项目名称来源于明日方舟角色拜松——一名龙门的信使，曾经骑自行车追上骑摩托车的德克萨斯

支持的平台：

- 微博
- Bilibili
- Bilibili 直播
- RSS
- 明日方舟
- 网易云音乐
- FF14

## 功能

- [x] 定时爬取指定网站
- [x] 通过图片发送文本，防止风控
- [x] 使用队列限制发送频率
- [x] 使用网页后台管理 Bot 订阅
- [ ] 使用可以设置权重的调度器按时间调节不同账号的权重

## 使用方法

> [!warning]
> 如果要使用后台管理功能请使用 pypi 版本或者 docker 版本，如果直接 clone 源代码，需要按下面方式进行 build

```bash
cd ./admin-frontend
pnpm && pnpm run build
```

可以使用 Docker，docker-compose，作为插件安装在 NoneBot 中，或者直接运行

在群里 @Bot 或者直接私聊 Bot 发送 “添加订阅”，按照提示输入需要订阅的账号，就可以愉快接收消息了。

参考[文档](https://nonebot-bison.netlify.app/usage/#%E4%BD%BF%E7%94%A8)

## FAQ

1. 报错 `TypeError: 'type' object is not subscriptable`  
   本项目使用了 Python 3.10 的语法，请将 Python 版本升级到 3.10 及以上，推荐使用 docker 部署
2. bot 不理我  
   请确认自己是群主或者管理员，并且检查 `COMMAND_START` 环境变量是否设为 `[""]`
   或者按照 `COMMAND_START` 中的设置添加命令前缀，例：
   `COMMAND_START=["/"]` 则应发送 `/添加订阅`
3. 微博漏订阅了
   微博更新了新的风控措施，某些含有某些关键词的微博会获取不到。
4. 无法使用后台管理页面
   1. 确认自己正确配置了 NoneBot 的端口，如果在远程或容器外访问网页请确保 `HOST=0.0.0.0`
   2. 确认自己的云服务器的防火墙配置正确
   3. 确认自己使用了正确的方法安装插件

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
