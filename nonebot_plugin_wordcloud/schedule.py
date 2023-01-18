from datetime import time
from typing import Dict, List, Optional, cast

from apscheduler.job import Job
from nonebot import get_bot
from nonebot.adapters.onebot.v11 import Bot, Message, MessageSegment
from nonebot.log import logger
from nonebot_plugin_apscheduler import scheduler
from nonebot_plugin_chatrecorder import get_messages_plain_text
from nonebot_plugin_datastore import create_session
from sqlmodel import select

from .utils import get_datetime_now_with_timezone, get_time_with_scheduler_timezone

try:
    from zoneinfo import ZoneInfo
except ImportError:
    from backports.zoneinfo import ZoneInfo  # type: ignore

from .config import plugin_config
from .data_source import get_wordcloud
from .model import Schedule
from .utils import time_astimezone


class Scheduler:
    def __init__(self):
        # 默认定时任务的 key 为 default
        # 其他则为 ISO 8601 格式的时间字符串
        self.schedules: Dict[str, Job] = {}

        # 转换到 APScheduler 的时区
        scheduler_time = get_time_with_scheduler_timezone(
            plugin_config.wordcloud_default_schedule_time
        )
        # 添加默认定时任务
        self.schedules["default"] = scheduler.add_job(
            self.run_task,
            "cron",
            hour=scheduler_time.hour,
            minute=scheduler_time.minute,
            second=scheduler_time.second,
        )

    async def update(self):
        """更新定时任务"""
        async with create_session() as session:
            statement = (
                select(Schedule).group_by(Schedule.time).where(Schedule.time != None)
            )
            schedules: List[Schedule] = await session.exec(statement)  # type: ignore
            for schedule in schedules:
                schedule.time = cast(time, schedule.time)
                time_str = schedule.time.isoformat()
                if time_str not in self.schedules:
                    # 转换到 APScheduler 的时区，因为数据库中的时间是 UTC 时间
                    scheduler_time = get_time_with_scheduler_timezone(
                        schedule.time.replace(tzinfo=ZoneInfo("UTC"))
                    )
                    self.schedules[time_str] = scheduler.add_job(
                        self.run_task,
                        "cron",
                        hour=scheduler_time.hour,
                        minute=scheduler_time.minute,
                        second=scheduler_time.second,
                        args=(schedule.time,),
                    )
                    logger.debug(f"已添加每日词云定时发送任务，发送时间：{time_str} UTC")

    async def run_task(self, time: Optional[time] = None):
        """执行定时任务

        时间为 UTC 时间，并且没有时区信息
        如果没有传入时间，则执行默认定时任务
        """
        async with create_session() as session:
            statement = select(Schedule).where(Schedule.time == time)
            results = await session.exec(statement)  # type: ignore
            schedules: List[Schedule] = results.all()
            # 如果该时间没有需要执行的定时任务，且不是默认任务则从任务列表中删除该任务
            if time and not schedules:
                self.schedules.pop(time.isoformat()).remove()
                return
            logger.info(f"开始发送每日词云，时间为 {time if time else '默认时间'}")
            for schedule in schedules:
                bot = get_bot(schedule.bot_id)
                bot = cast(Bot, bot)

                dt = get_datetime_now_with_timezone()
                start = dt.replace(hour=0, minute=0, second=0, microsecond=0)
                stop = dt
                messages = await get_messages_plain_text(
                    group_ids=[schedule.group_id],
                    types=["message"],
                    time_start=start.astimezone(ZoneInfo("UTC")),
                    time_stop=stop.astimezone(ZoneInfo("UTC")),
                )
                image = await get_wordcloud(messages, schedule.group_id)
                if image:
                    await bot.send_group_msg(
                        group_id=int(schedule.group_id),
                        message=Message(MessageSegment.image(image)),
                    )
                else:
                    await bot.send_group_msg(
                        group_id=int(schedule.group_id),
                        message="今天没有足够的数据生成词云",
                    )

    async def get_schedule(self, bot_id: str, group_id: str) -> Optional[time]:
        """获取定时任务时间"""
        async with create_session() as session:
            statement = (
                select(Schedule)
                .where(Schedule.bot_id == bot_id)
                .where(Schedule.group_id == group_id)
            )
            results = await session.exec(statement)  # type: ignore
            schedule = results.one_or_none()
            if schedule:
                schedule = cast(Schedule, schedule)
                if schedule.time:
                    # 将时间转换为本地时间
                    local_time = time_astimezone(
                        schedule.time.replace(tzinfo=ZoneInfo("UTC"))
                    )
                    return local_time
                else:
                    return plugin_config.wordcloud_default_schedule_time

    async def add_schedule(
        self, bot_id: str, group_id: str, time: Optional[time] = None
    ):
        """添加定时任务

        时间需要带时区信息
        """
        # 将时间转换为 UTC 时间
        if time:
            time = time_astimezone(time, ZoneInfo("UTC"))

        async with create_session() as session:
            statement = (
                select(Schedule)
                .where(Schedule.bot_id == bot_id)
                .where(Schedule.group_id == group_id)
            )
            results = await session.exec(statement)  # type: ignore
            schedule = results.one_or_none()
            if schedule:
                schedule.time = time
            else:
                schedule = Schedule(bot_id=bot_id, group_id=group_id, time=time)
                session.add(schedule)
            await session.commit()
        await self.update()

    async def remove_schedule(self, bot_id: str, group_id: str):
        """删除定时任务"""
        async with create_session() as session:
            statement = (
                select(Schedule)
                .where(Schedule.bot_id == bot_id)
                .where(Schedule.group_id == group_id)
            )
            results = await session.exec(statement)  # type: ignore
            schedule = results.first()
            if schedule:
                await session.delete(schedule)
                await session.commit()


schedule_service = Scheduler()
