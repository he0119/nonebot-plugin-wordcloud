from datetime import time

from nonebug import App

from .utils import fake_group_message_event


async def test_enable_schedule(app: App):
    from nonebot.adapters.onebot.v11 import Message

    from nonebot_plugin_wordcloud import schedule_cmd, schedule_service

    async with app.test_matcher(schedule_cmd) as ctx:
        bot = ctx.create_bot()
        event = fake_group_message_event(
            message=Message("/开启词云每日定时发送"), sender={"role": "admin"}
        )
        ctx.receive_event(bot, event)
        ctx.should_call_send(event, "已开启词云每日定时发送，发送时间为：22:00:00+08:00", True)
        ctx.should_finished()

    assert len(schedule_service.schedules) == 1

    async with app.test_matcher(schedule_cmd) as ctx:
        bot = ctx.create_bot()
        event = fake_group_message_event(
            message=Message("/开启词云每日定时发送 10:00"), sender={"role": "admin"}
        )

        ctx.receive_event(bot, event)
        ctx.should_call_send(event, "已开启词云每日定时发送，发送时间为：10:00:00+08:00", True)
        ctx.should_finished()

    assert len(schedule_service.schedules) == 2

    async with app.test_matcher(schedule_cmd) as ctx:
        bot = ctx.create_bot()
        event = fake_group_message_event(
            message=Message("/开启词云每日定时发送 10:"), sender={"role": "admin"}
        )

        ctx.receive_event(bot, event)
        ctx.should_call_send(event, "请输入正确的时间，不然我没法理解呢！", True)
        ctx.should_finished()


async def test_disable_schedule(app: App):
    from nonebot.adapters.onebot.v11 import Message
    from nonebot_plugin_datastore import create_session
    from sqlmodel import select

    from nonebot_plugin_wordcloud import schedule_cmd, schedule_service
    from nonebot_plugin_wordcloud.model import Schedule

    async with create_session() as session:
        schedule = Schedule(bot_id="test", group_id="10000", time=time(14, 0))
        session.add(schedule)
        await session.commit()

    await schedule_service.update()
    assert len(schedule_service.schedules) == 2

    async with app.test_matcher(schedule_cmd) as ctx:
        bot = ctx.create_bot()
        event = fake_group_message_event(
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
