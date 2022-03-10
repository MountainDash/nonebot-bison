<template><h1 id="开发指南" tabindex="-1"><a class="header-anchor" href="#开发指南" aria-hidden="true">#</a> 开发指南</h1>
<p>本插件需要你的帮助！只需要会写简单的爬虫，就能给本插件适配新的网站。</p>
<h2 id="基本概念" tabindex="-1"><a class="header-anchor" href="#基本概念" aria-hidden="true">#</a> 基本概念</h2>
<ul>
<li><code>nonebot_bison.post.Post</code>: 可以理解为推送内容，其中包含需要发送的文字，图片，链接，平台信息等</li>
<li><code>nonebot_bison.types.RawPost</code>: 从站点/平台中爬到的单条信息</li>
<li><code>nonebot_bison.types.Target</code>: 目标账号，Bilibili，微博等社交媒体中的账号</li>
<li><code>nonebot_bison.types.Category</code>: 信息分类，例如视频，动态，图文，文章等</li>
<li><code>nonebot_bison.types.Tag</code>: 信息标签，例如微博中的超话或者 hashtag</li>
</ul>
<h2 id="快速上手" tabindex="-1"><a class="header-anchor" href="#快速上手" aria-hidden="true">#</a> 快速上手</h2>
<p>上车！我们走</p>
<p>先明确需要适配的站点类型，先明确两个问题：</p>
<h4 id="我要发送什么样的推送" tabindex="-1"><a class="header-anchor" href="#我要发送什么样的推送" aria-hidden="true">#</a> 我要发送什么样的推送</h4>
<ul>
<li><code>nonebot_bison.platform.platform.NewMessage</code> 最常见的类型，每次爬虫向特定接口爬取一个消息列表，
与之前爬取的信息对比，过滤出新的消息，再根据用户自定义的分类和标签进行过滤，最后处理消息，把
处理过后的消息发送给用户<br>
例如：微博，Bilibili</li>
<li><code>nonebot_bison.platform.platform.StatusChange</code> 每次爬虫获取一个状态，在状态改变时发布推送<br>
例如：游戏开服提醒，主播上播提醒</li>
<li><code>nonebot_bison.platform.platform.SimplePost</code> 与<code>NewMessage</code>相似，但是不过滤新的消息
，每次发送全部消息<br>
例如：每日榜单定时发送</li>
</ul>
<h4 id="这个平台是否有账号的概念" tabindex="-1"><a class="header-anchor" href="#这个平台是否有账号的概念" aria-hidden="true">#</a> 这个平台是否有账号的概念</h4>
<ul>
<li>有账号的概念<br>
例如：B 站用户动态，微博用户动态，网易云电台更新</li>
<li>没有账号的概念<br>
例如：游戏公告，教务处公告</li>
</ul>
<p>现在你需要在<code>src/plugins/nonebot_bison/platform</code>下新建一个 py 文件，
在里面新建一个类，继承推送类型的基类，重载一些关键的函数，然后……就完成了，不需要修改别的东西了。</p>
<p>任何一种订阅类型需要实现的方法/字段如下：</p>
<ul>
<li><code>schedule_type</code>, <code>schedule_kw</code> 调度的参数，本质是使用 apscheduler 的<a href="https://apscheduler.readthedocs.io/en/3.x/userguide.html?highlight=trigger#choosing-the-right-scheduler-job-store-s-executor-s-and-trigger-s" target="_blank" rel="noopener noreferrer">trigger 参数<ExternalLinkIcon/></a>，<code>schedule_type</code>可以是<code>date</code>,<code>interval</code>和<code>cron</code>，
<code>schedule_kw</code>是对应的参数，一个常见的配置是<code>schedule_type=interval</code>, <code>schedule_kw={'seconds':30}</code></li>
<li><code>is_common</code> 是否常用，如果被标记为常用，那么和机器人交互式对话添加订阅时，会直接出现在选择列表中，否则
需要输入<code>全部</code>才会出现。</li>
<li><code>enabled</code> 是否启用</li>
<li><code>name</code> 平台的正式名称，例如<code>微博</code></li>
<li><code>has_target</code> 平台是否有“帐号”</li>
<li><code>category</code> 平台的发布内容分类，例如 B 站包括专栏，视频，图文动态，普通动态等，如果不包含分类功能则设为<code>{}</code></li>
<li><code>enable_tag</code> 平台发布内容是否带 Tag，例如微博</li>
<li><code>platform_name</code> 唯一的，英文的识别标识，比如<code>weibo</code></li>
<li><code>async get_target_name(Target) -&gt; Optional[str]</code> 通常用于获取帐号的名称，如果平台没有帐号概念，可以直接返回平台的<code>name</code></li>
<li><code>async parse(RawPost) -&gt; Post</code>将获取到的 RawPost 处理成 Post</li>
<li><code>get_tags(RawPost) -&gt; Optional[Collection[Tag]]</code> （可选） 从 RawPost 中提取 Tag</li>
<li><code>get_category(RawPos) -&gt; Optional[Category]</code> （可选）从 RawPost 中提取 Category</li>
</ul>
<p>例如要适配微博，我希望 bot 搬运新的消息，所以微博的类应该这样定义：</p>
<div class="language-python ext-py line-numbers-mode"><pre v-pre class="language-python"><code><span class="token keyword">class</span> <span class="token class-name">Weibo</span><span class="token punctuation">(</span>NewMessage<span class="token punctuation">)</span><span class="token punctuation">:</span>

    categories <span class="token operator">=</span> <span class="token punctuation">{</span>
        <span class="token number">1</span><span class="token punctuation">:</span> <span class="token string">"转发"</span><span class="token punctuation">,</span>
        <span class="token number">2</span><span class="token punctuation">:</span> <span class="token string">"视频"</span><span class="token punctuation">,</span>
        <span class="token number">3</span><span class="token punctuation">:</span> <span class="token string">"图文"</span><span class="token punctuation">,</span>
        <span class="token number">4</span><span class="token punctuation">:</span> <span class="token string">"文字"</span><span class="token punctuation">,</span>
    <span class="token punctuation">}</span>
    enable_tag <span class="token operator">=</span> <span class="token boolean">True</span>
    platform_name <span class="token operator">=</span> <span class="token string">"weibo"</span>
    name <span class="token operator">=</span> <span class="token string">"新浪微博"</span>
    enabled <span class="token operator">=</span> <span class="token boolean">True</span>
    is_common <span class="token operator">=</span> <span class="token boolean">True</span>
    schedule_type <span class="token operator">=</span> <span class="token string">"interval"</span>
    schedule_kw <span class="token operator">=</span> <span class="token punctuation">{</span><span class="token string">"seconds"</span><span class="token punctuation">:</span> <span class="token number">3</span><span class="token punctuation">}</span>
    has_target <span class="token operator">=</span> <span class="token boolean">True</span>
