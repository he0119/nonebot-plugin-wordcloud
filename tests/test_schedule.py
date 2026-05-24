from datetime import datetime, time
from io import BytesIO

from nonebot import get_adapter, get_driver
from nonebot.adapters.onebot.v11 import Adapter, Bot, Message
from nonebot.adapters.onebot.v12 import Adapter as AdapterV12
from nonebot.adapters.onebot.v12 import Bot as BotV12
from nonebot.adapters.onebot.v12 import Message as MessageV12
from nonebug import App
from pytest_mock import MockerFixture
from sqlalchemy import select

from .utils import (
    fake_channel_message_event_v12,
    fake_group_message_event_v11,
    fake_group_message_event_v12,
    fake_private_message_event_v11,
    make_channel_target,
    make_group_target,
    should_send_channel_image_v12,
    should_send_group_image,
    should_send_group_image_v12,
    should_send_group_text,
)


def test_get_target_scene_type():
    from nonebot_plugin_alconna import Target
    from nonebot_plugin_uninfo import SceneType

    from nonebot_plugin_wordcloud.schedule import get_target_scene_type

    assert get_target_scene_type(Target("10000")) == SceneType.GROUP
    assert (
        get_target_scene_type(Target("100000", "10000", channel=True))
        == SceneType.CHANNEL_TEXT
    )
    assert get_target_scene_type(Target("10", private=True)) == SceneType.PRIVATE


def test_get_schedule_time_range():
    from nonebot_plugin_wordcloud.model import ScheduleMode, ScheduleType
    from nonebot_plugin_wordcloud.schedule import get_schedule_time_range

    dt = datetime(2024, 5, 6, 22)

    assert get_schedule_time_range(ScheduleType.DAY, dt) == (
        datetime(2024, 5, 5),
        datetime(2024, 5, 6),
    )
    assert get_schedule_time_range(ScheduleType.DAY, dt, ScheduleMode.PERIOD_END) == (
        datetime(2024, 5, 6),
        datetime(2024, 5, 6, 22),
    )
    assert get_schedule_time_range(ScheduleType.WEEK, dt) == (
        datetime(2024, 4, 29),
        datetime(2024, 5, 6),
    )
    assert get_schedule_time_range(ScheduleType.WEEK, datetime(2024, 5, 7, 22)) is None
    assert get_schedule_time_range(
        ScheduleType.WEEK, datetime(2024, 5, 12, 22), ScheduleMode.PERIOD_END
    ) == (
        datetime(2024, 5, 6),
        datetime(2024, 5, 12, 22),
    )
    assert (
        get_schedule_time_range(
            ScheduleType.WEEK, datetime(2024, 5, 11, 22), ScheduleMode.PERIOD_END
        )
        is None
    )
    assert get_schedule_time_range(ScheduleType.MONTH, datetime(2024, 5, 1, 22)) == (
        datetime(2024, 4, 1),
        datetime(2024, 5, 1),
    )
    assert get_schedule_time_range(ScheduleType.MONTH, datetime(2024, 5, 2, 22)) is None
    assert get_schedule_time_range(
        ScheduleType.MONTH, datetime(2024, 5, 31, 22), ScheduleMode.PERIOD_END
    ) == (
        datetime(2024, 5, 1),
        datetime(2024, 5, 31, 22),
    )
    assert get_schedule_time_range(ScheduleType.YEAR, datetime(2024, 1, 1, 22)) == (
        datetime(2023, 1, 1),
        datetime(2024, 1, 1),
    )
    assert get_schedule_time_range(ScheduleType.YEAR, datetime(2024, 1, 2, 22)) is None
    assert get_schedule_time_range(
        ScheduleType.YEAR, datetime(2024, 12, 31, 22), ScheduleMode.PERIOD_END
    ) == (
        datetime(2024, 1, 1),
        datetime(2024, 12, 31, 22),
    )


