from datetime import time
from io import BytesIO

from nonebot.adapters.onebot.v11 import Bot, Message, MessageSegment
from nonebot.adapters.onebot.v12 import Bot as BotV12
from nonebot.adapters.onebot.v12 import Message as MessageV12
from nonebot.adapters.onebot.v12 import MessageSegment as MessageSegmentV12
from nonebug import App
from pytest_mock import MockerFixture
from sqlmodel import select

from .utils import (
    fake_channel_message_event_v12,
    fake_group_message_event_v11,
    fake_group_message_event_v12,
)


async def test_enable_schedule(app: App):
    from nonebot_plugin_wordcloud import schedule_cmd, schedule_service

    async with app.test_matcher(schedule_cmd) as ctx:
        bot = ctx.create_bot(base=Bot)
        event = fake_group_message_event_v11(
            message=Message("/开启词云每日定时发送"), sender={"role": "admin"}
        )
        ctx.receive_event(bot, event)
        ctx.should_call_send(event, "已开启词云每日定时发送，发送时间为：22:00:00+08:00", True)
        ctx.should_finished()

    assert len(schedule_service.schedules) == 1

    async with app.test_matcher(schedule_cmd) as ctx:
        bot = ctx.create_bot(base=Bot)
        event = fake_group_message_event_v11(
            message=Message("/开启词云每日定时发送 10:00"), sender={"role": "admin"}
        )

        ctx.receive_event(bot, event)
        ctx.should_call_send(event, "已开启词云每日定时发送，发送时间为：10:00:00+08:00", True)
        ctx.should_finished()

    assert len(schedule_service.schedules) == 2

    async with app.test_matcher(schedule_cmd) as ctx:
        bot = ctx.create_bot(base=Bot)
        event = fake_group_message_event_v11(
            message=Message("/开启词云每日定时发送 10:"), sender={"role": "admin"}
        )

        ctx.receive_event(bot, event)
        ctx.should_call_send(event, "请输入正确的时间，不然我没法理解呢！", True)
        ctx.should_finished()

    # OneBot V12
    async with app.test_matcher(schedule_cmd) as ctx:
        bot = ctx.create_bot(base=BotV12, platform="qq")
        event = fake_group_message_event_v12(message=MessageV12("/开启词云每日定时发送"))

        ctx.receive_event(bot, event)
        ctx.should_ignore_permission()
        ctx.should_call_send(event, "已开启词云每日定时发送，发送时间为：22:00:00+08:00", True)
        ctx.should_finished()

    assert len(schedule_service.schedules) == 2

    async with app.test_matcher(schedule_cmd) as ctx:
        bot = ctx.create_bot(base=BotV12, platform="qq")
        event = fake_channel_message_event_v12(message=MessageV12("/开启词云每日定时发送 09:00"))

        ctx.receive_event(bot, event)
        ctx.should_ignore_permission()
        ctx.should_call_send(event, "已开启词云每日定时发送，发送时间为：09:00:00+08:00", True)
        ctx.should_finished()

    assert len(schedule_service.schedules) == 3


async def test_disable_schedule(app: App):
    from nonebot_plugin_datastore import create_session

    from nonebot_plugin_wordcloud import schedule_cmd, schedule_service
    from nonebot_plugin_wordcloud.model import Schedule

    async with create_session() as session:
        schedule = Schedule(
            bot_id="test",
            platform="qq",
            group_id="10000",
            time=time(14, 0),
        )
        session.add(schedule)
        await session.commit()

    await schedule_service.update()
    assert len(schedule_service.schedules) == 2

    async with app.test_matcher(schedule_cmd) as ctx:
        bot = ctx.create_bot(base=Bot)
        event = fake_group_message_event_v11(
            message=Message("/关闭词云每日定时发送"), sender={"role": "admin"}
        )
        ctx.receive_event(bot, event)
        ctx.should_call_send(event, "已关闭词云每日定时发送", True)
        ctx.should_finished()

    async with create_session() as session:
        statement = select(Schedule)
        results = await session.exec(statement)  # type: ignore
        assert len(results.all()) == 0

    assert len(schedule_service.schedules) == 2


async def test_schedule_status(app: App):
    from nonebot_plugin_datastore import create_session

    from nonebot_plugin_wordcloud import schedule_cmd
    from nonebot_plugin_wordcloud.model import Schedule

    async with app.test_matcher(schedule_cmd) as ctx:
        bot = ctx.create_bot(base=Bot)
        event = fake_group_message_event_v11(
            message=Message("/词云每日定时发送状态"), sender={"role": "admin"}
        )
        ctx.receive_event(bot, event)
        ctx.should_call_send(event, "词云每日定时发送未开启", True)
        ctx.should_finished()

    async with create_session() as session:
        schedule = Schedule(bot_id="test", platform="qq", group_id="10000")
        session.add(schedule)
        await session.commit()

    async with app.test_matcher(schedule_cmd) as ctx:
        bot = ctx.create_bot(base=Bot)
        event = fake_group_message_event_v11(
            message=Message("/词云每日定时发送状态"), sender={"role": "admin"}
        )
        ctx.receive_event(bot, event)
        ctx.should_call_send(event, "词云每日定时发送已开启，发送时间为：22:00:00+08:00", True)
        ctx.should_finished()

    async with create_session() as session:
        schedule = Schedule(
            bot_id="test2", platform="qq", group_id="10000", time=time(15, 0)
        )
        session.add(schedule)
        await session.commit()

    async with app.test_matcher(schedule_cmd) as ctx:
        bot = ctx.create_bot(base=Bot, self_id="test2")
        event = fake_group_message_event_v11(
            message=Message("/词云每日定时发送状态"), sender={"role": "admin"}
        )
        ctx.receive_event(bot, event)
        ctx.should_call_send(event, "词云每日定时发送已开启，发送时间为：23:00:00+08:00", True)
        ctx.should_finished()


