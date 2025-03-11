---
prev: /usage/
next: /usage/easy-use
---

# 让拜松骑上自行车

本节将讲解如何部署 nonebot-bison 项目  
使用部分介绍请看 [简单使用](/usage/easy-use.md) 或者 [详细配置](/usage)

## 如何选择？

- 没有其他需要，只想使用 Nonebot-Bison？想以 Bison 的基础扩展其他插件？  
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
建议所有操作都在虚拟环境下进行，推荐使用[`uv`](https://docs.astral.sh/uv/)或者 python 自带的[`venv`](https://docs.python.org/zh-cn/3/library/venv.html)
:::

### 使用 nb-cli 安装 <Badge type="tip" text="推荐" vertical="top" />

1. 安装[`nb-cli`](https://cli.nonebot.dev/docs/guide/installation)

   ```bash
   pipx install nb-cli
   ```

2. 使用`nb-cli`执行在**项目根目录**执行

   ```bash
   nb plugin install nonebot-bison
   ```

3. 在项目中添加依赖

   ```bash
   uv add nonebot-bison
   ```

### 手动安装

1. 安装 pip 包`nonebot-bison`
   ::: code-tabs
   @tab uv

   ```bash
   uv add nonebot-bison
   ```

   @tab pip

   ```bash
   pip install nonebot-bison
   ```

   :::

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

   ::: code-tabs#shell
   @tab linux

   ```bash
   wget https://raw.githubusercontent.com/felinae98/nonebot-bison/main/docker-compose.yml
   ```

   @tab windows

   ```powershell
   Invoke-WebRequest -Uri https://raw.githubusercontent.com/felinae98/nonebot-bison/main/docker-compose.yml -OutFile docker-compose.yml
   ```

   :::

   部分片断：

   ```yml
       ...
         HOST: 0.0.0.0 # 0.0.0.0 代表监听所有地址
         # SUPERUSERS: '[<your QQ>]' #取消该行注释，并将<your QQ>改为自己的 QQ 号
         BISON_CONFIG_PATH: /data
         # BISON_OUTER_URL: 'http://<your server ip>:8080/bison'
         #取消上行注释，并将<your server ip>改为你的服务器 ip，bison 不会自动获取 ip
         BISON_FILTER_LOG: 'true'
         BISON_USE_PIC: 'false' # 如果需要将文字转为图片发送请改为 true
       ports:
         - 8080:8080 # 容器映射的端口，如果需要修改请同时修改上面的 BISON_OUTER_URL
       ...
   ```

   ::: tip
   想要指定更多配置请参考[详细配置](/usage#配置)
   :::

3. 启动项目
   - 在目录中运行`docker-compose up -d`启动 Nonebot-Bison
   - 启动 Bot 端（这里请八仙过海）

### docker-compose 部署（包括监控）

由于涉及到的配置文件较多，所以建议克隆仓库使用

1. clone 本仓库

   ```bash
   git clone https://github.com/felinae98/nonebot-bison.git
   cd nonebot-bison/docker
   ```

2. 根据需要修改 docker-compose_metrics.yaml 文件

修改说明请参考[docker-compose 部署](/usage/install.md#docker-compose-部署)

3. 启动项目
   - 在目录中运行`docker compose -f ./docker-compose_metrics.yaml up`启动 Nonebot-Bison
   - 启动 Bot 端（这里同样请八仙过海）
4. Enjoy!

   使用浏览器访问对应地址的 3000 端口，即可进入 Grafana ，默认用户名为 admin，密码为 nonebot-bison。

   在左边侧边栏找到「Dashboards」选项并进入，在右边点击并进入「Bison Status」即可看到监控面板。

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

相当于进行了源码部署，或者说是开发模式的部署。

可以参考[nonebot 的运行方法](https://nonebot.dev/docs/quick-start)
::: danger
Bison 的 WebUI 是需要编译后才能使用的，直接克隆源代码需要自行编译前端，否则会出现无法使用管理后台等情况。
:::

#### 本体安装

::: danger
本项目中使用了 Python 3.10 的语法，如果出现问题，请检查 Python 版本
:::

1. 首先安装 uv：[安装方法](https://docs.astral.sh/uv/getting-started/installation/)
2. clone 本项目，在项目中使用`uv sync`安装依赖

   ```bash
   git clone https://github.com/felinae98/nonebot-bison.git
   cd nonebot-bison
   uv sync
   ```

#### WebUI 安装

1. 安装包管理器
   Bison 仓库中使用了`pnpm`作为包管理器，如果没有安装请先安装`pnpm`  
   当然如果你因为一些原因不想使用`pnpm`，可以使用`yarn`或者`npm`进行安装

   - pnpm
     参见 [pnpm 安装](https://pnpm.io/zh/installation)
   - yarn
     - 安装[Node.js](https://nodejs.org/en/download)
     - 安装 yarn: `npm install -g yarn`

2. 在`admin-fronted`目录中编译前端

   ```bash
   cd admin-frontend
   ```

   ::: code-tabs
   @tab pnpm

   ```shell
   pnpm install
   pnpm build
   ```

   @tab yarn

   ```shell
   yarn && yarn build
   ```

   @tab npm

   ```shell
   npm i
   npm build
   ```

   :::

构建完毕后，dist 目录中生成的前端文件会自动移入`nonebot_bison/admin_page/dist`目录中，请前往检查

#### 运行

::: info 注意
构建完前端后，请回到项目根目录
:::

1. 编辑`.env.prod`配置各种环境变量，见[Nonebot2 配置](https://v2.nonebot.dev/docs/appendices/config)
   :::tip 找不到 .env.prod？
   `.env.prod`文件在项目根目录下，请确认当前目录为项目根目录
   :::

2. 启动 Bot

   ```bash
   uv run nb run
   ```
