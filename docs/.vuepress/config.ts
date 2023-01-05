import { defineUserConfig, defaultTheme } from "vuepress";

export default defineUserConfig({
  title: "Nonebot Bison",
  description: "Docs for Nonebot Bison",
  theme: defaultTheme({
    navbar: [
      { text: "主页", link: "/" },
      { text: "部署与使用", link: "/usage/" },
      { text: "开发", link: "/dev/" },
      { text: "Github", link: "https://github.com/felinae98/nonebot-bison" },
    ],
  }),
});
