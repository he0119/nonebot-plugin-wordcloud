from datetime import datetime

try:
    from zoneinfo import ZoneInfo
except ImportError:
    from backports.zoneinfo import ZoneInfo  # type: ignore

import pytest
from nonebug import App
from pytest_mock import MockerFixture

from .utils import fake_group_message_event


async def test_timezone(app: App, mocker: MockerFixture):
    """测试系统时区"""
    from nonebot_plugin_wordcloud import (
        get_datetime_fromisoformat_with_timezone,
        get_datetime_now_with_timezone,
    )

    mocked_datetime = mocker.patch("nonebot_plugin_wordcloud.datetime")
    mocked_datetime.now().astimezone.return_value = datetime(
        2022, 1, 1, 6, tzinfo=ZoneInfo("Asia/Shanghai")
    )
    mocked_datetime.fromisoformat().astimezone.return_value = datetime(
        2022, 1, 1, 7, tzinfo=ZoneInfo("Asia/Shanghai")
    )

    assert get_datetime_now_with_timezone() == datetime(
        2022, 1, 1, 6, tzinfo=ZoneInfo("Asia/Shanghai")
    )
    assert get_datetime_fromisoformat_with_timezone("2022-01-01") == datetime(
        2022, 1, 1, 7, tzinfo=ZoneInfo("Asia/Shanghai")
    )

    # 通过调用 astimezone 来获取当前时区
    mocked_datetime.now().astimezone.assert_called_once_with()
    mocked_datetime.fromisoformat.assert_any_call("2022-01-01")


async def test_set_timezone(app: App, mocker: MockerFixture):
    """测试设定时区"""
    from nonebot_plugin_wordcloud import (
        get_datetime_fromisoformat_with_timezone,
        get_datetime_now_with_timezone,
    )
    from nonebot_plugin_wordcloud.config import plugin_config

    # 设置时区
    plugin_config.wordcloud_timezone = "UTC"

    mocked_datetime = mocker.patch("nonebot_plugin_wordcloud.datetime")
    mocked_datetime.now.return_value = datetime(2022, 1, 1, 6, tzinfo=ZoneInfo("UTC"))
    mocked_datetime.fromisoformat().astimezone.return_value = datetime(
        2022, 1, 1, 7, tzinfo=ZoneInfo("UTC")
    )

    assert get_datetime_now_with_timezone() == datetime(
        2022, 1, 1, 6, tzinfo=ZoneInfo("UTC")
    )
    assert get_datetime_fromisoformat_with_timezone("2022-01-01") == datetime(
        2022, 1, 1, 7, tzinfo=ZoneInfo("UTC")
    )

    # 直接获取设定时区的时间
    mocked_datetime.now.assert_called_once_with(ZoneInfo("UTC"))
    mocked_datetime.fromisoformat.assert_any_call("2022-01-01")
    mocked_datetime.fromisoformat().astimezone.assert_called_once_with(ZoneInfo("UTC"))
