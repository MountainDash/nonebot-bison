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
    ],
  },
  {
    text: "开发",
    icon: "flask",
    link: "/dev/",
  },
]);
