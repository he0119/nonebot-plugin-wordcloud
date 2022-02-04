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
async def test_stopwords(app: App, mocker: MockerFixture):
    """测试消息均是 stopwords 的情况"""
    from nonebot.adapters.onebot.v11 import Message
    from nonebot_plugin_chatrecorder import serialize_message
    from nonebot_plugin_chatrecorder.model import MessageRecord
    from nonebot_plugin_datastore import create_session

    from nonebot_plugin_wordcloud import wordcloud_cmd

    now = datetime(2022, 1, 2, 12, 0, 0, tzinfo=ZoneInfo("Asia/Shanghai"))

    async with create_session() as session:
        for word in ["你", "我", "他"]:
            message = MessageRecord(
                type="message",
                user_id="10",
                time=now.astimezone(ZoneInfo("UTC")),
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
    mocked_datetime.return_value = datetime(
        2022, 1, 2, tzinfo=ZoneInfo("Asia/Shanghai")
    )
    mocked_datetime.now.return_value = now

    async with app.test_matcher(wordcloud_cmd) as ctx:
        bot = ctx.create_bot()
        event = fake_group_message_event(message=Message("/今日词云"))

        ctx.receive_event(bot, event)
        ctx.should_call_send(event, "没有足够的数据生成词云", True)
        ctx.should_finished()

    mocked_datetime.now.assert_called_once()
    mocked_datetime.assert_called_once_with(2022, 1, 2)