async def test_enable_schedule(app: App):
    from nonebot_plugin_wordcloud import schedule_cmd, schedule_service

    async with app.test_matcher(schedule_cmd) as ctx:
        adapter = get_adapter(Adapter)
        bot = ctx.create_bot(base=Bot, adapter=adapter, auto_connect=False)
        event = fake_group_message_event_v11(
            message=Message("/开启词云每日定时发送"), sender={"role": "admin"}
        )
        ctx.receive_event(bot, event)
        ctx.should_pass_permission(schedule_cmd)
        ctx.should_call_send(
            event, "已开启词云每日定时发送，发送时间为：00:00:00+08:00", True
        )
        ctx.should_finished(schedule_cmd)

    assert len(schedule_service.schedules) == 1

    async with app.test_matcher(schedule_cmd) as ctx:
        adapter = get_adapter(Adapter)
        bot = ctx.create_bot(base=Bot, adapter=adapter, auto_connect=False)
        event = fake_group_message_event_v11(
            message=Message("/开启词云每日定时发送 10:00"), sender={"role": "admin"}
        )

        ctx.receive_event(bot, event)
        ctx.should_pass_permission(schedule_cmd)
        ctx.should_call_send(
            event, "已开启词云每日定时发送，发送时间为：10:00:00+08:00", True
        )
        ctx.should_finished(schedule_cmd)

    assert len(schedule_service.schedules) == 2

    async with app.test_matcher(schedule_cmd) as ctx:
        adapter = get_adapter(Adapter)
        bot = ctx.create_bot(base=Bot, adapter=adapter, auto_connect=False)
        event = fake_group_message_event_v11(
            message=Message("/开启词云每日定时发送 10:"), sender={"role": "admin"}
        )

        ctx.receive_event(bot, event)
        ctx.should_pass_permission(schedule_cmd)
        ctx.should_call_send(event, "请输入正确的时间，不然我没法理解呢！", True)
        ctx.should_finished(schedule_cmd)

    # OneBot V12
    async with app.test_matcher(schedule_cmd) as ctx:
        adapter = get_adapter(AdapterV12)
        bot = ctx.create_bot(
            base=BotV12, adapter=adapter, auto_connect=False, platform="qq", impl="test"
        )
        event = fake_group_message_event_v12(
            message=MessageV12("/开启词云每日定时发送")
        )

        ctx.receive_event(bot, event)
        ctx.should_ignore_permission(schedule_cmd)
        ctx.should_call_send(
            event, "已开启词云每日定时发送，发送时间为：00:00:00+08:00", True
        )
        ctx.should_finished(schedule_cmd)

    assert len(schedule_service.schedules) == 2

    async with app.test_matcher(schedule_cmd) as ctx:
        adapter = get_adapter(AdapterV12)
        bot = ctx.create_bot(
            base=BotV12, adapter=adapter, auto_connect=False, platform="qq", impl="test"
        )
        event = fake_channel_message_event_v12(
            message=MessageV12("/开启词云每日定时发送 09:00")
        )

        ctx.receive_event(bot, event)
        ctx.should_ignore_permission(schedule_cmd)
        ctx.should_call_send(
            event, "已开启词云每日定时发送，发送时间为：09:00:00+08:00", True
        )
        ctx.should_finished(schedule_cmd)

    assert len(schedule_service.schedules) == 3


async def test_enable_periodic_schedule(app: App):
    from nonebot_plugin_orm import get_session

    from nonebot_plugin_wordcloud import schedule_cmd, schedule_service
    from nonebot_plugin_wordcloud.model import Schedule, ScheduleType

    for schedule_type in [ScheduleType.WEEK, ScheduleType.MONTH, ScheduleType.YEAR]:
        async with app.test_matcher(schedule_cmd) as ctx:
            adapter = get_adapter(Adapter)
            bot = ctx.create_bot(base=Bot, adapter=adapter, auto_connect=False)
            event = fake_group_message_event_v11(
                message=Message(f"/开启词云{schedule_type.value}定时发送 10:00"),
                sender={"role": "admin"},
            )

            ctx.receive_event(bot, event)
            ctx.should_pass_permission(schedule_cmd)
            ctx.should_call_send(
                event,
                f"已开启词云{schedule_type.value}定时发送，发送时间为：10:00:00+08:00",
                True,
            )
            ctx.should_finished(schedule_cmd)

    async with get_session() as session:
        results = await session.scalars(select(Schedule))
        schedules = results.all()
        assert {schedule.schedule_type for schedule in schedules} == {
            ScheduleType.WEEK,
            ScheduleType.MONTH,
            ScheduleType.YEAR,
        }

    assert len(schedule_service.schedules) == 2


