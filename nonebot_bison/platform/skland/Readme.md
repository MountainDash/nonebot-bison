# 森空岛接口说明文档

> 部分文件转载自：<https://gitee.com/FancyCabbage/skyland-auto-sign/>
> 原作者 xxyz30 @FancyCabbage
> 原项目：skyland-auto-sign
> 修改日期：2026/01/10
> MIT License
> Copyright (c) 2023 xxyz30

## 接口说明和使用示例

### 1. sk_token.py 接口

输入参数：

- `dId`: 设备ID（从shumei_did.py获取）
- `platform`: 平台标识，默认"3"
- `vName`: 版本名称，默认"1.0.0"

输出：

- `get_token()`: 返回有效的token字符串
- `get_current_token()`: 快捷函数获取token

使用示例：

```python
from shumei_did import get_d_id
from sk_token import get_token_manager

async def main():
    # 获取设备ID
    dId = get_d_id()

    # 获取token管理器
    token_manager = await get_token_manager(dId=dId)

    # 获取token
    token = await token_manager.get_token()
    print(f"获取到token: {token}")
```

### 2. sk_sign.py 接口说明

该模块负责生成请求所需的动态签名 `sign` 及包含时间戳的请求头 `headers`。为了提高请求成功率，请根据具体的 API 路径选择对应的签名函数。

输入参数：

- `token`: 访问令牌（由 `sk_token.py` 获取）
- `dId`: 设备 ID（由 `shumei_did.py` 获取）

输出

- `(sign, headers)`: 返回生成的签名字符串和包含 `timestamp` 等字段的请求头字典。

#### 接口分类与示例

##### A. 获取用户信息接口

函数: `generate_signature_for_user(token, userId, dId)`
适用路径: `/web/v1/user`

```python
from sk_sign import generate_signature_for_user

# 调用接口获取签名和基础头信息
sign, headers = generate_signature_for_user(token=token, userId=uid, dId=dId)
headers['sign'] = sign  # 必须手动注入生成的签名
```

##### B. 获取物品详情接口

函数: `generate_signature_for_item(token, itemId, dId)`
适用路径: `/web/v1/item`

```python
from sk_sign import generate_signature_for_item

# 针对具体物品 ID 生成签名
sign, headers = generate_signature_for_item(token=token, itemId="5650594", dId=dId)
headers['sign'] = sign
```

##### C. 获取用户物品列表接口

函数: `generate_signature_for_user_items(token, userId, pageSize, sortType, dId)`
适用路径: `/web/v1/user/items`

```python
from sk_sign import generate_signature_for_user_items

# 传入分页和排序参数以确保签名校验通过
sign, headers = generate_signature_for_user_items(
    token=token,
    userId=uid,
    pageSize="10",
    sortType="2",
    dId=dId
)
headers['sign'] = sign
```

#### 完整使用示例

```python
import httpx
import asyncio
from sk_sign import generate_signature_for_user_items

async def main():
    token = "你的token"
    dId = "你的设备ID"
    uid = "用户ID"

    # 调用专用接口生成签名
    sign, headers = generate_signature_for_user_items(
        token=token, userId=uid, pageSize="10", sortType="2", dId=dId
    )
    headers['sign'] = sign

    async with httpx.AsyncClient(http2=True) as client:
        res = await client.get(
            "https://zonai.skland.com/web/v1/user/items",
            params={'pageSize': '10', 'userId': uid, 'sortType': '2'},
            headers=headers
        )
        print(res.json())

if __name__ == "__main__":
    asyncio.run(main())
```

### 3. shumei_did.py 接口

输入参数：

- 无显式输入参数（依赖内部硬编码配置）

输出：

- `get_d_id()`: 返回设备ID字符串

使用示例：

```python
from shumei_did import get_d_id

def main():
    # 获取设备ID
    dId = get_d_id()
```

### 4. day_night_trigger.py 接口说明

该模块用于生成"分时调度"的自定义 APScheduler Trigger。
适用于需要按不同时段切换轮询频率的场景，例如：

- 白天高频轮询
- 夜间低频轮询
- 在固定基础间隔上附加正向抖动，避免请求时间过于整齐

当前实现逻辑为：

