---
prev: /usage/
next: /usage/install
---

# :cookie: Bison 的自行车电助力装置

Bison 支持 Cookie 啦，你可以将 Cookie 关联到订阅以获得更好的体验。

但是，盲目使用 Cookie 功能并不能解决问题，反而可能为你的账号带来风险。请阅读完本文档后再决定是否使用 Cookie 功能。

::: warning 免责声明
Bison 具有良好的风控应对机制，我们会尽力保护你的账户，但是无法保证绝对的安全。

nonebot-bison 开发者及 MountainDash 社区不对因使用 Cookie 导致的任何问题负责。
:::

## :monocle_face: 什么时候需要 Cookie？

首先，请确认 Cookie 的使用场景，并了解注意事项。

在绝大多数情况下，Bison 不需要 Cookie 即可正常工作。但是，部分平台只能够获取有限的内容，此时，Cookie 就可以帮助 Bison 获取更多的内容。

例如，微博平台可以设置微博为“仅粉丝可见”，正常情况下 Bison 无法获取到这些内容。如果你的账号是该博主的粉丝，那么你可以将你的 Cookie 关联到 Bison，这样 Bison 就可以获取到这些受限内容。

::: warning 使用须知
Cookie 全局生效，这意味着，通过你的 Cookie 获取到的内容，可能会被共享给其他用户。

当然，Bison 不会将你的 Cookie 透露给其他用户。但是，管理员或其他可以接触的数据库的人员可以看到**所有 Cookie**的内容。所以，在上传 Cookie 之前，请确保管理人员可信。
:::

## :wheelchair: 我该怎么使用 Cookie？

首先，需要明确的是，因为 Cookie 具有隐私性，所有与 Cookie 相关的操作，仅支持**管理员**通过**私聊**或者通过**WebUI**进行管理。

目前，使用 Cookie 主要有两个步骤：

- **添加 Cookie**: 将 Cookie 发给 Bison
- **关联 Cookie**: 告诉 Bison，你希望在什么时候使用这个 Cookie

## :nerd_face: 如何获取 Cookie？

对于大部分平台，Bison 支持 JSON 格式的 Cookie，你可以通过浏览器的开发者工具获取。

- RSS: 对于各种 RSS 订阅，你需要自行准备需要的 Cookie，以 JSON 格式添加即可
- 微博：Bison 兼容 RSSHub 的 Cookie，以下方法引用自[RSSHub 的文档](https://docs.rsshub.app/zh/deploy/config#%E5%BE%AE%E5%8D%9A)
  > 1. 打开并登录 https://m.weibo.cn（确保打开页面为手机版，如果强制跳转电脑端可尝试使用可更改 UserAgent 的浏览器插件）
  > 2. 按下 F12 打开控制台，切换至 Network（网络）面板
  > 3. 在该网页切换至任意关注分组，并在面板打开最先捕获到的请求（该情形下捕获到的请求路径应包含/feed/group）
  > 4. 查看该请求的 Headers（请求头）, 找到 Cookie 字段并复制内容
- Bilibili: Bison 兼容 RSSHub 的 Cookie，以下方法引用自[RSSHub 的文档](https://docs.rsshub.app/zh/deploy/config#bilibili)
  > 1. 打开 https://api.vc.bilibili.com/dynamic_svr/v1/dynamic_svr/dynamic_new?uid=0&type=8
  > 2. 打开控制台，切换到 Network 面板，刷新
  > 3. 点击 dynamic_new 请求，找到 Cookie
  > 4. 视频和专栏，UP 主粉丝及关注只要求 SESSDATA 字段，动态需复制整段 Cookie

## :sparkles: 给 Bison 添加 Cookie

打开 Bison 的私聊，发送 `添加cookie` 命令，Bison 会开始添加 Cookie 流程。
![add cookie](/images/add-cookie.png)

然后，依次输入平台名称和 Cookie 内容。
![add cookie 2](/images/add-cookie-2.png)

看到 Bison 的回复之后，Cookie 就添加成功啦！

## :children_crossing: 关联 Cookie 到具体的订阅

接下来要关联 Cookie 到一个具体的订阅。

输入 `添加关联cookie` 命令，Bison 就会列出当前所有的订阅。

我们选择一个订阅，Bison 会列出所有的可以选择的 Cookie。

![add-cookie-target.png](/images/add-cookie-target.png)

再选择需要关联的 Cookie。

至此，Bison 便会携带我们的 Cookie 去请求订阅目标啦！

## :stethoscope: 取消关联 Cookie

如果你想取消关联某个 Cookie，可以发送 `取消关联cookie` 命令，Bison 会列出所有已被关联的订阅和 Cookie。

选择需要取消关联的 Cookie，Bison 会取消此 Cookie 对该订阅的关联。

这是 `添加关联cookie` 的逆向操作。

## :wastebasket: 删除 Cookie

如果你想删除某个 Cookie，可以发送 `删除cookie` 命令，Bison 会列出所有已添加的 Cookie。

选择需要删除的 Cookie，Bison 会删除此 Cookie。

::: tip
只能删除未被关联的 Cookie。

也就是说，你需要先取消一个 Cookie 的所有关联，才能删除。
:::

这是 `添加cookie` 的逆向操作。

## :globe_with_meridians: 使用 WebUI 管理 Cookie

同样的，Bison 提供了一个网页管理 Cookie 的功能，即 WebUI，你可以在网页上查看、添加、删除 Cookie。

使用方法参见 [使用网页管理订阅](/usage/easy-use#使用网页管理订阅)。

## :tada: 完成！

至此，你已经掌握了使用 Cookie 的方法。

Congratulations! 🎉
