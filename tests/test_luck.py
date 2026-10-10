from concurrent.futures import ThreadPoolExecutor
from datetime import date, datetime, timezone
from fractions import Fraction
import sqlite3
from unittest.mock import Mock

import pytest

from nonebot_plugin_jrrp4 import luck


@pytest.fixture(autouse=True)
def clear_calendar_cache():
    luck.get_day_profile.cache_clear()
    luck._warn_missing_holidays.cache_clear()
    yield
    luck.get_day_profile.cache_clear()
    luck._warn_missing_holidays.cache_clear()


def weights(bias, lower=0, upper=100):
    cumulative = luck.cumulative_weights(bias, lower, upper)
    return [cumulative[0]] + [b - a for a, b in zip(cumulative, cumulative[1:])]


def test_ordinary_distribution_is_symmetric_and_all_scores_possible():
    probabilities = weights(0)
    assert probabilities == probabilities[::-1]
    assert all(w > 0 for w in probabilities)
    assert sum(i * w for i, w in enumerate(probabilities)) == 50 * sum(probabilities)


@pytest.mark.parametrize('lower,upper', [(0, 100), (75, 100), (0, 40)])
def test_every_higher_threshold_becomes_more_likely_on_better_days(lower, upper):
    # 精确有理数比较所有阈值，验证一阶随机占优，而非仅比较平均值。
    previous = None
    for bias in range(7):
        ws = weights(bias, lower, upper)
        tails = [Fraction(sum(ws[i:]), sum(ws)) for i in range(1, len(ws))]
        assert ws[0] > 0  # 即使最吉利的日子，最低允许分数仍有概率。
        if previous is not None:
            assert all(new > old for new, old in zip(tails, previous))
        previous = tails


def test_sampling_is_reproducible_bounded_and_date_sensitive():
    seed = bytes(range(32))
    day = date(2026, 10, 10)
    first = [luck.sample_score(seed, str(i), day, 1) for i in range(300)]
    assert first == [luck.sample_score(seed, str(i), day, 1) for i in range(300)]
    assert all(0 <= s <= 100 for s in first)
    assert len(set(first)) > 50
    assert first != [luck.sample_score(seed, str(i), date(2026, 10, 11), 1) for i in range(300)]
    assert first != [luck.sample_score(b'x' * 32, str(i), day, 1) for i in range(300)]


def test_rejection_sampling_does_not_reduce_overflow_modulo_bound(monkeypatch):
    digest = Mock(side_effect=[b'\xff' * 32, b'\x00' * 32])
    monkeypatch.setattr(luck.hmac, 'digest', digest)
    assert luck.deterministic_randbelow(b'x' * 32, b'test', 3) == 0
    assert digest.call_count == 2
    assert luck.deterministic_randbelow(b'x' * 32, b'test', 1) == 0
    with pytest.raises(ValueError):
        luck.deterministic_randbelow(b'x' * 32, b'test', 0)


def test_real_calendar_holiday_makeup_workday_and_plain_weekend():
    # 2026-10-01 数据中同时为国庆放假和天赦日；10-10 为调休工作日。
    holiday = luck.get_day_profile(date(2026, 10, 1))
    assert holiday.bias == 5
    assert '天赦日' in holiday.reasons
    assert any(r.startswith('法定放假') for r in holiday.reasons)
    makeup = luck.get_day_profile(date(2026, 10, 10))
    assert makeup.bias == 1
    assert makeup.reasons == ('黄道日',)
    weekend = luck.get_day_profile(date(2026, 10, 11))
    assert weekend.bias == 0


def test_overlapping_bonuses_are_added(monkeypatch):
    lunar = Mock()
    lunar.getDayTianShenType.return_value = '黄道'
    lunar.getDayJiShen.return_value = ['天赦', '其他']
    monkeypatch.setattr(luck.Solar, 'fromYmd', Mock(return_value=Mock(getLunar=Mock(return_value=lunar))))
    monkeypatch.setattr(luck, 'get_holiday_detail', lambda day: (True, 'test holiday'))
    assert luck.get_day_profile(date(2026, 1, 1)).bias == 6


def test_missing_future_holidays_falls_back_without_inventing_dates(monkeypatch):
    def missing(day):
        raise NotImplementedError
    monkeypatch.setattr(luck, 'get_holiday_detail', missing)
    with pytest.warns(RuntimeWarning, match='放假数据'):
        profile = luck.get_day_profile(date(2027, 1, 1))
    assert not profile.holiday_data_available
    assert not any(r.startswith('法定放假') for r in profile.reasons)


def test_chinese_date_changes_at_shanghai_midnight(monkeypatch):
    class Clock:
        @staticmethod
        def now(tz):
            return datetime(2026, 10, 10, 16, 0, tzinfo=timezone.utc).astimezone(tz)
    monkeypatch.setattr(luck, 'datetime', Clock)
    assert luck.today_in_china() == date(2026, 10, 11)


def test_persistence_freezes_scores_and_calendar_and_preserves_seed(tmp_path, monkeypatch):
    path = tmp_path / 'luck.sqlite3'
    day = date(2026, 10, 10)
    monkeypatch.setattr(luck, 'get_day_profile', lambda day: luck.DayProfile(0, ()))
    engine = luck.LuckEngine(path)
    first = engine.score('42', day)
    with sqlite3.connect(path) as connection:
        seed = connection.execute("SELECT value FROM metadata WHERE key='seed'").fetchone()[0]
    monkeypatch.setattr(luck, 'get_day_profile', lambda day: luck.DayProfile(6, ('test',)))
    restarted = luck.LuckEngine(path, high_list=['42'])
    assert restarted.score('42', day) == first
    restarted.score('43', day)
    with sqlite3.connect(path) as connection:
        assert connection.execute('SELECT bias FROM days WHERE day=?', (day.isoformat(),)).fetchone()[0] == 0
        assert connection.execute("SELECT value FROM metadata WHERE key='seed'").fetchone()[0] == seed
    next_day = date(2026, 10, 11)
    assert restarted.score('42', next_day) >= 75


def test_list_ranges_priority_and_no_100_escape_for_low_list(tmp_path):
    engine = luck.LuckEngine(tmp_path / 'luck.sqlite3', high_list=['both', 'high'], low_list=['both', 'low'])
    for day in [date(2026, 10, 1), date(2026, 10, 10), date(2026, 10, 11)]:
        assert 75 <= engine.score('both', day) <= 100
        assert 75 <= engine.score('high', day) <= 100
        assert 0 <= engine.score('low', day) <= 40


def test_concurrent_first_queries_use_one_persisted_score(tmp_path):
    path = tmp_path / 'luck.sqlite3'
    engines = [luck.LuckEngine(path) for _ in range(4)]
    with ThreadPoolExecutor(max_workers=8) as pool:
        scores = list(pool.map(lambda i: engines[i % 4].score('42', date(2026, 10, 10)), range(32)))
    assert len(set(scores)) == 1
    with sqlite3.connect(path) as connection:
        assert connection.execute('SELECT count(*) FROM scores').fetchone()[0] == 1


def test_damaged_seed_is_not_silently_reset(tmp_path):
    path = tmp_path / 'luck.sqlite3'
    engine = luck.LuckEngine(path)
    with sqlite3.connect(path) as connection:
        connection.execute("UPDATE metadata SET value=? WHERE key='seed'", (b'bad',))
    with pytest.raises(ValueError, match='种子损坏'):
        engine.score('42', date(2026, 10, 10))
