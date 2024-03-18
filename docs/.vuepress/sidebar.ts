import { sidebar } from "vuepress-theme-hope";

export default sidebar({
  "/": [
    "",
    {
      text: "指南",
      icon: "laptop-code",
      prefix: "usage/",
      children: "structure",
    },
    {
      text: "开发",
      icon: "terminal",
      prefix: "dev/",
      children: "structure",
    },
    {
      text: "相关",
      icon: "person-chalkboard",
      children: [
        {
          text: "Nonebot-Bison",
          link: "https://github.com/MountainDash/nonebot-bison",
        },
        {
          text: "Nonebot-Plugin-SAA",
          link: "https://github.com/MountainDash/nonebot-plugin-send-anything-anywhere",
        },
        {
          text: "MountainDash",
          link: "https://github.com/MountainDash/",
        },
      ],
    },
  ],
});
