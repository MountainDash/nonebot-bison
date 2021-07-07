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
2. 运行配置cq-http
    ```bash
    docker-compose run cq-http
    ```
    通信方式选择：3: 反向 Websocket 通信  
    编辑`bot-data/config.yml`，更改下面字段：
    ```
    account: # 账号相关
      uin: <QQ号> # QQ账号
      password: "<QQ密码>" # 密码为空时使用扫码登录

    ............

    servers:
      - ws-reverse:
          universal: ws://nonebot:8080/cqhttp/ws # 将这个字段写为这个值
    ```
3. 登录cq-http
    再次
    ```bash
    docker-compose run cq-http
    ```
    参考[cq-http文档](https://docs.go-cqhttp.org/faq/slider.html#%E6%96%B9%E6%A1%88a-%E8%87%AA%E8%A1%8C%E6%8A%93%E5%8C%85)
    完成登录
4. 确定完成登录后，启动bot：
    ```bash
    docker-compose up -d
    ```
#### docker部署
#### 直接运行（不推荐）
### 作为插件使用
本部分假设大家会部署nonebot2
## 配置
## 使用