async def test_enable_period_end_schedule(app: App):
    from nonebot_plugin_orm import get_session

    from nonebot_plugin_wordcloud import schedule_cmd
    from nonebot_plugin_wordcloud.model import Schedule, ScheduleMode, ScheduleType

    async with app.test_matcher(schedule_cmd) as ctx:
        adapter = get_adapter(Adapter)
        bot = ctx.create_bot(base=Bot, adapter=adapter, auto_connect=False)
        event = fake_group_message_event_v11(
            message=Message("/开启词云每周周期末定时发送 10:00"),
            sender={"role": "admin"},
        )

        ctx.receive_event(bot, event)
        ctx.should_pass_permission(schedule_cmd)
        ctx.should_call_send(
            event,
            "已开启词云每周定时发送，发送时间为：10:00:00+08:00，发送模式为：周期末",
            True,
        )
        ctx.should_finished(schedule_cmd)

    async with get_session() as session:
        schedule = (await session.scalars(select(Schedule))).one()
        assert schedule.schedule_type == ScheduleType.WEEK
        assert schedule.schedule_mode == ScheduleMode.PERIOD_END


async def test_enable_schedule_private(app: App, mocker: MockerFixture):
    """测试私聊开启词云每日定时发送"""
    from nonebot_plugin_wordcloud import schedule_cmd

    config = get_driver().config

    mocker.patch.object(config, "superusers", {"10"})

    async with app.test_matcher(schedule_cmd) as ctx:
        adapter = get_adapter(Adapter)
        bot = ctx.create_bot(base=Bot, adapter=adapter, auto_connect=False)
        event = fake_private_message_event_v11(message=Message("/开启词云每日定时发送"))
        ctx.receive_event(bot, event)
        ctx.should_pass_permission(schedule_cmd)
        ctx.should_call_send(event, "请在群组中使用！", True)
        ctx.should_finished(schedule_cmd)


async def test_enable_schedule_without_permission(app: App, mocker: MockerFixture):
    """测试没有权限的用户开启词云每日定时发送"""
    from nonebot_plugin_wordcloud import schedule_cmd

    async with app.test_matcher(schedule_cmd) as ctx:
        adapter = get_adapter(Adapter)
        bot = ctx.create_bot(base=Bot, adapter=adapter, auto_connect=False)
        event = fake_group_message_event_v11(message=Message("/开启词云每日定时发送"))
        ctx.receive_event(bot, event)
        ctx.should_not_pass_permission(schedule_cmd)


async def test_disable_schedule(app: App):
    from nonebot_plugin_orm import get_session

    from nonebot_plugin_wordcloud import schedule_cmd, schedule_service
    from nonebot_plugin_wordcloud.model import Schedule
    from nonebot_plugin_wordcloud.schedule import dump_target

    async with get_session() as session:
        schedule = Schedule(
            target=dump_target(make_group_target(group_id=10000)),
            time=time(14, 0),
        )
        session.add(schedule)
        await session.commit()

    await schedule_service.update()
    assert len(schedule_service.schedules) == 2

    async with app.test_matcher(schedule_cmd) as ctx:
        adapter = get_adapter(Adapter)
        bot = ctx.create_bot(base=Bot, adapter=adapter, auto_connect=False)
        event = fake_group_message_event_v11(
            message=Message("/关闭词云每日定时发送"), sender={"role": "admin"}
        )
        ctx.receive_event(bot, event)
        ctx.should_pass_permission(schedule_cmd)
        ctx.should_call_send(event, "已关闭词云每日定时发送", True)
        ctx.should_finished(schedule_cmd)

    async with get_session() as session:
        statement = select(Schedule)
        results = await session.scalars(statement)
        assert len(results.all()) == 0

    assert len(schedule_service.schedules) == 2


async def test_add_schedule_merges_equivalent_targets(app: App):
    from nonebot_plugin_orm import get_session

    from nonebot_plugin_wordcloud import schedule_service
    from nonebot_plugin_wordcloud.model import Schedule, ScheduleMode, ScheduleType

    target = make_group_target(group_id=10000)
    legacy_target = {
        "id": "10000",
        "parent_id": "",
        "channel": False,
        "private": False,
        "source": "",
        "extra": {"saa.platform_type": "QQ Group"},
        "scope": "QQClient",
    }

    async with get_session() as session:
        session.add(Schedule(target=legacy_target, time=None))
        await session.commit()

    assert str(await schedule_service.get_schedule(target)) == "00:00:00+08:00"

    await schedule_service.add_schedule(target, time=time(23, 0))

    async with get_session() as session:
        results = await session.scalars(select(Schedule))
        schedules = results.all()
        assert len(schedules) == 1
        assert schedules[0].alc_target == target
        assert schedules[0].time == time(15, 0)
        assert schedules[0].schedule_type == ScheduleType.DAY
        assert schedules[0].schedule_mode == ScheduleMode.COMPLETE

    await schedule_service.add_schedule(
        target,
        time=time(10, 0),
        schedule_type=ScheduleType.WEEK,
        schedule_mode=ScheduleMode.PERIOD_END,
    )

    async with get_session() as session:
        results = await session.scalars(select(Schedule))
        schedules = results.all()
        assert len(schedules) == 2
        assert {schedule.schedule_type for schedule in schedules} == {
            ScheduleType.DAY,
            ScheduleType.WEEK,
        }
        weekly_schedule = next(
            schedule
            for schedule in schedules
            if schedule.schedule_type == ScheduleType.WEEK
        )
        assert weekly_schedule.schedule_mode == ScheduleMode.PERIOD_END


