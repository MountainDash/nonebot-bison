---
sidebar: auto
prev: /usage
next: /usage/easy-use
---

# 让拜松骑上自行车

本节将教你部署 nonebot-bison 项目  
想知道如何开始使用请看[简单使用](/usage/easy-use.md)或者[详细配置](/usage)

## 如何选择？

- 没有其他需要，只想使用 Nonebot-Bison？想在 Bison 的基础上再加入其他插件？  
  试试[**作为 Bot 使用**](#作为-bot-使用)！
- 已有项目，想要增加 Nonebot-Bison？  
  试试[**作为插件使用**](#作为插件使用)！

## 作为插件使用

本部分假设大家会部署 nonebot2
::: tip 看看别的！
参考教程 [nonebot2 部署](https://v2.nonebot.dev/docs/quick-start)  
参考视频教程 [保姆级新手教学 - Well404](https://www.bilibili.com/video/BV1984y1b7JY)
:::
::: warning 防止环境冲突！
建议所有操作都在虚拟环境下进行，推荐使用[`poetry`](https://python-poetry.org/)或者 python 自带的[`venv`](https://docs.python.org/zh-cn/3/library/venv.html)
:::

### 使用 nb-cli 安装 <Badge type="tip" text="推荐" vertical="top" />

1. 安装`nb-cli`

   ```bash
   pip install nb-cli
   ```

2. 使用`nb-cli`执行在**项目根目录**执行

   ```bash
   nb plugin install nonebot-bison
   ```

### 手动安装

1. 安装 pip 包`nonebot-bison`

   ```bash
   pip install nonebot-bison
   ```

2. 在`pyproject.toml`中导入插件`nonebot_bison`
   编辑项目根目录下的`pyproject.toml`文件，添加如下内容：

   ```toml
   [tool.nonebot]
   plugins = [
     ... # 其他插件
     "nonebot_bison",
     ]
   ```

## 作为 Bot 使用

::: tip 额外提供

- 自动同意超级用户的好友申请
- 自动同意超级用户的加群邀请
  :::

### docker-compose 部署 <Badge type="tip" text="推荐" vertical="top" />

1. 首先创建一个新的空目录

   ```bash
   mkdir nonebot-bison && cd nonebot-bison
   ```

2. 在目录中下载[docker-compose.yml](https://raw.githubusercontent.com/felinae98/nonebot-bison/main/docker-compose.yml)  
   将其中的`<your QQ>`改成自己的 QQ 号

   :::: code-group
   ::: code-group-item linux

   ```bash
   wget https://raw.githubusercontent.com/felinae98/nonebot-bison/main/docker-compose.yml
   ```

   :::
   ::: code-group-item windows

   ```powershell
   Invoke-WebRequest -Uri https://raw.githubusercontent.com/felinae98/nonebot-bison/main/docker-compose.yml -OutFile docker-compose.yml
   ```

   :::
   ::::

   部分片断：

   ```yml
       ...
         HOST: 0.0.0.0 # 0.0.0.0代表监听所有地址
         # SUPERUSERS: '[<your QQ>]' #取消该行注释，并将<your QQ>改为自己的QQ号
         BISON_CONFIG_PATH: /data
         # BISON_OUTER_URL: 'http://<your server ip>:8080/bison'
         #取消上行注释，并将<your server ip>改为你的服务器ip，bison不会自动获取ip
         BISON_FILTER_LOG: 'true'
         BISON_USE_PIC: 'false' # 如果需要将文字转为图片发送请改为true
       ports:
         - 8080:8080 # 容器映射的端口，如果需要修改请同时修改上面的BISON_OUTER_URL
       ...
   ```

   ::: tip
   想要指定更多配置请参考[详细配置](/usage#配置)
   :::

3. 启动 Bot（这里请八仙过海）

### docker 部署

Bison 的 docker 镜像为[`felinae98/nonebot-bison`](https://hub.docker.com/r/felinae98/nonebot-bison)

在为服务器安装了`docker`后可以直接进行使用

```bash
docker pull felinae98/nonebot-bison

docker run -d --name nonebot-bison \
  -e SUPERUSERS='["<your QQ>"]' \
  -e BISON_CONFIG_PATH='/data' \
  -e BISON_OUTER_URL='http://<your server ip>:8080/bison' \
  -e BISON_FILTER_LOG='true' \
  -e BISON_USE_PIC='false' \
  -p 8080:8080 \
  felinae98/nonebot-bison
```

相关配置参数可以使用`-e`作为环境变量传入

### 直接运行 <Badge type="warning" text="不推荐" vertical="top" />

可以参考[nonebot 的运行方法](https://docs.nonebot.dev/guide/getting-started.html)
::: danger
直接克隆源代码需要自行编译前端，否则会出现无法使用管理后台等情况。
:::
::: danger
本项目中使用了 Python 3.10 的语法，如果出现问题，请检查 Python 版本
:::

1. 首先安装 poetry：[安装方法](https://python-poetry.org/docs/#installation)
2. clone 本项目，在项目中`poetry install`安装依赖

   ```bash
   git clone https://github.com/felinae98/nonebot-bison.git
   cd nonebot-bison
   poetry install
   ```

3. 安装 yarn，配置 yarn 源

   - 安装[`Node.js`](https://nodejs.org/en/download)
   - 安装`yarn`

     ```bash
     npm install -g yarn
     ```

4. 在`admin-fronted`目录中运行`yarn && yarn build`编译前端

   ```bash
   cd admin-frontend
   yarn && yarn build
   ```

5. 编辑`.env.prod`配置各种环境变量，见[Nonebot2 配置](https://v2.nonebot.dev/docs/appendices/config)
   :::tip 找不到 .env.prod ？
   `.env.prod`文件在项目根目录下，请确认当前目录为项目根目录
   :::
6. 运行`poetry run python bot.py`启动 Bot
