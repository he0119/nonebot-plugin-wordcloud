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
    from nonebot_plugin_chatrecorder import serialize_message
    from nonebot_plugin_chatrecorder.model import MessageRecord
    from nonebot_plugin_datastore import create_session

    from nonebot_plugin_wordcloud import wordcloud_cmd

    async with create_session() as session:
        for word in ["测试一下时区"]:
            message = MessageRecord(
                type="message",
                user_id="10",
                time=datetime(2022, 1, 1, 23, 0, 0),
                platform="qq",
                message_id="test",
                message=serialize_message(Message(word)),
                alt_message=word,
                detail_type="group",
                group_id="10000",
            )
            session.add(message)
        await session.commit()

    mocked_datetime = mocker.patch("nonebot_plugin_wordcloud.datetime")
    mocked_datetime.return_value = datetime(2022, 1, 1)
    mocked_datetime.now.return_value = datetime(2022, 1, 1, 6)
    mocked_get_wordcloud = mocker.patch("nonebot_plugin_wordcloud.get_wordcloud")
    mocked_get_wordcloud.return_value = None

    async with app.test_matcher(wordcloud_cmd) as ctx:
        bot = ctx.create_bot()
        event = fake_group_message_event(message=Message("/今日词云"))

        ctx.receive_event(bot, event)
        ctx.should_call_send(event, "没有足够的数据生成词云", True)
        ctx.should_finished()

    mocked_datetime.now.assert_called_once_with()
    mocked_datetime.assert_called_once_with(2022, 1, 1)
    mocked_get_wordcloud.assert_called_once_with([])


@pytest.mark.asyncio
async def test_different_timezone(app: App, mocker: MockerFixture):
    """测试设定时区"""
    from nonebot.adapters.onebot.v11 import Message
    from nonebot_plugin_chatrecorder import serialize_message
    from nonebot_plugin_chatrecorder.model import MessageRecord
    from nonebot_plugin_datastore import create_session

    from nonebot_plugin_wordcloud import wordcloud_cmd
    from nonebot_plugin_wordcloud.config import plugin_config

    async with create_session() as session:
        for word in ["测试一下时区"]:
            message = MessageRecord(
                type="message",
                user_id="10",
                time=datetime(2022, 1, 1, 23, 0, 0),
                platform="qq",
                message_id="test",
                message=serialize_message(Message(word)),
                alt_message=word,
                detail_type="group",
                group_id="10000",
            )
            session.add(message)
        await session.commit()

    plugin_config.wordcloud_timezone = "UTC"
    mocked_datetime = mocker.patch("nonebot_plugin_wordcloud.datetime")
    mocked_datetime.return_value = datetime(2022, 1, 1, tzinfo=ZoneInfo("UTC"))
    mocked_datetime.now.return_value = datetime(2022, 1, 1, 6, tzinfo=ZoneInfo("UTC"))
    mocked_get_wordcloud = mocker.patch("nonebot_plugin_wordcloud.get_wordcloud")
    mocked_get_wordcloud.return_value = None

    async with app.test_matcher(wordcloud_cmd) as ctx:
        bot = ctx.create_bot()
        event = fake_group_message_event(message=Message("/今日词云"))

        ctx.receive_event(bot, event)
        ctx.should_call_send(event, "没有足够的数据生成词云", True)
        ctx.should_finished()

    mocked_datetime.now.assert_called_once_with(ZoneInfo("UTC"))
    mocked_datetime.assert_called_once_with(2022, 1, 1, tzinfo=ZoneInfo("UTC"))
    mocked_get_wordcloud.assert_called_once_with(["测试一下时区"])
