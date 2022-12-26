from datetime import datetime
from pathlib import Path

try:
    from zoneinfo import ZoneInfo
except ImportError:
    from backports.zoneinfo import ZoneInfo  # type: ignore

from io import BytesIO

import pytest
from nonebug import App
from PIL import Image
from pytest_mock import MockerFixture

from .utils import fake_group_message_event

FAKE_IMAGE = (
    BytesIO(
        b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01\x08\x02\x00\x00\x00\x90wS\xde\x00\x00\x00\x0cIDATx\x9cc\xf8\xff\xff?\x00\x05\xfe\x02\xfe\r\xefF\xb8\x00\x00\x00\x00IEND\xaeB`\x82"
    ),
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
        # 星期日
        session.add(make_message_record("10:1-2", "10", datetime(2022, 1, 2, 4, 0, 0)))
        session.add(make_message_record("11:1-2", "11", datetime(2022, 1, 2, 4, 0, 0)))
        # 星期一
        session.add(make_message_record("10:1-3", "10", datetime(2022, 1, 3, 4, 0, 0)))
        session.add(make_message_record("11:1-3", "11", datetime(2022, 1, 3, 4, 0, 0)))
        # 星期二
        session.add(make_message_record("10:2-1", "10", datetime(2022, 2, 1, 4, 0, 0)))
        session.add(make_message_record("11:2-1", "11", datetime(2022, 2, 1, 4, 0, 0)))

        await session.commit()


async def test_get_wordcloud(app: App, mocker: MockerFixture):
    """测试生成词云"""
    import random

    from PIL import ImageChops

    from nonebot_plugin_wordcloud.data_source import get_wordcloud

    mocked_random = mocker.patch("wordcloud.wordcloud.Random")
    mocked_random.return_value = random.Random(0)

    image_byte = await get_wordcloud(["天气"])

    assert image_byte is not None

    # 比较生成的图片是否相同
    test_image_path = Path(__file__).parent / "test_wordcloud.png"
    test_image = Image.open(test_image_path)
    image = Image.open(image_byte)
    diff = ImageChops.difference(image, test_image)
    assert diff.getbbox() is None

    mocked_random.assert_called_once_with()


async def test_wordcloud_empty(app: App):
    """测试词云，消息为空的情况"""
    from nonebot.adapters.onebot.v11 import Message

    from nonebot_plugin_wordcloud import wordcloud_cmd

    async with app.test_matcher(wordcloud_cmd) as ctx:
        bot = ctx.create_bot()
        event = fake_group_message_event(message=Message("/今日词云"))

        ctx.receive_event(bot, event)
        ctx.should_call_send(event, "没有足够的数据生成词云", True, at_sender=False)
        ctx.should_finished()


async def test_wordcloud_help(app: App):
    """测试输出帮助信息"""
    from nonebot.adapters.onebot.v11 import Message

    from nonebot_plugin_wordcloud import __plugin_meta__, wordcloud_cmd

    async with app.test_matcher(wordcloud_cmd) as ctx:
        bot = ctx.create_bot()
        event = fake_group_message_event(message=Message("/词云"))

        ctx.receive_event(bot, event)
        ctx.should_call_send(
            event,
            __plugin_meta__.usage,
            True,
        )
        ctx.should_finished()

    async with app.test_matcher(wordcloud_cmd) as ctx:
        bot = ctx.create_bot()
        event = fake_group_message_event(message=Message("/词云 123"))

        ctx.receive_event(bot, event)
        ctx.should_finished()


async def test_wordcloud_exclude_bot_msg(
    app: App, mocker: MockerFixture, message_record: None
):
    """测试词云，排除机器人自己的消息"""
    from nonebot.adapters.onebot.v11 import Message, MessageSegment

    from nonebot_plugin_wordcloud import wordcloud_cmd

    mocked_datetime_now = mocker.patch(
        "nonebot_plugin_wordcloud.get_datetime_now_with_timezone",
        return_value=datetime(2022, 1, 2, 23, 0, 0, tzinfo=ZoneInfo("Asia/Shanghai")),
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
            at_sender=False,
        )
        ctx.should_finished()

    mocked_datetime_now.assert_called_once_with()
    mocked_get_wordcloud.assert_called_once_with(["11:1-2"])


async def test_today_wordcloud(app: App, mocker: MockerFixture, message_record: None):
    """测试今日词云"""
    from nonebot.adapters.onebot.v11 import Message, MessageSegment

    from nonebot_plugin_wordcloud import wordcloud_cmd

    mocked_datetime_now = mocker.patch(
        "nonebot_plugin_wordcloud.get_datetime_now_with_timezone",
        return_value=datetime(2022, 1, 2, 23, tzinfo=ZoneInfo("Asia/Shanghai")),
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
            at_sender=False,
        )
        ctx.should_finished()

    mocked_datetime_now.assert_called_once_with()
    mocked_get_wordcloud.assert_called_once_with(["10:1-2", "11:1-2"])


async def test_my_today_wordcloud(
    app: App, mocker: MockerFixture, message_record: None
):
    """测试我的今日词云"""
    from nonebot.adapters.onebot.v11 import Message, MessageSegment

    from nonebot_plugin_wordcloud import wordcloud_cmd

    mocked_datetime_now = mocker.patch(
        "nonebot_plugin_wordcloud.get_datetime_now_with_timezone",
        return_value=datetime(2022, 1, 2, 23, tzinfo=ZoneInfo("Asia/Shanghai")),
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
            at_sender=True,
        )
        ctx.should_finished()

    mocked_datetime_now.assert_called_once_with()
    mocked_get_wordcloud.assert_called_once_with(["10:1-2"])


async def test_yesterday_wordcloud(
    app: App, mocker: MockerFixture, message_record: None
):
    """测试昨日词云"""
    from nonebot.adapters.onebot.v11 import Message, MessageSegment

    from nonebot_plugin_wordcloud import wordcloud_cmd

    mocked_datetime_now = mocker.patch(
        "nonebot_plugin_wordcloud.get_datetime_now_with_timezone",
        return_value=datetime(2022, 1, 3, 2, tzinfo=ZoneInfo("Asia/Shanghai")),
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
            at_sender=False,
        )
        ctx.should_finished()

    mocked_datetime_now.assert_called_once_with()
    mocked_get_wordcloud.assert_called_once_with(["10:1-2", "11:1-2"])


async def test_my_yesterday_wordcloud(
    app: App, mocker: MockerFixture, message_record: None
):
    """测试我的昨日词云"""
    from nonebot.adapters.onebot.v11 import Message, MessageSegment

    from nonebot_plugin_wordcloud import wordcloud_cmd

    mocked_datetime_now = mocker.patch(
        "nonebot_plugin_wordcloud.get_datetime_now_with_timezone",
        return_value=datetime(2022, 1, 3, 2, tzinfo=ZoneInfo("Asia/Shanghai")),
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
            at_sender=True,
        )
        ctx.should_finished()

    mocked_datetime_now.assert_called_once_with()
    mocked_get_wordcloud.assert_called_once_with(["10:1-2"])


async def test_week_wordcloud(app: App, mocker: MockerFixture, message_record: None):
    """测试本周词云"""
    from nonebot.adapters.onebot.v11 import Message, MessageSegment

    from nonebot_plugin_wordcloud import wordcloud_cmd

    mocked_datetime_now = mocker.patch(
        "nonebot_plugin_wordcloud.get_datetime_now_with_timezone",
        return_value=datetime(2022, 1, 5, 2, tzinfo=ZoneInfo("Asia/Shanghai")),
    )

    mocked_get_wordcloud = mocker.patch(
        "nonebot_plugin_wordcloud.get_wordcloud",
        return_value=FAKE_IMAGE[0],
    )

    async with app.test_matcher(wordcloud_cmd) as ctx:
        bot = ctx.create_bot()
        event = fake_group_message_event(message=Message("/本周词云"))

        ctx.receive_event(bot, event)
        ctx.should_call_send(
            event,
            MessageSegment.image(FAKE_IMAGE[1]),
            True,
            at_sender=False,
        )
        ctx.should_finished()

    mocked_datetime_now.assert_called_once_with()
    mocked_get_wordcloud.assert_called_once_with(["10:1-3", "11:1-3"])


async def test_month_wordcloud(app: App, mocker: MockerFixture, message_record: None):
    """测试本月词云"""
    from nonebot.adapters.onebot.v11 import Message, MessageSegment

    from nonebot_plugin_wordcloud import wordcloud_cmd

    mocked_datetime_now = mocker.patch(
        "nonebot_plugin_wordcloud.get_datetime_now_with_timezone",
        return_value=datetime(2022, 2, 7, 2, tzinfo=ZoneInfo("Asia/Shanghai")),
    )

    mocked_get_wordcloud = mocker.patch(
        "nonebot_plugin_wordcloud.get_wordcloud",
        return_value=FAKE_IMAGE[0],
    )

    async with app.test_matcher(wordcloud_cmd) as ctx:
        bot = ctx.create_bot()
        event = fake_group_message_event(message=Message("/本月词云"))

        ctx.receive_event(bot, event)
        ctx.should_call_send(
            event,
            MessageSegment.image(FAKE_IMAGE[1]),
            True,
            at_sender=False,
        )
        ctx.should_finished()

    mocked_datetime_now.assert_called_once_with()
    mocked_get_wordcloud.assert_called_once_with(["10:2-1", "11:2-1"])


async def test_year_wordcloud(app: App, mocker: MockerFixture, message_record: None):
    """测试年度词云"""
    from nonebot.adapters.onebot.v11 import Message, MessageSegment

    from nonebot_plugin_wordcloud import wordcloud_cmd

    mocked_datetime_now = mocker.patch(
        "nonebot_plugin_wordcloud.get_datetime_now_with_timezone",
        return_value=datetime(2022, 12, 1, 2, tzinfo=ZoneInfo("Asia/Shanghai")),
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
            at_sender=False,
        )
        ctx.should_finished()

    mocked_datetime_now.assert_called_once_with()
    mocked_get_wordcloud.assert_called_once_with(
        ["10:1-2", "11:1-2", "10:1-3", "11:1-3", "10:2-1", "11:2-1"]
    )


async def test_my_year_wordcloud(app: App, mocker: MockerFixture, message_record: None):
    """测试我的年度词云"""
    from nonebot.adapters.onebot.v11 import Message, MessageSegment

    from nonebot_plugin_wordcloud import wordcloud_cmd

    mocked_datetime_now = mocker.patch(
        "nonebot_plugin_wordcloud.get_datetime_now_with_timezone",
        return_value=datetime(2022, 12, 1, 2, tzinfo=ZoneInfo("Asia/Shanghai")),
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
            at_sender=True,
        )
        ctx.should_finished()

    mocked_datetime_now.assert_called_once_with()
    mocked_get_wordcloud.assert_called_once_with(["10:1-2", "10:1-3", "10:2-1"])


async def test_history_wordcloud(app: App, mocker: MockerFixture, message_record: None):
    """测试历史词云"""
    from nonebot.adapters.onebot.v11 import Message, MessageSegment

    from nonebot_plugin_wordcloud import wordcloud_cmd

    mocked_get_wordcloud = mocker.patch(
        "nonebot_plugin_wordcloud.get_wordcloud",
        return_value=FAKE_IMAGE[0],
    )

    async with app.test_matcher(wordcloud_cmd) as ctx:
        bot = ctx.create_bot()
        event = fake_group_message_event(message=Message("/历史词云 2022-01-02"))

        ctx.receive_event(bot, event)
        ctx.should_call_send(
            event,
            MessageSegment.image(FAKE_IMAGE[1]),
            True,
            at_sender=False,
        )
        ctx.should_finished()

    mocked_get_wordcloud.assert_called_once_with(["10:1-2", "11:1-2"])


async def test_history_wordcloud_start_stop(
    app: App, mocker: MockerFixture, message_record: None
):
    """测试历史词云，有起始时间的情况"""
    from nonebot.adapters.onebot.v11 import Message, MessageSegment

    from nonebot_plugin_wordcloud import wordcloud_cmd

    mocked_get_wordcloud = mocker.patch(
        "nonebot_plugin_wordcloud.get_wordcloud",
        return_value=FAKE_IMAGE[0],
    )

    async with app.test_matcher(wordcloud_cmd) as ctx:
        bot = ctx.create_bot()
        event = fake_group_message_event(
            message=Message("/历史词云 2022-01-02T12:00:01~2022-02-22")
        )

        ctx.receive_event(bot, event)
        ctx.should_call_send(
            event,
            MessageSegment.image(FAKE_IMAGE[1]),
            True,
            at_sender=False,
        )
        ctx.should_finished()

    mocked_get_wordcloud.assert_called_once_with(
        ["10:1-3", "11:1-3", "10:2-1", "11:2-1"]
    )


async def test_history_wordcloud_start_stop_get_args(
    app: App, mocker: MockerFixture, message_record: None
):
    """测试历史词云，获取起始时间参数的情况"""
    from nonebot.adapters.onebot.v11 import Message, MessageSegment

    from nonebot_plugin_wordcloud import wordcloud_cmd

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

        invalid_stop_event = fake_group_message_event(message=Message("2022-02-30"))
        ctx.receive_event(bot, invalid_stop_event)
        ctx.should_call_send(invalid_stop_event, "请输入正确的日期，不然我没法理解呢！", True)
        ctx.should_rejected()

        stop_event = fake_group_message_event(message=Message("2022-02-22"))
        ctx.receive_event(bot, stop_event)
        ctx.should_call_send(
            stop_event,
            MessageSegment.image(FAKE_IMAGE[1]),
            True,
            at_sender=False,
        )
        ctx.should_finished()

    mocked_get_wordcloud.assert_called_once_with(
        ["10:1-2", "11:1-2", "10:1-3", "11:1-3", "10:2-1", "11:2-1"]
    )


async def test_history_wordcloud_invalid_date(app: App):
    """测试历史词云，输入的日期无效"""
    from nonebot.adapters.onebot.v11 import Message

    from nonebot_plugin_wordcloud import wordcloud_cmd

    async with app.test_matcher(wordcloud_cmd) as ctx:
        bot = ctx.create_bot()
        event = fake_group_message_event(message=Message("/历史词云 2022-13-01"))

        ctx.receive_event(bot, event)
        ctx.should_call_send(event, "请输入正确的日期，不然我没法理解呢！", True)
        ctx.should_finished()

    async with app.test_matcher(wordcloud_cmd) as ctx:
        bot = ctx.create_bot()
        event = fake_group_message_event(
            message=Message("/历史词云 2022-12-01T13:~2022-12-02")
        )

        ctx.receive_event(bot, event)
        ctx.should_call_send(event, "请输入正确的日期，不然我没法理解呢！", True)
        ctx.should_finished()

    async with app.test_matcher(wordcloud_cmd) as ctx:
        bot = ctx.create_bot()
        event = fake_group_message_event(message=Message("/历史词云 2022-12-01~2022-13-01"))

        ctx.receive_event(bot, event)
        ctx.should_call_send(event, "请输入正确的日期，不然我没法理解呢！", True)
        ctx.should_finished()
