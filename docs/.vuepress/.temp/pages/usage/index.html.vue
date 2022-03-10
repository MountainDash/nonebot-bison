<template><h1 id="部署和使用" tabindex="-1"><a class="header-anchor" href="#部署和使用" aria-hidden="true">#</a> 部署和使用</h1>
<p>本节将教你快速部署和使用一个 nonebot-bison，如果你不知道要选择哪种部署方式，推荐使用<a href="#docker-compose%E9%83%A8%E7%BD%B2-%E6%8E%A8%E8%8D%90">docker-compose</a></p>
<h2 id="部署" tabindex="-1"><a class="header-anchor" href="#部署" aria-hidden="true">#</a> 部署</h2>
<p>本项目可以作为单独的 Bot 使用，可以作为 nonebot2 的插件使用</p>
<h3 id="作为-bot-使用" tabindex="-1"><a class="header-anchor" href="#作为-bot-使用" aria-hidden="true">#</a> 作为 Bot 使用</h3>
<p>额外提供自动同意超级用户的好友申请和同意超级用户的加群邀请的功能</p>
<h4 id="docker-compose-部署-推荐" tabindex="-1"><a class="header-anchor" href="#docker-compose-部署-推荐" aria-hidden="true">#</a> docker-compose 部署（推荐）</h4>
<ol>
<li>
<p>在一个新的目录中下载<a href="https://raw.githubusercontent.com/felinae98/nonebot-bison/main/docker-compose.yml" target="_blank" rel="noopener noreferrer">docker-compose.yml<ExternalLinkIcon/></a><br>
将其中的<code>&lt;your QQ&gt;</code>改成自己的 QQ 号</p>
<div class="language-bash ext-sh line-numbers-mode"><pre v-pre class="language-bash"><code><span class="token function">wget</span> https://raw.githubusercontent.com/felinae98/nonebot-bison/main/docker-compose.yml
</code></pre><div class="line-numbers" aria-hidden="true"><span class="line-number">1</span><br></div></div></li>
<li>
<p>运行配置 go-cqhttp</p>
<div class="language-bash ext-sh line-numbers-mode"><pre v-pre class="language-bash"><code><span class="token function">docker-compose</span> run go-cqhttp
</code></pre><div class="line-numbers" aria-hidden="true"><span class="line-number">1</span><br></div></div><p>通信方式选择：<code>3: 反向 Websocket 通信</code><br>
编辑<code>bot-data/config.yml</code>，更改下面字段：</p>
<div class="language-text ext-text line-numbers-mode"><pre v-pre class="language-text"><code>account: # 账号相关
  uin: &lt;QQ号> # QQ账号
  password: "&lt;QQ密码>" # 密码为空时使用扫码登录

message:
  post-format: array

............

servers:
  - ws-reverse:
      universal: ws://nonebot:8080/onebot/v11/ws/ # 将这个字段写为这个值
