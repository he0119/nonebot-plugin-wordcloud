from datetime import time
from typing import Dict, List

from apscheduler.job import Job
from nonebot import get_bot
from nonebot.adapters.onebot.v11 import MessageSegment
from nonebot.utils import run_sync
from nonebot_plugin_apscheduler import scheduler
from nonebot_plugin_chatrecorder import get_message_records
from nonebot_plugin_datastore import create_session
from sqlmodel import select

from .utils import get_datetime_now_with_timezone

try:
    from zoneinfo import ZoneInfo
except ImportError:
    from backports.zoneinfo import ZoneInfo  # type: ignore

from .config import plugin_config
from .data_source import get_wordcloud
from .model import Schedule


class Scheduler:
    def __init__(self):
        self.schedules: Dict[time, Job] = {}

    async def refresh(self):
        """刷新定时任务"""
        for schedule in self.schedules.values():
            schedule.remove()
        self.schedules.clear()

        # 添加默认定时任务
        self.schedules[
            plugin_config.wordcloud_default_schedule_time
        ] = scheduler.add_job(
            self.run_task,
            "cron",
            hour=plugin_config.wordcloud_default_schedule_time.hour,
            minute=plugin_config.wordcloud_default_schedule_time.minute,
            second=plugin_config.wordcloud_default_schedule_time.second,
            args=(plugin_config.wordcloud_default_schedule_time,),
        )
        # 添加单独设置的定时任务
        async with create_session() as session:
            statement = (
                select(Schedule).group_by(Schedule.time).where(Schedule.time != None)
            )
            schedules: List[Schedule] = await session.exec(statement)  # type: ignore
            for schedule in schedules:
                if schedule.time not in self.schedules and schedule.time:
                    self.schedules[schedule.time] = scheduler.add_job(
                        self.run_task,
                        "cron",
                        hour=schedule.time.hour,
                        minute=schedule.time.minute,
                        second=schedule.time.second,
                        args=(schedule.time,),
                    )

    async def run_task(self, time: time):
        """执行定时任务"""
        async with create_session() as session:
            statement = select(Schedule).where(Schedule.time == time)
            schedules: List[Schedule] = await session.exec(statement)  # type: ignore
            for schedule in schedules:
                bot = get_bot(schedule.bot_id)

                dt = get_datetime_now_with_timezone()
                start = dt.replace(hour=0, minute=0, second=0, microsecond=0)
                stop = dt
                messages = await get_message_records(
                    group_ids=[schedule.group_id],
                    exclude_user_ids=[bot.self_id],
                    time_start=start.astimezone(ZoneInfo("UTC")),
                    time_stop=stop.astimezone(ZoneInfo("UTC")),
                    plain_text=True,
                )
                image = await run_sync(get_wordcloud)(messages)
                if image:
                    await bot.send_group_msg(
                        group_id=schedule.group_id,
                        message=MessageSegment.image(image),
                    )
