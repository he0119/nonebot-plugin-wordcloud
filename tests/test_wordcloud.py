from datetime import datetime

try:
    from zoneinfo import ZoneInfo
except ImportError:
    from backports.zoneinfo import ZoneInfo  # type: ignore

import pytest
from nonebug import App
from PIL import Image
from pytest_mock import MockerFixture

from .utils import fake_group_message_event

FAKE_IMAGE = (
    Image.new("RGB", (1, 1), (255, 255, 255)),
    "base64://iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAIAAACQd1PeAAAADElEQVR4nGP4//8/AAX+Av4N70a4AAAAAElFTkSuQmCC",
)


@pytest.fixture
async def message_record(app: App):
    from nonebot.adapters.onebot.v11 import Message
    from nonebot_plugin_chatrecorder import serialize_message
    from nonebot_plugin_chatrecorder.model import MessageRecord
    from nonebot_plugin_datastore import create_session

    def make_message_record(message: str, user_id: str, time: datetime):
        return MessageRecord(
            type="message",
            user_id=user_id,
            time=time,  # UTC 时间
            platform="qq",
            message_id="test",
            message=serialize_message(Message(message)),
            alt_message=message,
            detail_type="group",
            group_id="10000",
        )

    async with create_session() as session:
        # UTC 时间
        session.add(make_message_record("10-1", "10", datetime(2022, 1, 1, 4, 0, 0)))
        session.add(make_message_record("11-1", "11", datetime(2022, 1, 1, 4, 0, 0)))
        session.add(make_message_record("10-2", "10", datetime(2022, 1, 2, 4, 0, 0)))
        session.add(make_message_record("11-2", "11", datetime(2022, 1, 2, 4, 0, 0)))
        await session.commit()


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
async def test_wordcloud_help(app: App):
    """测试输出帮助信息"""
    from nonebot.adapters.onebot.v11 import Message

    from nonebot_plugin_wordcloud import cleandoc, wordcloud_cmd

    async with app.test_matcher(wordcloud_cmd) as ctx:
        bot = ctx.create_bot()
        event = fake_group_message_event(message=Message("/词云"))

        ctx.receive_event(bot, event)
        ctx.should_call_send(
            event,
            cleandoc(wordcloud_cmd.__doc__) if wordcloud_cmd.__doc__ else "",
            True,
        )
        ctx.should_finished()


@pytest.mark.asyncio
async def test_wordcloud_exclude_bot_msg(
    app: App, mocker: MockerFixture, message_record: None
):
    """测试词云，排除机器人自己的消息"""
    from nonebot.adapters.onebot.v11 import Message, MessageSegment

    from nonebot_plugin_wordcloud import wordcloud_cmd

    mocked_datetime_now = mocker.patch(
        "nonebot_plugin_wordcloud.get_datetime_now_with_timezone",
        return_value=datetime(2022, 1, 1, 12, 0, 0, tzinfo=ZoneInfo("Asia/Shanghai")),
    )

    mocked_get_wordcloud = mocker.patch(
        "nonebot_plugin_wordcloud.get_wordcloud",
        return_value=FAKE_IMAGE[0],
    )

    async with app.test_matcher(wordcloud_cmd) as ctx:
        bot = ctx.create_bot(self_id="10")
        event = fake_group_message_event(message=Message("/今日词云"))

        ctx.receive_event(bot, event)
        ctx.should_call_send(
            event,
            MessageSegment.image(FAKE_IMAGE[1]),
            True,
        )
        ctx.should_finished()

    mocked_datetime_now.assert_called_once_with()
    mocked_get_wordcloud.assert_called_once_with(["11-1"])


