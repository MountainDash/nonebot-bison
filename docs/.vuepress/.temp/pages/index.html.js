export const data = {
  "key": "v-8daa1a0e",
  "path": "/",
  "title": "",
  "lang": "en-US",
  "frontmatter": {
    "home": true,
    "heroText": "Nonebot Bison",
    "tagline": "本bot励志做全泰拉骑车最快的信使",
    "actionText": "快速部署",
    "actionLink": "/usage/",
    "features": [
      {
        "title": "拓展性强",
        "details": "没有自己想要的网站？只要简单的爬虫知识就可以给它适配一个新的网站"
      },
      {
        "title": "通用，强大",
        "details": "社交媒体？网站更新？游戏开服？只要能爬就都能推，还支持自定义过滤"
      },
      {
        "title": "后台管理",
        "details": "提供后台管理页面，简单快捷修改配置"
      }
    ],
    "footer": "MIT Licensed"
  },
  "excerpt": "",
  "headers": [],
  "git": {
    "updatedTime": 1644411914000,
    "contributors": [
      {
        "name": "felinae98",
        "email": "731499577@qq.com",
        "commits": 7
      },
      {
        "name": "hemengyang",
        "email": "hmy0119@gmail.com",
        "commits": 1
      }
    ]
  },
  "filePathRelative": "README.md"
}

if (import.meta.webpackHot) {
  import.meta.webpackHot.accept()
  if (__VUE_HMR_RUNTIME__.updatePageData) {
    __VUE_HMR_RUNTIME__.updatePageData(data)
  }
}

if (import.meta.hot) {
  import.meta.hot.accept(({ data }) => {
    __VUE_HMR_RUNTIME__.updatePageData(data)
  })
}