</code></pre><div class="line-numbers" aria-hidden="true"><span class="line-number">1</span><br><span class="line-number">2</span><br><span class="line-number">3</span><br><span class="line-number">4</span><br><span class="line-number">5</span><br><span class="line-number">6</span><br><span class="line-number">7</span><br><span class="line-number">8</span><br><span class="line-number">9</span><br><span class="line-number">10</span><br><span class="line-number">11</span><br><span class="line-number">12</span><br><span class="line-number">13</span><br><span class="line-number">14</span><br><span class="line-number">15</span><br><span class="line-number">16</span><br></div></div><p>当然我们非常希望你对自己适配的平台写一些单元测试，你可以模仿<code>tests/platforms/test_*.py</code>中的内容写
一些单元测试。为保证多次运行测试的一致性，可以 mock http 的响应，测试的内容包括获取 RawPost，处理成 Post
，测试分类以及提取 tag 等，当然最好和 rsshub 做一个交叉验证。</p>
<div class="custom-container danger"><p class="custom-container-title">DANGER</p>
<p>Nonebot 项目使用了全异步的处理方式，所以你需要对异步，Python asyncio 的机制有一定了解，当然，
依葫芦画瓢也是足够的</p>
</div>
<h2 id="类的方法与成员变量" tabindex="-1"><a class="header-anchor" href="#类的方法与成员变量" aria-hidden="true">#</a> 类的方法与成员变量</h2>
<h2 id="方法与变量的定义" tabindex="-1"><a class="header-anchor" href="#方法与变量的定义" aria-hidden="true">#</a> 方法与变量的定义</h2>
</template>