</code></pre><div class="line-numbers" aria-hidden="true"><span class="line-number">1</span><br><span class="line-number">2</span><br><span class="line-number">3</span><br><span class="line-number">4</span><br><span class="line-number">5</span><br><span class="line-number">6</span><br><span class="line-number">7</span><br><span class="line-number">8</span><br><span class="line-number">9</span><br><span class="line-number">10</span><br><span class="line-number">11</span><br><span class="line-number">12</span><br></div></div></li>
<li>
<p>登录 go-cqhttp
再次</p>
<div class="language-bash ext-sh line-numbers-mode"><pre v-pre class="language-bash"><code><span class="token function">docker-compose</span> run go-cqhttp
</code></pre><div class="line-numbers" aria-hidden="true"><span class="line-number">1</span><br></div></div><p>参考<a href="https://docs.go-cqhttp.org/faq/slider.html#%E6%96%B9%E6%A1%88a-%E8%87%AA%E8%A1%8C%E6%8A%93%E5%8C%85" target="_blank" rel="noopener noreferrer">go-cqhttp 文档<ExternalLinkIcon/></a>
完成登录</p>
</li>
<li>
<p>确定完成登录后，启动 bot：</p>
<div class="language-bash ext-sh line-numbers-mode"><pre v-pre class="language-bash"><code><span class="token function">docker-compose</span> up -d
</code></pre><div class="line-numbers" aria-hidden="true"><span class="line-number">1</span><br></div></div></li>
</ol>
<h4 id="docker-部署" tabindex="-1"><a class="header-anchor" href="#docker-部署" aria-hidden="true">#</a> docker 部署</h4>
<p>本项目的 docker 镜像为<code>felinae98/nonebot-bison</code>，可以直接 pull 后 run 进行使用，
相关配置参数可以使用<code>-e</code>作为环境变量传入</p>
<h4 id="直接运行-不推荐" tabindex="-1"><a class="header-anchor" href="#直接运行-不推荐" aria-hidden="true">#</a> 直接运行（不推荐）</h4>
<p>可以参考<a href="https://v2.nonebot.dev/guide/getting-started.html" target="_blank" rel="noopener noreferrer">nonebot 的运行方法<ExternalLinkIcon/></a></p>
<div class="custom-container danger"><p class="custom-container-title">DANGER</p>
<p>直接克隆源代码需要自行编译前端，否则会出现无法使用管理后台等情况。</p>
</div>
<div class="custom-container danger"><p class="custom-container-title">DANGER</p>
<p>本项目中使用了 Python 3.9 的语法，如果出现问题，请检查 Python 版本</p>
</div>
<ol>
<li>首先安装 poetry：<a href="https://python-poetry.org/docs/#installation" target="_blank" rel="noopener noreferrer">安装方法<ExternalLinkIcon/></a></li>
<li>clone 本项目，在项目中<code>poetry install</code>安装依赖</li>
<li>安装 yarn，配置 yarn 源（推荐）</li>
<li>在<code>admin-fronted</code>中运行<code>yarn &amp;&amp; yarn build</code>编译前端</li>
<li>编辑<code>.env.prod</code>配置各种环境变量，见<a href="https://v2.nonebot.dev/guide/basic-configuration.html" target="_blank" rel="noopener noreferrer">Nonebot2 配置<ExternalLinkIcon/></a></li>
<li>运行<code>poetry run python bot.py</code>启动机器人</li>
</ol>
<h3 id="作为插件使用" tabindex="-1"><a class="header-anchor" href="#作为插件使用" aria-hidden="true">#</a> 作为插件使用</h3>
<p>本部分假设大家会部署 nonebot2</p>
<h4 id="手动安装" tabindex="-1"><a class="header-anchor" href="#手动安装" aria-hidden="true">#</a> 手动安装</h4>
<ol>
<li>安装 pip 包<code>nonebot-bison</code></li>
<li>在<code>bot.py</code>中导入插件<code>nonebot_bison</code></li>
</ol>
<h3 id="自动安装" tabindex="-1"><a class="header-anchor" href="#自动安装" aria-hidden="true">#</a> 自动安装</h3>
<p>使用<code>nb-cli</code>执行：<code>nb plugin install nonebot_bison</code></p>
<h2 id="配置" tabindex="-1"><a class="header-anchor" href="#配置" aria-hidden="true">#</a> 配置</h2>
<p>可参考<a href="https://github.com/felinae98/nonebot-bison/blob/main/src/plugins/nonebot_bison/plugin_config.py" target="_blank" rel="noopener noreferrer">源文件<ExternalLinkIcon/></a></p>
<ul>
<li><code>BISON_CONFIG_PATH</code>: 插件存放配置文件的位置，如果不设定默认为项目目录下的<code>data</code>目录</li>
<li><code>BISON_USE_PIC</code>: 将文字渲染成图片后进行发送，多用于规避风控</li>
<li><code>BISON_BROWSER</code>: 本插件使用 Chrome 来渲染图片
<ul>
<li>使用 browserless 提供的 Chrome 管理服务，设置为<code>ws://xxxxxxxx</code>，值为 Chrome Endpoint（推荐）</li>
<li>使用 cdp 连接相关服务，设置为<code>wsc://xxxxxxxxx</code></li>
<li>使用本地安装的 Chrome，设置为<code>local:&lt;chrome path&gt;</code>，例如<code>local:/usr/bin/google-chrome-stable</code></li>
<li>如果不进行配置，那么会在启动时候自动进行安装，在官方的 docker 镜像中已经安装了浏览器<div class="custom-container warning"><p class="custom-container-title">WARNING</p>
<p>截止发布时，本项目尚不能完全与 browserless 兼容，目前建议使用镜像内自带的浏览器，即
不要配置这个变量</p>
</div>
</li>
</ul>
</li>
<li><code>BISON_SKIP_BROWSER_CHECK</code>: 是否在启动时自动下载浏览器，如果选择<code>False</code>会在用到浏览器时自动下载，
默认<code>True</code></li>
<li><code>BISON_OUTER_URL</code>: 从外部访问服务器的地址，默认为<code>http://localhost:8080/bison</code>，如果你的插件部署
在服务器上，建议配置为<code>http://&lt;你的服务器ip&gt;:8080/bison</code></li>
<li><code>BISON_FILTER_LOG</code>: 是否过滤来自<code>nonebot</code>的 warning 级以下的 log，如果你的 bot 只运行了这个插件可以考虑
开启，默认关</li>
<li><code>BISON_USE_QUEUE</code>: 是否用队列的方式发送消息，降低发送频率，默认开</li>
<li><code>BISON_RESEND_TIMES</code>: 最大重发次数，默认 0</li>
<li><code>BISON_USE_PIC_MERGE</code>: 是否启用多图片时合并转发（仅限群）
<ul>
<li><code>0</code>: 不启用(默认)</li>
<li><code>1</code>: 首条消息单独发送，剩余图片合并转发</li>
<li><code>2</code>: 所有消息全部合并转发<details class="custom-container details"><summary>配置项示例</summary>
<ul>
<li>当<code>BISON_USE_PIC_MERGE=1</code>时:
<img src="@source/usage/pic/forward-msg-simple1.png" alt="simple1"></li>
<li>当<code>BISON_USE_PIC_MERGE=2</code>时:
<img src="@source/usage/pic/forward-msg-simple2.png" alt="simple1"></li>
</ul>
</details>
<div class="custom-container warning"><p class="custom-container-title">WARNING</p>
<p>启用此功能时，可能会因为待推送图片过大/过多而导致文字消息与合并转发图片消息推送间隔过大(选择模式<code>1</code>时)，请谨慎考虑开启。或者选择模式<code>2</code>，使图文消息一同合并转发(可能会使消息推送延迟过长)</p>
</div>
</li>
</ul>
</li>
</ul>
<h2 id="使用" tabindex="-1"><a class="header-anchor" href="#使用" aria-hidden="true">#</a> 使用</h2>
<div class="custom-container warning"><p class="custom-container-title">WARNING</p>
<p>本节假设<code>COMMAND_START</code>设置中包含<code>''</code>，如果出现 bot 不响应的问题，请先
排查这个设置</p>
</div>
<h3 id="命令" tabindex="-1"><a class="header-anchor" href="#命令" aria-hidden="true">#</a> 命令</h3>
<h4 id="在本群中进行配置" tabindex="-1"><a class="header-anchor" href="#在本群中进行配置" aria-hidden="true">#</a> 在本群中进行配置</h4>
<p>所有命令都需要@bot 触发</p>
<ul>
<li>添加订阅（仅管理员和群主和 SUPERUSER）：<code>添加订阅</code></li>
<li>查询订阅：<code>查询订阅</code></li>
<li>删除订阅（仅管理员和群主和 SUPERUSER）：<code>删除订阅</code></li>
</ul>
<h4 id="私聊机器人获取后台地址" tabindex="-1"><a class="header-anchor" href="#私聊机器人获取后台地址" aria-hidden="true">#</a> 私聊机器人获取后台地址</h4>
<p><code>后台管理</code>，之后点击返回的链接<br>
如果你是 superuser，那么你可以管理所有群的订阅；如果你是 bot 所在的群的其中部分群的管理，
你可以管理你管理的群里的订阅；如果你不是任意一个群的管理，那么 bot 将会报错。</p>
<div class="custom-container tip"><p class="custom-container-title">TIP</p>
<p>可以和 bot 通过临时聊天触发</p>
</div>
<div class="custom-container warning"><p class="custom-container-title">WARNING</p>
<p>网页的身份鉴别机制全部由 bot 返回的链接确定，所以这个链接并不能透露给别人。
并且链接会过期，所以一段时间后需要重新私聊 bot 获取新的链接。</p>
</div>
<h4 id="私聊机器人进行配置-需要-superuer-权限" tabindex="-1"><a class="header-anchor" href="#私聊机器人进行配置-需要-superuer-权限" aria-hidden="true">#</a> 私聊机器人进行配置（需要 SUPERUER 权限）</h4>
<ul>
<li>添加订阅：<code>管理-添加订阅</code></li>
<li>查询订阅：<code>管理-查询订阅</code></li>
<li>删除订阅：<code>管理-删除订阅</code></li>
</ul>
<h3 id="所支持平台的-uid" tabindex="-1"><a class="header-anchor" href="#所支持平台的-uid" aria-hidden="true">#</a> 所支持平台的 uid</h3>
<h4 id="weibo" tabindex="-1"><a class="header-anchor" href="#weibo" aria-hidden="true">#</a> Weibo</h4>
<ul>
<li>对于一般用户主页<code>https://weibo.com/u/6441489862?xxxxxxxxxxxxxxx</code>，<code>/u/</code>后面的数字即为 uid</li>
<li>对于有个性域名的用户如：<code>https://weibo.com/arknights</code>，需要点击左侧信息标签下“更多”，链接为<code>https://weibo.com/6279793937/about</code>，其中中间数字即为 uid</li>
</ul>
<h4 id="bilibili" tabindex="-1"><a class="header-anchor" href="#bilibili" aria-hidden="true">#</a> Bilibili</h4>
<p>主页链接一般为<code>https://space.bilibili.com/161775300?xxxxxxxxxx</code>，数字即为 uid</p>
<h4 id="rss" tabindex="-1"><a class="header-anchor" href="#rss" aria-hidden="true">#</a> RSS</h4>
<p>RSS 链接即为 uid</p>
<h4 id="网易云音乐-歌手" tabindex="-1"><a class="header-anchor" href="#网易云音乐-歌手" aria-hidden="true">#</a> 网易云音乐-歌手</h4>
<p>在网易云网页上歌手的链接一般为<code>https://music.163.com/#/artist?id=32540734</code>，<code>id=</code>
后面的数字即为 uid</p>
<h4 id="网易云音乐-电台" tabindex="-1"><a class="header-anchor" href="#网易云音乐-电台" aria-hidden="true">#</a> 网易云音乐-电台</h4>
<p>在网易云网页上电台的链接一般为<code>https://music.163.com/#/djradio?id=793745436</code>，<code>id=</code>
后面的数字即为 uid</p>
</template>