async def test_schedule_status(app: App):
    from nonebot_plugin_wordcloud import schedule_cmd, schedule_service

    async with app.test_matcher(schedule_cmd) as ctx:
        adapter = get_adapter(Adapter)
        bot = ctx.create_bot(base=Bot, adapter=adapter, auto_connect=False)
        event = fake_group_message_event_v11(
            message=Message("/词云每日定时发送状态"), sender={"role": "admin"}
        )
        ctx.receive_event(bot, event)
        ctx.should_pass_permission(schedule_cmd)
        ctx.should_call_send(event, "词云每日定时发送未开启", True)
        ctx.should_finished(schedule_cmd)

    await schedule_service.add_schedule(make_group_target(group_id=10000))

    async with app.test_matcher(schedule_cmd) as ctx:
        adapter = get_adapter(Adapter)
        bot = ctx.create_bot(base=Bot, adapter=adapter, auto_connect=False)
        event = fake_group_message_event_v11(
            message=Message("/词云每日定时发送状态"), sender={"role": "admin"}
        )
        ctx.receive_event(bot, event)
        ctx.should_pass_permission(schedule_cmd)
        ctx.should_call_send(
            event,
            "词云每日定时发送已开启，发送时间为：00:00:00+08:00，发送模式为：完整周期",
            True,
        )
        ctx.should_finished(schedule_cmd)

    await schedule_service.add_schedule(
        make_group_target(group_id=10000), time=time(23, 0)
    )

    async with app.test_matcher(schedule_cmd) as ctx:
        adapter = get_adapter(Adapter)
        bot = ctx.create_bot(
            base=Bot, adapter=adapter, auto_connect=False, self_id="test2"
        )
        event = fake_group_message_event_v11(
            message=Message("/词云每日定时发送状态"), sender={"role": "admin"}
        )
        ctx.receive_event(bot, event)
        ctx.should_pass_permission(schedule_cmd)
        ctx.should_call_send(
            event,
            "词云每日定时发送已开启，发送时间为：23:00:00+08:00，发送模式为：完整周期",
            True,
        )
        ctx.should_finished(schedule_cmd)

    async with app.test_matcher(schedule_cmd) as ctx:
        adapter = get_adapter(Adapter)
        bot = ctx.create_bot(base=Bot, adapter=adapter, auto_connect=False)
        event = fake_group_message_event_v11(
            message=Message("/词云每周定时发送状态"), sender={"role": "admin"}
        )
        ctx.receive_event(bot, event)
        ctx.should_pass_permission(schedule_cmd)
        ctx.should_call_send(event, "词云每周定时发送未开启", True)
        ctx.should_finished(schedule_cmd)


async def test_run_task_group(app: App, mocker: MockerFixture):
    from nonebot_plugin_wordcloud import schedule_service

    image = BytesIO(b"test")
    target = make_group_target(group_id=10000)
    await schedule_service.add_schedule(target)

    mocked_get_messages_plain_text = mocker.patch(
        "nonebot_plugin_wordcloud.schedule.get_messages_plain_text",
        return_value=["test"],
    )
    mocked_get_wordcloud = mocker.patch(
        "nonebot_plugin_wordcloud.schedule.get_wordcloud", return_value=image
    )

    async with app.test_api() as ctx:
        adapter = get_adapter(Adapter)
        ctx.create_bot(base=Bot, adapter=adapter)
        should_send_group_image(ctx, image, group_id=10000)
        await schedule_service.run_task()

    mocked_get_messages_plain_text.assert_called_once()
    mocked_get_wordcloud.assert_called_once_with(["test"], "QQClient_10000")

    # OneBot V12
    mocked_get_messages_plain_text_v12 = mocker.patch(
        "nonebot_plugin_wordcloud.schedule.get_messages_plain_text",
        return_value=["test"],
    )

    mocked_get_wordcloud_v12 = mocker.patch(
        "nonebot_plugin_wordcloud.schedule.get_wordcloud", return_value=image
    )

    async with app.test_api() as ctx:
        adapter = get_adapter(AdapterV12)
        ctx.create_bot(base=BotV12, adapter=adapter, platform="qq", impl="test")
        should_send_group_image_v12(ctx, image, group_id="10000")
        await schedule_service.run_task()

    mocked_get_messages_plain_text_v12.assert_called_once()
    mocked_get_wordcloud_v12.assert_called_once_with(["test"], "QQClient_10000")