@pytest.mark.asyncio
async def test_today_wordcloud(app: App, mocker: MockerFixture, message_record: None):
    """测试今日词云"""
    from nonebot.adapters.onebot.v11 import Message, MessageSegment

    from nonebot_plugin_wordcloud import wordcloud_cmd

    mocked_datetime_now = mocker.patch(
        "nonebot_plugin_wordcloud.get_datetime_now_with_timezone",
        return_value=datetime(2022, 1, 1, 2, tzinfo=ZoneInfo("Asia/Shanghai")),
    )

    mocked_get_wordcloud = mocker.patch(
        "nonebot_plugin_wordcloud.get_wordcloud",
        return_value=FAKE_IMAGE[0],
    )

    async with app.test_matcher(wordcloud_cmd) as ctx:
        bot = ctx.create_bot()
        event = fake_group_message_event(message=Message("/今日词云"))

        ctx.receive_event(bot, event)
        ctx.should_call_send(
            event,
            MessageSegment.image(FAKE_IMAGE[1]),
            True,
        )
        ctx.should_finished()

    mocked_datetime_now.assert_called_once_with()
    mocked_get_wordcloud.assert_called_once_with(["10-1", "11-1"])


@pytest.mark.asyncio
async def test_my_today_wordcloud(
    app: App, mocker: MockerFixture, message_record: None
):
    """测试我的今日词云"""
    from nonebot.adapters.onebot.v11 import Message, MessageSegment

    from nonebot_plugin_wordcloud import wordcloud_cmd

    mocked_datetime_now = mocker.patch(
        "nonebot_plugin_wordcloud.get_datetime_now_with_timezone",
        return_value=datetime(2022, 1, 1, 2, tzinfo=ZoneInfo("Asia/Shanghai")),
    )

    mocked_get_wordcloud = mocker.patch(
        "nonebot_plugin_wordcloud.get_wordcloud",
        return_value=FAKE_IMAGE[0],
    )

    async with app.test_matcher(wordcloud_cmd) as ctx:
        bot = ctx.create_bot()
        event = fake_group_message_event(message=Message("/我的今日词云"))

        ctx.receive_event(bot, event)
        ctx.should_call_send(
            event,
            MessageSegment.image(FAKE_IMAGE[1]),
            True,
        )
        ctx.should_finished()

    mocked_datetime_now.assert_called_once_with()
    mocked_get_wordcloud.assert_called_once_with(["10-1"])


@pytest.mark.asyncio
async def test_yesterday_wordcloud(
    app: App, mocker: MockerFixture, message_record: None
):
    """测试昨日词云"""
    from nonebot.adapters.onebot.v11 import Message, MessageSegment

    from nonebot_plugin_wordcloud import wordcloud_cmd

    mocked_datetime_now = mocker.patch(
        "nonebot_plugin_wordcloud.get_datetime_now_with_timezone",
        return_value=datetime(2022, 1, 2, 2, tzinfo=ZoneInfo("Asia/Shanghai")),
    )

    mocked_get_wordcloud = mocker.patch(
        "nonebot_plugin_wordcloud.get_wordcloud",
        return_value=FAKE_IMAGE[0],
    )

    async with app.test_matcher(wordcloud_cmd) as ctx:
        bot = ctx.create_bot()
        event = fake_group_message_event(message=Message("/昨日词云"))

        ctx.receive_event(bot, event)
        ctx.should_call_send(
            event,
            MessageSegment.image(FAKE_IMAGE[1]),
            True,
        )
        ctx.should_finished()

    mocked_datetime_now.assert_called_once_with()
    mocked_get_wordcloud.assert_called_once_with(["10-1", "11-1"])


@pytest.mark.asyncio
async def test_my_yesterday_wordcloud(
    app: App, mocker: MockerFixture, message_record: None
):
    """测试我的昨日词云"""
    from nonebot.adapters.onebot.v11 import Message, MessageSegment

    from nonebot_plugin_wordcloud import wordcloud_cmd

    mocked_datetime_now = mocker.patch(
        "nonebot_plugin_wordcloud.get_datetime_now_with_timezone",
        return_value=datetime(2022, 1, 2, 2, tzinfo=ZoneInfo("Asia/Shanghai")),
    )

    mocked_get_wordcloud = mocker.patch(
        "nonebot_plugin_wordcloud.get_wordcloud",
        return_value=FAKE_IMAGE[0],
    )

    async with app.test_matcher(wordcloud_cmd) as ctx:
        bot = ctx.create_bot()
        event = fake_group_message_event(message=Message("/我的昨日词云"))

        ctx.receive_event(bot, event)
        ctx.should_call_send(
            event,
            MessageSegment.image(FAKE_IMAGE[1]),
            True,
        )
        ctx.should_finished()

    mocked_datetime_now.assert_called_once_with()
    mocked_get_wordcloud.assert_called_once_with(["10-1"])


