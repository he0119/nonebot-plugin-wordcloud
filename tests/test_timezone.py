from datetime import datetime, time
from zoneinfo import ZoneInfo

from nonebug import App
from pytest_mock import MockerFixture


async def test_get_datetime_now(app: App, mocker: MockerFixture):
    """测试获得当前时间"""
    from nonebot_plugin_wordcloud.config import plugin_config
    from nonebot_plugin_wordcloud.utils import get_datetime_now_with_timezone

    mocked_datetime = mocker.patch("nonebot_plugin_wordcloud.utils.datetime")
    mocked_datetime.now().astimezone.return_value = datetime(
        2022, 1, 1, 6, tzinfo=ZoneInfo("Asia/Shanghai")
    )

    assert get_datetime_now_with_timezone() == datetime(
        2022, 1, 1, 6, tzinfo=ZoneInfo("Asia/Shanghai")
    )

    # 通过调用 astimezone 来获取当前时区
    mocked_datetime.now().astimezone.assert_called_once_with()

    # 设置时区
    mocker.patch.object(plugin_config, "wordcloud_timezone", "UTC")

    mocked_datetime.now.return_value = datetime(2022, 1, 1, 6, tzinfo=ZoneInfo("UTC"))
    assert get_datetime_now_with_timezone() == datetime(
        2022, 1, 1, 6, tzinfo=ZoneInfo("UTC")
    )
    mocked_datetime.now.assert_called_with(ZoneInfo("UTC"))


async def test_time(app: App, mocker: MockerFixture):
    """测试时间相关函数"""
    from nonebot_plugin_wordcloud.config import plugin_config
    from nonebot_plugin_wordcloud.utils import (
        get_datetime_fromisoformat_with_timezone,
        get_time_fromisoformat_with_timezone,
        time_astimezone,
    )

    # 测试从 iso 格式字符串获取时间
    assert (
        get_datetime_fromisoformat_with_timezone("2022-01-01T10:00:00").isoformat()
        == "2022-01-01T10:00:00+08:00"
    )
    assert (
        get_datetime_fromisoformat_with_timezone(
            "2022-01-01T10:00:00+07:00"
        ).isoformat()
        == "2022-01-01T11:00:00+08:00"
    )

    # 设置时区
    mocker.patch.object(plugin_config, "wordcloud_timezone", "UTC")

    assert (
        get_datetime_fromisoformat_with_timezone("2022-01-01T10:00:00").isoformat()
        == "2022-01-01T10:00:00+00:00"
    )
    assert (
        get_datetime_fromisoformat_with_timezone(
            "2022-01-01T10:00:00+08:00"
        ).isoformat()
        == "2022-01-01T02:00:00+00:00"
    )

    # 测试转换 time 对象时区
    assert time_astimezone(time(10, 0, 0)).isoformat() == "10:00:00+08:00"

    assert (
        time_astimezone(time(10, 0, 0, tzinfo=ZoneInfo("UTC"))).isoformat()
        == "18:00:00+08:00"
    )

    # 测试从 iso 格式字符串获取时间
    mocker.patch.object(plugin_config, "wordcloud_timezone", None)
    assert (
        get_time_fromisoformat_with_timezone("10:00:00").isoformat() == "10:00:00+08:00"
    )
    assert (
        get_time_fromisoformat_with_timezone("10:00:00+07:00").isoformat()
        == "11:00:00+08:00"
    )

    mocker.patch.object(plugin_config, "wordcloud_timezone", "UTC")

    assert (
        get_time_fromisoformat_with_timezone("10:00:00").isoformat() == "10:00:00+00:00"
    )
    assert (
        get_time_fromisoformat_with_timezone("10:00:00+08:00").isoformat()
        == "02:00:00+00:00"
    )


def test_period_range_helpers():
    """测试周期范围辅助函数"""
    from nonebot_plugin_wordcloud.model import ScheduleType
    from nonebot_plugin_wordcloud.utils import (
        get_current_period_range,
        get_previous_period_range,
        is_period_end,
        is_period_start,
    )

    dt = datetime(2024, 5, 15, 22)

    assert get_current_period_range(dt, ScheduleType.DAY) == (
        datetime(2024, 5, 15),
        dt,
    )
    assert get_previous_period_range(dt, ScheduleType.DAY) == (
        datetime(2024, 5, 14),
        datetime(2024, 5, 15),
    )
    assert get_current_period_range(dt, ScheduleType.WEEK) == (
        datetime(2024, 5, 13),
        dt,
    )
    assert get_previous_period_range(dt, ScheduleType.WEEK) == (
        datetime(2024, 5, 6),
        datetime(2024, 5, 13),
    )
    assert get_current_period_range(dt, ScheduleType.MONTH) == (
        datetime(2024, 5, 1),
        dt,
    )
    assert get_previous_period_range(dt, ScheduleType.MONTH) == (
        datetime(2024, 4, 1),
        datetime(2024, 5, 1),
    )
    assert get_current_period_range(dt, ScheduleType.YEAR) == (
        datetime(2024, 1, 1),
        dt,
    )
    assert get_previous_period_range(dt, ScheduleType.YEAR) == (
        datetime(2023, 1, 1),
        datetime(2024, 1, 1),
    )

    assert is_period_start(datetime(2024, 5, 13, 22), ScheduleType.WEEK)
    assert not is_period_start(datetime(2024, 5, 14, 22), ScheduleType.WEEK)
    assert is_period_end(datetime(2024, 5, 12, 22), ScheduleType.WEEK)
    assert not is_period_end(datetime(2024, 5, 11, 22), ScheduleType.WEEK)
    assert is_period_end(datetime(2024, 5, 31, 22), ScheduleType.MONTH)
