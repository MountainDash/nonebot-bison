---
sidebar: auto
---
# 部署和使用
本节将教你快速部署和使用一个nonebot-hk-reporter，如果你不知道要选择哪种部署方式，推荐使用[docker-compose](#docker-compose部署-推荐)

## 部署
本项目可以作为单独的Bot使用，可以作为nonebot2的插件使用
### 作为Bot使用
额外提供自动同意超级用户的好友申请和同意超级用户的加群邀请的功能
#### docker-compose部署（推荐）
1. 在一个新的目录中下载[docker-compose.yml](https://raw.githubusercontent.com/felinae98/nonebot-hk-reporter/main/docker-compose.yml)  
    将其中的`<your QQ>`改成自己的QQ号
    ```bash
    wget https://raw.githubusercontent.com/felinae98/nonebot-hk-reporter/main/docker-compose.yml
    ```
2. 运行配置go-cqhttp
    ```bash
    docker-compose run go-cqhttp
    ```
    通信方式选择：`3: 反向 Websocket 通信`  
    编辑`bot-data/config.yml`，更改下面字段：
    ```
    account: # 账号相关
      uin: <QQ号> # QQ账号
      password: "<QQ密码>" # 密码为空时使用扫码登录

    message:
      post-format: array

    ............

    servers:
      - ws-reverse:
          universal: ws://nonebot:8080/cqhttp/ws # 将这个字段写为这个值
    ```
3. 登录go-cqhttp
    再次
    ```bash
    docker-compose run go-cqhttp
    ```
    参考[go-cqhttp文档](https://docs.go-cqhttp.org/faq/slider.html#%E6%96%B9%E6%A1%88a-%E8%87%AA%E8%A1%8C%E6%8A%93%E5%8C%85)
    完成登录
4. 确定完成登录后，启动bot：
    ```bash
    docker-compose up -d
    ```
#### docker部署
本项目的docker镜像为`felinae98/nonebot-hk-reporter`，可以直接pull后run进行使用，
相关配置参数可以使用`-e`作为环境变量传入
#### 直接运行（不推荐）
可以参考[nonebot的运行方法](https://v2.nonebot.dev/guide/getting-started.html)
::: danger
本项目中使用了Python 3.9的语法，如果出现问题，请检查Python版本
:::
1. 首先安装poetry：[安装方法](https://python-poetry.org/docs/#installation)
2. clone本项目，在项目中`poetry install`安装依赖
3. 编辑`.env.prod`配置各种环境变量，见[Nonebot2配置](https://v2.nonebot.dev/guide/basic-configuration.html)
4. 运行`poetry run python bot.py`启动机器人
### 作为插件使用
本部分假设大家会部署nonebot2
#### 手动安装
1. 安装pip包`nonebot-hk-reporter`
2. 在`bot.py`中导入插件`nonebot_hk_reporter`
### 自动安装
使用`nb-cli`执行：`nb plugin install nonebot_hk_reporter`
## 配置
可参考[源文件](https://github.com/felinae98/nonebot-hk-reporter/blob/main/src/plugins/nonebot_hk_reporter/plugin_config.py)  
* `HK_REPORTER_CONFIG_PATH`: 插件存放配置文件的位置，如果不设定默认为项目目录下的`data`目录
* `HK_REPORTER_USE_PIC`: 将文字渲染成图片后进行发送，多用于规避风控
* `HK_REPORTER_BROWSER`: 在某些情况下需要使用到chrome进行渲染
  * 使用browserless提供的Chrome管理服务，设置为`ws://xxxxxxxx`，值为Chrome Endpoint（推荐）
  * 使用本地安装的Chrome，设置为`local:<chrome path>`，例如`local:/usr/bin/google-chrome-stable`
  * 如果不进行配置，那么会在使用到Chrome的时候自动进行安装（不推荐）
### 需要使用Chrome的情况
* 设置了`HK_REPORTER_USE_PIC`，需要将文字渲染成图片
* 渲染明日方舟游戏内公告
## 使用
::: warning
本节假设`COMMAND_START`设置中包含`''`，如果出现bot不响应的问题，请先
排查这个设置
:::
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
### 所支持平台的uid
#### Weibo
* 对于一般用户主页`https://weibo.com/u/6441489862?xxxxxxxxxxxxxxx`，`/u/`后面的数字即为uid
* 对于有个性域名的用户如：`https://weibo.com/arknights`，需要点击左侧信息标签下“更多”，链接为`https://weibo.com/6279793937/about`，其中中间数字即为uid
#### Bilibili
主页链接一般为`https://space.bilibili.com/161775300?xxxxxxxxxx`，数字即为uid
#### RSS
RSS链接即为uid
