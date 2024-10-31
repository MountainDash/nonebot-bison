import { navbar } from "vuepress-theme-hope";

export default navbar([
  "/",
  {
    text: "指南",
    icon: "book",
    prefix: "/usage/",
    children: [
      {
        text: "安装",
        icon: "box-open",
        link: "install",
      },
      {
        text: "快速开始",
        icon: "truck-fast",
        link: "easy-use",
      },
      {
        text: "详细介绍",
        icon: "motorcycle",
        link: "",
        activeMatch: "^/usage/?$",
      },
      {
        text: "Cookie 使用",
        icon: "cookie",
        link: "cookie",
      },
    ],
  },
  {
    text: "开发",
    icon: "flask",
    prefix: "/dev/",
    children: [
      {
        text: "基本开发",
        icon: "tools",
        link: "",
        activeMatch: "^/dev/?$",
      },
      {
        text: "Cookie 开发",
        icon: "cookie",
        link: "cookie",
      },
    ],
  },
]);