async def test_run_task_week(app: App, mocker: MockerFixture):
    from nonebot_plugin_wordcloud import schedule_service
    from nonebot_plugin_wordcloud.model import ScheduleType

    image = BytesIO(b"test")
    target = make_group_target(group_id=10000)
    await schedule_service.add_schedule(target, schedule_type=ScheduleType.WEEK)

    dt = datetime(2024, 5, 6, 22)
    mocker.patch(
        "nonebot_plugin_wordcloud.schedule.get_datetime_now_with_timezone",
        return_value=dt,
    )
    mocked_get_messages_plain_text = mocker.patch(
        "nonebot_plugin_wordcloud.schedule.get_messages_plain_text",
        return_value=["test"],
    )
    mocked_get_wordcloud = mocker.patch(
        "nonebot_plugin_wordcloud.schedule.get_wordcloud", return_value=image
    )

    async with app.test_api() as ctx:
        adapter = get_adapter(Adapter)
        ctx.create_bot(base=Bot, adapter=adapter)
        should_send_group_image(ctx, image, group_id=10000)
        await schedule_service.run_task()

    mocked_get_messages_plain_text.assert_called_once()
    kwargs = mocked_get_messages_plain_text.call_args.kwargs
    assert kwargs["time_start"] == datetime(2024, 4, 29)
    assert kwargs["time_stop"] == datetime(2024, 5, 6)
    mocked_get_wordcloud.assert_called_once_with(["test"], "QQClient_10000")


async def test_run_task_week_not_due(app: App, mocker: MockerFixture):
    from nonebot_plugin_wordcloud import schedule_service
    from nonebot_plugin_wordcloud.model import ScheduleType

    target = make_group_target(group_id=10000)
    await schedule_service.add_schedule(target, schedule_type=ScheduleType.WEEK)

    mocker.patch(
        "nonebot_plugin_wordcloud.schedule.get_datetime_now_with_timezone",
        return_value=datetime(2024, 5, 7, 22),
    )
    mocked_get_messages_plain_text = mocker.patch(
        "nonebot_plugin_wordcloud.schedule.get_messages_plain_text",
        return_value=["test"],
    )

    async with app.test_api() as ctx:
        adapter = get_adapter(Adapter)
        ctx.create_bot(base=Bot, adapter=adapter)
        await schedule_service.run_task()

    mocked_get_messages_plain_text.assert_not_called()


async def test_run_task_week_period_end(app: App, mocker: MockerFixture):
    from nonebot_plugin_wordcloud import schedule_service
    from nonebot_plugin_wordcloud.model import ScheduleMode, ScheduleType

    image = BytesIO(b"test")
    target = make_group_target(group_id=10000)
    await schedule_service.add_schedule(
        target,
        schedule_type=ScheduleType.WEEK,
        schedule_mode=ScheduleMode.PERIOD_END,
    )

    dt = datetime(2024, 5, 12, 22)
    mocker.patch(
        "nonebot_plugin_wordcloud.schedule.get_datetime_now_with_timezone",
        return_value=dt,
    )
    mocked_get_messages_plain_text = mocker.patch(
        "nonebot_plugin_wordcloud.schedule.get_messages_plain_text",
        return_value=["test"],
    )
    mocked_get_wordcloud = mocker.patch(
        "nonebot_plugin_wordcloud.schedule.get_wordcloud", return_value=image
    )

    async with app.test_api() as ctx:
        adapter = get_adapter(Adapter)
        ctx.create_bot(base=Bot, adapter=adapter)
        should_send_group_image(ctx, image, group_id=10000)
        await schedule_service.run_task()

    mocked_get_messages_plain_text.assert_called_once()
    kwargs = mocked_get_messages_plain_text.call_args.kwargs
    assert kwargs["time_start"] == datetime(2024, 5, 6)
    assert kwargs["time_stop"] == dt
    mocked_get_wordcloud.assert_called_once_with(["test"], "QQClient_10000")