async def test_run_task_group(app: App, mocker: MockerFixture):
    from nonebot_plugin_datastore import create_session

    from nonebot_plugin_wordcloud import schedule_service
    from nonebot_plugin_wordcloud.model import Schedule

    async with create_session() as session:
        schedule = Schedule(bot_id="test", platform="qq", group_id="10000")
        session.add(schedule)
        await session.commit()

    mocked_get_messages_plain_text = mocker.patch(
        "nonebot_plugin_wordcloud.schedule.get_messages_plain_text",
        return_value=["test"],
    )
    mocked_bot = mocker.AsyncMock(spec=Bot)
    mocked_bot.send_group_msg = mocker.AsyncMock()
    mocked_get_bot = mocker.patch(
        "nonebot_plugin_wordcloud.schedule.get_bot", return_value=mocked_bot
    )
    mocked_get_wordcloud = mocker.patch(
        "nonebot_plugin_wordcloud.schedule.get_wordcloud", return_value="test"
    )

    await schedule_service.run_task()

    mocked_get_bot.assert_called_once_with("test")
    mocked_get_messages_plain_text.assert_called_once()
    mocked_get_wordcloud.assert_called_once_with(["test"], "qq-group-10000")
    mocked_bot.send_group_msg.assert_called_once_with(
        group_id=10000,
        message=Message(MessageSegment.image("test")),
    )

    # OneBot V12
    mocked_get_messages_plain_text_v12 = mocker.patch(
        "nonebot_plugin_wordcloud.schedule.get_messages_plain_text",
        return_value=["test"],
    )
    mocked_bot_v12 = mocker.AsyncMock(spec=BotV12)
    mocked_bot_v12.send_message = mocker.AsyncMock()
    mocked_bot_v12.upload_file = mocker.AsyncMock(return_value={"file_id": "test"})
    mocked_get_bot_v12 = mocker.patch(
        "nonebot_plugin_wordcloud.schedule.get_bot", return_value=mocked_bot_v12
    )
    mocked_get_wordcloud_v12 = mocker.patch(
        "nonebot_plugin_wordcloud.schedule.get_wordcloud", return_value=BytesIO(b"test")
    )

    await schedule_service.run_task()

    mocked_get_bot_v12.assert_called_once_with("test")
    mocked_get_messages_plain_text_v12.assert_called_once()
    mocked_get_wordcloud_v12.assert_called_once_with(["test"], "qq-group-10000")
    mocked_bot_v12.send_message.assert_called_once_with(
        detail_type="group",
        group_id="10000",
        guild_id=None,
        channel_id=None,
        message=MessageV12(MessageSegmentV12.image("test")),
    )


async def test_run_task_channel(app: App, mocker: MockerFixture):
    from nonebot_plugin_datastore import create_session

    from nonebot_plugin_wordcloud import schedule_service
    from nonebot_plugin_wordcloud.model import Schedule

    async with create_session() as session:
        schedule = Schedule(
            bot_id="test", platform="qq", guild_id="10000", channel_id="100000"
        )
        session.add(schedule)
        await session.commit()

    mocked_get_messages_plain_text = mocker.patch(
        "nonebot_plugin_wordcloud.schedule.get_messages_plain_text",
        return_value=["test"],
    )
    mocked_bot = mocker.AsyncMock(spec=BotV12)
    mocked_bot.send_message = mocker.AsyncMock()
    mocked_bot.upload_file = mocker.AsyncMock(return_value={"file_id": "test"})
    mocked_get_bot = mocker.patch(
        "nonebot_plugin_wordcloud.schedule.get_bot", return_value=mocked_bot
    )
    mocked_get_wordcloud_v12 = mocker.patch(
        "nonebot_plugin_wordcloud.schedule.get_wordcloud", return_value=BytesIO(b"test")
    )

    await schedule_service.run_task()

    mocked_get_bot.assert_called_once_with("test")
    mocked_get_messages_plain_text.assert_called_once()
    mocked_get_wordcloud_v12.assert_called_once_with(["test"], "qq-guild-10000")
    mocked_bot.send_message.assert_called_once_with(
        detail_type="channel",
        group_id=None,
        guild_id="10000",
        channel_id="100000",
        message=MessageV12(MessageSegmentV12.image("test")),
    )

    # 机器人类型不是 V11/V12
    mocked_get_messages_plain_text_invalid_bot = mocker.patch(
        "nonebot_plugin_wordcloud.schedule.get_messages_plain_text",
        return_value=["test"],
    )
    mocked_bot_invalid_bot = mocker.AsyncMock()
    mocked_bot_invalid_bot.send_message = mocker.AsyncMock()
    mocked_get_bot_invalid_bot = mocker.patch(
        "nonebot_plugin_wordcloud.schedule.get_bot", return_value=mocked_bot_invalid_bot
    )
    mocked_get_wordcloud_v12_invalid_bot = mocker.patch(
        "nonebot_plugin_wordcloud.schedule.get_wordcloud", return_value=BytesIO(b"test")
    )

    await schedule_service.run_task()

    mocked_get_bot_invalid_bot.assert_called_once_with("test")
    mocked_get_messages_plain_text_invalid_bot.assert_not_called()
    mocked_get_wordcloud_v12_invalid_bot.assert_not_called()
    mocked_bot_invalid_bot.send_message.assert_not_called()