@pytest.mark.asyncio
async def test_year_wordcloud(app: App, mocker: MockerFixture, message_record: None):
    """测试年度词云"""
    from nonebot.adapters.onebot.v11 import Message, MessageSegment

    from nonebot_plugin_wordcloud import wordcloud_cmd

    mocked_datetime_now = mocker.patch(
        "nonebot_plugin_wordcloud.get_datetime_now_with_timezone",
        return_value=datetime(2022, 1, 1, 2, tzinfo=ZoneInfo("Asia/Shanghai")),
    )

    mocked_get_wordcloud = mocker.patch(
        "nonebot_plugin_wordcloud.get_wordcloud",
        return_value=FAKE_IMAGE[0],
    )

    async with app.test_matcher(wordcloud_cmd) as ctx:
        bot = ctx.create_bot()
        event = fake_group_message_event(message=Message("/年度词云"))

        ctx.receive_event(bot, event)
        ctx.should_call_send(
            event,
            MessageSegment.image(FAKE_IMAGE[1]),
            True,
        )
        ctx.should_finished()

    mocked_datetime_now.assert_called_once_with()
    mocked_get_wordcloud.assert_called_once_with(["10-1", "11-1", "10-2", "11-2"])


@pytest.mark.asyncio
async def test_my_year_wordcloud(app: App, mocker: MockerFixture, message_record: None):
    """测试我的年度词云"""
    from nonebot.adapters.onebot.v11 import Message, MessageSegment

    from nonebot_plugin_wordcloud import wordcloud_cmd

    mocked_datetime_now = mocker.patch(
        "nonebot_plugin_wordcloud.get_datetime_now_with_timezone",
        return_value=datetime(2022, 1, 1, 2, tzinfo=ZoneInfo("Asia/Shanghai")),
    )

    mocked_get_wordcloud = mocker.patch(
        "nonebot_plugin_wordcloud.get_wordcloud",
        return_value=FAKE_IMAGE[0],
    )

    async with app.test_matcher(wordcloud_cmd) as ctx:
        bot = ctx.create_bot()
        event = fake_group_message_event(message=Message("/我的年度词云"))

        ctx.receive_event(bot, event)
        ctx.should_call_send(
            event,
            MessageSegment.image(FAKE_IMAGE[1]),
            True,
        )
        ctx.should_finished()

    mocked_datetime_now.assert_called_once_with()
    mocked_get_wordcloud.assert_called_once_with(["10-1", "10-2"])


@pytest.mark.asyncio
async def test_history_wordcloud(app: App, mocker: MockerFixture, message_record: None):
    """测试历史词云"""
    from nonebot.adapters.onebot.v11 import Message, MessageSegment

    from nonebot_plugin_wordcloud import wordcloud_cmd

    mocked_datetime_fromisoformat = mocker.patch(
        "nonebot_plugin_wordcloud.get_datetime_fromisoformat_with_timezone",
        return_value=datetime(2022, 1, 1, tzinfo=ZoneInfo("Asia/Shanghai")),
    )

    mocked_get_wordcloud = mocker.patch(
        "nonebot_plugin_wordcloud.get_wordcloud",
        return_value=FAKE_IMAGE[0],
    )

    async with app.test_matcher(wordcloud_cmd) as ctx:
        bot = ctx.create_bot()
        event = fake_group_message_event(message=Message("/历史词云 2022-01-01"))

        ctx.receive_event(bot, event)
        ctx.should_call_send(
            event,
            MessageSegment.image(FAKE_IMAGE[1]),
            True,
        )
        ctx.should_finished()

    mocked_datetime_fromisoformat.assert_called_once_with("2022-01-01")
    mocked_get_wordcloud.assert_called_once_with(["10-1", "11-1"])


