from datetime import datetime, time

try:
    from zoneinfo import ZoneInfo
except ImportError:
    from backports.zoneinfo import ZoneInfo  # type: ignore

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
    plugin_config.wordcloud_timezone = "UTC"

    mocked_datetime.now.return_value = datetime(2022, 1, 1, 6, tzinfo=ZoneInfo("UTC"))
    assert get_datetime_now_with_timezone() == datetime(
        2022, 1, 1, 6, tzinfo=ZoneInfo("UTC")
    )
    mocked_datetime.now.assert_called_with(ZoneInfo("UTC"))


async def test_get_datetime_fromisoformat(app: App):
    """测试从 iso 格式字符串获取时间"""
    from nonebot_plugin_wordcloud.config import plugin_config
    from nonebot_plugin_wordcloud.utils import get_datetime_fromisoformat_with_timezone

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
    plugin_config.wordcloud_timezone = "UTC"

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


async def test_time_astimezone(app: App):
    """测试转换 time 对象时区"""
    from nonebot_plugin_wordcloud.utils import time_astimezone

    assert time_astimezone(time(10, 0, 0)).isoformat() == "10:00:00+08:00"

    assert (
        time_astimezone(time(10, 0, 0, tzinfo=ZoneInfo("UTC"))).isoformat()
        == "18:00:00+08:00"
    )


async def test_get_time_fromisoformat(app: App):
    """测试从 iso 格式字符串获取时间"""
    from nonebot_plugin_wordcloud.config import plugin_config
    from nonebot_plugin_wordcloud.utils import get_time_fromisoformat_with_timezone

    assert (
        get_time_fromisoformat_with_timezone("10:00:00").isoformat() == "10:00:00+08:00"
    )
    assert (
        get_time_fromisoformat_with_timezone("10:00:00+07:00").isoformat()
        == "11:00:00+08:00"
    )

    plugin_config.wordcloud_timezone = "UTC"

    assert (
        get_time_fromisoformat_with_timezone("10:00:00").isoformat() == "10:00:00+00:00"
    )
    assert (
        get_time_fromisoformat_with_timezone("10:00:00+08:00").isoformat()
        == "02:00:00+00:00"
    )
