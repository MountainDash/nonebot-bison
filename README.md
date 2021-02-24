<div align="center">
<h1>hk-reporter </br>通用订阅推送插件</h1>
![https://badgen.net/github/license/felinae98/nonebot-hk-reporter]()
![https://badgen.net/pypi/v/nonebot-hk-reporter](https://pypi.org/project/nonebot-hk-reporter/)
</div>

## 简介
一款自动爬取各种站点，社交平台更新动态，并将信息推送到QQ的机器人。基于 [`NoneBot2`](https://github.com/nonebot/nonebot2 ) 开发（诞生于明日方舟的蹲饼活动）

支持的平台：
* 微博
    * 图片
    * 文字
    * 不支持视频
    * 不支持转发的内容
* bilibili
    * 图片
    * 专栏
    * 文字
    * 视频链接
    * 不支持转发的内容
* rss
    * 从description中提取图片
    * 文字

## 使用方法

### 使用以及部署
本项目可作为单独插件使用，仅包含订阅相关功能（绝对simple和stupid），也可直接克隆项目进行使用（包含自动同意superuser，自动接受入群邀请等功能）  
作为插件使用请安装`nonebot-hk-reporter`包，并在`bot.py`中加载`nonebot_hk_reporter`插件；或直接克隆本项目进行使用  
配置与安装请参考[nonebot2文档](https://v2.nonebot.dev/)
<details>
<summary>Docker部署方法</summary>
Docker镜像地址为`felinae98/nonebot-hk-reporter`对应main分支，`felinae98/nonebot-hk-reporter:arknights`对应arknights分支。例子：
```bash
docker run --name nonebot-hk-reporter --network <network name> -d -e 'SUPERUSERS=[<Your QQ>]' -v <config dir>:/data -e 'hk_reporter_config_path=/data' -e 'HK_REPORTER_USE_PIC=True' -e 'HK_REPORTER_USE_LOCAL=True'
```
go-cqhttp镜像可使用`felinae98/go-cqhttp-ffmpeg`（数据目录为`/data`），需要注意，两个容器需要在同一个network中。
</details>

### 配置变量
* `HK_REPORTER_CONFIG_PATH` (str) 配置文件保存目录，如果不设置，则为当前目录下的`data`文件夹
* `HK_REPORTER_USE_PIC` (bool) 以图片形式发送文字（推荐在帐号被风控时使用）
* `HK_REPORTER_USE_LOCAL` (bool) 使用本地chromium（文字转图片时需要），否则第一次启动会下载chromium

### 命令
所有命令都需要@bot触发
* 添加订阅（仅管理员和群主）：`添加订阅`
* 查询订阅：`查询订阅`
* 删除订阅（仅管理员和群主）：`删除订阅`

平台代码包含：weibo，bilibili，rss
<details>
<summary>各平台uid</summary>

下面均以pc站点为例
* weibo
    * 对于一般用户主页`https://weibo.com/u/6441489862?xxxxxxxxxxxxxxx`，`/u/`后面的数字即为uid
    * 对于有个性域名的用户如：`https://weibo.com/arknights`，需要点击左侧信息标签下“更多”，链接为`https://weibo.com/6279793937/about`，其中中间数字即为uid
* bilibili
    * 主页链接一般为`https://space.bilibili.com/161775300?xxxxxxxxxx`，数字即为uid
* rss
    * rss链接即为uid
</details>

### 文字转图片
因为可能要发送长文本，所以bot很可能被风控，如有需要请开启以图片形式发送文字，本项目使用的图片转文字方法是chromium（经典杀鸡用牛刀）。

如果确定要开启推荐自行安装chromium，设置使用本地chromium，并且保证服务器有比较大的内存。
## 功能
* 定时爬取制定网站
* 通过图片发送文本，防止风控
* 使用队列限制发送频率

## 鸣谢
* [`go-cqhttp`](https://github.com/Mrs4s/go-cqhttp)：简单又完善的 cqhttp 实现
* [`NoneBot2`](https://github.com/nonebot/nonebot2)：超好用的开发框架
* [`HarukaBot`](https://github.com/SK-415/HarukaBot/): 借鉴了大体的实现思路

## License
MIT