@pytest.mark.asyncio
async def test_history_wordcloud_start_stop(
    app: App, mocker: MockerFixture, message_record: None
):
    """测试历史词云，有起始时间的情况"""
    from nonebot.adapters.onebot.v11 import Message, MessageSegment

    from nonebot_plugin_wordcloud import wordcloud_cmd

    mocked_datetime_fromisoformat = mocker.patch(
        "nonebot_plugin_wordcloud.get_datetime_fromisoformat_with_timezone",
        side_effect=[
            datetime(2022, 1, 1, tzinfo=ZoneInfo("Asia/Shanghai")),
            datetime(2022, 2, 22, tzinfo=ZoneInfo("Asia/Shanghai")),
        ],
    )
    mocked_get_wordcloud = mocker.patch(
        "nonebot_plugin_wordcloud.get_wordcloud",
        return_value=FAKE_IMAGE[0],
    )

    async with app.test_matcher(wordcloud_cmd) as ctx:
        bot = ctx.create_bot()
        event = fake_group_message_event(message=Message("/历史词云 2022-01-01~2022-02-22"))

        ctx.receive_event(bot, event)
        ctx.should_call_send(event, MessageSegment.image(FAKE_IMAGE[1]), True)
        ctx.should_finished()

    mocked_datetime_fromisoformat.assert_has_calls(
        [
            mocker.call("2022-01-01"),
            mocker.call("2022-02-22"),
        ]
    )
    mocked_get_wordcloud.assert_called_once_with(["10-1", "11-1", "10-2", "11-2"])


@pytest.mark.asyncio
async def test_history_wordcloud_start_stop_get_args(
    app: App, mocker: MockerFixture, message_record: None
):
    """测试历史词云，获取起始时间参数的情况"""
    from nonebot.adapters.onebot.v11 import Message, MessageSegment

    from nonebot_plugin_wordcloud import wordcloud_cmd

    mocked_datetime_fromisoformat = mocker.patch(
        "nonebot_plugin_wordcloud.get_datetime_fromisoformat_with_timezone",
        side_effect=[
            datetime(2022, 1, 1, tzinfo=ZoneInfo("Asia/Shanghai")),
            datetime(2022, 2, 22, tzinfo=ZoneInfo("Asia/Shanghai")),
        ],
    )
    mocked_get_wordcloud = mocker.patch(
        "nonebot_plugin_wordcloud.get_wordcloud",
        return_value=FAKE_IMAGE[0],
    )

    async with app.test_matcher(wordcloud_cmd) as ctx:
        bot = ctx.create_bot()

        event = fake_group_message_event(message=Message("/历史词云"))
        ctx.receive_event(bot, event)
        ctx.should_call_send(event, "请输入你要查询的起始日期（如 2022-01-01）", True)
        ctx.should_rejected()

        start_event = fake_group_message_event(message=Message("2022-01-01"))
        ctx.receive_event(bot, start_event)
        ctx.should_call_send(start_event, "请输入你要查询的结束日期（如 2022-02-22）", True)
        ctx.should_rejected()

        stop_event = fake_group_message_event(message=Message("2022-02-22"))
        ctx.receive_event(bot, stop_event)
        ctx.should_call_send(stop_event, MessageSegment.image(FAKE_IMAGE[1]), True)
        ctx.should_finished()

    mocked_datetime_fromisoformat.assert_has_calls(
        [
            mocker.call("2022-01-01"),
            mocker.call("2022-02-22"),
        ]
    )
    mocked_get_wordcloud.assert_called_once_with(["10-1", "11-1", "10-2", "11-2"])


@pytest.mark.asyncio
async def test_history_wordcloud_invalid_date(app: App):
    """测试历史词云，输入的日期无效"""
    from nonebot.adapters.onebot.v11 import Message

    from nonebot_plugin_wordcloud import wordcloud_cmd

    async with app.test_matcher(wordcloud_cmd) as ctx:
        bot = ctx.create_bot()
        event = fake_group_message_event(message=Message("/历史词云 2022-13-01"))

        ctx.receive_event(bot, event)
        ctx.should_call_send(event, "请输入正确的日期（如 2022-02-22），不然我没法理解呢！", True)
        ctx.should_finished()

    async with app.test_matcher(wordcloud_cmd) as ctx:
        bot = ctx.create_bot()
        event = fake_group_message_event(message=Message("/历史词云 2022-12-01~2022-13-01"))

        ctx.receive_event(bot, event)
        ctx.should_call_send(event, "请输入正确的日期（如 2022-02-22），不然我没法理解呢！", True)
        ctx.should_finished()
