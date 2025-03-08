---
prev: /usage/install
next: /usage/cookie
---

# 全方位了解 Bison 的自行车

本节将详细列出 Bison 的使用方法，包括但不限于

- 如何配置 Bison
- 如何使用 Bison 的后台管理网页
- 如何使用 Bison 的 API

如果你想要快速上手 Bison，可以前往[简单使用](/usage/easy-use.md)

## 配置

::: tip INFO

- 想要在 nonebot 中配置需要的**Bison 配置项**，请参考[NoneBot 配置方式](https://v2.nonebot.dev/docs/appendices/config#dotenv-%E9%85%8D%E7%BD%AE%E6%96%87%E4%BB%B6)，在`.env`/`.env.*`文件中写入希望配置的 Bison 配置项
- 请注意，在`.env`/`.env.*`中添加的配置项 ==不需要== 声明变量类型

:::

- `BISON_TO_ME`: 是否需要 @Bot 或使用 Bot 的 Nickname 来触发 Bison 的命令，默认为`True`
- `BISON_CONFIG_PATH`<Badge text="弃用" type="warning" vertical="top"/>: 插件存放配置文件的位置，如果不设定默认为项目目录下的`data`目录，现用于从低版本迁移
- `BISON_USE_PIC`: 将几乎所有文字渲染成图片后进行发送，多用于规避风控
- `BISON_BROWSER`: 本插件使用 Chrome 来渲染图片
  - 如果不进行配置，那么会在启动时候自动进行安装，在官方的 docker 镜像中已经安装了浏览器
  - 使用本地安装的 Chrome，设置为`local:<chrome path>`，例如`local:/usr/bin/google-chrome-stable`
  - 使用 cdp 连接相关服务，设置为`wsc://xxxxxxxxx`
  - 使用 browserless 提供的 Chrome 管理服务，设置为`ws://xxxxxxxx`，值为 Chrome Endpoint
    ::: warning
    截止发布时，本项目尚不能完全与 browserless 兼容，目前建议使用镜像内自带的浏览器
    即 **不要配置这个变量**
    :::
- `BISON_SKIP_BROWSER_CHECK`: 是否在启动时自动下载浏览器，如果选择`False`会在用到浏览器时自动下载，
  默认`True`
- `BISON_OUTER_URL`: 从外部访问服务器的地址，不设置或为空时默认值为 `http://localhost:<Bot运行在的端口>/bison/`
  ::: warning
  请注意，该网址**并不能直接访问** Bison 的后台管理网页，正确的访问方法请参见[私聊机器人获取后台地址](#私聊机器人获取后台地址)
  :::
  ::: tip 配置建议
  请选择你的部署情况：
  <div class="outer-url-help">
  <input type="checkbox" id="docker" v-model="docker"/>
  <label for="docker">使用容器部署</label>
  <input type="checkbox" id="server" v-model="server"/>
  <label for="server">部署在服务器上</label>
  <input type="checkbox" id="reverse-proxy" v-model="reverseProxy"/>
  <label for="reverse-proxy">启用反代</label>
  </div>
  下面是配置建议：

  ```plaintext:no-v-pre :no-line-numbers
  {{ outerUrlHelp }}
  ```

  :::

- `BISON_FILTER_LOG`: 是否过滤来自`nonebot`的 warning 级以下的 log，如果你的 bot 只运行了这个插件可以考虑
  开启，默认关
- `BISON_USE_QUEUE`: 是否用队列的方式发送消息，降低发送频率，默认开
- `BISON_RESEND_TIMES`: 最大重发次数，默认 0
- `BISON_USE_PIC_MERGE`: 是否启用多图片时合并转发（仅限群）

  - `0`: 不启用 (默认)
  - `1`: 首条消息单独发送，剩余图片合并转发
  - `2`: 所有消息全部合并转发

  ::: details BISON_USE_PIC_MERGE 配置项示例

  - 当`BISON_USE_PIC_MERGE=1`时：
    ![simple1](/images/forward-msg-simple1.png)
  - 当`BISON_USE_PIC_MERGE=2`时：
    ![simple1](/images/forward-msg-simple2.png)

  :::
  ::: warning
  启用此功能时，可能会因为待推送图片过大/过多而导致文字消息与合并转发图片消息推送间隔过大 (选择模式`1`时)，请谨慎考虑开启。或者选择模式`2`，使图文消息一同合并转发 (可能会使消息推送延迟过长)
  :::

- `BISON_PROXY`: 使用的代理连接，形如`http://<ip>:<port>`（可选）
- `BISON_UA`: 使用的 User-Agent，默认为 Chrome
- `BISON_SHOW_NETWORK_WARNING`: 是否在日志中输出网络异常，默认为`True`
- `BISON_COLLAPSE_NETWORK_WARNING`: 在启用`BISON_SHOW_NETWORK_WARNING`后选择是否清理警告文本中的换行符并当文本字符数超过限制时折叠这段文本，默认为`False`
- `BISON_COLLAPSE_NETWORK_WARNING_LENGTH`: 在启用`BISON_COLLAPSE_NETWORK_WARNING`后限制警告文本字符数
- `BISON_USE_BROWSER`: 环境中是否存在浏览器，某些主题或者平台需要浏览器，默认为`False`
- `BISON_PLATFORM_THEME`: 为[平台](#平台)指定渲染用[主题](#主题)，用于渲染推送消息，默认为`{}`
  ::: details BISON_PLATFORM_THEME 配置项示例

  配置项使用`<platform>:<theme>`的形式来为某个平台指定其渲染主题，例如

  - `"weibo":"basic"`
  - `"bilibili":"ht2i"`。

  最外层使用`{}`包裹，多个配置项之间使用逗号`,`分隔。  
  需要注意，`<platform>`所用内容是平台的**代码英文名**，`<theme>`所用内容是主题的**代码英文名**。  
  并且不要忘记使用双引号`""`包裹内容。

  例子：

  ```env
  BISON_PLATFORM_THEME={"weibo":"basic","bilibili":"ht2i"}
  ```

  所有支持的平台请参见[平台](#平台)一节  
  所有支持的主题请参见[主题](#主题)一节
  :::

## 使用

::: warning
本节假设`COMMAND_START`配置中包含`''`

- 如果出现 bot 不响应的问题，请先排查这个设置
- 尝试在命令前添加设置的命令前缀，如`COMMAND_START=['/']`，则尝试使用`/添加订阅`

:::

### 命令

#### 在本群中进行配置

所有命令都需要 @bot 触发

- 添加订阅（仅管理员和群主和 SUPERUSER）：`添加订阅`
- 查询订阅：`查询订阅`
- 删除订阅（仅管理员和群主和 SUPERUSER）：`删除订阅`

::: details 关于中止命令
对于[**v0.5.3**](https://github.com/felinae98/nonebot-bison/releases/tag/v0.5.3)及以上的版本中，已经为`添加订阅/删除订阅`命令添加了中止删除功能。
在命令的~~几乎~~各个阶段，都可以向 Bot 发送`取消`消息来中止流程 (需要发起者本人发送)
:::

#### 私聊机器人获取后台地址

要管理订阅，请和 bot **私聊**输入`后台管理`命令，然后访问回复中的链接。你的管理权限取决于你的身份：

- 如果你是 superuser，你可以管理所有群的订阅；
- 如果你是某些群的管理员，你可以管理这些群的订阅；
- 如果你不是任何群的管理员，bot 会提示你无法执行此操作。

::: warning 注意隐私
bot 返回的链接是网页的唯一身份凭证，不要泄露给他人。  
链接具有有时效性，过期后需重新向 bot 索取新链接。
:::

#### 私聊机器人进行配置（需要 SUPERUER 权限）

请私聊 bot `群管理`

::: details 关于中止订阅
与普通的[`添加订阅`/`删除订阅`](#在本群中进行配置)命令一样，在`群管理`命令中使用的`添加订阅`/`删除订阅`命令也可以使用`取消`来中止流程
:::

### 命令行命令 (CLI)

Bison 在 `nb-cli` 中注册了一些命令，用于导出和导入订阅信息。

```shell
nb bison --help
```

```plaintext:no-line-numbers
Nonebot Bison CLI, 目前用于实现Bison订阅的导入导出功能

用法:
  nb bison COMMAND [OPTIONS] [ARGS]

Command(命令):

  export:
  导出 Nonebot Bison Exchangable Subcribes File
      Options(选项):
        -p, --path TEXT           导出路径, 如果不指定，则默认为工作目录
        --format [json|yaml|yml]  指定导出格式[json, yaml]，默认为 json
        --help                    显示帮助

  import:
  从 Nonebot Biosn Exchangable Subscribes File 导入订阅
      Options(选项):
        -p, --path TEXT           导入文件名  [必须]
        --format [json|yaml|yml]  指定导入格式[json, yaml]，默认为 json
        --help                    显示帮助
```

### 平台

Bison 支持的平台如下：

- `arknights`: 明日方舟游戏信息
- `bilibili`: B 站
- `bilibili-live`: Bilibili 直播
- `bilibili-bangumi`: Bilibili 剧集
- `ff14`: 最终幻想 XIV 官方公告
- `ncm-artist`: 网易云 - 歌手
- `ncm-radio`: 网易云 - 电台
- `rss`: RSS
- `weibo`: 新浪微博

:::tip
配置 `BISON_PLATFORM_THEME` 时，所用的 `<platform>` 是 `:` 左侧的值
:::

### 主题

Bison 支持的主题如下：

- `basic`: 基础主题，是每个平台都会支持的主题
- `ht2i`: 使用 `nonebot-plugin-htmlrender` 插件，将纯文本渲染成图片
- `brief`: 简报主题，仅发送标题、链接、图片
- `arknights`: 明日方舟专用主题，渲染为明日方舟公告风格

:::tip
配置 `BISON_PLATFORM_THEME` 时，所用的 `<theme>` 是 `:` 左侧的值
:::

### 所支持平台的 uid

#### Weibo

- 对于一般用户主页`https://weibo.com/u/6441489862?xxxxxxxxxxxxxxx`，`/u/`后面的数字即为 uid
- 对于有个性域名的用户如：`https://weibo.com/arknights`，需要点击左侧信息标签下“更多”，链接为`https://weibo.com/6279793937/about`，其中中间数字即为 uid

#### Bilibili

主页链接一般为`https://space.bilibili.com/161775300?xxxxxxxxxx`，数字即为 uid

#### RSS

整个 RSS 链接即为 uid

#### 网易云音乐 - 歌手

在网易云网页上歌手的链接一般为`https://music.163.com/#/artist?id=32540734`，`id=` 后面的数字即为 uid

#### 网易云音乐 - 电台

在网易云网页上电台的链接一般为`https://music.163.com/#/djradio?id=793745436`，`id=` 后面的数字即为 uid

### 平台订阅标签（Tag）

Tag 是社交平台中一种常见的功能，它用井号 (#) 作为前缀，标记关键词，方便用户搜索相关内容。
例如：

- `#明日方舟#` `#每日打卡#`（微博、哔哩哔哩）
- `#baracamp`（推特）

在 Bison 中，用户可以在添加平台账号订阅时（如果该平台支持 hashtag 功能），
选择需要订阅或屏蔽的 Tag。

**订阅** Tag 的方法是直接向 Bison 发送一系列 Tag，用空格分隔。  
例如：`A1行动预备组 罗德厨房——回甘`

**屏蔽** Tag 的方法是在 Tag 前加上前缀~，也用空格分隔。  
例如：`~123罗德岛 ~莱茵生命漫画`

订阅和屏蔽的 Tag 可以同时使用，按照上述方法发送即可。  
例如：`A1行动预备组 ~123罗德岛 罗德厨房——回甘 ~莱茵生命漫画`

#### Tag 的推送规则

Bison 在处理每条推送时，会按照以下规则顺序检查推送中的 Tag：

对于每条推送：

1. 检查 **需屏蔽 Tag** 列表
   - 如果推送中的 Tag 存在于 **需屏蔽 Tag** 列表中，则立刻**丢弃**该推送，检查结束
   - 如果推送中的 Tag 不存在于 **需屏蔽 Tag** 列表中，则**继续**第 2 条规则的检查
2. **需订阅 Tag** 列表不为空
   - 如果推送中的任何一个 Tag 存在于 **需订阅 Tag** 列表中，则**发送**该推送到群中，检查结束
   - 如果推送中的每一个 Tag 都不存在于 **需订阅 Tag** 列表中，则**丢弃**该推送，检查结束
3. **需订阅 Tag** 列表为空
   - **发送**该推送到群中，检查结束

#### Cookie 功能

Bison 支持携带 Cookie 进行请求。

目前支持的平台有：

- `rss`: RSS
- `weibo`: 新浪微博

::: warning 使用须知
Cookie 全局生效，这意味着，通过你的 Cookie 获取到的内容，可能会被发给其他用户。
:::

管理员可以通过**命令**或**管理后台**给 Bison 设置 Cookie。

<script setup lang="ts">
import { ref, computed } from 'vue';

const docker = ref(false);
const server = ref(false);
const reverseProxy = ref(false);

const outerUrlHelp = computed(() => {
  let helpText: string[] = [];

  if ((docker.value || server.value) && !reverseProxy.value)
    helpText.push('HOST=0.0.0.0');

  if (docker.value && !server.value && !reverseProxy.value)
    helpText.push('BISON_OUTER_URL=http://localhost:[Docker 映射到主机的端口]/bison/');

  if (server.value && !reverseProxy.value){
    if (docker.value)
      helpText.push('BISON_OUTER_URL=http://[你的服务器 ip]:[Docker 映射到主机的端口]/bison/');
    else
      helpText.push('BISON_OUTER_URL=http://[你的服务器 ip]:[Bot 运行的端口]/bison/');
  }

  if (reverseProxy.value){
    if (server.value){
      helpText.push('BISON_OUTER_URL=http://[你的服务器 ip]:[反代端口]/bison/');
      if (docker.value)
        helpText.push('# 请注意反代端口应该指向 Docker 映射到主机的端口<br>');
      else
        helpText.push('# 请注意反代端口应该指向 Bot 运行的端口');
    }
    else
      helpText.push('谁没事在自己电脑上起反代啊（');
  }

  if (!docker.value && !server.value && !reverseProxy.value)
    helpText.push('你无需设置此项');

  return helpText.join('\n');
});
</script>

<style>
.outer-url-help {
  margin-top: 10px;
  margin-bottom: 10px;
}

.outer-url-help label {
  margin-right: 15px;
}
</style>