- 白天时段：使用基础间隔 `base_interval_seconds`
- 非白天时段：使用 `base_interval_seconds * offpeak_multiplier`
- 每次调度时间额外增加 `[0, jitter_max_seconds]` 秒抖动

默认时区为北京时间 `Asia/Shanghai`。

#### 输入参数

##### A. `DayNightIntervalTrigger(...)`

用于直接创建分时调度 Trigger 实例。

输入参数：

- `base_interval_seconds`
  白天时段基础轮询间隔，单位秒

- `offpeak_multiplier`
  非高峰时段倍数
  例如：白天为 `180` 秒，倍数为 `3`，则夜间为 `540` 秒

- `jitter_max_seconds`
  单边抖动上限，实际抖动范围为 `[0, jitter_max_seconds]`

- `timezone_name`
  判定时区，默认 `"Asia/Shanghai"`

- `day_start`
  白天开始时间，默认 `10:00:00`

- `day_end`
  白天结束时间，默认 `20:00:00`

- `enable_jitter`
  是否启用抖动，默认 `True`

输出：

- `DayNightIntervalTrigger` 实例，可直接传入 APScheduler 的 `add_job(...)`

##### B. `create_day_night_trigger(...)`

用于快速创建 Trigger 的工厂函数，适合在 `platform.py` 中直接调用。

输入参数：

- `base_interval_seconds`
  白天时段基础轮询间隔，单位秒

- `offpeak_multiplier`
  非高峰时段倍数

- `jitter_max_seconds`
  单边抖动上限，单位秒

- `timezone_name`
  判定时区，默认 `"Asia/Shanghai"`

- `day_start_hour` / `day_start_minute` / `day_start_second`
  白天开始时间，默认 `10:00:00`

- `day_end_hour` / `day_end_minute` / `day_end_second`
  白天结束时间，默认 `20:00:00`

- `enable_jitter`
  是否启用抖动，默认 `True`

输出：

- `DayNightIntervalTrigger` 实例

#### 使用示例

##### A. 直接创建 Trigger

```python
from datetime import time
from day_night_trigger import DayNightIntervalTrigger

trigger = DayNightIntervalTrigger(
    base_interval_seconds=180,
    offpeak_multiplier=3,
    jitter_max_seconds=15,
    timezone_name="Asia/Shanghai",
    day_start=time(10, 0, 0),
    day_end=time(20, 0, 0),
    enable_jitter=True,
)
```

##### B. 使用工厂函数创建 Trigger

```python
from day_night_trigger import create_day_night_trigger

trigger = create_day_night_trigger(
    base_interval_seconds=180,
    offpeak_multiplier=3,
    jitter_max_seconds=15,
)
```

##### C. 在 APScheduler 中使用

```python
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from day_night_trigger import create_day_night_trigger

scheduler = AsyncIOScheduler()

trigger = create_day_night_trigger(
    base_interval_seconds=180,
    offpeak_multiplier=3,
    jitter_max_seconds=15,
)

scheduler.add_job(
    func=your_job_function,
    trigger=trigger,
)

scheduler.start()
```

##### D. 在 platform.py 中作为 Site 调度配置使用

```python
from .day_night_trigger import create_day_night_trigger

class ExampleSite(Site):
    name = "example.com"
    schedule_type = create_day_night_trigger(
        base_interval_seconds=180,
        offpeak_multiplier=3,
        jitter_max_seconds=15,
    )
    schedule_setting = {}
    client_mgr = ExampleClientManager
```

#### 调度规则示例

当配置如下：

```python
trigger = create_day_night_trigger(
    base_interval_seconds=180,
    offpeak_multiplier=3,
    jitter_max_seconds=15,
)
```

则实际规则为：

- 北京时间 `10:00:00 <= t < 20:00:00`：
  每 `180` 秒触发一次，并附加 `[0, 15]` 秒抖动

- 其它时间：
  每 `540` 秒触发一次，并附加 `[0, 15]` 秒抖动

#### 说明

1. 该模块不绑定具体平台，可复用于任意需要"分时轮询"的场景。
1. 抖动为"单边正向抖动"，不会提前执行，只会在原定触发时间基础上向后偏移。
1. 如需调整白天时段，只需修改 `day_start` 和 `day_end` 参数。
1. 如需关闭抖动，可设置 `enable_jitter=False` 或将 `jitter_max_seconds=0`。
