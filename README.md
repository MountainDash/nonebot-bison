<div align="center">
<h1>hk-reporter </br>通用订阅推送插件</h1>



[![pypi](https://badgen.net/pypi/v/nonebot-hk-reporter)](https://pypi.org/project/nonebot-hk-reporter/)
[![felinae98](https://circleci.com/gh/felinae98/nonebot-hk-reporter.svg?style=shield)](https://circleci.com/gh/felinae98/nonebot-hk-reporter)
[![qq group](https://img.shields.io/badge/QQ%E7%BE%A4-868610060-orange )](https://qm.qq.com/cgi-bin/qm/qr?k=pXYMGB_e8b6so3QTqgeV6lkKDtEeYE4f&jump_from=webapi)

</div>

## 简介
一款自动爬取各种站点，社交平台更新动态，并将信息推送到QQ的机器人。基于 [`NoneBot2`](https://github.com/nonebot/nonebot2 ) 开发（诞生于明日方舟的蹲饼活动）

支持的平台：
* 微博
    * 图片
    * 文字
    * 不支持视频
    * 不支持转发的内容
* Bilibili
    * 图片
    * 专栏
    * 文字
    * 视频链接
    * 不支持转发的内容
* RSS
    * 从description中提取图片
    * 文字

## 使用方法

### 使用以及部署
**!!本项目需要Python3.9及以上**  
本项目可作为单独插件使用，仅包含订阅相关功能（绝对simple和stupid），也可直接克隆项目进行使用（包含自动同意superuser，自动接受入群邀请等功能）  
作为插件使用请安装`nonebot-hk-reporter`包，并在`bot.py`中加载`nonebot_hk_reporter`插件；或直接克隆本项目进行使用  
配置与安装请参考[nonebot2文档](https://v2.nonebot.dev/)
<details>
<summary>Docker部署方法</summary>
   
Docker镜像地址为`felinae98/nonebot-hk-reporter`。例子：
```bash
docker run --name nonebot-hk-reporter --network <network name> -d -e 'SUPERUSERS=[<Your QQ>]' -v <config dir>:/data -e 'hk_reporter_config_path=/data' -e 'HK_REPORTER_USE_PIC=True' -e 'HK_REPORTER_USE_LOCAL=True' felinae98/nonebot-hk-reporter
```
go-cqhttp镜像可使用`felinae98/go-cqhttp-ffmpeg`（数据目录为`/data`），需要注意，两个容器需要在同一个network中。

并且docker版本中提供了自动同意SUPERUSER好友申请和自动同意SUPERUSER的入群邀请的功能。
</details>

### 配置变量
* `HK_REPORTER_CONFIG_PATH` (str) 配置文件保存目录，如果不设置，则为当前目录下的`data`文件夹
* `HK_REPORTER_USE_PIC` (bool) 以图片形式发送文字（推荐在帐号被风控时使用）
* ~~`HK_REPORTER_USE_LOCAL` (bool) 使用本地chromium（文字转图片时需要），否则第一次启动会下载chromium~~
* `HK_REPORTER_BROWSER` (str) 明日方舟游戏公告和以以图片形式发送文字需要浏览器支持，如果不设置会在使用到
    功能的时候自动下载Chromium（不推荐）
    * 使用本地安装的Chromiun: 设置为`local:<chromium path>`
    * 使用browserless提供的服务浏览器管理服务（推荐）:设置为`ws://********`

同时，建议配置`SUPERUSERS`环境变量便于机器人管理

### 命令
#### 在本群中进行配置
所有命令都需要@bot触发
* 添加订阅（仅管理员和群主和SUPERUSER）：`添加订阅`
* 查询订阅：`查询订阅`
* 删除订阅（仅管理员和群主和SUPERUSER）：`删除订阅`
#### 私聊机器人进行配置（需要SUPERUER权限）
* 添加订阅：`管理-添加订阅`
* 查询订阅：`管理-查询订阅`
* 删除订阅：`管理-删除订阅`

平台代码包含：Weibo，Bilibili，RSS
<details>
<summary>各平台uid</summary>

下面均以pc站点为例
* Weibo
    * 对于一般用户主页`https://weibo.com/u/6441489862?xxxxxxxxxxxxxxx`，`/u/`后面的数字即为uid
    * 对于有个性域名的用户如：`https://weibo.com/arknights`，需要点击左侧信息标签下“更多”，链接为`https://weibo.com/6279793937/about`，其中中间数字即为uid
* Bilibili
    * 主页链接一般为`https://space.bilibili.com/161775300?xxxxxxxxxx`，数字即为uid
* RSS
    * RSS链接即为uid
</details>

### 文字转图片
因为可能要发送长文本，所以bot很可能被风控，如有需要请开启以图片形式发送文字，本项目使用的文字转图片方法是Chromium（经典杀鸡用牛刀）。

如果确定要开启推荐自行安装Chromium，设置使用本地Chromium，并且保证服务器有比较大的内存。
## 功能
* 定时爬取指定网站
* 通过图片发送文本，防止风控
* 使用队列限制发送频率

# FAQ
1. 报错`TypeError: 'type' object is not subscriptable`  
    本项目使用了Python 3.9的语法，请将Python版本升级到3.9及以上，推荐使用docker部署
2. bot不理我  
    请确认自己是群主或者管理员，并且检查`COMMAND_START`环境变量是否设为`[""]`
3. 微博漏订阅了
    微博更新了新的风控措施，某些含有某些关键词的微博会获取不到。

## 鸣谢
* [`go-cqhttp`](https://github.com/Mrs4s/go-cqhttp)：简单又完善的 cqhttp 实现
* [`NoneBot2`](https://github.com/nonebot/nonebot2)：超好用的开发框架
* [`HarukaBot`](https://github.com/SK-415/HarukaBot/): 借鉴了大体的实现思路
* [`rsshub`](https://github.com/DIYgod/RSSHub)：提供了大量的api

## License
MIT

