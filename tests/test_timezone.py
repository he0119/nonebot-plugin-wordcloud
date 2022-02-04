from datetime import datetime

try:
    from zoneinfo import ZoneInfo
except ImportError:
    from backports.zoneinfo import ZoneInfo  # type: ignore

import pytest
from nonebug import App
from pytest_mock import MockerFixture

from .utils import fake_group_message_event


@pytest.mark.asyncio
async def test_timezone(app: App, mocker: MockerFixture):
    """测试系统时区"""
    from nonebot.adapters.onebot.v11 import Message

    from nonebot_plugin_wordcloud import wordcloud_cmd

    mocked_datetime = mocker.patch("nonebot_plugin_wordcloud.datetime")
    mocked_datetime.now().astimezone.return_value = datetime(
        2022, 1, 1, 6, tzinfo=ZoneInfo("Asia/Shanghai")
    )

    mocked_time = mocker.MagicMock()
    mocked_time.astimezone.return_value = datetime(
        2022, 1, 1, tzinfo=ZoneInfo("Asia/Shanghai")
    )

    mocked_datetime.return_value = mocked_time

    async with app.test_matcher(wordcloud_cmd) as ctx:
        bot = ctx.create_bot()
        event = fake_group_message_event(message=Message("/今日词云"))

        ctx.receive_event(bot, event)
        ctx.should_call_send(event, "没有足够的数据生成词云", True)
        ctx.should_finished()

    # 通过调用 astimezone 来获取当前时区
    mocked_datetime.now().astimezone.assert_called_once_with()
    mocked_datetime.assert_called_once_with(2022, 1, 1)
    mocked_time.astimezone.assert_called_once_with()


@pytest.mark.asyncio
async def test_different_timezone(app: App, mocker: MockerFixture):
    """测试设定时区"""
    from nonebot.adapters.onebot.v11 import Message

    from nonebot_plugin_wordcloud import wordcloud_cmd
    from nonebot_plugin_wordcloud.config import plugin_config

    # 设置时区
    plugin_config.wordcloud_timezone = "UTC"

    mocked_datetime = mocker.patch("nonebot_plugin_wordcloud.datetime")
    mocked_datetime.now.return_value = datetime(2022, 1, 1, 6, tzinfo=ZoneInfo("UTC"))

    mocked_datetime.return_value = datetime(2022, 1, 1, tzinfo=ZoneInfo("UTC"))

    async with app.test_matcher(wordcloud_cmd) as ctx:
        bot = ctx.create_bot()
        event = fake_group_message_event(message=Message("/今日词云"))

        ctx.receive_event(bot, event)
        ctx.should_call_send(event, "没有足够的数据生成词云", True)
        ctx.should_finished()

    # 直接获取设定时区的时间
    mocked_datetime.now.assert_called_once_with(ZoneInfo("UTC"))
    mocked_datetime.assert_called_once_with(2022, 1, 1, tzinfo=ZoneInfo("UTC"))
