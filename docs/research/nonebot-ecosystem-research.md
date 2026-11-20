# NoneBot2 Ecosystem & Runtime Architecture — Research Report

Scope: NoneBot2 **2.5.0** (latest stable docs, `nonebot2` 2.5.0 released 2026-04-01) plus `master` source.
Method: official docs at `nonebot.dev/docs` (2.5.0 versioned docs), the `nonebot/nonebot2` source tree, plugin repos/READMEs, and PyPI release metadata. Every claim carries a URL; anything I could not confirm is marked **UNVERIFIED**.

---

## A. NoneBot2 core architecture

### A1. Object model

| Concept | Class / API | What it is |
|---|---|---|
| Driver | `nonebot.drivers.Driver` (ABC) | "controls framework startup/shutdown, adapter registration, bot lifecycle"; `Forward` (client: HTTP/WS client) vs `Reverse` (server: ASGI/WebHook) ([driver docs](https://nonebot.dev/docs/advanced/driver), [API](https://nonebot.dev/docs/api/drivers/index)) |
| Adapter | `nonebot.adapters.Adapter` | Converts driver I/O ↔ NoneBot `Event`s, creates/registers `Bot`s; has `bots: dict[str, Bot]`, `get_name()`, `bot_connect()`, `bot_disconnect()`, `setup_http_server()`, `setup_websocket_server()` ([API](https://nonebot.dev/docs/api/adapters/index)) |
| Bot | `nonebot.adapters.Bot` | Holds `adapter`, `self_id`, exposes `call_api(api, **data)`, abstract `send(event, message, **kwargs)`, classmethod hooks `on_calling_api` / `on_called_api` ([API](https://nonebot.dev/docs/api/adapters/index)) |
| Event | `nonebot.adapters.Event` | `get_type()`, `get_event_name()`, `get_event_description()`, `get_log_string()`, `get_user_id()`, `get_session_id()`, `get_message()`, `get_plaintext()`, `is_tome()` ([API](https://nonebot.dev/docs/api/adapters/index), [adapter guide](https://nonebot.dev/docs/advanced/adapter)) |
| Matcher | `nonebot.matcher.Matcher` | The "event responder": `type`, `permission`, `rule`, `priority`, `block`, `temp`, `expire_time`, `default_state`; class-level `send/finish/pause/reject/reject_arg/reject_receive/skip/got/receive/handle`, `stop_propagation()`, `set_arg/get_arg`, `set_target/get_target`, `ensure_context()` ([matcher docs](https://nonebot.dev/docs/advanced/matcher), [source](https://github.com/nonebot/nonebot2/blob/master/nonebot/internal/matcher/matcher.py)) |
| Plugin | `nonebot.plugin.model.Plugin` | Module wrapper: `name`, `module`, `module_name`, `manager`, `matcher: set[type[Matcher]]`, `parent_plugin`, `sub_plugins`, `metadata`, `id_` ([API](https://nonebot.dev/docs/api/plugin/model)) |

Adapters are registered imperatively, not discovered: `driver.register_adapter(Adapter)` (multiple calls for multi-platform), then `nonebot.get_adapters()`, `nonebot.get_adapter(...)`, `nonebot.get_bots()`, `nonebot.get_bot(self_id)` ([adapter guide](https://nonebot.dev/docs/advanced/adapter)). Internally `Driver._adapters` is a `ClassVar[dict[str, Adapter]]`, and the public `nonebot.get_adapters()` literally returns `get_driver()._adapters.copy()` ([abstract.py](https://github.com/nonebot/nonebot2/blob/master/nonebot/internal/driver/abstract.py), [nonebot/__init__.py](https://github.com/nonebot/nonebot2/blob/master/nonebot/__init__.py)).

### A2. Plugins are modules; discovery is *not* entry-point based

A plugin **is** a Python module (single `.py` file or package with `__init__.py`) ([create-plugin](https://nonebot.dev/docs/tutorial/create-plugin)). Loading is done by `PluginManager`, which uses **import hooks + `pkgutil.iter_modules` over search paths** — there is **no setuptools entry-point discovery** (I grepped `nonebot/` for `entry_point`/`importlib.metadata` use: only `version()` is imported) ([manager.py](https://github.com/nonebot/nonebot2/blob/master/nonebot/plugin/manager.py)).

Loading APIs (exact names, all in `nonebot.plugin`, re-exported from `nonebot`) ([create-plugin](https://nonebot.dev/docs/tutorial/create-plugin), [load.py](https://github.com/nonebot/nonebot2/blob/master/nonebot/plugin/load.py)):

- `nonebot.load_plugin(module_path: str | Path) -> Plugin | None`
- `nonebot.load_plugins(*plugin_dir: str) -> set[Plugin]`
- `nonebot.load_all_plugins(module_path: Iterable[str], plugin_dir: Iterable[str]) -> set[Plugin]`
- `nonebot.load_from_json(file_path, encoding="utf-8")` — keys `plugins`, `plugin_dirs`
- `nonebot.load_from_toml(file_path, encoding="utf-8")` — reads `[tool.nonebot]`
- `nonebot.load_builtin_plugin(name)` / `nonebot.load_builtin_plugins(*names)` (→ `nonebot.plugins.<name>`)
- `nonebot.require(name) -> ModuleType`

`pyproject.toml` shape: new format is a **table of plugin groups**, old format a flat list ([load.py docstring](https://github.com/nonebot/nonebot2/blob/master/nonebot/plugin/load.py), [create-plugin](https://nonebot.dev/docs/tutorial/create-plugin)):

```toml
[tool.nonebot]
plugin_dirs = ["awesome_bot/plugins"]

[tool.nonebot.plugins]
"@local" = ["path.to.your.plugin"]
"nonebot-plugin-someplugin" = ["nonebot_plugin_someplugin"]
```

Old list form (`plugins = [...]`) still parses but logs `Legacy project format found! Upgrade with 'nb upgrade-format'.` (source above). Plugins whose name starts with `_` are skipped by directory scanning ([load.py](https://github.com/nonebot/nonebot2/blob/master/nonebot/plugin/load.py)).

> **Load order is not deterministic.** `PluginManager.available_plugins` is a **set union** (`third_party_plugins | searched_plugins`) and `load_all_plugins()` iterates that set (`set(filter(None, (self.load_plugin(name) for name in self.available_plugins)))`) ([manager.py](https://github.com/nonebot/nonebot2/blob/master/nonebot/plugin/manager.py)). Do not derive registration order from load order.

### A3. `PluginMetadata` — exact fields

Declared as module-level `__plugin_meta__ = PluginMetadata(...)`; **must be at plugin top level** or it is not recognized ([plugin-info](https://nonebot.dev/docs/advanced/plugin-info), [publishing](https://nonebot.dev/docs/developer/plugin-publishing)).

| Field | Type | Notes |
|---|---|---|
| `name` | `str` | human-readable name, **not** the index name ([API](https://nonebot.dev/docs/api/plugin/model)) |
| `description` | `str` | |
| `usage` | `str` | |
| `type` | `str \| None` | `library` / `application`; required for publishing |
| `homepage` | `str \| None` | required for publishing |
| `config` | `type[BaseModel] \| None` | plugin config model; required if a config class exists |
| `supported_adapters` | `set[str] \| None` | format `<module>[:<Adapter>]`, `~` = `nonebot.adapters.`; **`None` means "all adapters"**, and a plugin using only base abstractions should explicitly set `None` |
| `extra` | `dict[Any, Any]` | free-form; other plugins are expected to read agreed keys |

Methods: `PluginMetadata.get_supported_adapters() -> set[type[Adapter]] | None` — resolves dot notation **only for installed/importable adapters**, silently suppressing `ModuleNotFoundError`/`AttributeError`; returns `None` when `supported_adapters is None` ([model.py](https://github.com/nonebot/nonebot2/blob/master/nonebot/plugin/model.py)).
Helper: `nonebot.plugin.inherit_supported_adapters(*names)` — intersects the support sets of already-loaded plugins; requires `require(...)` first ([publishing](https://nonebot.dev/docs/developer/plugin-publishing), [load.py](https://github.com/nonebot/nonebot2/blob/master/nonebot/plugin/load.py)).

Reading plugin info: `nonebot.get_loaded_plugins() -> set[Plugin]`, `nonebot.get_plugin(plugin_id)`, `nonebot.get_plugin_by_module_name(module_name)`, `nonebot.get_available_plugin_names() -> set[str]` (includes declared-but-not-loaded) ([plugin-info](https://nonebot.dev/docs/advanced/plugin-info), [API](https://nonebot.dev/docs/api/plugin/index)). `Plugin.id_` is the index id; for nested sub-plugins it is `父插件标识符:子插件文件(夹)名` ([API](https://nonebot.dev/docs/api/plugin/index#get-plugin)).

### A4. Config: get_plugin_config, pydantic-settings, `.env`

Loading precedence, highest first: **`nonebot.init(**kwargs)` / post-init attribute assignment → system environment → dotenv files** ([config docs](https://nonebot.dev/docs/appendices/config)).

- `ENVIRONMENT` (case-insensitive, default `prod`) selects `.env.{ENVIRONMENT}`; `.env` is always loaded first and overridden by the env-specific file; `nonebot.init(_env_file=".env.dev")` overrides the selection ([config docs](https://nonebot.dev/docs/appendices/config)).
- dotenv values are parsed as **JSON**, falling back to `str`; empty → `""`, bare key → `None`.
- Nested dicts use pydantic `env_nested_delimiter` (default `__`): `WEATHER__API_KEY` → `{"weather": {"api_key": ...}}`.
- Plugin config: define `class Config(BaseModel)` (pydantic v1 **and** v2 both supported since 2.2.0) and call `nonebot.get_plugin_config(Config)` ([config docs](https://nonebot.dev/docs/appendices/config)).
  Implementation: `type_validate_python(config, BaseSettings._settings_build_values(config, model_dump(global_config), env_file=..., env_file_encoding=..., env_nested_delimiter=...))` — i.e. it re-runs settings resolution (including env) against a model seeded from the global config **on every call** ([plugin/__init__.py](https://github.com/nonebot/nonebot2/blob/master/nonebot/plugin/__init__.py)).
- Namespacing convention: prefix field names (`weather_api_key`) or use a nested model + `plugin_config.weather` so env becomes `WEATHER__API_KEY` ([config docs](https://nonebot.dev/docs/appendices/config)).
- Flat global config object: `nonebot.get_driver().config`; missing attribute raises.
- Built-in config keys include `DRIVER` (default `~fastapi`), `HOST`, `PORT`, `LOG_LEVEL`, `API_TIMEOUT` (default `30.0`), `SUPERUSERS`, `NICKNAME`, `COMMAND_START`, `COMMAND_SEP`, `SESSION_EXPIRE_TIMEOUT`, `ENVIRONMENT` ([config docs](https://nonebot.dev/docs/appendices/config)).

> **`EXT_` prefix: no such mechanism exists.** `grep -rn "EXT_"` over the whole `nonebot2` repo (docs + source) returns **zero** hits, and NoneBot v1's configuration guide also contains none. Treat "`.env` with `EXT_` prefixes" as **UNVERIFIED / not a NoneBot feature**; the real mechanisms are per-plugin field prefixes and `env_nested_delimiter` scopes.

### A5. `require` and cross-plugin dependency resolution

Plugins are tracked through **import hooks**, so you must not `import` a plugin before NoneBot loads it ([requiring](https://nonebot.dev/docs/advanced/requiring)). `require(name)` accepts a dotted module name **or** a plugin id; if the plugin is not loaded it looks for a manager that owns it and loads it, else calls `load_plugin(name)`, and raises `RuntimeError(f'Cannot load plugin "{name}"!')` on failure ([load.py](https://github.com/nonebot/nonebot2/blob/master/nonebot/plugin/load.py)). Canonical usage:

```python
from nonebot import require
require("nonebot_plugin_apscheduler")
from nonebot_plugin_apscheduler import scheduler
```

### A6. Sub-plugins (nested plugins)

Yes — "嵌套插件". A parent plugin calls `nonebot.load_plugins(str(Path(__file__).parent / "plugins"))` inside its `__init__.py`; NoneBot records parent/child relations (`Plugin.parent_plugin`, `Plugin.sub_plugins`) and the child id becomes `parent:child` ([plugin-nesting](https://nonebot.dev/docs/advanced/plugin-nesting), [API](https://nonebot.dev/docs/api/plugin/model)). LocalStore also mirrors this: sub-plugin data dirs live **under** the parent plugin dir, and per-plugin overrides are keyed by `plugin2:sub_plugin` ([localstore README](https://github.com/nonebot/plugin-localstore), [data-storing](https://nonebot.dev/docs/best-practice/data-storing)).

---

## B. Registration patterns in the ecosystem

### B1. What registries actually exist

NoneBot has **no general-purpose extension registry**. The registries are fixed and mostly private:

| Registry | Location | Public access |
|---|---|---|
| Plugins | `nonebot.plugin._plugins: dict[str, Plugin]` | `get_plugin`, `get_plugin_by_module_name`, `get_loaded_plugins`, `get_available_plugin_names` ([source](https://github.com/nonebot/nonebot2/blob/master/nonebot/plugin/__init__.py)) |
| Matchers | `nonebot.matcher.matchers: MatcherManager` (`MutableMapping[int, list[type[Matcher]]]` delegating to a `MatcherProvider`) | `Matcher.new(...)`, `Matcher.destroy()`, plus the module-level manager ([source](https://github.com/nonebot/nonebot2/blob/master/nonebot/internal/matcher/manager.py)) |
| Adapters | `Driver._adapters: ClassVar[dict[str, Adapter]]` | `nonebot.get_adapters()` = `.copy()` ([source](https://github.com/nonebot/nonebot2/blob/master/nonebot/internal/driver/abstract.py)) |
| Bots | `Driver._bots` | `nonebot.get_bots()`, `Adapter.bots` |
| Hooks | `Driver._bot_connection_hook` / `_bot_disconnection_hook`, `Bot._calling_api_hook` / `_called_api_hook`, module-level `_event_preprocessors` / `_run_preprocessors` | decorators only |
| Plugin-scoped matcher set | `Plugin.matcher` | read-only inspection |

Third-party "registries" (SAA target adapters, Alconna exporters, APScheduler jobs) are **plugin-owned** and registered into that plugin's own dicts — NoneBot does not arbitrate them.

### B2. Matcher creation and registration

Helpers: `on`, `on_metaevent`, `on_message`, `on_request`, `on_notice`, plus rule-specialized `on_startswith`, `on_endswith`, `on_fullmatch`, `on_keyword`, `on_command`, `on_shell_command`, `on_regex`, `on_type`; grouping via `CommandGroup` / `MatcherGroup` ([matcher docs](https://nonebot.dev/docs/advanced/matcher), [plugin API](https://nonebot.dev/docs/api/plugin/index)). Built-in rules live in `nonebot.rule`: `startswith`, `endswith`, `fullmatch`, `keyword`, `command` (honors `COMMAND_START`/`COMMAND_SEP`, `force_whitespace`), `shell_command`, `regex`, `to_me`, `is_type` ([matcher docs](https://nonebot.dev/docs/advanced/matcher), [rule.py](https://github.com/nonebot/nonebot2/blob/master/nonebot/rule.py)).

`Rule` and `Permission` have **asymmetric** combinators (source-verified, and a real foot-gun):

- `Rule.__and__` / `__rand__` build a new `Rule(*checkers)`; `Rule.__or__` raises `RuntimeError("Or operation between rules is not allowed.")` ([internal/rule.py](https://github.com/nonebot/nonebot2/blob/master/nonebot/internal/rule.py)).
- `Permission.__or__` / `__ror__` combine checkers (any-of); `Permission.__and__` raises `RuntimeError("And operation between Permissions is not allowed.")` ([internal/permission.py](https://github.com/nonebot/nonebot2/blob/master/nonebot/internal/permission.py)).
- Predefined permissions: `SUPERUSER`, `MESSAGE`, `NOTICE`, `REQUEST`, `METAEVENT`, `USER`; superuser match accepts `"<adapter>:<user_id>"` **or** legacy bare `user_id` in `config.superusers` ([nonebot/permission.py](https://github.com/nonebot/nonebot2/blob/master/nonebot/permission.py)).

Registration side-effect: creating a matcher inside a plugin module attaches it to the current plugin (`Matcher.new` uses the current plugin context and `Plugin.matcher.add`), which is why matcher inspection via `Plugin.matcher` works ([matcher source](https://github.com/nonebot/nonebot2/blob/master/nonebot/internal/matcher/matcher.py), [model](https://nonebot.dev/docs/api/plugin/model)).

### B3. Official hook / extension points (exact names)

Global (driver-run, obtained via `get_driver()`): `@driver.on_startup`, `@driver.on_shutdown`, `@driver.on_bot_connect`, `@driver.on_bot_disconnect` ([runtime-hook](https://nonebot.dev/docs/advanced/runtime-hook), [API](https://nonebot.dev/docs/api/drivers/index)).

Event-pipeline: `@event_preprocessor`, `@event_postprocessor`, `@run_preprocessor`, `@run_postprocessor` — all imported from `nonebot.message`; raising `nonebot.exception.IgnoredException` inside a preprocessor skips the event/run ([runtime-hook](https://nonebot.dev/docs/advanced/runtime-hook), [API](https://nonebot.dev/docs/api/message)).

API-call: `@Bot.on_calling_api(bot, api, data)` and `@Bot.on_called_api(bot, exception, api, data, result)`; raising `nonebot.exception.MockApiException(result=...)` short-circuits/replaces the platform call (used by `nonebot-plugin-webui`-style virtual chat and by tests) ([runtime-hook](https://nonebot.dev/docs/advanced/runtime-hook), [bot.py](https://github.com/nonebot/nonebot2/blob/master/nonebot/internal/adapter/bot.py)).

Adapter lifecycle: `Adapter.on_ready(func)` ([API](https://nonebot.dev/docs/api/adapters/index)). Matcher runtime: `Matcher.type_updater`, `Matcher.permission_updater`, `Matcher.got`, `Matcher.receive`, `Matcher.handle`, `matcher.stop_propagation()`, `Matcher.skip()`.

Dispatch entry point (public, documented for exactly this purpose): `nonebot.message.handle_event(bot, event)`, with the documented usage `driver.task_group.start_soon(handle_event, bot, event)` ([API](https://nonebot.dev/docs/api/message)). Internally `handle_event` applies event preprocessors → resolves matchers by priority → runs them concurrently within a task group, respecting `block`/`StopPropagation` ([message.py](https://github.com/nonebot/nonebot2/blob/master/nonebot/message.py)).

There is **no** `EventPreprocessor` class — the names are the decorator functions above. Hook sets are **unordered Python sets**, and hooks inside one stage run **concurrently** in an `anyio` task group; exceptions are logged per-hook ([abstract.py](https://github.com/nonebot/nonebot2/blob/master/nonebot/internal/driver/abstract.py), [bot.py](https://github.com/nonebot/nonebot2/blob/master/nonebot/internal/adapter/bot.py)). So: **no ordering guarantee among hooks of the same kind.**

### B4. Shared-service plugins as the de-facto "registry" pattern

- Scheduler: `require("nonebot_plugin_apscheduler")` then `from nonebot_plugin_apscheduler import scheduler` — one module-level `AsyncIOScheduler` shared by all plugins ([scheduler docs](https://nonebot.dev/docs/best-practice/scheduler), [plugin source](https://github.com/nonebot/plugin-apscheduler/blob/master/nonebot_plugin_apscheduler/__init__.py)).
- Storage: `require("nonebot_plugin_localstore")` then `import nonebot_plugin_localstore as store`; `get_plugin_{cache,config,data}_{dir,file}()` return `pathlib.Path` ([data-storing](https://nonebot.dev/docs/best-practice/data-storing), [localstore README](https://github.com/nonebot/plugin-localstore)).
- Cross-plugin data channel: `PluginMetadata.extra` is the only sanctioned generic metadata channel ("other plugins can collect special info by agreeing on `extra` keys") ([plugin-info](https://nonebot.dev/docs/advanced/plugin-info)).

---

## C. Message sending APIs

### C1. `Bot.send`, `call_api`, and dynamic dispatch

- Abstract: `async Bot.send(event: Event, message: str | Message | MessageSegment, **kwargs) -> Any` ([API](https://nonebot.dev/docs/api/adapters/index)).
- `async Bot.call_api(api: str, **data) -> Any`; `Bot.__getattr__` returns `partial(self.call_api, name)` for any non-dunder name, so `await bot.send_msg(message="hi")` == `await bot.call_api("send_msg", message="hi")` ([API](https://nonebot.dev/docs/api/adapters/index), [bot.py](https://github.com/nonebot/nonebot2/blob/master/nonebot/internal/adapter/bot.py)). Practical consequence: **any** protocol action is callable by string, including `send_msg_rate_limited` (see §G).
- Errors surface as NoneBot exceptions: `ActionFailed`, `NetworkError`, `ApiNotAvailable`, `MockApiException`, `WebSocketClosed` ([exception.py](https://github.com/nonebot/nonebot2/blob/master/nonebot/exception.py)). The OneBot v11 adapter documents `NetworkError`/`ActionFailed` on `send` ([adapter-onebot bot.py](https://github.com/nonebot/adapter-onebot/blob/master/nonebot/adapters/onebot/v11/bot.py)).
- `API_TIMEOUT` (default `30.0`s, `None` disables) bounds platform API calls for HTTP-based adapters ([config docs](https://nonebot.dev/docs/appendices/config)).
- **No retry, no queue, no rate limit in core `call_api`** — it runs calling-api hooks, calls the adapter, runs called-api hooks, and propagates exceptions (source above).

### C2. `Message` / `MessageSegment` model

`Message` is `List[MessageSegment]` subclass; the wire form is a flat array of `{"type": str, "data": dict}` segments, constructible via `TypeAdapter(Message).validate_python([...])` ([message tutorial](https://nonebot.dev/docs/tutorial/message), [API](https://nonebot.dev/docs/api/adapters/index)). Key methods: `Message.get_segment_class()`, `MessageSegment.get_message_class()`, `MessageSegment.type`, `MessageSegment.data`, `MessageSegment.is_text()`, `Message.extract_plain_text()`, `Message.include/exclude/get/only/has/index/count/join/copy`, `Message.template()` → `MessageTemplate` ([API](https://nonebot.dev/docs/api/adapters/index), [message tutorial](https://nonebot.dev/docs/tutorial/message)).

**There is no cross-adapter segment enum.** Each adapter defines its own `MessageSegment` subclass with static factory methods and string `type` values:

- OneBot v11: `text, at, contact, contact_group, contact_user, dice, face, forward, image, json, location, music, music_custom, node, node_custom, poke, record, reply, rps, shake, share, video, xml, anonymous` ([v11 message.py](https://github.com/nonebot/adapter-onebot/blob/master/nonebot/adapters/onebot/v11/message.py)).
- OneBot v12: `text, mention, mention_all, image, voice, audio, video, file, location, reply` ([v12 message.py](https://github.com/nonebot/adapter-onebot/blob/master/nonebot/adapters/onebot/v12/message.py)).

### C3. How a plugin discovers adapter capabilities

There is no capability API. The available signals are:

1. `PluginMetadata.supported_adapters` (declared) and `PluginMetadata.get_supported_adapters()` (resolved classes) ([API](https://nonebot.dev/docs/api/plugin/model)).
2. `bot.type` / `bot.adapter.get_name()`, `nonebot.get_adapters()`, `Adapter.bots` ([adapter guide](https://nonebot.dev/docs/advanced/adapter)).
3. Structural checks: `isinstance(bot, SomeAdapterBot)`, `event.get_type()`, `MessageSegment.is_text()`.
4. Runtime probing/Duck typing — what SAA and Alconna do (below).

Official guidance is to write platform-agnostic code against base classes and to split platform-specific extraction/rendering from business logic, using `Event` subclass annotations (overloads) per platform ([multi-adapter](https://nonebot.dev/docs/best-practice/multi-adapter)). Official warning: when sending, **only `str` and plain-text `MessageTemplate` are portable**; platform-specific `MessageSegment`s require the matching adapter ([api-calling](https://nonebot.dev/docs/appendices/api-calling)).

### C4. `nonebot-plugin-send-anything-anywhere` (SAA)

Repo moved: `github.com/felinae98/nonebot-plugin-send-anything-anywhere` → **`github.com/MountainDash/nonebot-plugin-send-anything-anywhere`** (README badges still point at the old slug; `__plugin_meta__.name` is literally `"峯驰物流"`) ([repo](https://github.com/MountainDash/nonebot-plugin-send-anything-anywhere)). Docs site: <https://send-anything-anywhere.felinae98.cn/>. PyPI latest is **0.7.1 (2024-08-17)** while the repo was pushed 2026-11-18 — i.e. active repo, stale release ([PyPI](https://pypi.org/project/nonebot-plugin-send-anything-anywhere/)).

Exported interface (`nonebot_plugin_saa/__init__.py`):

- Segment factories: `Text`, `Image`, `Mention`, `MentionAll`, `Reply`, `Custom`; base `MessageSegmentFactory`; container `MessageFactory` (a `list[MessageSegmentFactory]`, supports `+`, `.append/.extend/.join`, `__getitem__` by segment type).
- Send: `await MessageFactory(...).send(reply=..., at_sender=...)` (inside a handler), `await MessageFactory(...).send_to(target, bot=None)`, `MessageFactory.finish/pause/reject/reject_arg/reject_receive` mirroring `Matcher`; plus `AggregatedMessageFactory` for merging multiple messages into one send.
- Targets: abstract `PlatformTarget` / `SaaTarget`; concrete `TargetQQGroup`, `TargetQQPrivate`, `TargetQQGroupOpenId`, `TargetQQPrivateOpenId`, `TargetQQGuildChannel`, `TargetQQGuildDirect`, `TargetTelegramCommon`, `TargetTelegramForum`, `TargetKaiheilaChannel`, `TargetKaiheilaPrivate`, `TargetFeishuGroup`, `TargetFeishuPrivate`, `TargetDoDoChannel`, `TargetDoDoPrivate`, `TargetDiscordChannel`, `TargetOB12Unknow`, `TargetSatoriUnknown`; helpers `extract_target(event, bot)`, `get_target(...)`; serialization via `target.json()` / `PlatformTarget.deserialize(...)`.
- Bot selection: `enable_auto_select_bot()`, which caches targets per bot via `driver.on_bot_connect` and refreshes them ([auto_select_bot.py](https://github.com/MountainDash/nonebot-plugin-send-anything-anywhere/blob/master/nonebot_plugin_saa/auto_select_bot.py)).

How it works: each factory knows how to `build(bot) -> MessageSegment` for the bot's adapter; `MessageFactory._do_send` looks up a per-adapter sender in a `sender_map` and raises `RuntimeError(f"send method for {adapter} not registered")` otherwise ([abstract_factories.py](https://github.com/MountainDash/nonebot-plugin-send-anything-anywhere/blob/master/nonebot_plugin_saa/abstract_factories.py)). It converts a platform-agnostic segment list into the concrete adapter's `Message` at send time — the abstraction is **render-time translation**, not a new protocol.

Limitations (evidence-based):

- **Needs a registered sender per adapter**; unknown adapters hard-fail with `RuntimeError` (above).
- Some segments are unsupported per platform (README matrix marks `🚧` for e.g. mention-all on Telegram/DoDo, reply on Red) ([README](https://github.com/MountainDash/nonebot-plugin-send-anything-anywhere)).
- **No retry, no backoff, no rate limiting, no queue**: grepping the send path for `retry|sleep|rate` yields nothing but a loop index; failures propagate from `bot.send` ([abstract_factories.py](https://github.com/MountainDash/nonebot-plugin-send-anything-anywhere/blob/master/nonebot_plugin_saa/abstract_factories.py)).
- Target coverage is per-platform-class: unsupported combos fall back to `TargetOB12Unknow` / `TargetSatoriUnknown`, which are lossy escape hatches (README notes).
- Still requires a `Bot` for sending (`send_to(target, bot=None)` resolves/auto-selects one).

### C5. `nonebot-plugin-alconna`

Repo <https://github.com/nonebot/plugin-alconna>; PyPI **0.62.1 (2026-07-10)**; docs <https://nonebot.dev/docs/best-practice/alconna/>.

What it provides (module re-exports in `nonebot_plugin_alconna/__init__.py`):

- **Command parsing (from Arclet `Alconna`)**: `Alconna`, `CommandMeta`, `Option`, `Subcommand`, `Arparma` (parse result), `Args`, `Field`, `MultiVar`, `KeyWordVar`, `OptionResult`, `SubcommandResult`, `command_manager`, `output_manager`, `namespace`. `CommandMeta` carries command metadata (name/aliases/separators/help text/`compact`/`fuzzy` etc., per upstream Alconna); Alconna also does typed arg parsing and auto-generated help.
- **NoneBot integration**: `on_alconna(command, rule=..., aliases=..., comp_config=..., use_cmd_start=..., use_cmd_sep=..., auto_send_output=..., skip_for_unmatch=True, priority=1, block=False, ...) -> type[AlconnaMatcher]`, `AlconnaMatcher` (subclass of `Matcher`, metaclass `AlconnaMatcherMeta`), `AlconnaRule`, and DI params `AlconnaResult`, `AlconnaMatches`, `AlconnaExecResult`, `AlconnaArg`, `AlconnaDuplication`, `AlcContext`, `AlcResult`, `Query`, `Match`.
- **Unified messaging**: `UniMessage` / `UniMsg` (universal message), universal segments `Text`, `Image`, `At`, `AtAll`, `Reply`, `Emoji`, `Hyper`, `File`, `Audio`, `Video`, `Voice`, `Keyboard`, `Button`, `Reference`, `CustomNode`, `Other`; `Segment` with `custom_register(custom_type, condition)` and `custom_handler(custom_type)` extension hooks; `Target` (active send: `await Target.group(...).send(UniMessage...)`, `Target.send(..., fallback=True, at_sender=..., reply_to=...)`), `SupportScope` (platform families: `QQClient`, `QQGuild`, `QQAPI`, `Telegram`, `Discord`, `Feishu`, `DoDo`, `Kook`, ...), `SupportAdapter`.
- **Rendering/fallback control**: `AlconnaMatcher.send/finish/pause/reject` accept `UniMessage` plus `fallback: bool | FallbackStrategy` — the strategy enum includes `AUTO`, `FORBID`, `IGNORE`, `TO_TEXT`, `ROLLBACK`; `patch_matcher_send()` monkey-patches `Matcher.send` so all matchers accept `UniMessage`; `patch_saa()` bridges SAA.

Cross-adapter value: one parse tree (`Arparma`) and one message model (`UniMessage`) across ~22+ adapters, with per-adapter export/fallback rather than per-adapter branching in user code ([README](https://github.com/nonebot/plugin-alconna), [exporter.py](https://github.com/nonebot/plugin-alconna/blob/master/src/nonebot_plugin_alconna/uniseg/exporter.py)).

---

## D. Concurrency & scheduling

### D1. The task model is `anyio`, not raw asyncio

`Driver.task_group` returns `Lifespan.task_group`, an `anyio.abc.TaskGroup` created in `Lifespan.startup()` via `anyio.create_task_group()` and entered manually ([`_lifespan.py`](https://github.com/nonebot/nonebot2/blob/master/nonebot/internal/driver/_lifespan.py), [`abstract.py`](https://github.com/nonebot/nonebot2/blob/master/nonebot/internal/driver/abstract.py)).

Shutdown sequence (`Lifespan.shutdown`), exact order:

1. Run `on_shutdown` funcs **in reverse registration order** (documented as "stack order"), each awaited (sync funcs offloaded via `run_sync`).
2. `self.task_group.cancel_scope.cancel()` — **cancels every task started via `driver.task_group.start_soon`**.
3. `await self.task_group.__aexit__(...)`, swallowing exception groups.

NoneBot itself uses `handle_event` in that task group (`driver.task_group.start_soon(handle_event, bot, event)`, the documented pattern) ([API](https://nonebot.dev/docs/api/message)).

Implications for background work:

- Tasks created with bare `asyncio.create_task` are **not** tracked or cancelled by NoneBot; they die with the loop and can raise "Task was destroyed but it is pending". Only `driver.task_group.start_soon(...)` participates in shutdown cancellation.
- `Lifespan.startup()` also supports `on_ready` funcs (`Lifespan.on_ready`), but there is no public `driver.on_ready` — only `Adapter.on_ready` ([`_lifespan.py`](https://github.com/nonebot/nonebot2/blob/master/nonebot/internal/driver/_lifespan.py), [adapter API](https://nonebot.dev/docs/api/adapters/index)).
- Startup funcs run **sequentially in registration order** (source), but registration order follows plugin load order, which is set-iteration order → cross-plugin init order is effectively **unspecified**. `nonebot-plugin-datastore` documents exactly this and exposes `post_db_init` instead of `on_startup` for "after DB init" work ([datastore README](https://github.com/he0119/nonebot-plugin-datastore)).
- Driver shutdown is signal-driven: `none.py` serves with `anyio.open_signal_receiver`, first signal → graceful shutdown, second → force exit ([none.py](https://github.com/nonebot/nonebot2/blob/master/nonebot/drivers/none.py)). FastAPI driver delegates to `uvicorn.run` with `lifespan=self._lifespan_manager` ([fastapi.py](https://github.com/nonebot/nonebot2/blob/master/nonebot/drivers/fastapi.py)).

### D2. Official guidance on long-running work

- **Blocking is explicitly forbidden**: "NoneBot 是一个异步框架，插件中**禁止**使用任何可能阻塞事件循环的同步操作" (e.g. `requests`), with the rule extending to "other operations that may block the event loop for a long time" ([plugin-publishing](https://nonebot.dev/docs/developer/plugin-publishing)). For sync-only libs, `nonebot.utils.run_sync` is the escape hatch ([API](https://nonebot.dev/docs/api/utils)).
- There is **no documented guidance** on background task supervision, worker pools, or a separate process for heavy work. The only official mention of background tasks is the `driver.task_group.start_soon` usage snippet in the `handle_event` API page ([API](https://nonebot.dev/docs/api/message)). Claims that NoneBot "recommends a separate process for heavy work" are **UNVERIFIED** — I found no such recommendation in the docs.
- Matcher-bound sends (`Matcher.send/finish/...`) read `current_bot`/`current_event` **ContextVar**s set only inside the matcher run; from a background task they raise `LookupError`, so out-of-band sending must use `bot.send(event=...)`, `bot.call_api(...)`, `Target.send(...)` (Alconna) or `MessageFactory.send_to(target)` (SAA) ([matcher.py](https://github.com/nonebot/nonebot2/blob/master/nonebot/internal/matcher/matcher.py)).

### D3. `nonebot-plugin-apscheduler`

Single global `scheduler = AsyncIOScheduler()`, configured by `scheduler.configure(plugin_config.apscheduler_config)`; `_start_scheduler`/`_shutdown_scheduler` are wired to `driver.on_startup`/`on_shutdown` when `apscheduler_autostart` (default `True`) ([source](https://github.com/nonebot/plugin-apscheduler/blob/master/nonebot_plugin_apscheduler/__init__.py)).

Config: `apscheduler_autostart: bool = True`, `apscheduler_log_level: int = 30`, `apscheduler_config: dict = {"apscheduler.timezone": "Asia/Shanghai"}` — keys must be prefixed `apscheduler.` ([config.py](https://github.com/nonebot/plugin-apscheduler/blob/master/nonebot_plugin_apscheduler/config.py), [scheduler docs](https://nonebot.dev/docs/best-practice/scheduler)).

Jobstores: the plugin only forwards `apscheduler.*` keys to APScheduler; the actual jobstore choices are APScheduler's — `memory` (default, non-persistent), `sqlalchemy`, `redis`, `mongodb`, configured through `apscheduler.jobstores` ([APScheduler userguide](https://apscheduler.readthedocs.io/en/3.x/userguide.html), [SQLAlchemyJobStore](https://apscheduler.readthedocs.io/en/3.x/modules/jobstores/sqlalchemy.html), [RedisJobStore](https://apscheduler.readthedocs.io/en/3.x/modules/jobstores/redis.html), [MemoryJobStore](https://apscheduler.readthedocs.io/en/3.x/modules/jobstores/memory.html)). Docs that the plugin persists jobs by itself: none found — **jobstore persistence is entirely your config** (see constraints).
Note the docs' explicit caveat: scheduler jobs are not triggered by events, so **no dependency injection**; use `bot.call_api`/`Target.send` instead ([scheduler docs](https://nonebot.dev/docs/best-practice/scheduler)).

---

## E. Persistence options

### E1. `nonebot-plugin-localstore` — file paths only

`get_plugin_cache_dir()`, `get_plugin_cache_file(name)`, `get_plugin_config_dir()`, `get_plugin_config_file(name)`, `get_plugin_data_dir()`, `get_plugin_data_file(name)` → `pathlib.Path` ([data-storing](https://nonebot.dev/docs/best-practice/data-storing)). Defaults (when `LOCALSTORE_USE_CWD` is false): cache `~/.cache/nonebot2` (Unix), data `~/.local/share/nonebot2` (XDG), config `~/.config/nonebot2`; Windows/macOS variants documented; when `LOCALSTORE_USE_CWD=true` → `<cwd>/{cache,data,config}` ([localstore README](https://github.com/nonebot/plugin-localstore)). Overrides: `LOCALSTORE_{CACHE,DATA,CONFIG}_DIR` and per-plugin JSON dicts `LOCALSTORE_PLUGIN_{CACHE,DATA,CONFIG}_DIR` keyed by plugin id (incl. `parent:sub`). **Documented hazard:** on Windows and macOS the data dir and config dir are the *same* directory → avoid filename collisions; nested sub-plugins get dirs under the parent ([data-storing](https://nonebot.dev/docs/best-practice/data-storing)). Publishing rules make it **mandatory** for file storage ([plugin-publishing](https://nonebot.dev/docs/developer/plugin-publishing)). Last release 0.7.4 (2025-03-01) ([PyPI](https://pypi.org/project/nonebot-plugin-localstore/)).

### E2. Databases

| Option | Stack | Config surface | Maintenance |
|---|---|---|---|
| `nonebot-plugin-orm` | SQLAlchemy 2.0 async (`Model`, `async_scoped_session`, `SQLDepends`) + **Alembic** migrations via `nb orm` | `SQLALCHEMY_DATABASE_URL`, `SQLALCHEMY_BINDS`, `SQLALCHEMY_ECHO`, `SQLALCHEMY_ENGINE_OPTIONS`, `SQLALCHEMY_SESSION_OPTIONS`, `ALEMBIC_CONFIG`, `ALEMBIC_STARTUP_CHECK` | **Active**, 0.8.4 (2026-10-22), `nonebot/*` org ([README](https://github.com/nonebot/plugin-orm), [PyPI](https://pypi.org/project/nonebot-plugin-orm/)) |
| `nonebot-plugin-datastore` | SQLAlchemy async + per-plugin JSON config store + data dirs; `get_plugin_data()`, `get_session`, `post_db_init` | uses its own DB config; documents `on_startup` ordering problem | 1.3.1 (2025-08-13) ([README](https://github.com/he0119/nonebot-plugin-datastore), [PyPI](https://pypi.org/project/nonebot-plugin-datastore/)) |
| `nonebot-plugin-sqlalchemy` | SQLAlchemy (older, sync-ish API) | — | **Stale**: last release 0.2.2 (2023-07-20) ([PyPI](https://pypi.org/project/nonebot-plugin-sqlalchemy/)) |
| `nonebot-plugin-tortoise-orm` | Tortoise ORM generic connection plugin | — | 0.1.4 (2024-07-09) ([PyPI](https://pypi.org/project/nonebot-plugin-tortoise-orm/)) |
| Direct `sqlite3`/`aiosqlite`/`SQLModel` in-plugin | — | — | No NoneBot-specific integration; SQLModel is not packaged as a plugin on PyPI (`nonebot-plugin-sqlmodel` → not found) |

Documented tradeoffs, as far as they are documented:

- `plugin-orm` is the only org-maintained DB plugin and the only one with first-class Alembic migration tooling (`nb orm revision/upgrade/check`, `ALEMBIC_STARTUP_CHECK` consistency check at boot) ([README](https://github.com/nonebot/plugin-orm)).
- `datastore` bundles "data dir + JSON config + SQLAlchemy model" and warns that startup ordering is not guaranteed, providing `post_db_init` ([README](https://github.com/he0119/nonebot-plugin-datastore)).
- LocalStore gives you **no locking, no transactions, no schema** — it is purely path resolution ([localstore README](https://github.com/nonebot/plugin-localstore)).
- SQLite + multiple processes/threads is a known SQLAlchemy concern, not NoneBot-documented; **UNVERIFIED** for NoneBot's specific setup.

---

## F. Web UI alongside NoneBot

### F1. Serving HTTP from the bot process

Two officially documented routes, both requiring a **server-type (Reverse/ASGI) driver** ([routing](https://nonebot.dev/docs/advanced/routing)):

1. **Compatibility layer** (portable across server drivers): `HTTPServerSetup(path: URL, method: str, name: str, handle_func: Callable[[Request], Awaitable[Response]])` → `driver.setup_http_server(...)`; WebSocket equivalent `WebSocketServerSetup(path, name, handle_func)`. Constraint: paths do **not** support placeholder expressions, and `name` must be unique.
2. **Direct ASGI app access**: `driver.server_app` / `driver.asgi` (`ASGIMixin` properties); shortcuts `nonebot.get_app()` and `nonebot.get_asgi()`; then plain `@app.get("/api")` on FastAPI or Quart ([routing](https://nonebot.dev/docs/advanced/routing), [API](https://nonebot.dev/docs/api/drivers/index)).

Default driver is `~fastapi` ([driver docs](https://nonebot.dev/docs/advanced/driver)); the FastAPI driver constructs `FastAPI(lifespan=self._lifespan_manager)` so the ASGI app's lifespan **is** NoneBot's startup/shutdown, and serves via `uvicorn.run` ([fastapi.py](https://github.com/nonebot/nonebot2/blob/master/nonebot/drivers/fastapi.py)).

### F2. Rendering images (dashboards/cards) — htmlrender vs htmlkit

- `nonebot-plugin-htmlrender` 0.8.1 (2026-07-30): provider architecture — `Application`/`Renderer` with pluggable providers (Playwright, Takumi, experimental HTMLKit), unified `render_html` / `render_text` / `render_markdown` / `render_template`, typed `RenderedImage`/`RenderedHtml`, `app.extensions`, bounded caches, strict local-path policy. Core installs **no** bitmap backend; you pick `[playwright]`, `[takumi]`, or `[htmlkit]` extras ([README](https://github.com/kexue-z/nonebot-plugin-htmlrender), [PyPI](https://pypi.org/project/nonebot-plugin-htmlrender/)).
- `nonebot-plugin-htmlkit` (official docs page; PyPI 0.1.0rc5, 2026-01-17): litehtml-based, no extra deps, ~10 MB wheel, and docs give a rough benchmark — PEP 7 page at 800×5788 px ≈ **100 ms**, ≈ **40 MB** peak per render on a Ryzen 7 9700X; supported: Windows x64, macOS arm64, Linux x64/arm64 (non-musl); **network resource access requires a client-type driver** (`~httpx`/`~aiohttp`) ([htmlkit-render](https://nonebot.dev/docs/best-practice/htmlkit-render), [repo](https://github.com/nonebot/plugin-htmlkit)).

### F3. Management UIs that exist (2025–2026)

- `nonebot-plugin-webui` 0.1.5 (2026-05-17, single release): mounts on the FastAPI `server_app` at `/webui`, shows runtime info, config with secret masking, loaded plugins + `PluginMetadata`, pulls the official registry (`https://registry.nonebot.dev/plugins.json`) to emit `nb plugin install` commands, offers a virtual chat that triggers matchers (this is where `MockApiException`-style interception matters), token auth via `WEBUI_ACCESS_TOKEN` (login `admin`), SQLite at `.nonebot-plugin-webui/webui.sqlite3` ([PyPI](https://pypi.org/project/nonebot-plugin-webui/)).
- `nb-cli-plugin-webui` 0.4.2 (2024-04-12, last release): Web UI **for nb-cli** — create/add instances, install/uninstall plugins/adapters/drivers, multi-instance status/performance and visual config ([repo](https://github.com/nonebot/cli-plugin-webui), [PyPI](https://pypi.org/project/nb-cli-plugin-webui/)).
- `nonebot-plugin-maestro` 0.5.0 (2026-09-26): visual command-panel manager for the official QQ bot adapter ([PyPI](https://pypi.org/project/nonebot-plugin-maestro/)).
- Historical: `nonebot-plugin-manager` (import-hook plugin manager) — last release 2023-06-24, effectively dead ([PyPI](https://pypi.org/project/nonebot-plugin-manager/)); `RubinTry/NBUI` is an unrelated UI component library, not a NoneBot dashboard ([repo](https://github.com/RubinTry/NBUI)).

"Popular in 2025–2026" — I can only substantiate *existence and release recency*, not adoption. No download/usage statistics were checked; treat popularity rankings as **UNVERIFIED**.

### F4. Documented constraints for web UI work

- **Single event loop, single process**: everything (event handling, scheduler, ASGI routes) runs in the one loop uvicorn/NoneBot started; blocking code in a route blocks message handling ([plugin-publishing](https://nonebot.dev/docs/developer/plugin-publishing)).
- **Hot reload is discouraged**: `fastapi_reload`/`quart_reload` are explicitly "not recommended", with an alternative `nb run --reload`; and on Windows enabling reload switches asyncio from `ProactorEventLoop` to `SelectorEventLoop` (no subprocess creation, ≤512 sockets), breaking e.g. Playwright ([driver docs](https://nonebot.dev/docs/advanced/driver)).
- **Path constraints** in the compatibility layer: no placeholders, unique route names ([routing](https://nonebot.dev/docs/advanced/routing)).
- **Renderer cost**: browser rendering is heavy in storage/memory vs PIL; htmlkit exists precisely to avoid a browser process ([htmlkit-render](https://nonebot.dev/docs/best-practice/htmlkit-render)).
- **Auth**: none provided by NoneBot; webui implements its own token ([PyPI](https://pypi.org/project/nonebot-plugin-webui/)). Put it behind a reverse proxy / bind `HOST=127.0.0.1`.

---

## G. Rate limiting & anti-flood

### G1. What the OneBot v11 protocol actually specifies (the only documented limit I could verify)

OneBot v11 defines **rate-limited calls** at the protocol level:

- Any action may be suffixed `_rate_limited` (`send_msg_rate_limited`, `send_private_msg_rate_limited`, ...), "mainly used for message-sending APIs, to avoid account bans caused by sending too fast"; such calls are **queued and executed at a configured speed**, and their response `status` is `async` ([OneBot 11 API README](https://github.com/botuniverse/onebot-11/blob/master/api/README.md)).
- The config key is `api.rate_limit_interval`, **default `500` ms** (same page).
- `_async` suffix exists separately for fire-and-forget calls (same page).
- The rest of the spec (`api/public.md`) contains **no** rate/limit language — there is no per-message-type quota in the protocol ([public.md](https://github.com/botuniverse/onebot-11/blob/master/api/public.md)).

### G2. Implementations

- **go-cqhttp** (legacy, archived-ish): FAQ documents the practical failure mode — "消息发送失败，账号可能被风控", with the advice to keep the account online 3–7 days to clear risk control ([go-cqhttp FAQ](https://docs.go-cqhttp.org/faq/)). It is not a documented rate number.
- **NapCat**: docs exist at <https://napcat.napneko.icu/> (root renders), but the config pages I tried (`/config/basic`, `/config/advanced`, and the `napneko.github.io` equivalents) return 404 and the VitePress site is SPA-rendered, so I could **not** retrieve a documented send-rate/throttle setting. Whether NapCat enforces or exposes a client-side send rate limit is **UNVERIFIED**. (It is a NTQQ-based protocol-side implementation, not a NoneBot component: [repo](https://github.com/NapNeko/NapCatQQ).)
- **LLOneBot**: `github.com/LLOneBot/LLOneBot` now 301-redirects to `LuckyLilliaDev/LuckyLilliaBot` ("LLBot"); its README contains no rate-limit configuration, and the docs repo (`LuckyLilliaDev/LuckyLilliaDoc`) is a Next.js app I could not crawl for text. Any claim about an LLOneBot throttle setting is **UNVERIFIED** ([redirect target](https://github.com/LuckyLilliaDev/LuckyLilliaBot)).
- Common practice in the ecosystem (visible in both SAA and Alconna) is **not** to rely on server-side throttling but to reduce sends and pace them client-side; Alconna exposes per-send `fallback` control and `AggregatedMessageFactory` in SAA merges several logical messages into one API call ([SAA README](https://github.com/MountainDash/nonebot-plugin-send-anything-anywhere), [Alconna README](https://github.com/nonebot/plugin-alconna)).

### G3. What NoneBot core gives you (and doesn't)

- No rate limiter, no send queue, no retry/backoff anywhere in `Bot.call_api` / `Matcher.send` ([bot.py](https://github.com/nonebot/nonebot2/blob/master/nonebot/internal/adapter/bot.py), [matcher.py](https://github.com/nonebot/nonebot2/blob/master/nonebot/internal/matcher/matcher.py)).
- Available interception points: `@Bot.on_calling_api` (inspect/deny/delay before the platform call — raising `MockApiException` short-circuits), `@Bot.on_called_api` (observe failures), `@run_postprocessor` (observe `ActionFailed`), and `driver.task_group` for a paced worker ([runtime-hook](https://nonebot.dev/docs/advanced/runtime-hook)).
- Because `Bot.__getattr__` forwards any name to `call_api`, `await bot.call_api("send_msg_rate_limited", **kw)` is mechanically possible; whether the connected protocol implementation honors it is **UNVERIFIED** per implementation.

---

## CONSTRAINTS FOR A PLUGIN-BASED PIPELINE CORE

Design target: a registration/inspection registry; pluggable fetchers/parsers/renderers/senders; an ordered per-destination queue; a web management UI. These are the constraints the NoneBot runtime imposes, each grounded above.

1. **Your registry must be your own object, not NoneBot's.** NoneBot exposes no third-party extension registry; `_plugins`, `Driver._adapters`, and `matchers` are fixed and mostly private. A pluggable-core registry has to live in your plugin (module-level singleton, or a shared-service plugin in the style of APScheduler/LocalStore) and be discovered by `require()` — not by scanning NoneBot internals. ([A1/B1](#b-registration-patterns-in-the-ecosystem))
2. **Discovery must go through `require()`.** Import-hook tracking means importing a plugin module before NoneBot loads it breaks tracking; cross-plugin access requires `require("plugin_id")` first, which also guarantees load-before-use. ([A5](https://nonebot.dev/docs/advanced/requiring))
3. **Plugin load order is set-iteration order; never derive ordering from it.** `available_plugins` is a `set` and `load_all_plugins` iterates it, so registration order across plugins is arbitrary. Order your pipeline stages by explicit priority numbers stored in your registry. ([A2](#a2-plugins-are-modules-discovery-is-not-entry-point-based))
4. **Hook order is also unspecified within a stage.** `on_startup` funcs run sequentially in registration order (itself dependent on load order), while pre/post-processors and bot-connection hooks are stored in `set`s and executed concurrently in an `anyio` task group. Initialization that must happen after your registry is populated needs an explicit readiness barrier (cf. datastore's `post_db_init`). ([D1](https://github.com/nonebot/nonebot2/blob/master/nonebot/internal/driver/_lifespan.py), [B3](#b3-official-hook--extension-points-exact-names))
5. **Long-lived workers must be started on `driver.task_group`, not `asyncio.create_task`.** Only the former is cancelled by `Lifespan.shutdown`; the latter leaks past shutdown. The queue consumer has to be an `anyio`-friendly coroutine started there (or in `on_startup` via `start_soon`), and must handle cancellation cleanly. ([D1](https://github.com/nonebot/nonebot2/blob/master/nonebot/internal/driver/_lifespan.py))
6. **Shutdown is reverse-order `on_shutdown` then hard cancel.** Flush semantics must be implemented explicitly: drain the queue and persist pending items inside `on_shutdown` *before* returning, because the following step cancels all task-group tasks and swallows their exceptions. ([D1](https://github.com/nonebot/nonebot2/blob/master/nonebot/internal/driver/_lifespan.py))
7. **Sending is ContextVar-bound; a queue worker is outside matcher context.** `Matcher.send/finish` read `current_bot`/`current_event` ContextVars and will fail from a worker. The pipeline's sender layer must call `bot.send(event=...)`/`bot.call_api(...)` (needs a stored `event` or `Bot` + target) or use SAA/Alconna target objects. ([D2](https://github.com/nonebot/nonebot2/blob/master/nonebot/internal/matcher/matcher.py), [C4](#c4-nonebot-plugin-send-anything-anywhere-saa))
8. **There is no portable message model across adapters.** `Message`/`MessageSegment` are per-adapter; only `str` and plain-text templates are portable. A renderer/sender abstraction must either pick a target-platform-neutral IR (SAA's `MessageSegmentFactory`, Alconna's `UniMessage`) or accept per-adapter renderers with explicit capability declarations (`PluginMetadata.supported_adapters`). ([C2/C3](https://nonebot.dev/docs/appendices/api-calling))
9. **Adapters must be registered before your pipeline can enumerate them, and `supported_adapters` is a string contract, not a capability map.** Use `bot.type`/`adapter.get_name()` + `PluginMetadata.get_supported_adapters()` for reporting, and keep your own capability matrix (segment types, max lengths, rate) because NoneBot has none. ([A1](https://nonebot.dev/docs/api/plugin/model), [C3](#c3-how-a-plugin-discovers-adapter-capabilities))
10. **`Bot.call_api` has no retry, no queue, no throttle.** Ordered per-destination queues, backoff, dedup and `_rate_limited` usage are entirely your layer; `API_TIMEOUT` (default 30 s) is the only built-in bound and applies per call for HTTP adapters. ([C1](https://nonebot.dev/docs/appendices/config), [G3](#g3-what-nonebot-core-gives-you-and-doesnt))
11. **Failures arrive as exceptions, and there is no delivery receipt.** `ActionFailed`/`NetworkError` are raised from `send`/`call_api`; async/`_rate_limited` calls return `status: "async"` with no result. Your queue item states must be derived from exceptions plus optional `on_called_api` observation — plan for at-least-once, not exactly-once. ([C1](https://nonebot.dev/docs/api/adapters/index), [G1](https://github.com/botuniverse/onebot-11/blob/master/api/README.md))
12. **Everything shares one asyncio loop; blocking is forbidden.** Fetchers, parsers and renderers must be async or run via `run_sync` in a thread; a browser renderer (Playwright) must not be driven synchronously, and enabling `fastapi_reload` on Windows breaks subprocess-based tooling. ([D2](https://nonebot.dev/docs/developer/plugin-publishing), [F4](https://nonebot.dev/docs/advanced/driver))
13. **Web UI mounting is driver-conditional.** `driver.server_app`/`nonebot.get_app()` exist only on ASGI drivers (`~fastapi`, `~quart`); the portable fallback is `driver.setup_http_server(HTTPServerSetup(...))` with static paths and unique names. If you ship a UI plugin, gate on `isinstance(get_driver(), ASGIMixin)`. ([F1](https://nonebot.dev/docs/advanced/routing))
14. **Config is a single flat, pydantic-validated namespace with env re-resolution on every `get_plugin_config` call.** All pipeline options must live under one prefix (or a nested scope with `__`), and `EXT_`-style per-extension env namespaces do not exist — per-stage config has to be a dict/JSON field or a sub-model you validate per stage. ([A4](https://nonebot.dev/docs/appendices/config))
15. **Persistence paths are LocalStore's job, and two OSes collide data/config dirs.** Any queue journal, cache or SQLite file must be placed via `get_plugin_data_file()`/`get_plugin_cache_file()` (mandatory by publishing rules), with unique filenames, because data and config directories are identical on Windows and macOS. ([E1](https://nonebot.dev/docs/best-practice/data-storing))
16. **Schema lives in Alembic if you use `nonebot-plugin-orm`.** That is the maintained DB plugin; it expects `SQLALCHEMY_DATABASE_URL`, `nb orm`-managed migrations and can refuse to start with `ALEMBIC_STARTUP_CHECK=true` when models drift — a pipeline DB therefore needs a migration story, not `create_all` at import time. ([E2](https://github.com/nonebot/plugin-orm))
17. **Scheduling is shared and un-namespaced.** One global `AsyncIOScheduler`; job ids must be namespaced by your plugin, jobs get no dependency injection (no `Bot`/`Event`), and persistence exists only if you configure `apscheduler.jobstores` yourself. ([D3](https://nonebot.dev/docs/best-practice/scheduler))
18. **Registry state dies with the process; inspection must be reconstructable.** `Plugin.matcher`, `PluginMetadata` and any module-level registry are in-memory only, and matchers can be transient (`temp`, `expire_time`). A management UI that inspects "registered fetchers/parsers/renderers/senders" must be able to rebuild that view by loading plugins at startup and exposing your registry over HTTP — NoneBot offers no persistence or snapshot mechanism. ([A3](https://nonebot.dev/docs/api/plugin/model), [B1](#b1-what-registries-actually-exist))

---

### Summary of things marked UNVERIFIED

- `.env` `EXT_` prefix as a NoneBot mechanism (no evidence in nonebot2 repo or v1 docs).
- A documented NapCat or LLOneBot/LLBot client-side send-rate/throttle configuration.
- Any NoneBot official recommendation to run heavy work in a separate process.
- Quantitative popularity of web-UI plugins in 2025–2026 (only release dates verified).
- SQLite multi-process behavior under NoneBot specifically.
- Whether NapCat/LLOneBot honor the OneBot v11 `_rate_limited` suffix.
