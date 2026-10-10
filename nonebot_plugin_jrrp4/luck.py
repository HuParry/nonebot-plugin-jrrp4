"""可复现的每日抽样与历法权重；分数不预测现实中的运气。"""

from bisect import bisect_right
from contextlib import closing
from dataclasses import dataclass
from datetime import date, datetime
from functools import lru_cache
import hashlib
import hmac
import json
from pathlib import Path
import secrets
import sqlite3
from typing import Iterable
import warnings
from zoneinfo import ZoneInfo

from chinese_calendar import get_holiday_detail
from lunar_python import Solar

ALGORITHM_VERSION = "calendar-v1"
CHINA_TIMEZONE = ZoneInfo("Asia/Shanghai")


@dataclass(frozen=True)
class DayProfile:
    """bias 为整数概率倾斜参数，不是直接增加的分数。"""

    bias: int
    reasons: tuple[str, ...]
    holiday_data_available: bool = True


def today_in_china() -> date:
    return datetime.now(CHINA_TIMEZONE).date()


@lru_cache(maxsize=16)
def _warn_missing_holidays(year: int) -> None:
    warnings.warn(
        f"chinesecalendar 尚无 {year} 年的放假数据；该年仅应用黄历权重。"
        "请在官方安排公布后更新 chinesecalendar。",
        RuntimeWarning,
        stacklevel=2,
    )


@lru_cache(maxsize=128)
def get_day_profile(day: date) -> DayProfile:
    """以同一民用日期的零时黄历为准；周末和调休上班日不算节假日。"""
    lunar = Solar.fromYmd(day.year, day.month, day.day).getLunar()
    bias = 0
    reasons = []
    if lunar.getDayTianShenType() == "黄道":
        bias += 1
        reasons.append("黄道日")
    if "天赦" in lunar.getDayJiShen():
        bias += 3
        reasons.append("天赦日")
    available = True
    try:
        on_holiday, holiday_name = get_holiday_detail(day)
    except NotImplementedError:
        available = False
        _warn_missing_holidays(day.year)
    else:
        if on_holiday and holiday_name is not None:
            bias += 2
            reasons.append(f"法定放假：{holiday_name}")
    return DayProfile(bias, tuple(reasons), available)


@lru_cache(maxsize=64)
def cumulative_weights(bias: int, lower: int = 0, upper: int = 100) -> tuple[int, ...]:
    """精确整数权重：w(s)=(s+1)(101-s)(100+bias)^s 100^(100-s)。

    去掉公共因子后，相当于对 Beta-Binomial(100, 2, 2) 做指数倾斜。
    bias 增大时，任意高分阈值的尾概率严格增大（非退化区间）。
    所有允许分数都有正权重；截断名单区间后重新归一化。
    """
    if not 0 <= bias <= 6 or not 0 <= lower <= upper <= 100:
        raise ValueError("无效的概率参数或分数范围")
    cumulative = []
    total = 0
    for score in range(lower, upper + 1):
        total += (score + 1) * (101 - score) * (100 + bias) ** score * 100 ** (100 - score)
        cumulative.append(total)
    return tuple(cumulative)


def deterministic_randbelow(seed: bytes, payload: bytes, bound: int) -> int:
    """HMAC-SHA256 扩展随机位并拒绝越界值，避免取模偏差和浮点误差。"""
    if bound < 1:
        raise ValueError("bound 必须为正数")
    bits = (bound - 1).bit_length()
    if bits == 0:
        return 0
    byte_count = (bits + 7) // 8
    attempt = 0
    while True:
        output = bytearray()
        for block in range((byte_count + 31) // 32):
            message = payload + b"\x00sample\x00" + attempt.to_bytes(8, "big") + block.to_bytes(4, "big")
            output.extend(hmac.digest(seed, message, hashlib.sha256))
        candidate = int.from_bytes(output[:byte_count], "big") & ((1 << bits) - 1)
        if candidate < bound:
            return candidate
        attempt += 1


def sample_score(seed: bytes, user_id: str, day: date, bias: int, lower: int = 0, upper: int = 100) -> int:
    cumulative = cumulative_weights(bias, lower, upper)
    # 使用结构化编码和完整日期，防止字符串拼接歧义及跨年重复。
    payload = json.dumps([ALGORITHM_VERSION, day.isoformat(), user_id], separators=(",", ":")).encode()
    ticket = deterministic_randbelow(seed, payload, cumulative[-1])
    return lower + bisect_right(cumulative, ticket)


class LuckEngine:
    """持久化种子、当天历法快照和已查询结果，支持线程/进程并发。"""

    def __init__(self, database: Path, high_list: Iterable[str] = (), low_list: Iterable[str] = ()):
        self.database = database
        self.high_list = frozenset(high_list)
        self.low_list = frozenset(low_list)
        database.parent.mkdir(parents=True, exist_ok=True)
        with closing(self._connect()) as connection:
            with connection:
                connection.execute("CREATE TABLE IF NOT EXISTS metadata (key TEXT PRIMARY KEY, value BLOB NOT NULL)")
                connection.execute("""CREATE TABLE IF NOT EXISTS days (
                    day TEXT PRIMARY KEY, bias INTEGER NOT NULL CHECK(bias BETWEEN 0 AND 6),
                    reasons TEXT NOT NULL, holiday_data_available INTEGER NOT NULL)""")
                connection.execute("""CREATE TABLE IF NOT EXISTS scores (
                    day TEXT NOT NULL, user_id TEXT NOT NULL,
                    score INTEGER NOT NULL CHECK(score BETWEEN 0 AND 100),
                    PRIMARY KEY(day, user_id))""")
                connection.execute("INSERT OR IGNORE INTO metadata VALUES ('seed', ?)", (secrets.token_bytes(32),))

    def _connect(self) -> sqlite3.Connection:
        return sqlite3.connect(self.database, timeout=30)

    def score(self, user_id: str, day: date | None = None) -> int:
        day = today_in_china() if day is None else day
        date_key = day.isoformat()
        with closing(self._connect()) as connection:
            # 先锁定再查/写，两个并发的首次查询不会生成不同的当天结果。
            with connection:
                connection.execute("BEGIN IMMEDIATE")
                existing = connection.execute(
                    "SELECT score FROM scores WHERE day=? AND user_id=?", (date_key, user_id)
                ).fetchone()
                if existing is not None:
                    return existing[0]
                stored_day = connection.execute("SELECT bias FROM days WHERE day=?", (date_key,)).fetchone()
                if stored_day is None:
                    profile = get_day_profile(day)
                    connection.execute("INSERT INTO days VALUES (?, ?, ?, ?)", (
                        date_key, profile.bias, json.dumps(profile.reasons, ensure_ascii=False),
                        int(profile.holiday_data_available),
                    ))
                    bias = profile.bias
                else:
                    bias = stored_day[0]
                seed = connection.execute("SELECT value FROM metadata WHERE key='seed'").fetchone()[0]
                if not isinstance(seed, bytes) or len(seed) != 32:
                    raise ValueError("今日人品数据库种子损坏，请恢复备份；不会自动重置已有种子")
                lower, upper = (0, 100)
                if user_id in self.high_list:
                    lower = 75
                elif user_id in self.low_list:
                    upper = 40
                score = sample_score(seed, user_id, day, bias, lower, upper)
                connection.execute("INSERT INTO scores VALUES (?, ?, ?)", (date_key, user_id, score))
                return score
