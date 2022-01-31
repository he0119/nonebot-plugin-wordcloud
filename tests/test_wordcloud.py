from datetime import datetime, timedelta
from io import BytesIO
from typing import List

try:
    from zoneinfo import ZoneInfo
except ImportError:
    from backports.zoneinfo import ZoneInfo  # type: ignore

import pytest
from nonebug import App
from pytest_mock import MockerFixture
from sqlmodel import select

from .utils import fake_group_message_event


@pytest.mark.asyncio
async def test_wordcloud(app: App, mocker: MockerFixture):
    """测试词云"""
    from nonebot.adapters.onebot.v11 import Message, MessageSegment
    from nonebot_plugin_datastore import create_session

    from nonebot_plugin_wordcloud import GroupMessage, get_wordcloud, today_cmd

    now = datetime(2022, 1, 2, 12, 0, 0, tzinfo=ZoneInfo("Asia/Shanghai"))

    async with create_session() as session:
        for word in ["你", "我", "他", "这是一句完整的话", "你知道吗？今天的天气真好呀！", "/今日词云"]:
            message = GroupMessage(
                user_id="10",
                group_id="10000",
                message=word,
                time=datetime(2022, 1, 2, 4, 0, 0),
                platform="qq",
            )
            session.add(message)
        await session.commit()

        # 中国时区差了 8 小时
        statement = select(GroupMessage).where(
            GroupMessage.group_id == "10000",
            GroupMessage.time >= now - timedelta(days=1),
            GroupMessage.time <= now,
        )
        messages: List[GroupMessage] = (await session.exec(statement)).all()  # type: ignore

    image = get_wordcloud(messages)

    assert image is not None
    assert image.size == (1920, 1200)

    mocked_datetime = mocker.patch("nonebot_plugin_wordcloud.datetime")
    mocked_datetime.now.return_value = now
    mocked_get_wordcloud = mocker.patch("nonebot_plugin_wordcloud.get_wordcloud")
    mocked_get_wordcloud.return_value = image
    img_bytes = BytesIO()
    image.save(img_bytes, format="PNG")

    async with app.test_matcher(today_cmd) as ctx:
        bot = ctx.create_bot()
        event = fake_group_message_event(message=Message("/今日词云"))

        ctx.receive_event(bot, event)
        ctx.should_call_send(event, MessageSegment.image(img_bytes), True)
        ctx.should_finished()

    mocked_datetime.now.assert_called_once()
    mocked_get_wordcloud.assert_called_once()


@pytest.mark.asyncio
async def test_wordcloud_empty(app: App):
    """测试词云，消息为空的情况"""
    from nonebot.adapters.onebot.v11 import Message

    from nonebot_plugin_wordcloud import today_cmd

    async with app.test_matcher(today_cmd) as ctx:
        bot = ctx.create_bot()
        event = fake_group_message_event(message=Message("/今日词云"))

        ctx.receive_event(bot, event)
        ctx.should_call_send(event, "没有足够的数据生成词云", "")
        ctx.should_finished()


@pytest.mark.asyncio
async def test_wordcloud_empty_msg(
    app: App,
    mocker: MockerFixture,
):
    """测试词云，消息均是 stopwords 的情况"""
    from nonebot.adapters.onebot.v11 import Message
    from nonebot_plugin_datastore import create_session

    from nonebot_plugin_wordcloud import GroupMessage, today_cmd

    now = datetime(2022, 1, 2, 12, 0, 0, tzinfo=ZoneInfo("Asia/Shanghai"))

    async with create_session() as session:
        for word in ["你", "我", "他"]:
            message = GroupMessage(
                user_id="10",
                group_id="10000",
                message=word,
                time=datetime(2022, 1, 2, 4, 0, 0),
                platform="qq",
            )
            session.add(message)
        await session.commit()

    mocked_datetime = mocker.patch("nonebot_plugin_wordcloud.datetime")
    mocked_datetime.now.return_value = now

    async with app.test_matcher(today_cmd) as ctx:
        bot = ctx.create_bot()
        event = fake_group_message_event(message=Message("/今日词云"))

        ctx.receive_event(bot, event)
        ctx.should_call_send(event, "没有足够的数据生成词云", True)
        ctx.should_finished()