async def test_run_task_without_data(app: App, mocker: MockerFixture):
    from nonebot_plugin_datastore import create_session

    from nonebot_plugin_wordcloud import schedule_service
    from nonebot_plugin_wordcloud.model import Schedule

    async with create_session() as session:
        schedule = Schedule(bot_id="test", platform="qq", group_id="10000")
        session.add(schedule)
        await session.commit()

    mocked_get_messages_plain_text = mocker.patch(
        "nonebot_plugin_wordcloud.schedule.get_messages_plain_text",
        return_value=["test"],
    )
    mocked_bot = mocker.AsyncMock(spec=Bot)
    mocked_bot.send_group_msg = mocker.AsyncMock()
    mocked_get_bot = mocker.patch(
        "nonebot_plugin_wordcloud.schedule.get_bot", return_value=mocked_bot
    )
    mocked_get_wordcloud = mocker.patch(
        "nonebot_plugin_wordcloud.schedule.get_wordcloud", return_value=None
    )

    await schedule_service.run_task()

    mocked_get_bot.assert_called_once_with("test")
    mocked_get_messages_plain_text.assert_called_once()
    mocked_get_wordcloud.assert_called_once_with(["test"], "qq-group-10000")
    mocked_bot.send_group_msg.assert_called_once_with(
        group_id=10000,
        message=Message("今天没有足够的数据生成词云"),
    )


async def test_run_task_without_data_channel(app: App, mocker: MockerFixture):
    from nonebot_plugin_datastore import create_session

    from nonebot_plugin_wordcloud import schedule_service
    from nonebot_plugin_wordcloud.model import Schedule

    async with create_session() as session:
        schedule = Schedule(
            bot_id="test", platform="qq", guild_id="10000", channel_id="100000"
        )
        session.add(schedule)
        await session.commit()

    mocked_get_messages_plain_text = mocker.patch(
        "nonebot_plugin_wordcloud.schedule.get_messages_plain_text",
        return_value=["test"],
    )
    mocked_bot = mocker.AsyncMock(spec=BotV12)
    mocked_bot.send_message = mocker.AsyncMock()
    mocked_get_bot = mocker.patch(
        "nonebot_plugin_wordcloud.schedule.get_bot", return_value=mocked_bot
    )
    mocked_get_wordcloud = mocker.patch(
        "nonebot_plugin_wordcloud.schedule.get_wordcloud", return_value=None
    )

    await schedule_service.run_task()

    mocked_get_bot.assert_called_once_with("test")
    mocked_get_messages_plain_text.assert_called_once()
    mocked_get_wordcloud.assert_called_once_with(["test"], "qq-guild-10000")
    mocked_bot.send_message.assert_called_once_with(
        detail_type="channel",
        group_id=None,
        guild_id="10000",
        channel_id="100000",
        message=MessageV12("今天没有足够的数据生成词云"),
    )


async def test_run_task_remove_schedule(app: App):
    """测试运行定时任务时，删除没有内容的定时任务"""
    from nonebot_plugin_datastore import create_session

    from nonebot_plugin_wordcloud.model import Schedule
    from nonebot_plugin_wordcloud.schedule import schedule_service

    async with create_session() as session:
        schedule = Schedule(
            bot_id="test", platform="qq", group_id="10000", time=time(15, 0)
        )
        session.add(schedule)
        await session.commit()

    await schedule_service.update()

    assert "15:00:00" in schedule_service.schedules

    async with create_session() as session:
        schedule.time = time(16, 0)
        session.add(schedule)
        await session.commit()

    await schedule_service.update()

    assert "15:00:00" in schedule_service.schedules
    assert "16:00:00" in schedule_service.schedules

    await schedule_service.run_task(time(15, 0))

    assert "15:00:00" not in schedule_service.schedules
    assert "16:00:00" in schedule_service.schedules
