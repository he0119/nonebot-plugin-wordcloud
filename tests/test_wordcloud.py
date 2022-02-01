from datetime import datetime, timedelta
from io import BytesIO

try:
    from zoneinfo import ZoneInfo
except ImportError:
    from backports.zoneinfo import ZoneInfo  # type: ignore

import pytest
from nonebug import App
from pytest_mock import MockerFixture

from .utils import fake_group_message_event


@pytest.mark.asyncio
async def test_wordcloud(app: App, mocker: MockerFixture):
    """测试词云"""
    from nonebot.adapters.onebot.v11 import Message, MessageSegment
    from nonebot_plugin_chatrecorder import get_message_records, serialize_message
    from nonebot_plugin_chatrecorder.model import MessageRecord
    from nonebot_plugin_datastore import create_session

    from nonebot_plugin_wordcloud import get_wordcloud, wordcloud_cmd

    now = datetime(2022, 1, 2, 12, 0, 0, tzinfo=ZoneInfo("Asia/Shanghai"))

    async with create_session() as session:
        for word in ["你", "我", "他", "这是一句完整的话", "你知道吗？今天的天气真好呀！", "/今日词云"]:
            message = MessageRecord(
                type="message",
                user_id="10",
                time=datetime(2022, 1, 2, 4, 0, 0),
                platform="qq",
                message_id="test",
                message=serialize_message(Message(word)),
                alt_message=word,
                detail_type="group",
                group_id="10000",
            )
            session.add(message)
        await session.commit()

    messages = await get_message_records(
        group_ids=["10000"],
        time_start=now - timedelta(days=1),
        time_stop=now,
        plain_text=True,
    )
    image = get_wordcloud(messages)

    assert image is not None
    assert image.size == (1920, 1200)

    mocked_datetime = mocker.patch("nonebot_plugin_wordcloud.datetime")
    mocked_datetime.return_value = datetime(
        2022, 1, 2, tzinfo=ZoneInfo("Asia/Shanghai")
    )
    mocked_datetime.now.return_value = now
    mocked_get_wordcloud = mocker.patch("nonebot_plugin_wordcloud.get_wordcloud")
    mocked_get_wordcloud.return_value = image
    img_bytes = BytesIO()
    image.save(img_bytes, format="PNG")

    async with app.test_matcher(wordcloud_cmd) as ctx:
        bot = ctx.create_bot()
        event = fake_group_message_event(message=Message("/今日词云"))

        ctx.receive_event(bot, event)
        ctx.should_call_send(event, MessageSegment.image(img_bytes), True)
        ctx.should_finished()

    mocked_datetime.now.assert_called_once()
    mocked_datetime.assert_called_once_with(
        2022, 1, 2, tzinfo=ZoneInfo("Asia/Shanghai")
    )
    mocked_get_wordcloud.assert_called_once()


@pytest.mark.asyncio
async def test_history_wordcloud(app: App, mocker: MockerFixture):
    """测试历史词云"""
    from nonebot.adapters.onebot.v11 import Message, MessageSegment
    from nonebot_plugin_chatrecorder import get_message_records, serialize_message
    from nonebot_plugin_chatrecorder.model import MessageRecord
    from nonebot_plugin_datastore import create_session

    from nonebot_plugin_wordcloud import get_wordcloud, wordcloud_cmd

    history = datetime(2022, 1, 1, 12, 0, 0, tzinfo=ZoneInfo("Asia/Shanghai"))

    async with create_session() as session:
        for word in ["你", "我", "他", "这是一句完整的话", "你知道吗？今天的天气真好呀！", "/今日词云"]:
            message = MessageRecord(
                type="message",
                user_id="10",
                time=datetime(2022, 1, 1, 4, 0, 0),
                platform="qq",
                message_id="test",
                message=serialize_message(Message(word)),
                alt_message=word,
                detail_type="group",
                group_id="10000",
            )
            session.add(message)
        await session.commit()

    messages = await get_message_records(
        group_ids=["10000"],
        time_start=history - timedelta(days=1),
        time_stop=history,
        plain_text=True,
    )
    image = get_wordcloud(messages)

    assert image is not None
    assert image.size == (1920, 1200)

    mocked_datetime = mocker.patch("nonebot_plugin_wordcloud.datetime")
    mocked_datetime.return_value = datetime(
        2022, 1, 1, tzinfo=ZoneInfo("Asia/Shanghai")
    )
    mocked_get_wordcloud = mocker.patch("nonebot_plugin_wordcloud.get_wordcloud")
    mocked_get_wordcloud.return_value = image
    img_bytes = BytesIO()
    image.save(img_bytes, format="PNG")

    async with app.test_matcher(wordcloud_cmd) as ctx:
        bot = ctx.create_bot()
        event = fake_group_message_event(message=Message("/历史词云 2022-01-01"))

        ctx.receive_event(bot, event)
        ctx.should_call_send(event, MessageSegment.image(img_bytes), True)
        ctx.should_finished()

    mocked_datetime.assert_called_once_with(
        2022, 1, 1, tzinfo=ZoneInfo("Asia/Shanghai")
    )
    mocked_get_wordcloud.assert_called_once()


@pytest.mark.asyncio
async def test_wordcloud_empty(app: App):
    """测试词云，消息为空的情况"""
    from nonebot.adapters.onebot.v11 import Message

    from nonebot_plugin_wordcloud import wordcloud_cmd

    async with app.test_matcher(wordcloud_cmd) as ctx:
        bot = ctx.create_bot()
        event = fake_group_message_event(message=Message("/今日词云"))

        ctx.receive_event(bot, event)
        ctx.should_call_send(event, "没有足够的数据生成词云", True)
        ctx.should_finished()


@pytest.mark.asyncio
async def test_wordcloud_empty_msg(
    app: App,
    mocker: MockerFixture,
):
    """测试词云，消息均是 stopwords 的情况"""
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
                time=datetime(2022, 1, 2, 4, 0, 0),
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
    mocked_datetime.assert_called_once_with(
        2022, 1, 2, tzinfo=ZoneInfo("Asia/Shanghai")
    )


@pytest.mark.asyncio
async def test_wordcloud_help(app: App):
    """测试输出帮助信息"""
    from nonebot.adapters.onebot.v11 import Message

    from nonebot_plugin_wordcloud import wordcloud_cmd

    async with app.test_matcher(wordcloud_cmd) as ctx:
        bot = ctx.create_bot()
        event = fake_group_message_event(message=Message("/词云"))

        ctx.receive_event(bot, event)
        ctx.should_call_send(
            event,
            "词云\n\n获取今天的词云\n/今日词云\n获取昨天的词云\n/昨日词云\n获取历史词云\n/历史词云\n/历史词云 2022-01-01",
            True,
        )
        ctx.should_finished()
