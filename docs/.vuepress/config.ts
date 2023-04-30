import { defineUserConfig, defaultTheme } from "vuepress";

export default defineUserConfig({
  lang: "zh-CN",
  title: "Nonebot Bison",
  description: "Docs for Nonebot Bison",
  theme: defaultTheme({
    navbar: [
      { text: "主页", link: "/" },
      {
        text: "上车",
        children: [
          {
            text: "安装",
            link: "/usage/install.md",
            activeMatch: "^/usage/install",
          },
          {
            text: "简单使用",
            link: "/usage/easy-use.md",
            activeMatch: "^/usage/easy-use",
          },
          {
            text: "详细配置",
            link: "/usage",
            activeMatch: "^/usage$",
          },
        ],
      },
      { text: "开发", link: "/dev/" },
      { text: "Github", link: "https://github.com/felinae98/nonebot-bison" },
    ],
  }),
});
