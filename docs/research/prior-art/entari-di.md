# Entari's dependency injection, mechanism by mechanism

Research note for the Courier kernel. Everything below was read from source at `main` on
2026‑11‑20, and the behavioural claims marked **[verified]** were reproduced by installing
`arclet-letoderea==0.22.1` in a throwaway venv (see the appendix).

## TL;DR

Entari has **no DI library and no DI module of its own**. Injection is a feature of its event
dispatcher, [`arclet-letoderea`](https://github.com/ArcletProject/letoderea), and Entari only
contributes ~260 lines of `Provider` subclasses that know how to pull Satori `Session`,
`Account`, `User`, … and `launart.Service` objects out of the per-event context.

The engine is a **flat, ordered list of `Provider` objects per handler**, not a
`dict[type, factory]`. A provider is a tiny class with a `validate(param) -> bool` predicate and
an `async __call__(context) -> T | None`; the first provider whose `validate` returns true *and*
whose call returns non-`None` wins. Signatures are inspected **once, at handler registration**,
with `inspect.signature` + `inspect.get_annotations(eval_str=True)` (not `typing.get_type_hints`),
and `Annotated[T, marker]` is honoured by pushing the marker's provider to the front of that
handler's provider list.

Consequences that matter for copying: registration never fails on a missing dependency (the error
is deferred to the first call), providers added after a handler is registered do not affect it, and
there is no cycle detection anywhere in the DI path.

---

## 0. Where the code actually lives

| Concern | File |
| --- | --- |
| `Provider`, `ProviderFactory`, `provide()`, `global_providers` | [`arclet/letoderea/provider.py`](https://github.com/ArcletProject/letoderea/blob/main/arclet/letoderea/provider.py) (149 lines) |
| signature → `CompileParam` compilation, `Subscriber.handle` | [`arclet/letoderea/subscriber.py`](https://github.com/ArcletProject/letoderea/blob/main/arclet/letoderea/subscriber.py) (554 lines, ~180 DI-specific) |
| per-plugin/per-scope provider lists, `register()` | [`arclet/letoderea/scope.py`](https://github.com/ArcletProject/letoderea/blob/main/arclet/letoderea/scope.py) (253 lines) |
| annotation evaluation | [`tarina/signature.py`](https://github.com/ArcletProject/tarina/blob/main/src/tarina/signature.py) (`signatures()`) |
| Satori + `launart` providers | [`arclet/entari/core.py`](https://github.com/ArcletProject/Entari/blob/main/arclet/entari/core.py) lines 64–232 and 525–615 |
| plugin-scoped provider list | [`arclet/entari/plugin/model.py`](https://github.com/ArcletProject/Entari/blob/main/arclet/entari/plugin/model.py) (`PluginDispatcher.providers`) |
| service registry (different mechanism!) | [`GraiaProject/launart`](https://github.com/GraiaProject/launart/blob/master/launart/service.py) |

Entari's own `pyproject.toml` declares no DI package:

```toml
# https://github.com/ArcletProject/Entari/blob/main/pyproject.toml#L7-L15
dependencies = [
    "arclet-letoderea<0.23.0,>=0.22.1",
    "arclet-alconna<2.0.0,>=1.8.44",
    "satori-python-core<1.4.0,>=1.3.11",
    "satori-python-client<1.4.0,>=1.3.11",
    "arclet-alconna-tools>=0.7.12",
    "nonestorage>=0.1.0",
    "simpleeval>=1.0.8",
]
requires-python = ">=3.11"
```

and letoderea declares only `tarina` + `typing-extensions`:

```toml
# https://github.com/ArcletProject/letoderea/blob/main/pyproject.toml#L7-L10
dependencies = [
    "tarina<0.8.0,>=0.7.0",
    "typing-extensions>=4.12.0",
]
```

So: **no `injector` / `punq` / `dependency-injector` / `wireup` anywhere.** The price is paid
elsewhere, not in the DI layer: `launart`, `graia-amnesia`, `loguru` and `aiohttp` arrive
transitively through `satori-python-client` (PyPI metadata for `satori-python-client==1.3.11`
lists `loguru`, `yarl`, `aiohttp`, `launart>=0.8.2`, `satori-python-core`, `graia-amnesia`), and
`creart` arrives through `launart`.

---

## 1. How Entari's DI works end to end

### 1.1 Entry points

There is no `run()`-time injection and no container object. Injection happens because you
register a *handler* on an event:

* `plugin.listen(...)` is literally `letoderea.on` — [`arclet/entari/plugin/__init__.py#L360`](https://github.com/ArcletProject/Entari/blob/main/arclet/entari/plugin/__init__.py#L360) (`listen = on`)
* `plugin.dispatch(Event)` returns a `PluginDispatcher` whose `.register`/`.on`/`.handle` forward to `Scope.register`
* the docs' minimal form `async def handler(session: Session)` — [docs](https://arclet.top/tutorial/entari/)

The chain is:

```
on()/Plugin.register()  →  Scope.register()            # scope.py:157  builds the provider list
                        →  RegisterWrapper.__call__()  # scope.py:73   constructs Subscriber
                        →  Subscriber.__init__()       # subscriber.py:205
                        →  Subscriber._recompile()     # subscriber.py:241
                        →  _compile(target, providers) # subscriber.py:164   ← INSPECTION HAPPENS HERE
event dispatch          →  Subscriber.handle()         # subscriber.py:337   ← RESOLUTION HAPPENS HERE
```

### 1.2 Signature inspection

Not `typing.get_type_hints`. Two `lru_cache(4096)`-decorated helpers:

```python
# https://github.com/ArcletProject/tarina/blob/main/src/tarina/signature.py#L67-L81
@functools.lru_cache(4096)
def signatures(callable_target: Callable) -> list[tuple[str, Any, Any]]:
    callable_annotation = get_annotations(callable_target, eval_str=True)
    return [
        (
            param.name,
            (
                (callable_annotation.get(param.name) if isinstance(param.annotation, str) else param.annotation)
                if param.annotation is not inspect.Signature.empty
                else None
            ),
            param.default,
        )
        for param in get_signature(callable_target)
    ]
```

`get_signature` is `inspect.signature(target).parameters.values()`
([same file, L10-12](https://github.com/ArcletProject/tarina/blob/main/src/tarina/signature.py#L10-L12)),
and `get_annotations` is `inspect.get_annotations` from the stdlib (with a backport fallback).
Using `get_annotations(eval_str=True)` instead of `get_type_hints` is deliberate: it resolves
`from __future__ import annotations` strings but **does not strip `Annotated` extras**, which the
compiler then splits by hand.

### 1.3 The compiler

```python
# https://github.com/ArcletProject/letoderea/blob/main/arclet/letoderea/subscriber.py#L164-L171
def _compile(target: Callable, providers: list[Provider | ProviderFactory]) -> list[CompileParam]:
    res = []
    for name, anno, default in signatures(target):
        meta = []
        if get_origin(anno) is Annotated:
            anno, *meta = get_args(anno)
        res.append(_compile_single(CompileParam(name, anno, default, tuple(meta), [], None, None), providers))
    return res
```

```python
# https://github.com/ArcletProject/letoderea/blob/main/arclet/letoderea/subscriber.py#L130-L161
def _compile_single(param: CompileParam, providers: list[Provider | ProviderFactory]) -> CompileParam:
    from .ref import Deref, generate

    name = param.name
    anno = param.annotation
    for _provider in providers:
        if isinstance(_provider, ProviderFactory):
            if result := _provider.validate(param):
                param.providers.append(result)
        elif _provider.validate(param):
            param.providers.append(_provider)
    param.providers.sort(key=lambda x: x.priority)
    if param.meta:
        for m in reversed(param.meta):
            if isinstance(m, Depend):
                param.depend = m.fork(providers)
                break
            if isinstance(m, Provider):
                param.providers.insert(0, m)
            elif isinstance(m, str):
                param.providers.insert(0, provide(anno, name, lambda x: x.get(m)))
            elif isinstance(m, Deref):
                param.providers.insert(0, provide(anno, name, generate(m)))
            elif callable(m):
                param.providers.insert(0, provide(anno, name, m))
    if isinstance(param.default, Deref):
        param.providers.insert(0, provide(anno, name, generate(param.default)))
        param.default = Empty
    if isinstance(param.default, Depend):
        param.depend = param.default.fork(providers)
        param.default = Empty
    return param
```

Note what is *not* here: no error if `param.providers` ends up empty. Compilation only records
candidates.

### 1.4 The resolver

This is the function you asked for — `CompileParam.solve`:

```python
# https://github.com/ArcletProject/letoderea/blob/main/arclet/letoderea/subscriber.py#L105-L127
@dataclass(slots=True)
class CompileParam(Param):
    depend: Depend | None
    record: Provider | None

    async def solve(self, context: Contexts | dict[str, Any]):
        if self.name in context:
            return context[self.name]
        if self.record and (res := await self.record(context)) is not None:  # type: ignore
            if res.__class__ is Force:
                res = res.value
            return res
        for _provider in self.providers:
            res = await _provider(context)  # type: ignore
            if res is None:
                continue
            if res.__class__ is Force:
                res = res.value
            self.record = _provider
            return res
        if self.default is not Empty:
            return self.default
        raise UnresolvedRequirement(self.name, self.annotation, self.default, self.providers)
```

Lookup order, therefore, is:

1. **by parameter name** in the event context dict (`context[self.name]`) — this is a
   string-keyed escape hatch that beats every provider;
2. the **memoised winner** from the previous call for this same parameter object (`self.record`);
3. each candidate provider in priority order (lower `priority` value first, stable for ties),
   skipping `None` returns;
4. the Python default value;
5. `UnresolvedRequirement`.

And the call site that drives it:

```python
# https://github.com/ArcletProject/letoderea/blob/main/arclet/letoderea/subscriber.py#L337-L353
    async def handle(self, context: Contexts, inner=False):
        token = current_subscriber.set(self)
        if not inner:
            context[SUBSCRIBER] = self
        try:
            if self._cursor and (ans := await self._run_propagate(context, self._propagates[: self._cursor])):
                return ans
            arguments = {}  # type: ignore
            for param in self.params:
                arguments[param.name] = await param.depend(context) if param.depend else await param.solve(context)
            if self.is_cm:
                stack = context.setdefault(STACK, AsyncExitStack())
                result = await stack.enter_async_context(self._execute(**arguments))
```

So the "dependency lookup" is: **a list of `Provider` objects, filtered by a `validate(param)`
predicate at compile time, tried in priority order at call time** — plus a name-keyed dict
(`Contexts`) for event payload data. Not a type-keyed dict.

### 1.5 What a provider is

```python
# https://github.com/ArcletProject/letoderea/blob/main/arclet/letoderea/provider.py#L33-L58
@dataclass(init=False, repr=True)
class Provider(Generic[T], metaclass=ABCMeta):
    priority: ClassVar[int] = 20
    origin: type[T]

    def __init__(self):
        self.origin = self.__class__.__orig_bases__[0].__args__[0]  # type: ignore

    def __init_subclass__(cls, **kwargs):
        if cls.__orig_bases__[0].__args__[0] is T:  # type: ignore
            raise TypeError("Subclass of Provider must be generic. If you need a wildcard, please using `typing.Any`")

    def validate(self, param: Param):
        anno = get_origin(param.annotation)
        if self.origin is bool:
            return generic_issubclass(anno, bool)
        return self.origin == param.annotation or (
            generic_issubclass(param.annotation, self.origin)
            or is_optional(param.annotation, self.origin)
            or (origin_is_union(anno) and generic_issubclass(self.origin, param.annotation))
        )

    @abstractmethod
    async def __call__(self, context: Contexts) -> T | None:
        """依据提供模式，从集合中提供一个对象"""
        raise NotImplementedError
```

Two things worth flagging for a copy decision:

* `self.origin` is recovered from `__orig_bases__` — fragile, but works because subclasses are
  required to write `Provider[Concrete]`.
* `__call__` is **always awaitable**, and returning `None` means "not me, try the next one".
  `None` is consequently un-injectable except through `Force(None)` (a wrapper checked in `solve`).

---

## 2. Registration model

There are **four** registration surfaces, and no decorator that says "this type is injectable"
in the abstract.

### (a) Per-handler / per-dispatcher: `providers=[...]`

```python
# https://github.com/ArcletProject/letoderea/blob/main/arclet/letoderea/scope.py#L157-L189 (abridged)
    def register(self, func=None, event=None, *, priority=16, providers=None, propagators=None, ...):
        ...
        register_wrapper = self.wrapper_class()(self, slots, priority, [*event_providers, *self.providers, *providers], ...)
```

Order of the merged list is **event-class providers, then scope (plugin) providers, then the ones
passed at registration**; each group keeps insertion order, and `_compile_single` then sorts the
whole thing by `priority` (stable). A plugin author's normal API is
`plugin.dispatch(Event).providers.append(p)` before registering handlers
([`plugin/model.py#L78-L86`](https://github.com/ArcletProject/Entari/blob/main/arclet/entari/plugin/model.py#L78-L86)):

```python
class PluginDispatcher(Generic[T]):
    def __init__(self, plugin: Plugin, event: type, name: str | None = None):
        ...
        self.providers: DisposableList[Provider[Any] | ProviderFactory] = DisposableList([])
```

### (b) Event-class attribute: `providers = [...]`

`Publisher.__init__` calls `get_providers(target)`, which walks the event class MRO and collects
any `providers` class attribute plus any nested `Provider` class:

```python
# https://github.com/ArcletProject/letoderea/blob/main/arclet/letoderea/provider.py#L105-L110
@lru_cache
def get_providers(event: Any) -> list[Provider[Any] | ProviderFactory]:
    res = [p for cls in reversed(event.__mro__[:-1]) for p in getattr(cls, "providers", [])]  # type: ignore
    res.extend(p for _, p in inspect.getmembers(event, lambda x: inspect.isclass(x) and issubclass(x, (Provider, ProviderFactory))))
    providers = [p() if isinstance(p, type) else p for p in res]
    return list({p.__class__: p for p in providers}.values())
```

Entari uses this in its own event definitions, e.g.
[`event/command.py#L35`](https://github.com/ArcletProject/Entari/blob/main/arclet/entari/event/command.py#L35):

```python
class CommandOutput:
    ...
    providers = [
        provide(str, target="content", call="$out_content"),
        provide(str, target="type", call="$out_type"),
    ]
```

### (c) Global list: `global_providers`

```python
# https://github.com/ArcletProject/letoderea/blob/main/arclet/letoderea/provider.py#L113
global_providers: list[Provider | ProviderFactory | type[Provider] | type[ProviderFactory]] = []
```

extended by letoderea itself ([L148](https://github.com/ArcletProject/letoderea/blob/main/arclet/letoderea/provider.py#L148))
and by Entari at import time:

```python
# https://github.com/ArcletProject/Entari/blob/main/arclet/entari/core.py#L615
global_providers.extend([EntariProvider(), LaunartProvider(), ServiceProviderFactory()])  # type: ignore
```

Every `Subscriber` copies this list at construction
([`subscriber.py#L210`](https://github.com/ArcletProject/letoderea/blob/main/arclet/letoderea/subscriber.py#L210)).

### (d) `ProviderFactory` — the "match on annotation shape" hook

```python
# https://github.com/ArcletProject/letoderea/blob/main/arclet/letoderea/provider.py#L99-L103
class ProviderFactory(metaclass=ABCMeta):
    @abstractmethod
    def validate(self, param: Param) -> Provider | None:
        """依据参数类型自行分配对应 Provider"""
```

This is how arbitrary *parameterised* annotations get injected. Entari's service injection is one:

```python
# https://github.com/ArcletProject/Entari/blob/main/arclet/entari/core.py#L539-L583
class ServiceProviderFactory(ProviderFactory):
    priority = 10

    class _Provider(Provider[Service]):
        def __init__(self, origin: type[Service], serv_id: str | None = None, stage: str = "prepared"):
            super().__init__()
            self.origin = origin
            self.serv_id = serv_id
            self.stage = stage

        def validate(self, param: Param):
            anno = get_origin(param.annotation)
            return isinstance(anno, type) and issubclass(anno, self.origin)

        async def __call__(self, context: Contexts):
            launart = it(Launart)
            sub = f"{context[SUBSCRIBER].__repr__()[13:-1]}"
            serv_id = self.serv_id or self.origin.id
            try:
                service = launart.get_component(self.origin)
            except ValueError:  # Service not loaded yet
                await plugin_service.service_waiter.wait_for(serv_id)
                service = launart.get_component(self.origin)
            log.plugin.trace(f"<y>{sub}</y> waiting for service <w><u>{serv_id}</u></w> to <g>{self.stage!r}</g>")
            await service.status.wait_for(self.stage)  # type: ignore
            return service
```

### The user-facing "declare a type available" story

For **services** (the only blessed, documented, plugin-to-plugin mechanism) the docs say: subclass
`launart.Service`, then `add_service(...)`, then annotate a handler parameter with the class.
From [the official tutorial](https://arclet.top/tutorial/entari/):

```python
# my_plugin.py  (from the docs; class body elided with "...")
from launart import Service, Launart
from arclet.entari import add_service

class CacheService(Service):
    id = "my_cache_service"
    ...
add_service(CacheService)
```

```python
# other_plugin.py
from my_plugin import CacheService  # entari: plugin

@plugin.listen(MessageCreatedEvent)
async def on_message_created(event: MessageCreatedEvent, cache_service: CacheService):
    cache_service.set(event.message_id, event.content)
```

The code path behind `add_service` is two hops into the plugin object:

```python
# https://github.com/ArcletProject/Entari/blob/main/arclet/entari/plugin/__init__.py#L321-L323
def add_service(serv: TS | type[TS]) -> TS:
    """添加一个服务到当前插件"""
    return get_plugin(1).service(serv)
```

```python
# https://github.com/ArcletProject/Entari/blob/main/arclet/entari/plugin/model.py#L611-L620
    def service(self, serv: TS | type[TS]) -> TS:
        if self.reusable:
            raise ReusablePluginError("reusable plugin cannot provide services")
        if isinstance(serv, type):
            serv = serv()
        self._services[serv.id] = serv
        if plugin_service.status.blocking and self.is_available:
            it(Launart).add_component(serv)
            plugin_service.service_waiter.assign(serv.id)
        return serv
```

Note the asymmetry: **`add_service` registers into `launart`'s string-keyed component map (by
`Service.id`), not into any type-keyed DI map.** The type→instance lookup is reconstruction by
`isinstance` at resolution time:

```python
# https://github.com/GraiaProject/launart/blob/master/launart/manager.py#L235-L247
    def get_component(self, target: str | type[TL]) -> TL | Service:
        if isinstance(target, str):
            if target not in self.components:
                raise ValueError(f"Service {target} does not exists.")
            return self.components[target]

        if _id := getattr(target, "id", None):
            return self.get_component(_id)

        try:
            return next(comp for comp in self.components.values() if isinstance(comp, target))
        except StopIteration as e:
            raise ValueError(f"Service {target.__name__} does not exists.") from e
```

So Entari's real answer to "how does a user declare that this type is available" is: **make it a
`Service` with a unique string `id`, hand it to the plugin manager, and let
`ServiceProviderFactory` find it by `issubclass` at injection time.** Everything else is providers
attached to handlers.

---

## 3. Openness — can a downstream plugin inject an arbitrary new type?

**Yes, three different ways, none requiring a framework patch.** In increasing order of intrusiveness:

### 3.1 `Annotated[X, Depends(fn)]` type alias (no registry at all)

This is what real Entari plugins do. From `entari-plugin-permission`:

```python
# https://github.com/ArcletProject/entari-plugin-permission/blob/main/src/entari_plugin_permission/params.py#L1-L17
from typing import Annotated

from arclet.cithun import User
from arclet.letoderea import Depends
from arclet.entari import Session
from entari_plugin_user import get_user

from .service import system


async def get_user_model(sess: Session) -> User:
    user_model = await get_user(sess.account.platform, sess.user)
    user = await system.get_or_create_user(f"user:{user_model.id}", user_model.name)
    return user


UserOwner = Annotated[User, Depends(get_user_model)]
```

and then `async def handler(current_user: UserOwner)` works anywhere. `Depends(fn)` builds a
*sub-`Subscriber`* for `fn`, so `get_user_model`'s own `session: Session` is injected recursively
([`subscriber.py#L53-L91`](https://github.com/ArcletProject/letoderea/blob/main/arclet/letoderea/subscriber.py#L53-L91)):

```python
@dataclass(init=False, eq=True)
class Depend:
    target: TTarget[Any]
    sub: Subscriber[Any]
    cache: bool = False

    def __init__(self, callable_func: TTarget[Any], cache: bool = False):
        self.target = callable_func
        self.cache = cache

    def fork(self, provider: list[Provider | ProviderFactory]):
        if hasattr(self, "sub"):  # pragma: no cover
            return self
        new = Depend(self.target, self.cache)
        new.sub = Subscriber(self.target, providers=provider)
        return new
```

The `entari-plugin-database` plugin does the same thing at scale, with a `Provider` **and** a
`Propagator` that retro-fits its provider onto handlers that need it — note `DatabasePropagator`
inspects `subscriber.params` and then injects a provider via `providers()`:

```python
# https://github.com/ArcletProject/entari-plugin-database/blob/main/src/entari_plugin_database/param.py#L28-L56
class SessionProvider(Provider[sa_async.AsyncSession]):
    priority = 10

    async def __call__(self, context: Contexts):
        if "$db_session" in context:
            return context["$db_session"]
        try:
            db = it(Launart).get_component(SqlalchemyService)
            stack = context[STACK]
            sess = await stack.enter_async_context(db.get_session())
            context["$db_session"] = sess
            return sess
        except ValueError:
            return


class DatabasePropagator(Propagator):
    def validate(self, subscriber: Subscriber):
        params = subscriber.params
        ...
    def providers(self):
        return [SessionProvider()]
```

### 3.2 Plugin-scoped provider list

`PluginDispatcher.providers` is a public `DisposableList`; `Scope.providers` is a plain list. Both
are mutated by plugins at import time. Entari's own command plugin does exactly what a third-party
plugin would do — reach into a global `Publisher` and append a factory:

```python
# https://github.com/ArcletProject/Entari/blob/main/arclet/entari/command/plugin.py#L22-L25
exec_pub = define(CommandExecute)
exec_provider = CommandExecute.providers[0]
exec_pub.providers.append(AlconnaProviderFactory())
out_pub = define(CommandOutput)
```

```python
# https://github.com/ArcletProject/Entari/blob/main/arclet/entari/event/api.py#L57-L58
send_pub = define(SendResponse, name="entari.event/after_send")
send_pub.providers.append(provide(list[MessageObject], call="$resp_result"))
```

### 3.3 `global_providers.append(...)`

The nuclear option: a module-level mutable list consulted by every subscriber created afterwards.

### Namespacing and collisions

* **Per-plugin scope exists** (`Scope.of(self.id)` — [`plugin/model.py#L243-L249`](https://github.com/ArcletProject/Entari/blob/main/arclet/entari/plugin/model.py#L243-L249)), so a plugin's own providers do not leak into another plugin's handlers *unless* the plugin also touches `global_providers` or a shared `Publisher.providers`.
* **There is no collision handling inside one list.** Two providers matching the same parameter both enter `param.providers`; ordering is `priority` (lower first, stable sort) and the first non-`None` result wins. There is no diagnostic, no shadowing warning, no "multiple providers for T" error.
* One accidental dedup: **event-level providers are deduped by provider class**, in `get_providers` (`{p.__class__: p}` — see quote above), so defining two `P1()` instances on an event silently keeps one. Providers passed via `providers=` are *not* deduped.

---

## 4. Lifetime, scope, caching, async, errors

### Instances

| What | Lifetime | Where |
| --- | --- | --- |
| `Provider.__call__` result | **per call** — invoked on every event handling; nothing is cached | `CompileParam.solve` |
| The *choice* of provider | cached per parameter (`self.record`) after first success | `subscriber.py#L113` |
| `Depends(fn)` result | per call by default; shared within one event if `cache=True` | `$depend_cache` dict |
| `launart.Service` | singleton component, created at plugin load | `Launart.add_component` |
| Context values (`context["..."]`) | per event dispatch | `Contexts` dict |

The per-event memo for `Depends`:

```python
# https://github.com/ArcletProject/letoderea/blob/main/arclet/letoderea/subscriber.py#L70-L91
    async def __call__(self, context: Contexts):
        if "$depend_cache" not in context:
            context["$depend_cache"] = {}
        cache = context["$depend_cache"]
        if self.cache and self.target in cache:
            fut = cache[self.target]
            await fut
            return fut.result()
        cache[self.target] = fut = asyncio.Future()
        try:
            res = await self.sub.handle(context.copy(), inner=True)
```

So the cache key is **the callable object**, not the type, and the cache lives in the event
context, i.e. its scope is one `publish()`.

### Lazy vs eager

Everything is lazy: providers run at first use, per event. The only eager part is *matching*
(`validate`) at registration. Services are constructed eagerly at plugin load
(`Plugin.service` instantiates the class immediately: `if isinstance(serv, type): serv = serv()`).

### Async factories

`Provider.__call__` is `async def` by contract, so async factories are native. The sugar form
`provide(...)` wraps whatever it is given with `run_always_await`:

```python
# https://github.com/ArcletProject/letoderea/blob/main/arclet/letoderea/provider.py#L61-L96 (abridged)
def provide(
    origin: TypeForm[T],
    target: str | None = None,
    call: Callable[[Contexts], T | None | Awaitable[T | None]] | str | None = None,
    validate: Callable[[Param], bool] | None = None,
    priority: int = 20,
    _id: str = "_Provider",
) -> Provider[T]:
    ...
    class _Provider(Provider[origin]):  # type: ignore  # noqa
        def validate(self, param: Param):
            if validate:
                return validate(param)
            if param.annotation:
                return super().validate(param) and (not target or param.name == target)
            return param.name == target

        async def __call__(self, context: Contexts):
            if not call and target:
                return context.get(target)
            if isinstance(call, str):
                return context.get(call)
            return await run_always_await(call, context)  # type: ignore
```

`provide(T, call="ctx_key")` is the one-liner "take this value out of the event context and hand it
to parameters annotated `T`" — that is how the framework injects `MessageChain`, `Arparma`, etc.

### Error reporting and *when*

* **Missing provider** → `UnresolvedRequirement`, raised **at call time**, first dispatch of an
  event that reaches the handler. Never at registration. **[verified]**
  The message is rich — it prints the parameter, the candidate providers, and the whole context:

  ```
  arclet.letoderea.exceptions.UnresolvedRequirement: Unable to parse parameter `m: __main__.Missing`
  > providers on parameter `m: __main__.Missing`:
  []
  > current context
  {'$depend_cache': {}, '$event': <...>, '$subscriber': <Subscriber: h at __main__:16>, ...}
  ```
* **`skip_req_missing=True`** (global `configure(...)` or per-`on`), the same error is swallowed and
  the handler is dropped for that event; other handlers still run. Entari exposes this as the
  config key `basic.skip_req_missing` ([`config/model.py#L91`](https://github.com/ArcletProject/Entari/blob/main/arclet/entari/config/model.py#L91), wired at [`core.py#L348`](https://github.com/ArcletProject/Entari/blob/main/arclet/entari/core.py#L348)). **[verified]**
* **Circular `Depends`** → **no detection**. Mutual `Depends` recurses while compiling the
  sub-`Subscriber`s and dies with a bare `RecursionError` **at registration time**
  (traceback frames: `Subscriber.__init__ → _recompile → _compile → _compile_single`). **[verified]**
* **Circular `Service` requirements** → detected, but by `launart`, at startup, and only logged:

  ```python
  # https://github.com/ArcletProject/Entari/blob/main/arclet/entari/plugin/service.py#L158-L181 (abridged)
      async def launch(self, manager: Launart):
          ...
          try:
              results = resolve_requirements(servs)
          except RequirementResolveFailed as e:
              unresolved = "\n".join(f"  - <y>{serv.id}</y> (required: {', '.join(serv.required)})" for serv in e.args[0])
              log.plugin.error(
                  f"failed to resolve service requirements, maybe caused by circular dependencies or missing services:"
                  f"\n{unresolved}"
              )
              return
  ```
* **Bad annotation** (e.g. `from __future__ import annotations` + a class defined inside a function)
  → `NameError` at registration, because resolution uses module globals only. **[verified]**

---

## 5. What does it cost?

Line counts (measured with `wc -l` on the raw files at `main`):

| File | Lines | DI-specific |
| --- | --- | --- |
| `letoderea/provider.py` | 149 | 149 (all of it) |
| `letoderea/subscriber.py` | 554 | ~180 (`Param`/`CompileParam`/`Depend`/`_compile*`/arg loop) |
| `letoderea/scope.py` | 253 | ~40 (provider merging in `register`) |
| `letoderea/context.py` | 37 | 37 |
| `tarina/signature.py` | 113 | ~30 (`signatures`, `get_signature`) |
| **generic DI engine, total** | | **≈ 300–350 lines** |
| `entari/core.py` provider classes | 616 total | ~260 lines (Satori/launart providers + `OnStage`) |
| `entari/plugin/model.py` dispatcher plumbing | 701 | ~40 |
| `entari/command/provider.py` (Alconna providers) | 291 | optional, per-feature |

Third-party weight: **none added for DI**. letoderea's only dependencies are `tarina` and
`typing-extensions`. But Entari's transitive runtime is heavy for unrelated reasons
(`satori-python-client` → `aiohttp`, `loguru`, `launart`, `graia-amnesia`; plus `creart`).

Honest comparison: a hand-rolled kernel that covers the same *feature set as used by Entari*
(type hints + markers + lazy async factories + per-call memo) is ~80–150 lines and has zero
dependencies; Entari's extra ~200 lines buy provider *predicates* (`validate`), `ProviderFactory`
annotation-shape dispatch, `Deref`/`ref` expression injection, and event-context/handler-lifecycle
integration.

---

## 6. Comparison points

### 6.1 NoneBot2 — `Dependent.parse` + `Param` subclass hierarchy

* **Declaration is by parameter default or `Annotated`**: `Dependent.parse_params` walks
  `get_typed_signature(call)`, and for each parameter first checks `isinstance(param.default, Param)`
  (so `arg: str = CommandArg()`), else asks each allowed `Param` subclass's
  `_check_param(param, allow_types)` classmethod. Unknown parameter → `ValueError` **at parse time**
  (i.e. at matcher/handler declaration — earlier than Entari).
  ([`dependencies/__init__.py#L115-L145`](https://github.com/nonebot/nonebot2/blob/master/nonebot/dependencies/__init__.py#L115-L145))
* **The type→resolver mapping is a fixed tuple of classes, not a registry**:
  `HANDLER_PARAM_TYPES = (DependParam, BotParam, EventParam, StateParam, ArgParam, MatcherParam, DefaultParam)`,
  a `ClassVar` on `Matcher`
  ([`internal/matcher/matcher.py#L166-L174`](https://github.com/nonebot/nonebot2/blob/master/nonebot/internal/matcher/matcher.py#L166-L174)).
  Each class's `_check_param` inspects the annotation itself; resolution is `await param._solve(**params)`
  with the whole handler context passed as kwargs.
* **`Annotated` is supported with a marker class** (`DependsInner`, `StateInner`, `ArgInner`), and
  sub-dependencies (`Depends`) are first-class with their own cache:
  `dependency_cache[call] = DependencyCache()` keyed by the callable, with exceptions *cached and
  re-raised* to every dependent, generator/async-generator dependencies entered on the handler's
  `AsyncExitStack`, and parameters solved **concurrently** in an `anyio` task group with
  `run_coro_with_shield`
  ([`internal/params.py#L172-L325`](https://github.com/nonebot/nonebot2/blob/master/nonebot/internal/params.py#L172-L325),
  [`dependencies/__init__.py#L201-L222`](https://github.com/nonebot/nonebot2/blob/master/nonebot/dependencies/__init__.py#L201-L222)).
* **It is not open by type.** A third-party wanting a new injectable type cannot add to
  `allow_types` of the base `Matcher`; it must subclass `Param` *and* get its class into the
  `allow_types` tuple, which normally means subclassing `Matcher` or `on_*` factories. Plugins in
  practice register *values* (`State`, `T_State`) rather than *types*.
* **Cost**: `dependencies/` (225 + 63) + `internal/params.py` (667) ≈ **950 lines**, plus a hard
  dependency on `pydantic`'s `ModelField` abstraction (`nonebot.compat`) and on `anyio`. Every
  injected value also gets pydantic type validation (`check_field_type`).

Verdict: **much more machinery than Entari** (≈950 vs ≈350 lines), strongly tied to pydantic, and
closed to third-party types. It buys real features Entari lacks: per-handler concurrent dependency
solving, an exit-stack lifecycle for generator dependencies, and exception sharing across
dependent caches.

### 6.2 Entari (letoderea)

* **Provider = predicate + async getter**, matched at handler-registration time, tried in
  priority order with `None` meaning "not me". `Annotated[T, marker]` markers are lowered to a
  provider inserted at the head of the list, so a marker beats priority.
* **Binding is frozen at `Subscriber` construction**; `global_providers` / `Scope.providers` /
  `Publisher.providers` are mutable at runtime but only affect handlers created afterwards. **[verified]**
* **No satisfiability check at registration**; the first dispatch raises `UnresolvedRequirement`
  (or silently skips the handler if `skip_req_missing`). No cycle detection; mutual `Depends` is a
  `RecursionError` at registration.
* **Openness is excellent**: `Annotated[X, Depends(fn)]` type aliases need no registry at all, and
  `PluginDispatcher.providers` / `global_providers` let a plugin add types wholesale.
* **~350 lines of engine, zero heavy deps**, but the provider abstraction is coarser than a
  type-keyed dict: "which provider applies" is a method on the provider (`validate`), not a key,
  and a provider may legitimately return `None` to decline.

Verdict: **medium machinery, very high openness, weak static guarantees.** It is "an injection
system that grew out of an event dispatcher", and it shows: the resolution primitive is a list of
callables over an event context, not a container.

### 6.3 Hand-rolled 60-line version (`get_type_hints` + `dict[type, Callable]` + `Annotated`)

* `get_type_hints(fn, include_extras=True)` once at declaration → `dict[param_name, type]`;
  registry is `dict[type, Callable[[], T]]`; `Annotated[T, "name"]` becomes key `(T, "name")` so
  two providers of one type coexist. That is ~25 lines.
* Validation at declaration is trivial (check every key is present) — which is *better* than
  Entari, because it satisfies "missing providers caught at registration time" for free.
* What you lose vs Entari: predicate-based matching (`Provider.validate` handles `Optional[T]`,
  `Union[A, B]`, generic aliases like `Session[MessageCreatedEvent]`), the "return `None` to
  decline" protocol, event-context name fallback, `ProviderFactory` for parameterised annotations,
  and handler-lifecycle coupling (`AsyncExitStack`, `once`, dispose).
* Cost: **~60–80 lines, zero dependencies**, and it is testable in isolation. Our prototype
  `courier_di.py` in this directory is 70 lines of code (82 non-blank, 109 with its docstring) and
  covers (a)–(e) of the brief: async factories, singletons, `Annotated` marker keys,
  registration-time errors, and Entari-style derived providers (a provider whose own parameters are
  injected) with cycle detection — the last one was a 3-line diff over the base kernel.

Verdict: **this is the right amount of machinery for a 500-line kernel.** Entari's extra ~250
lines are buying dispatcher integration and predicate matching, neither of which Courier needs if
stations are declared explicitly rather than discovered by event subscription.

---

## 7. Failure modes Entari's design accepts

1. **Runtime registration: yes, but not retroactive.** All three registries are plain mutable
   lists/dicts mutated at import or run time; however a `Subscriber` snapshots the provider list in
   `__init__` (`subscriber.py#L210`, `scope.py#L185`). Adding a provider after handlers exist does
   not fix them. **[verified]** Only `Subscriber._recompile(new_providers)` — reachable from
   `propagate(..., providers=...)` — rebinds, and nothing in the public API calls it for you.
2. **No startup satisfiability check for handlers.** Entari validates the *service graph*
   (`plugin_service.launch` → `resolve_requirements`) and logs unresolved services, but a handler
   with an unregistered parameter type is only discovered when an event reaches it. In production
   this means the failure surfaces as a per-event exception (or, with `skip_req_missing`, as a
   silently dead handler).
3. **`Annotated[X, marker]` disambiguates — but only by supplying a provider, not by selecting
   among registered ones.** `Annotated[A, AProv()]` inserts that provider at index 0, so it wins
   even over a lower-`priority` competitor. **[verified]** There is no "give me the provider
   registered under marker M" lookup; string markers are interpreted as *context keys*
   (`provide(anno, name, lambda x: x.get(m))`), and `provide(T, target="param_name")` is the
   name-based disambiguator.
4. **Provider collisions are silent.** First non-`None` wins after a stable priority sort; no
   warning, no error. Event-level providers even dedup by class, silently dropping duplicates.
5. **`None` is not injectable** without the internal `Force` wrapper, because `None` means "decline".
   Optional-typed parameters work only via `is_optional` in `validate`.
6. **`Provider.__init__` depends on `__orig_bases__[0].__args__[0]`** — a subclass must declare
   `class P(Provider[Concrete])` as its *direct* generic base, otherwise `origin` is wrong or the
   metaclass raises. Copied naively, this is a footgun.
7. **Annotation resolution is module-globals-only** (`get_annotations(eval_str=True)`), so
   function-local types + `from __future__ import annotations` fail with `NameError` at registration. **[verified]**
8. **No cycle detection in DI.** `RecursionError` at compile time for `Depends` cycles; service
   cycles are caught only by `launart`'s separate requirement resolver.

---

# DESIGN RECOMMENDATION FOR A ~500-LINE COURIER KERNEL

## Copy

1. **Provider = zero-arg callable returning `T` or `Awaitable[T]`.** Entari's `async __call__`
   contract makes async factories free; keep that, but drop the mandatory `context` argument —
   Courier has no ambient event context, and threading one in is what forces `Provider.validate`
   to exist at all.
2. **`Annotated[T, marker]` as an additional registry key `(T, marker)`.** This is the single best
   idea to steal: it gives per-station disambiguation *and* is what lets a downstream plugin add a
   "virtual type" (`UserOwner = Annotated[User, Depends(get_user)])` with zero framework changes.
3. **Compile the signature once, at declaration, and validate there.** Entari does the compile at
   registration but validates at call time; do both at registration. This is the one place where
   copying Entari literally would be a mistake.
4. **`Depends(fn)`-style derived providers.** A provider that itself declares needs is how real
   Entari plugins compose (`UserOwner`). Support it by compiling the factory's signature with the
   same `_plan()` and passing an explicit resolve `stack` for cycle detection (which Entari lacks).
   In the shipped prototype this is exactly three lines over the base kernel: one `plan` slot on
   the spec, `self.plan = _plan(factory)` in `__init__`, and
   `value = spec.factory(**{n: await resolve(dep, (*_stack, k)) for n, dep in spec.plan})`.
5. **Singleton-by-default, per-call opt-in.** Entari's effective default for services is singleton
   and for handlers per-call; a kernel wants an explicit flag per registration, as the prototype does.

## Leave out

* **`Provider.validate(param) -> bool` predicates.** They exist because letoderea must guess which
  of N providers applies to an arbitrary annotation (`Optional[T]`, `Union`, `Session[Evt]`). With
  a keyed registry you look the key up; `Optional[T]` becomes an explicit second registration.
* **`ProviderFactory`.** It is a workaround for "annotation is a parameterised generic and I must
  build a provider per instantiation". If Courier needs it later, add `register(type, factory, for_origin=True)`;
  don't build the machinery now.
* **`global_providers`.** A process-global mutable list plus a per-plugin list plus a per-dispatcher
  list is three scopes for one concept, and the binding-freeze semantics make them confusing.
  One registry + optional child registries (`registry.child()`) that copy-on-write is enough.
* **Event-context name lookup (`context[self.name]`).** It silently shadows providers and makes
  resolution order surprising. Pass per-call values explicitly instead (`call(fn, **overrides)`).
* **`Force(None)`.** If `None` must be injectable, don't overload the "decline" signal; use a
  sentinel for "decline" or require providers to raise.
* **`launart.Service`.** A second, string-keyed service container with its own lifecycle phases is
  a whole subsystem. If Courier needs ordered startup/shutdown, that is a separate 100-line
  lifecycle object, not part of DI.
* **`__orig_bases__` introspection for the provided type.** Store the type explicitly on the spec.

## Minimal API (concrete signatures)

```python
# courier/di.py  — 70 lines of code, stdlib only (inspect + typing)
Key = type | tuple[type, object]          # (T, marker) for Annotated[T, marker]

class DIError(Exception): ...
class MissingProviders(DIError):
    owner: object; missing: list[str]     # raised at @inject time
class CircularDependency(DIError): ...

def register(key: Key, factory: Callable[[], Any], *, singleton: bool = True) -> None: ...
def provider(key: Key, *, singleton: bool = True) -> Callable[[F], F]: ...   # decorator form
async def resolve(key: Key, _stack: tuple[Key, ...] = ()) -> Any: ...
def inject(fn: F) -> F: ...               # validates all needs now; sets fn.__di_plan__
async def call(fn: F, /, **overrides: Any) -> Any: ...
```

Usage, which satisfies (a)–(e):

```python
from typing import Annotated
from courier.di import inject, provider, call

class Clock: ...
class Store: ...

@provider(Clock)                          # (b) host registers a type; later plugins can too
def _clock() -> Clock: return Clock()

@provider(Store, singleton=False)         # per-call instance
async def _store(clock: Clock) -> Store:  # async factory, needs are themselves injected
    ...

StationName = Annotated[str, "station"]   # (b) a marker-keyed "virtual type", no registry change

@provider(StationName)
def _name() -> str: return "oslo"

@inject                                   # (c) raises MissingProviders HERE if anything is absent
async def dispatch(station: StationName, store: Store, clock: Clock) -> None:
    ...

await call(dispatch)                      # (a) needs came from type hints
await call(dispatch, station="bergen")     # explicit override, no shadowing magic
```

Error surfaces: `MissingProviders` lists *every* missing key at once (better than Entari's
first-failure `UnresolvedRequirement`), cycles are caught by the `_stack` check in `resolve`
(including cycles that run through derived providers), and duplicate registration of a key raises
immediately.

One deliberate asymmetry, worth stating because it is a decision and not an oversight: **stations**
are validated at `@inject` time, but a **provider factory's** own needs are only checked when that
provider is first resolved (its `_plan` runs in `_Spec.__init__`, which raises on a *missing
annotation* but does not consult the registry). Moving that check to `register()` costs two more
lines:

```python
    missing = [dep for _, dep in _registry[k].plan if dep not in _registry]
    if missing: raise MissingProviders(factory, [repr(d) for d in missing])
```

If Courier registers all providers during application assembly (the recommended order), the
practical difference is nil; if providers are registered lazily by plugins, pay the two lines.

## What a ~500-line kernel should spend its remaining ~420 lines on

Not DI. Concretely: station declaration/registry (~80), the dispatch/scheduling loop (~150),
retry/backoff policy (~80), structured errors/telemetry (~60), and config (~50). Entari's own
split is instructive — its DI is ~350 lines because it also is an event dispatcher; a library that
is *not* an event dispatcher should keep DI at 80 lines and put the budget into the courier
semantics that Entari delegates to `launart` and `satori`.

---

## Appendix — behavioural checks actually executed

Venv: `python3 -m venv /tmp/venv-leto && pip install arclet-letoderea==0.22.1` (Python 3.14).

| Claim | Method | Result |
| --- | --- | --- |
| registration does not fail on missing provider | `@le.on(Ev) async def h(m: Missing)` | decorator returns; `h.params[0].providers == []` |
| error is at first dispatch | `await le.publish(Ev())` | `UnresolvedRequirement: Unable to parse parameter 'm: __main__.Missing'` |
| providers added later don't rebind | append `LateProvider()` to `Scope.root().providers` then publish, then register a second handler | old handler still raises; new handler succeeds (`got == 1`) |
| `Annotated` marker beats priority | providers `[AProv(20), AProv2(5)]`; param `Annotated[A, AProv()]` vs `A` | plain → `"high-5"`, marked → `"default-20"` |
| `provide(T, target=name)` disambiguates same type | `left: int, right: int` | `(1, 2)` |
| event-level providers dedup by class | `class Ev2: providers = [P1(), P1()]` | `get_providers(Ev2)` → 1 entry |
| mutual `Depends` → RecursionError at compile | `fa.__defaults__ = (Depends(fb),)`, `fb.__defaults__ = (Depends(fa),)`; `Subscriber(fa)` | `RecursionError`, frames `Subscriber.__init__ → _recompile → _compile → _compile_single` |
| `skip_req_missing` drops only the bad handler | two handlers, one unsatisfiable | `['good']` |
| local class + `from __future__ import annotations` fails at registration | handler param annotated with function-local class | `NameError: name 'LocalThing' is not defined` |
| prototype `courier_di.py`: provider with its own needs | `@provider(Store) async def _store(clock: Clock)`; `@inject async def dispatch(store, clock, name)` | `store.clock is clock` (singleton shared through the derived provider); marker key `("station")` resolved |
| prototype: missing station need | `@inject def broken(x: Unregistered)` | `MissingProviders: ... needs unregistered: x: <class 'Unregistered'>` at decoration |
| prototype: per-call vs singleton | `@provider(Store, singleton=False)` vs `@provider(Clock)` | 2 factory invocations across 2 `call()`s, clock instance shared |

## Sources

* Entari: <https://github.com/ArcletProject/Entari> — `pyproject.toml`, `arclet/entari/core.py`, `arclet/entari/plugin/{__init__,model,service}.py`, `arclet/entari/event/{command,api}.py`, `arclet/entari/command/{plugin,provider}.py`
* letoderea: <https://github.com/ArcletProject/letoderea> — `arclet/letoderea/{provider,subscriber,scope,context,utils}.py`, `pyproject.toml`
* tarina: <https://github.com/ArcletProject/tarina> — `src/tarina/signature.py`
* launart: <https://github.com/GraiaProject/launart> — `launart/service.py`, `launart/manager.py`
* NoneBot2: <https://github.com/nonebot/nonebot2> — `nonebot/dependencies/{__init__,utils}.py`, `nonebot/internal/params.py`, `nonebot/internal/matcher/matcher.py`
* Downstream plugin examples: <https://github.com/ArcletProject/entari-plugin-permission> (`src/entari_plugin_permission/params.py`), <https://github.com/ArcletProject/entari-plugin-database> (`src/entari_plugin_database/param.py`)
* Entari docs: <https://arclet.top/tutorial/entari/> (service + injection example), <https://arclet.top/tutorial/entari/permission.html> (`UserOwner` alias)
* PyPI metadata for the transitive dependency tree: <https://pypi.org/pypi/satori-python-client/json>
