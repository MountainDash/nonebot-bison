from __future__ import annotations

from datetime import datetime, time, timedelta
import random
from zoneinfo import ZoneInfo

from apscheduler.triggers.base import BaseTrigger


class DayNightIntervalTrigger(BaseTrigger):
    def __init__(
        self,
        *,
        base_interval_seconds: int,  # 白天基础间隔(秒)
        offpeak_multiplier: float,  # 非高峰时段倍数
        jitter_max_seconds: int,  # 单边抖动上限,范围 [0, N]
        timezone_name: str = "Asia/Shanghai",  # 判定时区
        day_start: time = time(10, 0, 0),  # 白天开始时间
        day_end: time = time(20, 0, 0),  # 白天结束时间(右开区间)
        enable_jitter: bool = True,  # 是否启用抖动
    ):
        if base_interval_seconds <= 0:
            raise ValueError("base_interval_seconds 必须大于 0")
        if offpeak_multiplier <= 0:
            raise ValueError("offpeak_multiplier 必须大于 0")
        if jitter_max_seconds < 0:
            raise ValueError("jitter_max_seconds 不能小于 0")

        self.base_interval_seconds = int(base_interval_seconds)
        self.offpeak_multiplier = float(offpeak_multiplier)
        self.jitter_max_seconds = int(jitter_max_seconds)
        self.timezone_name = timezone_name
        self.timezone = ZoneInfo(timezone_name)
        self.day_start = day_start
        self.day_end = day_end
        self.enable_jitter = enable_jitter

    def __getstate__(self):
        return {
            "base_interval_seconds": self.base_interval_seconds,
            "offpeak_multiplier": self.offpeak_multiplier,
            "jitter_max_seconds": self.jitter_max_seconds,
            "timezone_name": self.timezone_name,
            "day_start": self.day_start.isoformat(),
            "day_end": self.day_end.isoformat(),
            "enable_jitter": self.enable_jitter,
        }

    def __setstate__(self, state):
        self.base_interval_seconds = int(state["base_interval_seconds"])
        self.offpeak_multiplier = float(state["offpeak_multiplier"])
        self.jitter_max_seconds = int(state["jitter_max_seconds"])
        self.timezone_name = state["timezone_name"]
        self.timezone = ZoneInfo(self.timezone_name)
        self.day_start = time.fromisoformat(state["day_start"])
        self.day_end = time.fromisoformat(state["day_end"])
        self.enable_jitter = bool(state["enable_jitter"])

    def _is_day_window(self, dt: datetime) -> bool:
        local_dt = dt.astimezone(self.timezone)
        local_t = local_dt.timetz().replace(tzinfo=None)
        return self.day_start <= local_t < self.day_end

    def _get_day_interval_seconds(self) -> int:
        return self.base_interval_seconds

    def _get_offpeak_interval_seconds(self) -> int:
        interval = self.base_interval_seconds * self.offpeak_multiplier
        return max(1, round(interval))

    def _interval_for(self, dt: datetime) -> int:
        return self._get_day_interval_seconds() if self._is_day_window(dt) else self._get_offpeak_interval_seconds()

    def _next_boundary_after(self, dt: datetime) -> datetime:
        local_dt = dt.astimezone(self.timezone)
        today = local_dt.date()
        today_day_start = datetime.combine(today, self.day_start, self.timezone)
        today_day_end = datetime.combine(today, self.day_end, self.timezone)

        if local_dt < today_day_start:
            return today_day_start
        if local_dt < today_day_end:
            return today_day_end

        tomorrow = today + timedelta(days=1)
        return datetime.combine(tomorrow, self.day_start, self.timezone)

    def _add_positive_jitter(self, dt: datetime) -> datetime:
        if not self.enable_jitter or self.jitter_max_seconds <= 0:
            return dt
        return dt + timedelta(seconds=random.randint(0, self.jitter_max_seconds))

    def get_next_fire_time(
        self,
        previous_fire_time: datetime | None,
        now: datetime,
    ) -> datetime | None:
        if previous_fire_time is None:
            base = now.astimezone(self.timezone)
        else:
            prev_local = previous_fire_time.astimezone(self.timezone)
            now_local = now.astimezone(self.timezone)
            base = max(prev_local, now_local)

        current_interval = self._interval_for(base)
        candidate = base + timedelta(seconds=current_interval)
        boundary = self._next_boundary_after(base)

        if candidate > boundary:
            next_interval = self._interval_for(boundary)
            candidate = boundary + timedelta(seconds=next_interval)

        return self._add_positive_jitter(candidate)


def create_day_night_trigger(
    *,
    base_interval_seconds: int,  # 白天基础间隔(秒)
    offpeak_multiplier: float,  # 非高峰时段倍数
    jitter_max_seconds: int,  # 单边抖动上限,范围 [0, N]
    timezone_name: str = "Asia/Shanghai",  # 判定时区
    day_start_hour: int = 10,
    day_start_minute: int = 0,
    day_start_second: int = 0,
    day_end_hour: int = 20,
    day_end_minute: int = 0,
    day_end_second: int = 0,
    enable_jitter: bool = True,
) -> DayNightIntervalTrigger:
    return DayNightIntervalTrigger(
        base_interval_seconds=base_interval_seconds,
        offpeak_multiplier=offpeak_multiplier,
        jitter_max_seconds=jitter_max_seconds,
        timezone_name=timezone_name,
        day_start=time(day_start_hour, day_start_minute, day_start_second),
        day_end=time(day_end_hour, day_end_minute, day_end_second),
        enable_jitter=enable_jitter,
    )
