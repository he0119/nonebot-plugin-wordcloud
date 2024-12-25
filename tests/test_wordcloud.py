import random
from datetime import datetime
from io import BytesIO
from pathlib import Path
from zoneinfo import ZoneInfo

import pytest
from nonebot import get_adapter, get_driver
from nonebot.adapters.onebot.v11 import Adapter, Bot, Message
from nonebot.adapters.onebot.v12 import Adapter as AdapterV12
from nonebot.adapters.onebot.v12 import Bot as BotV12
from nonebot.adapters.onebot.v12 import Message as MessageV12
from nonebug import App
from nonebug_saa import should_send_saa
from PIL import Image, ImageChops
from pytest_mock import MockerFixture

from .utils import (
    fake_channel_message_event_v12,
    fake_group_message_event_v11,
    fake_group_message_event_v12,
    fake_private_message_event_v11,
)

FAKE_IMAGE = BytesIO(
    b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01\x08\x02\x00\x00\x00\x90wS\xde\x00\x00\x00\x0cIDATx\x9cc\xf8\xff\xff?\x00\x05\xfe\x02\xfe\r\xefF\xb8\x00\x00\x00\x00IEND\xaeB`\x82"
)


@pytest.fixture
async def _message_record(app: App):
    from nonebot_plugin_chatrecorder import serialize_message
    from nonebot_plugin_chatrecorder.model import MessageRecord
    from nonebot_plugin_orm import get_session
    from nonebot_plugin_uninfo import (
        Scene,
        SceneType,
        Session,
        SupportAdapter,
        SupportScope,
        User,
    )
    from nonebot_plugin_uninfo.orm import get_session_persist_id

    async with app.test_api() as ctx:
        adapter = Adapter(get_driver())
        adapter_v12 = AdapterV12(get_driver())
        bot = ctx.create_bot(base=Bot, adapter=adapter, auto_connect=False)
        bot_v12 = ctx.create_bot(
            base=BotV12,
            adapter=adapter_v12,
            auto_connect=False,
            platform="test",
            impl="test",
        )

    sessions = [
        Session(
            self_id="test",
            adapter=SupportAdapter.onebot11,
            scope=SupportScope.qq_client,
            scene=Scene("10000", SceneType.GROUP),
            user=User("bot"),
        ),
        Session(
            self_id="test",
            adapter=SupportAdapter.onebot11,
            scope=SupportScope.qq_client,
            scene=Scene("10000", SceneType.GROUP),
            user=User("10"),
        ),
        Session(
            self_id="test",
            adapter=SupportAdapter.onebot11,
            scope=SupportScope.qq_client,
            scene=Scene("10000", SceneType.GROUP),
            user=User("11"),
        ),
        Session(
            self_id="test",
            adapter=SupportAdapter.onebot12,
            scope=SupportScope.qq_guild,
            scene=Scene(
                "100000", SceneType.CHANNEL_TEXT, parent=Scene("10000", SceneType.GUILD)
            ),
            user=User("10"),
        ),
        Session(
            self_id="test",
            adapter=SupportAdapter.onebot12,
            scope=SupportScope.qq_guild,
            scene=Scene(
                "100000", SceneType.CHANNEL_TEXT, parent=Scene("10000", SceneType.GUILD)
            ),
            user=User("11"),
        ),
    ]
    session_ids: list[int] = []
    async with get_session() as db_session:
        for session in sessions:
            session_model_id = await get_session_persist_id(session)
            session_ids.append(session_model_id)

    records = [
        # 星期日
        MessageRecord(
            session_persist_id=session_ids[0],
            time=datetime(2022, 1, 2, 4, 0, 0),
            type="message_sent",
            message_id="1",
            message=serialize_message(bot, Message("bot:1-2")),
            plain_text="bot:1-2",
        ),
        MessageRecord(
            session_persist_id=session_ids[1],
            time=datetime(2022, 1, 2, 4, 0, 0),
            type="message",
            message_id="2",
            message=serialize_message(bot, Message("10:1-2")),
            plain_text="10:1-2",
        ),
        MessageRecord(
            session_persist_id=session_ids[2],
            time=datetime(2022, 1, 2, 4, 0, 0),
            type="message",
            message_id="3",
            message=serialize_message(bot, Message("11:1-2")),
            plain_text="11:1-2",
        ),
        MessageRecord(
            session_persist_id=session_ids[3],
            time=datetime(2022, 1, 2, 4, 0, 0),
            type="message",
            message_id="4",
            message=serialize_message(bot_v12, MessageV12("v12-10:1-2")),
            plain_text="v12-10:1-2",
        ),
        MessageRecord(
            session_persist_id=session_ids[4],
            time=datetime(2022, 1, 2, 4, 0, 0),
            type="message",
            message_id="4",
            message=serialize_message(bot_v12, MessageV12("v12-11:1-2")),
            plain_text="v12-11:1-2",
        ),
        # 星期一
        MessageRecord(
            session_persist_id=session_ids[1],
            time=datetime(2022, 1, 3, 4, 0, 0),
            type="message",
            message_id="2",
            message=serialize_message(bot, Message("10:1-3")),
            plain_text="10:1-3",
        ),
        MessageRecord(
            session_persist_id=session_ids[2],
            time=datetime(2022, 1, 3, 4, 0, 0),
            type="message",
            message_id="3",
            message=serialize_message(bot, Message("11:1-3")),
            plain_text="11:1-3",
        ),
        # 星期二
        MessageRecord(
            session_persist_id=session_ids[1],
            time=datetime(2022, 2, 1, 4, 0, 0),
            type="message",
            message_id="2",
            message=serialize_message(bot, Message("10:2-1")),
            plain_text="10:2-1",
        ),
        MessageRecord(
            session_persist_id=session_ids[2],
            time=datetime(2022, 2, 1, 4, 0, 0),
            type="message",
            message_id="3",
            message=serialize_message(bot, Message("11:2-1")),
            plain_text="11:2-1",
        ),
    ]
    async with get_session() as db_session:
        db_session.add_all(records)
        await db_session.commit()


async def test_get_wordcloud(app: App, mocker: MockerFixture):
    """测试生成词云"""
    from nonebot_plugin_wordcloud.data_source import get_wordcloud

    mocked_random = mocker.patch("wordcloud.wordcloud.Random")
    mocked_random.return_value = random.Random(0)

    image_byte = await get_wordcloud(["天气"], "")

    assert image_byte is not None

    # 比较生成的图片是否相同
    test_image_path = Path(__file__).parent / "test_wordcloud.png"
    test_image = Image.open(test_image_path)
    image = Image.open(BytesIO(image_byte))
    diff = ImageChops.difference(image, test_image)
    assert diff.getbbox() is None

    mocked_random.assert_called_once_with()


async def test_get_wordcloud_private(app: App):
    """测试私聊词云"""
    from nonebot_plugin_wordcloud import wordcloud_cmd

    async with app.test_matcher(wordcloud_cmd) as ctx:
        adapter = get_adapter(Adapter)
        bot = ctx.create_bot(base=Bot, adapter=adapter, auto_connect=False)
        event = fake_private_message_event_v11(message=Message("/词云"))

        ctx.receive_event(bot, event)
        ctx.should_call_send(
            event,
            "请在群组中使用！",
            True,
        )
        ctx.should_finished()


async def test_wordcloud_cmd(app: App):
    """测试输出帮助信息与没有数据的情况"""
    from nonebot_plugin_wordcloud import __plugin_meta__, wordcloud_cmd

    async with app.test_matcher(wordcloud_cmd) as ctx:
        adapter = get_adapter(Adapter)
        bot = ctx.create_bot(base=Bot, adapter=adapter, auto_connect=False)
        event = fake_group_message_event_v11(message=Message("/词云"))

        ctx.receive_event(bot, event)
        ctx.should_call_send(
            event,
            __plugin_meta__.usage,
            True,
        )
        ctx.should_finished()

    async with app.test_matcher(wordcloud_cmd) as ctx:
        adapter = get_adapter(Adapter)
        bot = ctx.create_bot(base=Bot, adapter=adapter, auto_connect=False)
        event = fake_group_message_event_v11(message=Message("/词云 123"))

        ctx.receive_event(bot, event)
        ctx.should_finished()

    async with app.test_matcher(wordcloud_cmd) as ctx:
        adapter = get_adapter(Adapter)
        bot = ctx.create_bot(base=Bot, adapter=adapter, auto_connect=False)
        event = fake_group_message_event_v11(message=Message("/今日词云"))

        ctx.receive_event(bot, event)
        ctx.should_call_send(event, "没有足够的数据生成词云", True, at_sender=False)
        ctx.should_finished()


@pytest.mark.usefixtures("_message_record")
async def test_today_wordcloud(app: App, mocker: MockerFixture):
    """测试今日词云"""
    from nonebot_plugin_chatrecorder import get_messages_plain_text
    from nonebot_plugin_saa import Image, MessageFactory

    from nonebot_plugin_wordcloud import wordcloud_cmd

    # 排除机器人自己的消息
    messages = await get_messages_plain_text()
    assert len(messages) == 9

    mocked_datetime_now = mocker.patch(
        "nonebot_plugin_wordcloud.get_datetime_now_with_timezone",
        return_value=datetime(2022, 1, 2, 23, tzinfo=ZoneInfo("Asia/Shanghai")),
    )

    mocked_get_wordcloud = mocker.patch(
        "nonebot_plugin_wordcloud.get_wordcloud",
        return_value=FAKE_IMAGE,
    )

    async with app.test_matcher(wordcloud_cmd) as ctx:
        adapter = get_adapter(Adapter)
        bot = ctx.create_bot(base=Bot, adapter=adapter, auto_connect=False)
        event = fake_group_message_event_v11(message=Message("/今日词云"))

        ctx.receive_event(bot, event)
        should_send_saa(
            ctx, MessageFactory(Image(FAKE_IMAGE, "wordcloud.png")), bot, event=event
        )
        ctx.should_finished()

    mocked_datetime_now.assert_called_once_with()
    mocked_get_wordcloud.assert_called_once_with(
        ["10:1-2", "11:1-2"], "qq_group-group_id=10000"
    )


@pytest.mark.usefixtures("_message_record")
async def test_my_today_wordcloud(app: App, mocker: MockerFixture):
    """测试我的今日词云"""
    from nonebot_plugin_saa import Image, MessageFactory

    from nonebot_plugin_wordcloud import wordcloud_cmd

    mocked_datetime_now = mocker.patch(
        "nonebot_plugin_wordcloud.get_datetime_now_with_timezone",
        return_value=datetime(2022, 1, 2, 23, tzinfo=ZoneInfo("Asia/Shanghai")),
    )

    mocked_get_wordcloud = mocker.patch(
        "nonebot_plugin_wordcloud.get_wordcloud",
        return_value=FAKE_IMAGE,
    )

    async with app.test_matcher(wordcloud_cmd) as ctx:
        adapter = get_adapter(Adapter)
        bot = ctx.create_bot(base=Bot, adapter=adapter, auto_connect=False)
        event = fake_group_message_event_v11(message=Message("/我的今日词云"))

        ctx.receive_event(bot, event)
        should_send_saa(
            ctx,
            MessageFactory(Image(FAKE_IMAGE, "wordcloud.png")),
            bot,
            event=event,
            at_sender=True,
        )
        ctx.should_finished()

    mocked_datetime_now.assert_called_once_with()
    mocked_get_wordcloud.assert_called_once_with(["10:1-2"], "qq_group-group_id=10000")


@pytest.mark.usefixtures("_message_record")
async def test_yesterday_wordcloud(app: App, mocker: MockerFixture):
    """测试昨日词云"""
    from nonebot_plugin_saa import Image, MessageFactory

    from nonebot_plugin_wordcloud import wordcloud_cmd

    mocked_datetime_now = mocker.patch(
        "nonebot_plugin_wordcloud.get_datetime_now_with_timezone",
        return_value=datetime(2022, 1, 3, 2, tzinfo=ZoneInfo("Asia/Shanghai")),
    )

    mocked_get_wordcloud = mocker.patch(
        "nonebot_plugin_wordcloud.get_wordcloud",
        return_value=FAKE_IMAGE,
    )

    async with app.test_matcher(wordcloud_cmd) as ctx:
        adapter = get_adapter(Adapter)
        bot = ctx.create_bot(base=Bot, adapter=adapter, auto_connect=False)
        event = fake_group_message_event_v11(message=Message("/昨日词云"))

        ctx.receive_event(bot, event)
        should_send_saa(
            ctx,
            MessageFactory(Image(FAKE_IMAGE, "wordcloud.png")),
            bot,
            event=event,
        )
        ctx.should_finished()

    mocked_datetime_now.assert_called_once_with()
    mocked_get_wordcloud.assert_called_once_with(
        ["10:1-2", "11:1-2"], "qq_group-group_id=10000"
    )


@pytest.mark.usefixtures("_message_record")
async def test_my_yesterday_wordcloud(app: App, mocker: MockerFixture):
    """测试我的昨日词云"""
    from nonebot_plugin_saa import Image, MessageFactory

    from nonebot_plugin_wordcloud import wordcloud_cmd

    mocked_datetime_now = mocker.patch(
        "nonebot_plugin_wordcloud.get_datetime_now_with_timezone",
        return_value=datetime(2022, 1, 3, 2, tzinfo=ZoneInfo("Asia/Shanghai")),
    )

    mocked_get_wordcloud = mocker.patch(
        "nonebot_plugin_wordcloud.get_wordcloud",
        return_value=FAKE_IMAGE,
    )

    async with app.test_matcher(wordcloud_cmd) as ctx:
        adapter = get_adapter(Adapter)
        bot = ctx.create_bot(base=Bot, adapter=adapter, auto_connect=False)
        event = fake_group_message_event_v11(message=Message("/我的昨日词云"))

        ctx.receive_event(bot, event)
        should_send_saa(
            ctx,
            MessageFactory(Image(FAKE_IMAGE, "wordcloud.png")),
            bot,
            event=event,
            at_sender=True,
        )
        ctx.should_finished()

    mocked_datetime_now.assert_called_once_with()
    mocked_get_wordcloud.assert_called_once_with(["10:1-2"], "qq_group-group_id=10000")


@pytest.mark.usefixtures("_message_record")
async def test_week_wordcloud(app: App, mocker: MockerFixture):
    """测试本周词云"""
    from nonebot_plugin_saa import Image, MessageFactory

    from nonebot_plugin_wordcloud import wordcloud_cmd

    mocked_datetime_now = mocker.patch(
        "nonebot_plugin_wordcloud.get_datetime_now_with_timezone",
        return_value=datetime(2022, 1, 5, 2, tzinfo=ZoneInfo("Asia/Shanghai")),
    )

    mocked_get_wordcloud = mocker.patch(
        "nonebot_plugin_wordcloud.get_wordcloud",
        return_value=FAKE_IMAGE,
    )

    async with app.test_matcher(wordcloud_cmd) as ctx:
        adapter = get_adapter(Adapter)
        bot = ctx.create_bot(base=Bot, adapter=adapter, auto_connect=False)
        event = fake_group_message_event_v11(message=Message("/本周词云"))

        ctx.receive_event(bot, event)
        should_send_saa(
            ctx,
            MessageFactory(Image(FAKE_IMAGE, "wordcloud.png")),
            bot,
            event=event,
        )
        ctx.should_finished()

    mocked_datetime_now.assert_called_once_with()
    mocked_get_wordcloud.assert_called_once_with(
        ["10:1-3", "11:1-3"], "qq_group-group_id=10000"
    )


@pytest.mark.usefixtures("_message_record")
async def test_last_week_wordcloud(app: App, mocker: MockerFixture):
    """测试上周词云"""
    from nonebot_plugin_saa import Image, MessageFactory

    from nonebot_plugin_wordcloud import wordcloud_cmd

    mocked_datetime_now = mocker.patch(
        "nonebot_plugin_wordcloud.get_datetime_now_with_timezone",
        return_value=datetime(2022, 1, 5, 2, tzinfo=ZoneInfo("Asia/Shanghai")),
    )

    mocked_get_wordcloud = mocker.patch(
        "nonebot_plugin_wordcloud.get_wordcloud",
        return_value=FAKE_IMAGE,
    )

    async with app.test_matcher(wordcloud_cmd) as ctx:
        adapter = get_adapter(Adapter)
        bot = ctx.create_bot(base=Bot, adapter=adapter, auto_connect=False)
        event = fake_group_message_event_v11(message=Message("/上周词云"))

        ctx.receive_event(bot, event)
        should_send_saa(
            ctx,
            MessageFactory(Image(FAKE_IMAGE, "wordcloud.png")),
            bot,
            event=event,
        )
        ctx.should_finished()

    mocked_datetime_now.assert_called_once_with()
    mocked_get_wordcloud.assert_called_once_with(
        ["10:1-2", "11:1-2"], "qq_group-group_id=10000"
    )


@pytest.mark.usefixtures("_message_record")
async def test_month_wordcloud(app: App, mocker: MockerFixture):
    """测试本月词云"""
    from nonebot_plugin_saa import Image, MessageFactory

    from nonebot_plugin_wordcloud import wordcloud_cmd

    mocked_datetime_now = mocker.patch(
        "nonebot_plugin_wordcloud.get_datetime_now_with_timezone",
        return_value=datetime(2022, 2, 7, 2, tzinfo=ZoneInfo("Asia/Shanghai")),
    )

    mocked_get_wordcloud = mocker.patch(
        "nonebot_plugin_wordcloud.get_wordcloud",
        return_value=FAKE_IMAGE,
    )

    async with app.test_matcher(wordcloud_cmd) as ctx:
        adapter = get_adapter(Adapter)
        bot = ctx.create_bot(base=Bot, adapter=adapter, auto_connect=False)
        event = fake_group_message_event_v11(message=Message("/本月词云"))

        ctx.receive_event(bot, event)
        should_send_saa(
            ctx,
            MessageFactory(Image(FAKE_IMAGE, "wordcloud.png")),
            bot,
            event=event,
        )
        ctx.should_finished()

    mocked_datetime_now.assert_called_once_with()
    mocked_get_wordcloud.assert_called_once_with(
        ["10:2-1", "11:2-1"], "qq_group-group_id=10000"
    )


@pytest.mark.usefixtures("_message_record")
async def test_last_month_wordcloud(app: App, mocker: MockerFixture):
    """测试上月词云"""
    from nonebot_plugin_orm import get_session

    engine = get_session().get_bind()
    if engine.dialect.name == "mysql":
        pytest.skip("MySQL 上获取消息的顺序不同")

    from nonebot_plugin_saa import Image, MessageFactory

    from nonebot_plugin_wordcloud import wordcloud_cmd

    mocked_datetime_now = mocker.patch(
        "nonebot_plugin_wordcloud.get_datetime_now_with_timezone",
        return_value=datetime(2022, 2, 7, 2, tzinfo=ZoneInfo("Asia/Shanghai")),
    )

    mocked_get_wordcloud = mocker.patch(
        "nonebot_plugin_wordcloud.get_wordcloud",
        return_value=FAKE_IMAGE,
    )

    async with app.test_matcher(wordcloud_cmd) as ctx:
        adapter = get_adapter(Adapter)
        bot = ctx.create_bot(base=Bot, adapter=adapter, auto_connect=False)
        event = fake_group_message_event_v11(message=Message("/上月词云"))

        ctx.receive_event(bot, event)
        should_send_saa(
            ctx,
            MessageFactory(Image(FAKE_IMAGE, "wordcloud.png")),
            bot,
            event=event,
        )
        ctx.should_finished()

    mocked_datetime_now.assert_called_once_with()
    mocked_get_wordcloud.assert_called_once_with(
        ["10:1-2", "11:1-2", "10:1-3", "11:1-3"], "qq_group-group_id=10000"
    )


@pytest.mark.usefixtures("_message_record")
async def test_year_wordcloud(app: App, mocker: MockerFixture):
    """测试年度词云"""
    from nonebot_plugin_orm import get_session

    engine = get_session().get_bind()
    if engine.dialect.name == "mysql":
        pytest.skip("MySQL 上获取消息的顺序不同")

    from nonebot_plugin_saa import Image, MessageFactory

    from nonebot_plugin_wordcloud import wordcloud_cmd

    mocked_datetime_now = mocker.patch(
        "nonebot_plugin_wordcloud.get_datetime_now_with_timezone",
        return_value=datetime(2022, 12, 1, 2, tzinfo=ZoneInfo("Asia/Shanghai")),
    )

    mocked_get_wordcloud = mocker.patch(
        "nonebot_plugin_wordcloud.get_wordcloud",
        return_value=FAKE_IMAGE,
    )

    async with app.test_matcher(wordcloud_cmd) as ctx:
        adapter = get_adapter(Adapter)
        bot = ctx.create_bot(base=Bot, adapter=adapter, auto_connect=False)
        event = fake_group_message_event_v11(message=Message("/年度词云"))

        ctx.receive_event(bot, event)
        should_send_saa(
            ctx,
            MessageFactory(Image(FAKE_IMAGE, "wordcloud.png")),
            bot,
            event=event,
        )
        ctx.should_finished()

    mocked_datetime_now.assert_called_once_with()
    mocked_get_wordcloud.assert_called_once_with(
        ["10:1-2", "11:1-2", "10:1-3", "11:1-3", "10:2-1", "11:2-1"],
        "qq_group-group_id=10000",
    )


@pytest.mark.usefixtures("_message_record")
async def test_my_year_wordcloud(app: App, mocker: MockerFixture):
    """测试我的年度词云"""
    from nonebot_plugin_saa import Image, MessageFactory

    from nonebot_plugin_wordcloud import wordcloud_cmd

    mocked_datetime_now = mocker.patch(
        "nonebot_plugin_wordcloud.get_datetime_now_with_timezone",
        return_value=datetime(2022, 12, 1, 2, tzinfo=ZoneInfo("Asia/Shanghai")),
    )

    mocked_get_wordcloud = mocker.patch(
        "nonebot_plugin_wordcloud.get_wordcloud",
        return_value=FAKE_IMAGE,
    )

    async with app.test_matcher(wordcloud_cmd) as ctx:
        adapter = get_adapter(Adapter)
        bot = ctx.create_bot(base=Bot, adapter=adapter, auto_connect=False)
        event = fake_group_message_event_v11(message=Message("/我的年度词云"))

        ctx.receive_event(bot, event)
        should_send_saa(
            ctx,
            MessageFactory(Image(FAKE_IMAGE, "wordcloud.png")),
            bot,
            event=event,
            at_sender=True,
        )
        ctx.should_finished()

    mocked_datetime_now.assert_called_once_with()
    mocked_get_wordcloud.assert_called_once_with(
        ["10:1-2", "10:1-3", "10:2-1"], "qq_group-group_id=10000"
    )


@pytest.mark.usefixtures("_message_record")
async def test_history_wordcloud(app: App, mocker: MockerFixture):
    """测试历史词云"""
    from nonebot_plugin_saa import Image, MessageFactory

    from nonebot_plugin_wordcloud import wordcloud_cmd

    mocked_get_wordcloud = mocker.patch(
        "nonebot_plugin_wordcloud.get_wordcloud",
        return_value=FAKE_IMAGE,
    )

    async with app.test_matcher(wordcloud_cmd) as ctx:
        adapter = get_adapter(Adapter)
        bot = ctx.create_bot(base=Bot, adapter=adapter, auto_connect=False)
        event = fake_group_message_event_v11(message=Message("/历史词云 2022-01-02"))

        ctx.receive_event(bot, event)
        should_send_saa(
            ctx,
            MessageFactory(Image(FAKE_IMAGE, "wordcloud.png")),
            bot,
            event=event,
        )
        ctx.should_finished()

    mocked_get_wordcloud.assert_called_once_with(
        ["10:1-2", "11:1-2"], "qq_group-group_id=10000"
    )


@pytest.mark.usefixtures("_message_record")
async def test_history_wordcloud_start_stop(app: App, mocker: MockerFixture):
    """测试历史词云，有起始时间的情况"""
    from nonebot_plugin_orm import get_session

    engine = get_session().get_bind()
    if engine.dialect.name == "mysql":
        pytest.skip("MySQL 上获取消息的顺序不同")

    from nonebot_plugin_saa import Image, MessageFactory

    from nonebot_plugin_wordcloud import wordcloud_cmd

    mocked_get_wordcloud = mocker.patch(
        "nonebot_plugin_wordcloud.get_wordcloud",
        return_value=FAKE_IMAGE,
    )

    async with app.test_matcher(wordcloud_cmd) as ctx:
        adapter = get_adapter(Adapter)
        bot = ctx.create_bot(base=Bot, adapter=adapter, auto_connect=False)
        event = fake_group_message_event_v11(
            message=Message("/历史词云 2022-01-02T12:00:01~2022-02-22")
        )

        ctx.receive_event(bot, event)
        should_send_saa(
            ctx,
            MessageFactory(Image(FAKE_IMAGE, "wordcloud.png")),
            bot,
            event=event,
        )
        ctx.should_finished()

    mocked_get_wordcloud.assert_called_once_with(
        ["10:1-3", "11:1-3", "10:2-1", "11:2-1"], "qq_group-group_id=10000"
    )


@pytest.mark.usefixtures("_message_record")
async def test_history_wordcloud_start_stop_get_args(app: App, mocker: MockerFixture):
    """测试历史词云，获取起始时间参数的情况"""
    from nonebot_plugin_orm import get_session

    engine = get_session().get_bind()
    if engine.dialect.name == "mysql":
        pytest.skip("MySQL 上获取消息的顺序不同")

    from nonebot_plugin_saa import Image, MessageFactory

    from nonebot_plugin_wordcloud import wordcloud_cmd

    mocked_get_wordcloud = mocker.patch(
        "nonebot_plugin_wordcloud.get_wordcloud",
        return_value=FAKE_IMAGE,
    )

    async with app.test_matcher(wordcloud_cmd) as ctx:
        adapter = get_adapter(Adapter)
        bot = ctx.create_bot(base=Bot, adapter=adapter, auto_connect=False)

        event = fake_group_message_event_v11(message=Message("/历史词云"))
        ctx.receive_event(bot, event)
        ctx.should_call_send(event, "请输入你要查询的起始日期（如 2022-01-01）", True)
        ctx.should_rejected()

        start_event = fake_group_message_event_v11(message=Message("2022-01-01"))
        ctx.receive_event(bot, start_event)
        ctx.should_call_send(
            start_event, "请输入你要查询的结束日期（如 2022-02-22）", True
        )
        ctx.should_rejected()

        invalid_stop_event = fake_group_message_event_v11(message=Message("2022-02-30"))
        ctx.receive_event(bot, invalid_stop_event)
        ctx.should_call_send(
            invalid_stop_event, "请输入正确的日期，不然我没法理解呢！", True
        )
        ctx.should_rejected()

        stop_event = fake_group_message_event_v11(message=Message("2022-02-22"))
        ctx.receive_event(bot, stop_event)
        should_send_saa(
            ctx,
            MessageFactory(Image(FAKE_IMAGE, "wordcloud.png")),
            bot,
            event=stop_event,
        )
        ctx.should_finished()

    mocked_get_wordcloud.assert_called_once_with(
        ["10:1-2", "11:1-2", "10:1-3", "11:1-3", "10:2-1", "11:2-1"],
        "qq_group-group_id=10000",
    )


async def test_history_wordcloud_invalid_input(app: App):
    """测试历史词云，输入的日期无效"""
    from nonebot_plugin_wordcloud import wordcloud_cmd

    async with app.test_matcher(wordcloud_cmd) as ctx:
        adapter = get_adapter(Adapter)
        bot = ctx.create_bot(base=Bot, adapter=adapter, auto_connect=False)
        event = fake_group_message_event_v11(message=Message("/历史词云 2022-13-01"))

        ctx.receive_event(bot, event)
        ctx.should_call_send(event, "请输入正确的日期，不然我没法理解呢！", True)
        ctx.should_finished()

    async with app.test_matcher(wordcloud_cmd) as ctx:
        adapter = get_adapter(Adapter)
        bot = ctx.create_bot(base=Bot, adapter=adapter, auto_connect=False)
        event = fake_group_message_event_v11(
            message=Message("/历史词云 2022-12-01T13:~2022-12-02")
        )

        ctx.receive_event(bot, event)
        ctx.should_call_send(event, "请输入正确的日期，不然我没法理解呢！", True)
        ctx.should_finished()

    async with app.test_matcher(wordcloud_cmd) as ctx:
        adapter = get_adapter(Adapter)
        bot = ctx.create_bot(base=Bot, adapter=adapter, auto_connect=False)
        event = fake_group_message_event_v11(
            message=Message("/历史词云 2022-12-01~2022-13-01")
        )

        ctx.receive_event(bot, event)
        ctx.should_call_send(event, "请输入正确的日期，不然我没法理解呢！", True)
        ctx.should_finished()


@pytest.mark.usefixtures("_message_record")
async def test_today_wordcloud_v12(app: App, mocker: MockerFixture):
    from nonebot_plugin_saa import Image, MessageFactory

    from nonebot_plugin_wordcloud import wordcloud_cmd

    mocked_datetime_now = mocker.patch(
        "nonebot_plugin_wordcloud.get_datetime_now_with_timezone",
        return_value=datetime(2022, 1, 2, 23, tzinfo=ZoneInfo("Asia/Shanghai")),
    )

    mocked_get_wordcloud = mocker.patch(
        "nonebot_plugin_wordcloud.get_wordcloud",
        return_value=FAKE_IMAGE,
    )
    async with app.test_matcher(wordcloud_cmd) as ctx:
        adapter = get_adapter(AdapterV12)
        bot = ctx.create_bot(
            base=BotV12,
            adapter=adapter,
            auto_connect=False,
            platform="test",
            impl="test",
        )
        event = fake_channel_message_event_v12(message=MessageV12("/今日词云"))

        ctx.receive_event(bot, event)
        should_send_saa(
            ctx,
            MessageFactory(Image(FAKE_IMAGE, "wordcloud.png")),
            bot,
            event=event,
        )
        ctx.should_finished()

    mocked_datetime_now.assert_called_once_with()
    mocked_get_wordcloud.assert_called_once_with(
        ["v12-10:1-2", "v12-11:1-2"],
        "unknown_ob12-platform=qq-detail_type=channel-guild_id=10000-channel_id=100000",
    )


@pytest.mark.usefixtures("_message_record")
async def test_my_today_wordcloud_v12(app: App, mocker: MockerFixture):
    from nonebot_plugin_saa import Image, MessageFactory

    from nonebot_plugin_wordcloud import wordcloud_cmd

    mocked_datetime_now = mocker.patch(
        "nonebot_plugin_wordcloud.get_datetime_now_with_timezone",
        return_value=datetime(2022, 1, 2, 23, tzinfo=ZoneInfo("Asia/Shanghai")),
    )

    mocked_get_wordcloud = mocker.patch(
        "nonebot_plugin_wordcloud.get_wordcloud",
        return_value=FAKE_IMAGE,
    )

    async with app.test_matcher(wordcloud_cmd) as ctx:
        adapter = get_adapter(AdapterV12)
        bot = ctx.create_bot(
            base=BotV12,
            adapter=adapter,
            auto_connect=False,
            platform="test",
            impl="test",
        )
        event = fake_channel_message_event_v12(message=MessageV12("/我的今日词云"))

        ctx.receive_event(bot, event)
        should_send_saa(
            ctx,
            MessageFactory(Image(FAKE_IMAGE, "wordcloud.png")),
            bot,
            event=event,
            at_sender=True,
        )
        ctx.should_finished()

    mocked_datetime_now.assert_called_once_with()
    mocked_get_wordcloud.assert_called_once_with(
        ["v12-10:1-2"],
        "unknown_ob12-platform=qq-detail_type=channel-guild_id=10000-channel_id=100000",
    )


@pytest.mark.usefixtures("_message_record")
async def test_today_wordcloud_qq_group_v12(app: App, mocker: MockerFixture):
    """测试 ob12 的 QQ群 今日词云"""
    from nonebot_plugin_saa import Image, MessageFactory

    from nonebot_plugin_wordcloud import wordcloud_cmd

    mocked_datetime_now = mocker.patch(
        "nonebot_plugin_wordcloud.get_datetime_now_with_timezone",
        return_value=datetime(2022, 1, 2, 23, tzinfo=ZoneInfo("Asia/Shanghai")),
    )

    mocked_get_wordcloud = mocker.patch(
        "nonebot_plugin_wordcloud.get_wordcloud",
        return_value=FAKE_IMAGE,
    )
    async with app.test_matcher(wordcloud_cmd) as ctx:
        adapter = get_adapter(AdapterV12)
        bot = ctx.create_bot(
            base=BotV12,
            adapter=adapter,
            auto_connect=False,
            platform="qq",
            impl="test",
        )
        event = fake_group_message_event_v12(message=MessageV12("/今日词云"))

        ctx.receive_event(bot, event)
        should_send_saa(
            ctx,
            MessageFactory(Image(FAKE_IMAGE, "wordcloud.png")),
            bot,
            event=event,
        )
        ctx.should_finished()

    mocked_datetime_now.assert_called_once_with()
    mocked_get_wordcloud.assert_called_once_with(
        ["10:1-2", "11:1-2"], "qq_group-group_id=10000"
    )


@pytest.mark.usefixtures("_message_record")
async def test_today_wordcloud_exclude_user_ids(app: App, mocker: MockerFixture):
    """测试今日词云，排除特定用户"""
    from nonebot_plugin_saa import Image, MessageFactory

    from nonebot_plugin_wordcloud import plugin_config, wordcloud_cmd

    mocker.patch.object(plugin_config, "wordcloud_exclude_user_ids", {"10"})

    mocked_datetime_now = mocker.patch(
        "nonebot_plugin_wordcloud.get_datetime_now_with_timezone",
        return_value=datetime(2022, 1, 2, 23, tzinfo=ZoneInfo("Asia/Shanghai")),
    )

    mocked_get_wordcloud = mocker.patch(
        "nonebot_plugin_wordcloud.get_wordcloud",
        return_value=FAKE_IMAGE,
    )

    async with app.test_matcher(wordcloud_cmd) as ctx:
        adapter = get_adapter(Adapter)
        bot = ctx.create_bot(base=Bot, adapter=adapter, auto_connect=False)
        event = fake_group_message_event_v11(message=Message("/今日词云"))

        ctx.receive_event(bot, event)
        should_send_saa(
            ctx,
            MessageFactory(Image(FAKE_IMAGE, "wordcloud.png")),
            bot,
            event=event,
        )
        ctx.should_finished()

    mocked_datetime_now.assert_called_once_with()
    mocked_get_wordcloud.assert_called_once_with(["11:1-2"], "qq_group-group_id=10000")