async def test_run_task_channel(app: App, mocker: MockerFixture):
    from nonebot_plugin_wordcloud import schedule_service

    image = BytesIO(b"test")
    target = make_channel_target(channel_id=100000)
    await schedule_service.add_schedule(target)

    mocked_get_messages_plain_text = mocker.patch(
        "nonebot_plugin_wordcloud.schedule.get_messages_plain_text",
        return_value=["test"],
    )
    mocked_get_wordcloud_v12 = mocker.patch(
        "nonebot_plugin_wordcloud.schedule.get_wordcloud", return_value=image
    )

    async with app.test_api() as ctx:
        adapter = get_adapter(AdapterV12)
        ctx.create_bot(base=BotV12, adapter=adapter, impl="test", platform="qqguild")
        should_send_channel_image_v12(ctx, image, guild_id="10000", channel_id="100000")
        await schedule_service.run_task()

    mocked_get_messages_plain_text.assert_called_once()
    mocked_get_wordcloud_v12.assert_called_once_with(["test"], "QQGuild_10000_100000")


async def test_run_task_without_data(app: App, mocker: MockerFixture):
    from nonebot_plugin_wordcloud import schedule_service

    target = make_group_target(group_id=10000)
    await schedule_service.add_schedule(target)

    mocked_get_messages_plain_text = mocker.patch(
        "nonebot_plugin_wordcloud.schedule.get_messages_plain_text",
        return_value=["test"],
    )
    mocked_get_wordcloud = mocker.patch(
        "nonebot_plugin_wordcloud.schedule.get_wordcloud", return_value=None
    )

    async with app.test_api() as ctx:
        adapter = get_adapter(Adapter)
        ctx.create_bot(base=Bot, adapter=adapter)
        should_send_group_text(ctx, "这段时间没有足够的数据生成词云", group_id=10000)
        await schedule_service.run_task()

    mocked_get_messages_plain_text.assert_called_once()
    mocked_get_wordcloud.assert_called_once_with(["test"], "QQClient_10000")


async def test_run_task_remove_schedule(app: App):
    """测试运行定时任务时，删除没有内容的定时任务"""
    from nonebot_plugin_wordcloud.schedule import schedule_service

    assert "15:00:00" not in schedule_service.schedules
    assert "16:00:00" not in schedule_service.schedules

    await schedule_service.add_schedule(
        make_group_target(group_id=10000), time=time(23, 0)
    )

    await schedule_service.update()

    assert "15:00:00" in schedule_service.schedules
    assert "16:00:00" not in schedule_service.schedules

    await schedule_service.add_schedule(
        make_group_target(group_id=10000), time=time(0, 0)
    )

    await schedule_service.update()

    assert "15:00:00" in schedule_service.schedules
    assert "16:00:00" in schedule_service.schedules

    await schedule_service.run_task(time(15, 0))

    assert "15:00:00" not in schedule_service.schedules
    assert "16:00:00" in schedule_service.schedules


async def test_run_task_send_error(app: App, mocker: MockerFixture):
    """发送时出现错误"""
    from nonebot_plugin_wordcloud import schedule_service

    image = BytesIO(b"test")
    target = make_group_target(group_id=10000)
    target2 = make_group_target(group_id=10001)
    await schedule_service.add_schedule(target)
    await schedule_service.add_schedule(target2)

    mocked_get_messages_plain_text = mocker.patch(
        "nonebot_plugin_wordcloud.schedule.get_messages_plain_text",
        return_value=["test"],
    )
    mocked_get_wordcloud = mocker.patch(
        "nonebot_plugin_wordcloud.schedule.get_wordcloud", return_value=image
    )

    async with app.test_api() as ctx:
        adapter = get_adapter(Adapter)
        ctx.create_bot(base=Bot, adapter=adapter)
        should_send_group_image(
            ctx, image, group_id=10000, exception=Exception("发送失败")
        )
        # 如果第一个群组发送失败，不应该影响第二个群组
        should_send_group_image(ctx, image, group_id=10001)
        await schedule_service.run_task()

    assert mocked_get_messages_plain_text.call_count == 2
    mocked_get_wordcloud.assert_has_calls(
        [
            mocker.call(["test"], "QQClient_10000"),
            mocker.call(["test"], "QQClient_10001"),
        ]  # type: ignore
    )
