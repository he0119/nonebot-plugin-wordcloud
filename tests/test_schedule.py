from datetime import time
from io import BytesIO

from nonebot import get_driver
from nonebot.adapters.onebot.v11 import Bot, Message
from nonebot.adapters.onebot.v12 import Bot as BotV12
from nonebot.adapters.onebot.v12 import Message as MessageV12
from nonebug import App
from nonebug_saa import should_send_saa
from pytest_mock import MockerFixture
from sqlalchemy import select

from .utils import (
    fake_channel_message_event_v12,
    fake_group_message_event_v11,
    fake_group_message_event_v12,
    fake_private_message_event_v11,
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
        bot = ctx.create_bot(base=BotV12, platform="qq", impl="test")
        event = fake_group_message_event_v12(message=MessageV12("/开启词云每日定时发送"))

        ctx.receive_event(bot, event)
        ctx.should_ignore_permission()
        ctx.should_call_send(event, "已开启词云每日定时发送，发送时间为：22:00:00+08:00", True)
        ctx.should_finished()

    assert len(schedule_service.schedules) == 2

    async with app.test_matcher(schedule_cmd) as ctx:
        bot = ctx.create_bot(base=BotV12, platform="qq", impl="test")
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
            target={
                "platform_type": "QQ Group",
                "group_id": 10000,
            },
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
        results = await session.scalars(statement)
        assert len(results.all()) == 0

    assert len(schedule_service.schedules) == 2


async def test_schedule_status(app: App):
    from nonebot_plugin_saa import TargetQQGroup

    from nonebot_plugin_wordcloud import schedule_cmd, schedule_service

    async with app.test_matcher(schedule_cmd) as ctx:
        bot = ctx.create_bot(base=Bot)
        event = fake_group_message_event_v11(
            message=Message("/词云每日定时发送状态"), sender={"role": "admin"}
        )
        ctx.receive_event(bot, event)
        ctx.should_call_send(event, "词云每日定时发送未开启", True)
        ctx.should_finished()

    await schedule_service.add_schedule(TargetQQGroup(group_id=10000))

    async with app.test_matcher(schedule_cmd) as ctx:
        bot = ctx.create_bot(base=Bot)
        event = fake_group_message_event_v11(
            message=Message("/词云每日定时发送状态"), sender={"role": "admin"}
        )
        ctx.receive_event(bot, event)
        ctx.should_call_send(event, "词云每日定时发送已开启，发送时间为：22:00:00+08:00", True)
        ctx.should_finished()

    await schedule_service.add_schedule(TargetQQGroup(group_id=10000), time=time(23, 0))

    async with app.test_matcher(schedule_cmd) as ctx:
        bot = ctx.create_bot(base=Bot, self_id="test2")
        event = fake_group_message_event_v11(
            message=Message("/词云每日定时发送状态"), sender={"role": "admin"}
        )
        ctx.receive_event(bot, event)
        ctx.should_call_send(event, "词云每日定时发送已开启，发送时间为：23:00:00+08:00", True)
        ctx.should_finished()


async def test_run_task_group(app: App, mocker: MockerFixture):
    from nonebot_plugin_saa import Image, MessageFactory, TargetQQGroup

    from nonebot_plugin_wordcloud import schedule_service

    image = BytesIO(b"test")
    target = TargetQQGroup(group_id=10000)
    await schedule_service.add_schedule(target)

    mocked_get_messages_plain_text_by_target = mocker.patch(
        "nonebot_plugin_wordcloud.schedule.get_messages_plain_text_by_target",
        return_value=["test"],
    )
    mocked_get_wordcloud = mocker.patch(
        "nonebot_plugin_wordcloud.schedule.get_wordcloud", return_value=image
    )

    async with app.test_api() as ctx:
        bot = ctx.create_bot(base=Bot)
        should_send_saa(ctx, MessageFactory(Image(image)), bot, target=target)
        await schedule_service.run_task()

    mocked_get_messages_plain_text_by_target.assert_called_once()
    mocked_get_wordcloud.assert_called_once_with(["test"], "qq_group-group_id=10000")

    # OneBot V12
    mocked_get_messages_plain_text_by_target_v12 = mocker.patch(
        "nonebot_plugin_wordcloud.schedule.get_messages_plain_text_by_target",
        return_value=["test"],
    )

    mocked_get_wordcloud_v12 = mocker.patch(
        "nonebot_plugin_wordcloud.schedule.get_wordcloud", return_value=image
    )

    async with app.test_api() as ctx:
        bot = ctx.create_bot(base=BotV12, impl="test", platform="qq")
        should_send_saa(ctx, MessageFactory(Image(image)), bot, target=target)
        await schedule_service.run_task()

    mocked_get_messages_plain_text_by_target_v12.assert_called_once()
    mocked_get_wordcloud_v12.assert_called_once_with(
        ["test"], "qq_group-group_id=10000"
    )


async def test_run_task_channel(app: App, mocker: MockerFixture):
    from nonebot_plugin_saa import Image, MessageFactory, TargetQQGuildChannel

    from nonebot_plugin_wordcloud import schedule_service

    image = BytesIO(b"test")
    target = TargetQQGuildChannel(channel_id=100000)
    await schedule_service.add_schedule(target)

    mocked_get_messages_plain_text_by_target = mocker.patch(
        "nonebot_plugin_wordcloud.schedule.get_messages_plain_text_by_target",
        return_value=["test"],
    )
    mocked_get_wordcloud_v12 = mocker.patch(
        "nonebot_plugin_wordcloud.schedule.get_wordcloud", return_value=image
    )

    async with app.test_api() as ctx:
        bot = ctx.create_bot(base=BotV12, impl="test", platform="qqguild")
        should_send_saa(ctx, MessageFactory(Image(image)), bot, target=target)
        await schedule_service.run_task()

    mocked_get_messages_plain_text_by_target.assert_called_once()
    mocked_get_wordcloud_v12.assert_called_once_with(
        ["test"], "qq_guild_channel-channel_id=100000"
    )


async def test_run_task_without_data(app: App, mocker: MockerFixture):
    from nonebot_plugin_saa import MessageFactory, TargetQQGroup, Text

    from nonebot_plugin_wordcloud import schedule_service

    target = TargetQQGroup(group_id=10000)
    await schedule_service.add_schedule(target)

    mocked_get_messages_plain_text_by_target = mocker.patch(
        "nonebot_plugin_wordcloud.schedule.get_messages_plain_text_by_target",
        return_value=["test"],
    )
    mocked_get_wordcloud = mocker.patch(
        "nonebot_plugin_wordcloud.schedule.get_wordcloud", return_value=None
    )

    async with app.test_api() as ctx:
        bot = ctx.create_bot(base=Bot)
        should_send_saa(ctx, MessageFactory(Text("今天没有足够的数据生成词云")), bot, target=target)
        await schedule_service.run_task()

    mocked_get_messages_plain_text_by_target.assert_called_once()
    mocked_get_wordcloud.assert_called_once_with(["test"], "qq_group-group_id=10000")


async def test_run_task_remove_schedule(app: App):
    """测试运行定时任务时，删除没有内容的定时任务"""
    from nonebot_plugin_saa import TargetQQGroup

    from nonebot_plugin_wordcloud.schedule import schedule_service

    await schedule_service.add_schedule(TargetQQGroup(group_id=10000), time=time(23, 0))

    await schedule_service.update()

    assert "15:00:00" in schedule_service.schedules

    await schedule_service.add_schedule(TargetQQGroup(group_id=10000), time=time(0, 0))

    await schedule_service.update()

    assert "15:00:00" in schedule_service.schedules
    assert "16:00:00" in schedule_service.schedules

    await schedule_service.run_task(time(15, 0))

    assert "15:00:00" not in schedule_service.schedules
    assert "16:00:00" in schedule_service.schedules


async def test_enable_schedule_private(app: App, mocker: MockerFixture):
    """测试私聊开启词云每日定时发送"""
    from nonebot_plugin_wordcloud import schedule_cmd

    config = get_driver().config

    mocker.patch.object(config, "superusers", {"10"})

    async with app.test_matcher(schedule_cmd) as ctx:
        bot = ctx.create_bot(base=Bot)
        event = fake_private_message_event_v11(message=Message("/开启词云每日定时发送"))
        ctx.receive_event(bot, event)
        ctx.should_call_send(event, "请在群组中使用！", True)
        ctx.should_finished()
