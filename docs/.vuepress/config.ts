import { defineUserConfig } from "vuepress";
import theme from "./theme.js";
import { mdEnhancePlugin } from "vuepress-plugin-md-enhance";

export default defineUserConfig({
  base: "/",

  lang: "zh-CN",
  title: "NoneBot Bison",
  description: "NoneBot Bison 文档",
  plugins: [
    mdEnhancePlugin({
      mermaid: true,
    }),
  ],

  theme,

  // 和 PWA 一起启用
  // shouldPrefetch: false,
});
