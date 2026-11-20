# NoneBot-Bison: Technical Archaeology Report

**Target:** `MountainDash/nonebot-bison` — a NoneBot2 plugin that polls social-media sources and pushes new posts to chat platforms.
**Snapshot analyzed:** `main` @ `c891b9282129066a7e05ad0d8a25fd1eb7bb1df2` (commit date 2026-08-12), version `0.9.14`.
**Method:** shallow clone of `main` + all 106 remote branches, GitHub issues/PR corpus (843 issues+PRs), CHANGELOG, docs site, SAA (sender abstraction) README. Facts derived from code are marked *(derived)* with file/line links.

**Premise corrections up front (important for the redesign):**
- Twitter/X is **not** a native platform. There is no `twitter.py`. Twitter is ingested through the generic **RSS** platform pointed at an RSSHub route (fixtures `tests/platforms/static/rss-twitter-ArknightsStaff.xml`, and issue #704 uses `rsshub.app/twitter/user/...`).
- Discord/Telegram are **send-side only**, via `nonebot-plugin-send-anything-anywhere` (SAA) adapters (Telegram and Discord are both ✅ in SAA's adapter table). Bison itself ships with OneBot v11 required, QQ-official + Satori optional.
- The repo has **no** `v1/` and `v2/` directories. "v1/v2/v3" in bison-speak means three different things: (a) the nbesf **file format** versions 1/2/3, (b) the tinydb→sqlite era, (c) the abandoned v3 rewrite branches (`renew/*`).

---

## 1. Repo structure and module layout

### 1.1 Top level

```
nonebot_bison/          # the plugin (9,371 lines of Python)
admin-frontend/         # React + Redux + arco-design SPA (ships prebuilt into admin_page/dist)
docs/                   # VuePress (theme-hope) docs → https://nonebot-bison.netlify.app/
docker/                 # Dockerfile, Dockerfile_without_browser, prometheus.yml, grafana dashboards
tests/                  # 39 test_*.py files, 161 test functions
extra_plugins/          # auto_agree.py (group-join auto-accept helper)
pyproject.toml          # version 0.9.14, requires-python >=3.10,<4
```

`nonebot_bison/__init__.py` imports and exports exactly: `admin_page, bootstrap, config, platform, post, scheduler, send, sub_manager, theme, types, utils` ([`__init__.py#L75-L86`](https://github.com/MountainDash/nonebot-bison/blob/main/nonebot_bison/__init__.py#L75-L86)).

### 1.2 `platform/` — fetchers ("platforms" and "sites")

Layout:

```
nonebot_bison/platform/
├── platform.py                 # 504 lines: ALL base classes live here
├── weibo.py                    # Weibo(NewMessage)
├── rss.py                      # Rss(NewMessage)
├── arknights.py                # 4 classes: Arknights, AkVersion, MonsterSiren, TerraHistoricusComic
├── ncm.py                      # NcmArtist, NcmRadio
├── ff14.py                     # FF14
├── bilibili/                   # the only multi-file platform
│   ├── platforms.py  (552 L)   # Bilibili, Bilibililive, BilibiliBangumi
│   ├── scheduler.py            # BilibiliSite/BililiveSite/BiliBangumiSite + BilibiliClientManager
│   ├── models.py     (403 L)   # pydantic models of the B站 dynamic API
│   ├── retry.py      (261 L)   # 352-error state machine
│   └── fsm.py                  # generic FSM used by retry.py
└── ceobecanteen/               # platform.py, cache.py (hishel HTTP cache), models.py, const.py, utils.py
```

**Inventory (exact counts, from code):** 12 concrete platform classes over **10 distinct `platform_name` values** — `bilibili`, `bilibili-live`, `bilibili-bangumi`, `weibo`, `rss`, `arknights` (4 classes share it, aggregated by `make_no_target_group`), `ncm-artist`, `ncm-radio`, `ff14`, `ceobecanteen`. Docs advertise 10 platforms ([docs home](https://nonebot-bison.netlify.app/)).

Only **one** platform uses the batch API (`use_batch = True`): `Bilibililive` ([`bilibili/platforms.py:324`](https://github.com/MountainDash/nonebot-bison/blob/main/nonebot_bison/platform/bilibili/platforms.py#L324)). Everything else polls one target per request.

### 1.3 Base classes / abstract interfaces (the real API surface)

All in [`platform/platform.py`](https://github.com/MountainDash/nonebot-bison/blob/main/nonebot_bison/platform/platform.py):

| Class | Role | Key abstract methods |
|---|---|---|
| `Platform` | root ABC, `base=True` | `get_target_name()`, `fetch_new_post()`, `batch_fetch_new_post()`, `parse()`, `get_category()`, `get_tags()` |
| `MessageProcess(Platform)` | adds id/date/category filtering + `parse_cache` | `get_id()`, `get_sub_list()`, `batch_get_sub_list()`, `get_date()` |
| `NewMessage(MessageProcess)` | fetch list → diff against seen ids → dispatch | — (`_handle_new_post`) |
| `StatusChange(Platform)` | watch a scalar status, fire on change | `get_status()`, `batch_get_status()`, `compare_status()` |
| `SimplePost(NewMessage)` | send everything each poll, no dedupe | — |

Class attributes are the declarative contract: `platform_name`, `name`, `site`, `categories: dict[int,str]`, `enable_tag`, `has_target`, `is_common`, `enabled`, `default_theme`, `use_batch`, `parse_target_promot`.

**Registration is metaclass magic, not config:** `RegistryMeta` appends every non-abstract subclass to `cls.registry`; `PlatformMeta` builds `reverse_category`; abstract bases are flagged with `**{"abstract": True}` kwargs, and the root with `base=True` ([`platform.py#L27-L80`](https://github.com/MountainDash/nonebot-bison/blob/main/nonebot_bison/platform/platform.py#L27-L80)). `Site` has its own `SiteMeta` registering into `site_manager` by `name` ([`utils/site.py#L158-L180`](https://github.com/MountainDash/nonebot-bison/blob/main/nonebot_bison/utils/site.py#L158-L180)).

`make_no_target_group()` synthesizes a virtual platform class at import time to merge the four `arknights` classes into one "site without a target" — it raises at import if two subclasses declare conflicting categories or different `Site`s.

The "developer guide" formalizes the contract in prose: implement `get_sub_list` + `get_id` (+ optional `get_date`) and "就完成了~(??)~，不需要修改别的东西了" ([docs/dev/README.md](https://raw.githubusercontent.com/MountainDash/nonebot-bison/main/docs/dev/README.md)).

### 1.4 `post/` — the message payload

- `Post` is a **dataclass** holding `platform, content, title, images, timestamp, url, avatar, nickname, description, repost` ([`post/post.py#L24-L56`](https://github.com/MountainDash/nonebot-bison/blob/main/nonebot_bison/post/post.py#L24-L56)).
- `AbstractPost` adds `compress`, `extra_msg`, and the send pipeline `generate()` → `message_segments_process()` (optionally converts every `Text` to an image when `BISON_USE_PIC`) → `message_process()` ([`post/abstract_post.py`](https://github.com/MountainDash/nonebot-bison/blob/main/nonebot_bison/post/abstract_post.py)).
- Content-shape is negotiated by `Protocol`s: `PlainContentSupport`, `HTMLContentSupport`, `MarkdownContentSupport` ([`post/protocol.py`](https://github.com/MountainDash/nonebot-bison/blob/main/nonebot_bison/post/protocol.py)).

### 1.5 `theme/` — renderers

5 themes, registered by `__theme_meta__` convention at startup: `basic`, `brief` (pure code), `arknights`, `ht2i`, `ceobecanteen` (`need_browser = True`, require `nonebot_plugin_htmlrender`/Playwright).

`Theme` is a pydantic `BaseModel` ABC with `name`, `need_browser`, `is_support_render()`, and abstract `render(post) -> list[MessageSegmentFactory]` ([`theme/types.py`](https://github.com/MountainDash/nonebot-bison/blob/main/nonebot_bison/theme/types.py)). Failures raise `ThemeRenderUnsupportError` / `ThemeRenderError`, which drive fallback.

### 1.6 `scheduler/` — APScheduler + weighted round-robin

- `manager.init_scheduler()` groups all `Target` rows by their `Site` class and creates **one `Scheduler` per Site**, i.e. **one APScheduler job per site**; sites whose `require_browser` is set are skipped when `BISON_USE_BROWSER=false` ("{site} requires browser, it will not schedule.") ([`scheduler/manager.py`](https://github.com/MountainDash/nonebot-bison/blob/main/nonebot_bison/scheduler/manager.py)).
- `scheduler.add_job(self.exec_fetch, site.schedule_type, **site.schedule_setting)` — plain APScheduler interval triggers, **no jitter, no max_instances tuning, no coalesce tuning** ([`scheduler/scheduler.py#L61-L65`](https://github.com/MountainDash/nonebot-bison/blob/main/nonebot_bison/scheduler/scheduler.py#L61-L65)).
- Each tick fetches **exactly one** `Schedulable` (one target), chosen by weighted round-robin: `weight += current_weight_val; pick max; picked -= sum(weights)` ([`scheduler.py#L73-L87`](https://github.com/MountainDash/nonebot-bison/blob/main/nonebot_bison/scheduler/scheduler.py#L73-L87)). Weights come from the DB: `Target.default_schedule_weight` (default `10`) plus `ScheduleTimeWeight` rows (per time-of-day).
- Newly added targets are inserted with weight `1000` and bump `pre_weight_val += 1000` (instant first fetch).

**Configured intervals (verbatim from code):**

| Site | `schedule_type` | `schedule_setting` | Source |
|---|---|---|---|
| `bilibili.com` | interval | `{"seconds": 60}` | `bilibili/scheduler.py:118-123` |
| `live.bilibili.com` | interval | `{"seconds": 5}` | `bilibili/scheduler.py:126-130` |
| `bilibili.com/bangumi` | interval | `{"seconds": 30}` | `bilibili/scheduler.py:132-136` |
| `weibo.com` | interval | `{"seconds": 10}` | `weibo.py:78-82` |
| `rss` | interval | `{"seconds": 30}` | `rss.py:17-21` |
| `arknights` | interval | `{"seconds": 30}` | `arknights.py:59-62` |
| `ncm` | interval | `{"minutes": 1}` | `ncm.py:13-16` |
| `ceobecanteen` | interval | `{"seconds": 15}` | `ceobecanteen/platform.py:47-51` |
| `ff14` | interval | `{"seconds": 60}` (via `anonymous_site`) | `ff14.py:20` |

*(derived)* Because each tick handles one target and APScheduler's default `max_instances=1`, the **effective per-target poll period is `N_targets × interval`**. 100 weibo targets ⇒ each target re-checked every ~16.7 min. Weibo was deliberately slowed from 3s to 10s ("将 weibo 的调度间隔减慢为 10s 一次", PR #725, v0.9.11) — i.e. the interval knob is being used as a rate-limit lever.

### 1.7 `send.py` — the send path

A module-global `collections.deque` plus **one** dispatcher coroutine; spacing is a hard-coded module constant `MESSGE_SEND_INTERVAL = 1.5` seconds **globally, not per group** ([`send.py#L13-L15`](https://github.com/MountainDash/nonebot-bison/blob/main/nonebot_bison/send.py#L13-L15)). Retry is `bison_resend_times` (default **0** = no retry) with `appendleft` re-queue. `bison_use_pic_merge` (0/1/2) wraps the tail of a post's messages in SAA's `AggregatedMessageFactory` (QQ合并转发).

Failure handling for OneBot is a single hardcoded `except ActionFailed` → `refresh_bots()`; the code carries its own TODO: `# TODO: catch exception of other adapters` ([`send.py#L22-L27`](https://github.com/MountainDash/nonebot-bison/blob/main/nonebot_bison/send.py#L22-L27)).

### 1.8 Persistence: SQLAlchemy + `nonebot-plugin-datastore` (not JSON)

Six tables ([`config/db_model.py`](https://github.com/MountainDash/nonebot-bison/blob/main/nonebot_bison/config/db_model.py)), all prefixed `nonebot_bison_`:

- `User(id, user_target JSON/JSONB)` — `user_target` stores the **SAA `PlatformTarget` serialized to a dict**; `User.saa_target` deserializes on read.
- `Target(id, platform_name String(20), target String(1024), target_name String(1024), default_schedule_weight int=10)` with `UniqueConstraint("target","platform_name","name"="unique-target-constraint")`.
- `Subscribe(id, target_id FK, user_id FK, categories JSON, tags JSON)` with `UniqueConstraint("target_id","user_id")`.
- `ScheduleTimeWeight(id, target_id, start_time, end_time, weight)`.
- `Cookie(id, site_name, content String(1024), cookie_name, last_usage, status, cd_milliseconds, is_universal, is_anonymous, tags JSON)`.
- `CookieTarget(id, target_id FK CASCADE, cookie_id FK CASCADE)`.

14 Alembic migrations in `config/migrations/` (init → rename tables → add time weight → map user → add cookie → remove old target …). A **legacy tinydb** config still exists (`config/config_legacy.py`, 253 lines) and is auto-migrated at startup: `data_migrate()` logs "You are still using legacy db, migrating to sqlite" and then `drop()`s the old file ([`config/db_migration.py`](https://github.com/MountainDash/nonebot-bison/blob/main/nonebot_bison/config/db_migration.py)).

`bootstrap.py` also does alembic-table surgery: it inspects `alembic_version`, accepts only 5 known revision ids, and renames the table to `nonebot_bison_alembic_version` to avoid colliding with other plugins sharing the DB.

### 1.9 Dedupe: an in-memory set, per process

`NewMessage.filter_common_with_diff()` keeps `class MessageStorage(inited: bool, exists_posts: set[Any])` in `Platform.store: dict[Target, Any]` — a **class-level dict** ([`platform.py#L70-L71`](https://github.com/MountainDash/nonebot-bison/blob/main/nonebot_bison/platform/platform.py#L70-L71), [`#L143-L150`](https://github.com/MountainDash/nonebot-bison/blob/main/nonebot_bison/platform/platform.py#L143-L150), [`#L291-L320`](https://github.com/MountainDash/nonebot-bison/blob/main/nonebot_bison/platform/platform.py#L291-L320)).

- First poll after start with `BISON_INIT_FILTER=true` (default): ids are **recorded but nothing is sent**, logged as `init {platform}-{target} with {...}`.
- Posts older than **2 hours** are dropped, and that drop is *gated on the same flag*: `if (post_time := self.get_date(raw_post)) and time.time() - post_time > 2 * 60 * 60 and plugin_config.bison_init_filter` ([`#L262-L275`](https://github.com/MountainDash/nonebot-bison/blob/main/nonebot_bison/platform/platform.py#L262-L275)).
- `BISON_INIT_FILTER=false` ⇒ the `else` branch runs on the first poll ⇒ **the whole current feed window is treated as new and sent** (mass duplicate risk on every restart).
- Nothing is persisted: restart = amnesia. `parse_cache` (id → `Post`, with 3 retries inside `do_parse`) is also in-memory and cleared every batch ([`#L228-L246`](https://github.com/MountainDash/nonebot-bison/blob/main/nonebot_bison/platform/platform.py#L228-L246)).

### 1.10 `admin_page/`, `sub_manager/`, `metrics.py`

- `admin_page/api.py` = **16 routes** (`/global_conf, /auth, /subs GET/POST/DELETE, /target_name, /weight GET/PUT, /cookie GET/POST/DELETE, /cookie_target GET/POST/DELETE, /cookie/validate`), JWT-ish auth with an in-process `ExpiringDict(capacity=100, default_age=10min)` token store ([`admin_page/token_manager.py`](https://github.com/MountainDash/nonebot-bison/blob/main/nonebot_bison/admin_page/token_manager.py)).
- `sub_manager/` = chat-command FSM (`add_sub, del_sub, query_sub, add_cookie, del_cookie, add_cookie_target, del_cookie_target`).
- `metrics.py` = Prometheus counters/histograms (`bison_request_counter`, `bison_sent_counter`, `bison_cookie_choose_counter`, `bison_request_histogram`, `bison_render_histogram` buckets `0.1…60s`), shipped with a Grafana dashboard in `docker/grafana-dashboard-bison.json`.

---

## 2. Known pain points & failures (with issue numbers and quotes)

**Honest negative result:** a full-text scan of all 180 issues finds **zero** occurrences of 乱序 and zero titles/bodies matching 重复发送/重复推送. Out-of-order and duplicate delivery are therefore **not reported as symptoms** — but both mechanisms are visible in code and in the APScheduler logs (2.1, 2.2). Likewise **no issue reports scale/群数量多 or 内存占用 as such** (the only `内存` hits are bot PR bodies about Pillow CVEs and one design comment). Treat those as *unreported* risks, not as evidence of absence.

### 2.1 APScheduler overlap / missed runs / skipped executions (the runner-up to 乱序)

- **#250 "不断提醒警告信息"** (open, 2023-04-29) — https://github.com/MountainDash/nonebot-bison/issues/250
  > `Run time of job "Scheduler.exec_fetch (trigger: interval[0:00:03], next run at: …)" was missed by 0:00:01.969608`
  > `Execution of job "Scheduler.exec_fetch (trigger: interval[0:00:03] …)" skipped: maximum number of running instances reached (1)`
- **#49 "订阅经常超时"** (closed, 2022) — same `skipped: maximum number of running instances reached (1)` + `httpx.ReadTimeout` — https://github.com/MountainDash/nonebot-bison/issues/49
- **#195** (closed, 2023-02) — same `missed by …` warnings reproduced again — https://github.com/MountainDash/nonebot-bison/issues/195
- **#14** (closed, 2021-07) — same, plus `fetch_and_send (trigger: interval[0:00:30])` — https://github.com/MountainDash/nonebot-bison/issues/14

*(derived)* These are exactly the conditions under which a per-target "last seen id" heuristic degrades: a skipped tick means an entire poll window is never observed.

### 2.2 Risk control / rate limiting (429 / 352 / 403 / `ok:-100`)

- **#602 "订阅"B站"内容报错"** (open, 2024-07-30, 20 comments) — https://github.com/MountainDash/nonebot-bison/issues/602
  > `httpx.HTTPStatusError: ("Client error '429 Too Many Requests' for url 'https://api.vc.bilibili.com/dynamic_svr/v1/dynamic_svr/space_history?…'`, with `'bili-status-code': '-509'`, `'x-bili-retry-after': '3'`
- **#437 "微博也许需要支持登陆模块"** (open, 2023-11, 10 comments) — https://github.com/MountainDash/nonebot-bison/issues/437
  > "在未登录情况下，**部分用户**的微博的风控可能出现问题，导致未登录的用户无法从 `https://m.weibo.cn/api/container/getIndex?containerid=` 接口获取用户数据"
- **#744 "微博按照规则获取token后仍报 "ok":-100"** (open, 2025-10) — https://github.com/MountainDash/nonebot-bison/issues/744
- **#726 "添加b站订阅报错"** (closed) — "个人认为这个问题可能是因为添加时的查询没有cookie，被b站风控了。请问能增加添加订阅时使用cookie查询的功能吗？" — https://github.com/MountainDash/nonebot-bison/issues/726
- **#145 "微博下载图片报错"** (closed) — "由于微博更新了图床防盗链逻辑，导致下载微博图片403。改反扒逻辑是：如果使用了浏览器ua，那么必须加上referer" — https://github.com/MountainDash/nonebot-bison/issues/145
- **README FAQ #3** — "微博漏订阅了 / 微博更新了新的风控措施，某些含有某些关键词的微博会获取不到。" — https://github.com/MountainDash/nonebot-bison/blob/main/README.md
- **#543 "[Feature Request]添加停止整个平台或者某个Target蹲饼的命令"** (open, 2024-05) — the escape hatch that does not exist: https://github.com/MountainDash/nonebot-bison/issues/543
  > "目的: 主要是为了在触发B站风控（使用新Api）后不必关闭掉整个Bison或者手动删除B站的订阅，从而不影响其他平台的蹲饼"
  > "可以在scheduler的schedulable_list中添加一个disable以表示是否禁用？但这样缺乏持久化。"

Code-side reaction: `Bilibili` wraps its dynamic-API call in a **state machine** `NORMAL → REFRESH → BACKOFF → RAISE` with `max_refresh_count=3`, `max_backoff_count=3`, backoff `timedelta(minutes=5) * backoff_count**2` (5/20/45 min) and a literal `if random.random() < 0.1236: refresh_client()` ([`bilibili/retry.py`](https://github.com/MountainDash/nonebot-bison/blob/main/nonebot_bison/platform/bilibili/retry.py)); B站 cookies get `_default_cookie_cd = timedelta(seconds=120)`, weibo 15s (base `CookieClientManager._default_cookie_cd`). The FSM itself carries `# FIXME: 拿出来是方便测试了，但全局单例会导致所有被装饰的函数共享状态，有待改进`.

### 2.3 Render failures (图片渲染失败)

- **#730 "nonebot-plugin-htmlrender0.6.8不兼容此插件了"** (open, 2025-09) — "安装htmlrender0.68版本后出现如下报错，安装0.67后恢复正常" — https://github.com/MountainDash/nonebot-bison/issues/730
- **#699 "nonebot-plugin-htmlrender>=0.6.2 中破坏更新了 capture_element方法, 考虑锁依赖/适配"** (closed) — https://github.com/MountainDash/nonebot-bison/issues/699
- **#526 "Fallback主题渲染时不清理富文本部分"** (closed) — fallback path degrades badly — https://github.com/MountainDash/nonebot-bison/issues/526
- **#732** "修复 ceobecanteen 主题渲染错误"; **#723/#722** "支持分离式渲染" — theme templates break routinely (CHANGELOG v0.9.11/0.9.12).
- **#14** "使用docker运行时偶尔不会自动下载chromium导致无法生成图片" — https://github.com/MountainDash/nonebot-bison/issues/14
- **#236 / #135 / #93** — `require("nonebot_plugin_htmlrender")` import errors at startup.
- **#686 "数据初始化报错，无法推送"** (closed, 2025-01) — not a render bug but a silent total outage: `数据库初始化后执行的函数出错: AsyncClient.__init__() got an unexpected keyword argument 'proxies'` — https://github.com/MountainDash/nonebot-bison/issues/686

### 2.4 Message send failures / retry

- **#678 "个别群聊的订阅始终无法成功发送消息"** (closed, 2025-01) — https://github.com/MountainDash/nonebot-bison/issues/678
  > "有一个群聊不管订阅weibo还是bilibili都无法发送，报错：send msg err <nonebot_plugin_saa.abstract_factories.AggregatedM..." / "其余群聊都能正常发送。"
  (I.e. one group fails permanently on `AggregatedMessageFactory` — 合并转发 — while the rest succeed, and the queue just logs `send msg err` three times.)
- **#737** `ActionFailed(status='failed', retcode=1200, …)` while *adding* a subscription through the FSM — https://github.com/MountainDash/nonebot-bison/issues/737
- **#626** "[bilibili-live]B站直播订阅，下播缺少图片报错" — `文件消息缺少参数 {"file":"","type":null,...}` when `keyframe` is empty; post still has `images: ['']` — https://github.com/MountainDash/nonebot-bison/issues/626
- **#635 "系统断电恢复后的未发送信息补发机制"** (open, 2024-09) — the canonical missed-post report: https://github.com/MountainDash/nonebot-bison/issues/635
  > "某 RSS 源在14:00有更新…然而，服务器在13:50 - 18:30时间段内断电，导致服务器重启后无法发送14:00更新的RSS内容。"
  > "将 RSS 相关的状态信息（包括发送状态）持久化存储在数据库中…引入一个重试阈值，以确保历史未发送的信息最多被重试发送 X 次，以避免无限次重发的问题。"
- **#632 "订阅的微博有时候会发不出来"** (open, 2024-09) — https://github.com/MountainDash/nonebot-bison/issues/632 — one post's parse failure (`_get_long_weibo` returned HTML, `json error, parsing: <!DOCTYPE html>…微博-出错了`) propagates out of `dispatch_user_post` and kills the whole `exec_fetch` job for that tick.

### 2.5 Duplicates (weak signal, but real)

- **#694 "网页重复订阅导致user表出现重复数据，无法删除订阅"** (open, 2025-02, 10 comments, label `bug`) — https://github.com/MountainDash/nonebot-bison/issues/694
  > "网页端在第一次添加"明日方舟游戏信息"后，添加b站源后，再次添加"明日方舟游戏信息"，会导致第一次添加的"明日方舟游戏信息"无法删除。在聊天交互中添加无问题"
- **#704 "一些问题"** (closed, 2025-04) — "上面那个RSS示例输出了3张图片，有一张重复的，但实际RSS里面只有两张，不知是否为Bug" — https://github.com/MountainDash/nonebot-bison/issues/704
- Legacy migration logs already knew about it: `config/db_migration.py` prints "用户 {type}-{uid} 订阅了 {platform}-{name} 两次，随机采用了一个订阅".

### 2.6 Content truncation / rendering fidelity

- **#446 "长微博推送时微博内容不全"** — "发现QQ群里推送的内容不全，末尾有省略号" — https://github.com/MountainDash/nonebot-bison/issues/446
- **#470 "bot对bilibili的up的新视频推送展示效果不好"** — video posts look identical to plain dynamics — https://github.com/MountainDash/nonebot-bison/issues/470
- **#708** rsshub 超链接在合并转发时丢失 — https://github.com/MountainDash/nonebot-bison/issues/708
- **#675** "建议增加无url模式以适配qq官方bot" (QQ 官方 bot 无法发外链图片) — https://github.com/MountainDash/nonebot-bison/issues/675
- **#202** "希望可以将信息合并转发形式推送。消息多的时候容易刷屏。" — https://github.com/MountainDash/nonebot-bison/issues/202

### 2.7 Database / migration pain

- **#5 "Drop Tinydb，use SQLite"** (2021-05-30) — "本项目的储存结构涉及到了多对多的存储关系，现在使用了比较手动的方法去处理这个关系…使用ORM确定类型，改变当前混乱的模式" — https://github.com/MountainDash/nonebot-bison/issues/5
- **#270** Postgres: `operator does not exist: json = json` (fixed by switching `user_target` to JSONB) — https://github.com/MountainDash/nonebot-bison/issues/270
- **#623** MySQL 8.4: `Specified key was too long` on `nb datastore upgrade` (String(1024) indexed columns) — https://github.com/MountainDash/nonebot-bison/issues/623
- **#116** Windows + `FASTAPI_RELOAD=true` breaks migration — https://github.com/MountainDash/nonebot-bison/issues/116
- **#195** `Multiple classes found for path "User" in the registry of this declarative base` (datastore/orm coexistence) — https://github.com/MountainDash/nonebot-bison/issues/195
- **#740 "统一 cookie 存储格式"** (open, 2025-09) — https://github.com/MountainDash/nonebot-bison/issues/740
  > "目前的 cookie 的内容(content)以字符串的形式存储在数据库中，可能同时是 json 或者 plain 格式。所以在每一次取cookie 时，都要解析并校验 content。这增加了无谓的性能开销，并增加了复杂性"

### 2.8 Configuration complexity

- **#608 "独立的toml配置文件"** (open, 2024-08) — https://github.com/MountainDash/nonebot-bison/issues/608
  > "bison的现有的配置开始变得复杂起来了，加上以后可能还需要按platform配置，感觉得加一个自己的配置文件了"
- **#382** (see §3): "在项目越发复杂的现在，现有的`plugin_config`结构难以满足使用上的多样需求，按`platform`, `post`甚至`target(发送对象)`进行配置的需求日益必要"
- **#607 "Platform未启用时应从订阅命令列表中移除"** — `BISON_USE_BROWSER` silently disables platforms that still appear in menus — https://github.com/MountainDash/nonebot-bison/issues/607
- **#241** `.env.prod` 配置后无效 — `BISON_USE_PIC` / `BISON_USE_PIC_MERGE` confusion — https://github.com/MountainDash/nonebot-bison/issues/241
- **#107 / #308** `BISON_OUTER_URL` 配置无效/文档不明确.
- Config surface today is **19 `PlugConfig` fields** ([`plugin_config.py`](https://github.com/MountainDash/nonebot-bison/blob/main/nonebot_bison/plugin_config.py)), all flat and global.

### 2.9 Refactor / architecture threads

- **#382 "Bison 重构计划备忘"** (open, 2023-09-15, 4 comments) — https://github.com/MountainDash/nonebot-bison/issues/382
- **#478 "提案：传送带(Conveyor)与包裹(Parcel)"** (open, 2024-02-20) — https://github.com/MountainDash/nonebot-bison/issues/478
- **#487 "后台整体重构"** (open, 2024-03-01) — https://github.com/MountainDash/nonebot-bison/issues/487
- **#503 "重命名计划"** (open, 2024-03-19) — https://github.com/MountainDash/nonebot-bison/issues/503
- **#688 "项目代码结构调整和可配置化方案"** (open, 2025-01-31) — https://github.com/MountainDash/nonebot-bison/issues/688
- **#702 "考虑引入 workflow 模型，允许用户自行拼装组合抓取渲染发送等流程"** (open, 2025-04-12, **empty body**) — https://github.com/MountainDash/nonebot-bison/issues/702
- **#635** (persistence/backfill), **#543** (per-target disable) — the two functional gaps most cited.
- No issue carries a `design`/`rfc` label; there is no `docs/rfc/` directory. All architecture discussion lives in the issues above.

---

## 3. The rewrite history: how many attempts, what changed

### 3.1 Release-line eras (CHANGELOG + 46 releases, 59 tags, v0.1.0 → v0.9.14 2026-01-11)

| Era | Version/date | Event (verbatim) |
|---|---|---|
| 0 | 2021-02 repo created; **v0.4.0 2021-11-18** | renamed `nonebot-hk-reporter` → `nonebot-bison` ("本项目名称来源于明日方舟角色拜松") |
| 1 | **v0.4.4** | **"又双叒叕重构了一下"** (refactored *yet again*) |
| 2 | **v0.6.0** | breaking: **"弃用 tinydb，使用 sqlite 作为数据库（届时将自动迁移数据库，可能存在失败的情况）"**, **"重写前端"**, **"使用了新的调度器"**, drop Py3.9 |
| 3 | v0.7.0 (2023-01) | **"适配最新的 DataStore 插件，并切换模型为 SQLModel"** (PR #178) |
| 4 | v0.7.1 (2023-03) | **"又切换回 sqlalchemy，但是 2.0"** (PR #206) — SQLModel experiment reverted 1 month later |
| 5 | v0.8.0 (2023-06) | **"使用 saa 代替所有发送"** (PR #219) — breaks all direct OneBot sending |
| 6 | v0.9.0 (2023-10) | **"Theme 功能添加"** (PR #400) + 适配 Pydantic V2 + 移除 `mcbbsnews` |
| 7 | v0.9.6 → v0.9.14 (2024-10 → 2026-01) | Cookie 组件 (PR #633), OPUS 动态, Metrics (PR #666), plain cookie (#709), cookie 解析重构 (#735) |

Ongoing micro-refactors in the same period: PR #211 "修改 nonebot_bison 项目结构" (v0.7.1), PR #544 "refactor client getting logic in platform config", PR #290 "提供批量 api 接口" (v0.8.2), PR #447 "调整 Dockerfile 以及 Bison 的运行方式".

### 3.2 The three big *unfinished* rewrites (visible as branches, all against `main`)

| Branch | Last commit | Diff vs main | Intent |
|---|---|---|---|
| `feat/delivery-queue` | 2024-01-10 | 277 files, +36,689/−39,945 | ":construction: 尝试使用queue来渲染和发送" |
| `feat/bison-core` | 2024-01-31 | 284 files, +37,299/−40,224 | ":construction: 可怕吗 是的很可怕" |
| `feat/core` | 2025-02-25 | 77 files, +7,290/−10,103 | ":sparkles: 添加包裹入口" (Parcel/Conveyor) |
| `feat/courier` | 2025-04-03 | 66 files, +7,659/−7,465 | ":sparkles: 添加courier" |
| `feat/courier2` | 2025-08-17 | 81 files, +8,355/−7,195 | ":sparkles: Courier 添加依赖注入功能" |
| `next` | 2026-04-02 | 348 files, +4,091/−**115,729** | ":construction: 施工中" |
| `renew/init` | 2026-04-20 | 350 files, +711/−**121,078** | ":sparkles: 重建项目基本结构" (delete-everything restart) |
| `renew/core-impl` | 2026-04-28 | 368 files, +1,866/−**120,877** | ":sparkles: 实现 core 部分" |

Others in the same family: `refactor/message-send` (2026-05-20, 28 files, +959/−1,665), `remote-render` (2025-09-14, "use remote render", 43 files), `feat/nb-orm` (2026-07-07, 43 files), `feat/all-target` (2025-09-25), `feat/cookies-format` (2025-09-16), `feat/set-interval` (2025-03-03, "add bison_site_schedule config"), `feat/webui` (2025-01-05, "通过兼容层添加路由"), `doc/fetch-flow`, `feat/simple-stats`, `feat/color-plus-plus-plus` (2023-09-17, "泛型的简单尝试").

**Also abandoned as a PR:** **#611 ":sparkles: 实现：传送带(Conveyor)与包裹(Parcel)"**, opened 2024-08-13, **closed unmerged 2024-08-14** — https://github.com/MountainDash/nonebot-bison/pull/611
> "目前做了基础的 ConveyorManager，尝试使用 Conveyor 作为 Scheduler -> send 的通道，测试正常发生消息。康康这样子做怎么样，可以的话就把剩下的都换了）"

(The PR is not merged and its 2 review comments could not be retrieved — GitHub REST API returned `403 rate limit exceeded` for `/issues/611/comments` from this environment. State/merge data above comes from the `/issues` corpus.)

### 3.3 What the (currently stalled) v3 was meant to be

`renew/core-impl` is a **monorepo**: `packages/bison-core`, `packages/courier`, `packages/plugins/`, `nonebot_bison/` (near-empty adapter). `bison_core/__init__.py` exports `platform, post, schedule, site, theme, utils`. `requires-python = ">=3.14"`, dependencies = `["anyio>=4.13.0"]` only. Both package READMEs are **empty**; `courier/courier/__init__.py` is literally `def hello() -> str: return "Hello from courier!"`. So: **the v3 exists as a package skeleton + core interfaces, with zero real implementation** (largest file: `schedule/scheduler.py`, 7 KB).

Its design, read off the skeleton:
- `Platform[RawPost]` base + **mixins**: `FetchMixin`, `BatchFetchMixin`, `FilterMixin`, `ParseTargetMixin` — replacing today's `NewMessage/StatusChange/SimplePost` inheritance tree ([`bison_core/platform/platform.py`](https://github.com/MountainDash/nonebot-bison/blob/origin/renew/core-impl/packages/bison-core/bison_core/platform/platform.py)).
- `SiteConfig` / `PlatformConfig` as **dataclasses** instead of class attributes, incl. `store_cls: type[StoreLike]` ([`site/site.py`](https://github.com/MountainDash/nonebot-bison/blob/renew/core-impl/packages/bison-core/bison_core/site/site.py)).
- `ProcessContext(client_mgr, store)` with a **`StoreLike` Protocol** (`inited`, `__getitem__/__setitem__/__contains__`, `on_init`) — i.e. the in-memory dedupe store becomes an injectable, persistent-able interface ([`site/context.py`](https://github.com/MountainDash/nonebot-bison/blob/renew/core-impl/packages/bison-core/bison_core/site/context.py)).
- `Post` no longer holds a `Platform` instance and has **no render method** (rendering leaves the payload); adds `extras: dict`.
- `Scheduler` becomes an ABC with `get_current_weight_val()`, `get_userinfo()`, `process_fetch_result()` — DB decoupled from scheduling.
- Python 3.14 generic syntax (`class Platform[RawPost](ABC)`, `type Category = int`).

### 3.4 What was learned / dropped

- **Dropped:** tinydb (v0.6.0), SQLModel (v0.7.0→v0.7.1, 6 weeks), direct OneBot sending (v0.8.0), `mcbbsnews` platform (v0.9.0, "移除 mcbbsnews platform"), the Conveyor/Parcel abstraction (PR #611, 1 day), and at least 3 full-core restarts (`feat/bison-core`, `next`, `renew/*`).
- **Kept despite criticism:** the weighted round-robin scheduler (unchanged from v0.6.0 to v0.9.14), the per-Site APScheduler job, the in-memory dedupe set, `Platform` class-attribute registry.
- **The rename plan never happened** (#503, 2024-03, still open): `target -> source`, `user -> target`, `config -> db`, `plugin_config -> config`. The 2023 memo already proposed a glossary with `Shipper / ShipAddr / ShipStub / Receiver / ReceiveAddr / WayBill` for the old `Target/db_target/SubUnit` (#382 comment, 2023-09-16). Today's code still uses the *old* names — so `Target` means "source account" in `platform/` and "chat destination" in `send/` simultaneously.

---

## 4. Notable design decisions visible in code

**4.1 How senders declare supported message types:** they don't. Bison imports SAA's metadata verbatim — `__supported_adapters__ = nonebot_plugin_saa.__plugin_meta__.supported_adapters` ([`__init__.py#L22`](https://github.com/MountainDash/nonebot-bison/blob/main/nonebot_bison/__init__.py#L22)) — and renderers emit `list[MessageSegmentFactory]`. SAA supports 10 adapters (OneBot v11/v12, Kaiheila, Telegram, Feishu, Red, DoDo, Satori, QQ 官方, Discord) but only 5 message kinds: 文字 / 图片 / 提及 / 提及全体 / 回复 ([SAA README](https://raw.githubusercontent.com/felinae98/nonebot-plugin-send-anything-anywhere/main/README.md)). **No video, no audio, no file, no card** — so video posts degrade to a cover image (#470, #704). `AggregatedMessageFactory` (合并转发) is the only "rich" primitive and it is QQ-group-only (#678).

**4.2 How a renderer is selected per subscription:** it is **per platform, never per subscription**. `Post.get_priority_themes()` returns `[BISON_PLATFORM_THEME[platform]] + [platform.default_theme] + ["basic"]`, then renders are attempted in order, catching `ThemeRenderUnsupportError`/`ThemeRenderError` to fall through ([`post/post.py#L58-L95`](https://github.com/MountainDash/nonebot-bison/blob/main/nonebot_bison/post/post.py#L58-L95)). Docs state the rule explicitly and quote the same function ([docs/dev README](https://raw.githubusercontent.com/MountainDash/nonebot-bison/main/docs/dev/README.md)). Defaults: `Platform.default_theme = "basic"`, arknights→`"arknights"`, `AkVersion`/`TerraHistoricusComic`→`"brief"`.

**4.3 How a "target" is represented (three incompatible things):**
1. Subscribe side: `Target = NewType("Target", str)` (`types.py`) + DB row `Target(platform_name, target, target_name)`.
2. Send side: SAA `PlatformTarget` subclass (`TargetQQGroup(group_id=…)`, `TargetQQPrivate`, `TargetQQChannel`, `TargetTelegramCommon`, `TargetDiscordChannel`, …), stored as JSON in `User.user_target` via `model_dump` / `PlatformTarget.deserialize`.
3. The in-flight join: `SubUnit(sub_target: Target, user_sub_infos: list[UserSubInfo])`, `UserSubInfo(user, categories, tags)`.
So dispatching one post to K subscribers produces K `(PlatformTarget, list[Post])` tuples, and the DB user row is keyed by the **serialized JSON dict** (`select(User).where(User.user_target == model_dump(user))`) — which is the direct cause of #694's duplicate-user rows.

**4.4 Rate limiting / send interval per group:** there is none per group. Global `deque` + single consumer + `MESSGE_SEND_INTERVAL = 1.5` s. The queue also holds a `retry_time` countdown seeded from `bison_resend_times` (default 0). Comment in code explains a subtle self-reentrancy bug they worked around: *"why read from queue then pop item from queue? … the length of queue will be 0. At that time, adding items to queue will trigger a new execution of this func, which is not expected."* Dedupe/backpressure is therefore purely serial-global.

**4.5 How images are produced and cached:**
- Produced: (a) by PIL in `utils/image.py` (`pic_merge` builds a 1×3 or 2×3 square grid when ≥3 images of equal height, else returns originals); (b) by Playwright screenshots for `need_browser` themes; (c) `text_to_image()` for the `BISON_USE_PIC` anti-风控 path, applied to **every Text segment of every message for every recipient** ([`abstract_post.py`](https://github.com/MountainDash/nonebot-bison/blob/main/nonebot_bison/post/abstract_post.py)).
- **Not cached.** There is no render cache, no image cache, no disk cache. `hishel` (an HTTP cache) is used only by `ceobecanteen/cache.py`. `parse_cache` is per-batch and cleared (`self.parse_cache = {}`). *Consequence (derived):* the same post is parsed once per user in `dispatch_user_post` (cache hit) but **rendered once per user** in the scheduler's send loop (`for user, send_list: for send_post: await send_post.generate_messages()`), so render cost scales O(posts × subscribers). `bison_render_histogram` exists precisely to watch this.

**4.6 Error containment:** `catch_network_error` swallows `httpx.RequestError`/`ssl.SSLError` → returns `None` → `or []` (poll silently yields nothing) but **re-raises** `JSONDecodeError` ([`platform.py#L48-L63`](https://github.com/MountainDash/nonebot-bison/blob/main/nonebot_bison/platform/platform.py#L48-L63)). Because the whole per-tick pipeline is one `await` chain, one bad post aborts the tick (#632) and the exception surfaces as an APScheduler job error.

**4.7 Observability:** Prometheus metrics are first-class (16 labels-ish, 5 metrics) + Grafana dashboard JSON in `docker/`; `ProcessContext` records every HTTP response (`gen_req_records()`) and dumps them into the exception args so issues can quote raw API responses (visible throughout #602, #678).

---

## 5. Third-party forks / rewrites

From the GitHub forks API (36 forks total, sorted by stars — **none has more than 1 star**, i.e. **no significant fork exists**):

```
hotwa/nonebot-bison              1★  pushed 2024-08-17
myclms/nonebot-bison             1★  pushed 2024-05-07
he0119/nonebot-bison             0★  pushed 2024-08-16   (datastore/saa author)
MigangBot/nonebot-bison          0★  2023-05-19
LambdaYH/nonebot-bison-migang    0★  2024-10-31
gugugugle/nonebot-bison-customed 0★  2024-11-20
58563528/nonebot-hk-reporter     0★  2026-08-12   (the pre-rename name, still pushed)
```

- There is **no "bison v3" project** anywhere; `MountainDash bison v3` returns nothing. The only "v3" artifacts are the in-repo branches in §3.2.
- A **Gitea mirror run by a core maintainer** exists: `https://git.suyiiyii.top/suyiiyii/nonebot-bison` (surfaced by search; content matches upstream README/CHANGELOG). Treat as mirror, not fork-with-changes.
- Adjacent/related by the same org: `MountainDash/nonebot-plugin-send-anything-anywhere` (the sender abstraction, actively used) and `MountainDash/nonebug-saa` (test helper).
- Predecessor/neighbour in the ecosystem credited in README: [`HarukaBot`](https://github.com/SK-415/HarukaBot/) ("借鉴了大体的实现思路") and RSSHub.

---

## 6. IMPLIED CONSTRAINTS FOR A REWRITE

Each item traces to a source above.

1. **Dedupe state must be persisted and per-(source,target) keyed.** Today it is a class-level in-memory dict (`platform.py#L143-L150`, `#L291-L320`); consequences are visible as #635 (断电后漏发) and the `BISON_INIT_FILTER` foot-gun (restart ⇒ either skip everything since downtime, or re-send the whole feed window). A rewrite needs a `(platform, target, post_id)` table and a durable cursor.
2. **Scheduling must decouple "how often a site is polled" from "how many targets exist".** Current design = 1 APScheduler job per Site, 1 target per tick, so per-target period = `N × interval` (weibo 10s, bilibili 60s, live 5s). Any design that keeps this couples user count directly to staleness.
3. **Polling must be leaky-bucket/rate-limited per upstream host+credential, with explicit jitter, `max_instances` handling and backoff.** Evidence: #250/#49/#195/#14 (`maximum number of running instances reached`, `missed by …`), #602 (429 + `bili-status-code -509` + `x-bili-retry-after: 3`), and the hand-rolled `NORMAL/REFRESH/BACKOFF/RAISE` FSM with 5/20/45-min backoff and a `random.random() < 0.1236` refresh.
4. **A single failing post must not abort the poll for the whole target (or site).** #632 shows one `JSONDecodeError` from Weibo's long-text endpoint killing `exec_fetch`; #626 shows an empty-string image URL propagating into a hard `ActionFailed`.
5. **Sending needs per-destination failure isolation + retry with backoff, not a global 1.5s deque.** #678: one group permanently fails while others succeed, and the only signal is `send msg err` ×3; `BISON_RESEND_TIMES` defaults to 0, so retry is off by default.
6. **A durable outbox is required** (post → rendered → delivered, per recipient), because the roadmap's own #635 asks for "优先补发断电期间未发送" with a bounded "最多重试 X 次" — that is an outbox with a dead-letter policy, not a deque.
7. **Renderer selection must become a per-subscription (or per-destination) setting.** It is currently per-platform only (`BISON_PLATFORM_THEME`) with hard-coded fallback `platform.default_theme → basic` (`post/post.py#L58-L95`); #382 explicitly calls for "按 `platform`, `post` 甚至 `target(发送对象)` 进行配置", and #704 shows users expecting per-subscription rendering that silently does nothing.
8. **Rendering must be cached or fanned out once per post, not once per recipient.** *Derived:* the send loop renders inside `for user … for post …` (`scheduler.py#L140-L155`) and `BISON_USE_PIC` converts every Text segment per recipient (`abstract_post.py`). There is no render/image cache at all.
9. **The render layer must tolerate upstream breakage.** #699/#730 (`nonebot-plugin-htmlrender` 0.6.2 `capture_element` change broke rendering; 0.6.8 broke it again), #526 (fallback theme leaves dirty rich text), #14 (Chromium auto-download). Pinning + a pure-Python fallback theme is mandatory; `need_browser` also *disables* platforms when `BISON_USE_BROWSER=false` (#607).
10. **The message model must stay inside SAA's 5 primitives** (text/image/at/at-all/reply) unless adapters are hand-written per target platform: 10 adapters supported, no video/audio/file; 合并转发 is QQ-group-only (`AggregatedMessageFactory`, #678, #675). Any "rich rendering" ambition must be expressed as images.
11. **A single "target" abstraction must cover both ends, or names must be split.** Today `Target` = source account in `platform/` and = chat id in `send/`; the rename plan `target→source, user→target, config→db, plugin_config→config` (#503) is 2 years old and unimplemented; the 2023 glossary proposed `Shipper/Receiver/WayBill` (#382 comment).
12. **One subscriber row must be uniquely identified independently of the serialized JSON blob.** `UniqueConstraint("target_id","user_id")` exists, but `User` is found by `User.user_target == model_dump(user)` (JSON equality) — which is exactly #694's duplicate-user rows and #270's Postgres `json = json` failure. Identity must be a typed key (platform + native id), not JSON equality.
13. **Portability is part of the contract:** SQLite (default), PostgreSQL (JSONB variant), MySQL (String length limits — #623) must all migrate cleanly; there are already 14 alembic revisions plus a legacy tinydb importer, plus the `alembic_version` table-collision workaround in `bootstrap.py`. A rewrite must ship a migration path from `nonebot_bison_user/target/subscribe/cookie*` and keep nbesf v1/v2/v3 import working (`config/subs_io/nbesf_model/{v1,v2,v3}.py`; v1→v2 swapped `{type,uid}` for SAA targets, v2→v3 added `cookies`).
14. **Configuration must be layered (file > env > defaults) and per-platform/per-target.** 19 flat `PlugConfig` fields today; #608 asks for "独立的 toml 配置文件" because "bison的现有的配置开始变得复杂起来了"; #688 proposes a Core with per-module "模式/路径" config; and the `feat/set-interval` branch ("add bison_site_schedule config") shows even the poll interval is currently hard-coded per Site class.
15. **The 3 rejected core abstractions are a warning, not a template.** Conveyor/Parcel (#478) was implemented and closed in 1 day (PR #611), `feat/bison-core` was abandoned, and `next`/`renew/*` deleted 115k–121k lines without landing. Whatever replaces the `Platform` inheritance tree should preserve what survived 5 years of churn: `Site`-grouped scheduling by interval, weighted round-robin fairness, the `get_sub_list + get_id (+ get_date)` implementer contract that makes a new platform ~100 lines (`docs/dev/README.md`), and the "任何 theme 渲染失败都回退到 basic" rule.

---

### Reachability notes

- All raw.githubusercontent.com, github.com HTML and `api.github.com` **search** endpoints used above were reachable. The **core REST rate limit (60/h, unauthenticated) was exhausted** mid-research; `/issues/611/comments` (PR review comments) and a few late per-issue comment fetches returned `403 rate limit exceeded` and are therefore **not** quoted. Issue/PR *state, dates, labels and bodies* were taken from a complete `/issues?state=all` pagination (843 items: 180 issues, 663 PRs) before the limit hit.
- `https://nonebot-bison.netlify.app/` is live and current (matches README links). The older `nonebot-bison.vercel.app` domain still appears in old CHANGELOG entries only.
- Branch diffstats come from a shallow `--no-single-branch` clone; because history is depth-1, the diffs are tree-vs-tree against `main` and **file/line counts may include formatting churn**.
