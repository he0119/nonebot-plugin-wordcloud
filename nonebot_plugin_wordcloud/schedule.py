from datetime import datetime, time, timedelta
from typing import TYPE_CHECKING
from zoneinfo import ZoneInfo

from nonebot.log import logger
from nonebot_plugin_alconna import Image, Target, Text, UniMessage
from nonebot_plugin_apscheduler import scheduler
from nonebot_plugin_chatrecorder import get_messages_plain_text
from nonebot_plugin_orm import get_session
from nonebot_plugin_uninfo import SceneType
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from .config import plugin_config
from .data_source import get_wordcloud
from .model import Schedule, ScheduleMode, ScheduleType
from .utils import (
    get_datetime_now_with_timezone,
    get_mask_key,
    get_time_with_scheduler_timezone,
    time_astimezone,
)

if TYPE_CHECKING:
    from apscheduler.job import Job


def dump_target(target: Target) -> dict:
    return target.dump(only_scope=True, save_self_id=False)


def get_target_scene_type(target: Target) -> SceneType:
    if target.private:
        return SceneType.PRIVATE
    if target.channel:
        return SceneType.CHANNEL_TEXT
    return SceneType.GROUP


def get_schedule_time_range(
    schedule_type: ScheduleType,
    dt: datetime,
    schedule_mode: ScheduleMode = ScheduleMode.COMPLETE,
) -> tuple[datetime, datetime] | None:
    """获取定时发送对应的词云时间范围，不到发送日期时返回 None。"""
    stop = dt.replace(hour=0, minute=0, second=0, microsecond=0)
    if schedule_mode == ScheduleMode.PERIOD_END:
        if schedule_type == ScheduleType.DAY:
            return stop, dt
        if schedule_type == ScheduleType.WEEK:
            if dt.weekday() != 6:
                return None
            return stop - timedelta(days=6), dt
        if schedule_type == ScheduleType.MONTH:
            if (stop + timedelta(days=1)).day != 1:
                return None
            return stop.replace(day=1), dt
        if schedule_type == ScheduleType.YEAR:
            if dt.month != 12 or dt.day != 31:
                return None
            return stop.replace(month=1, day=1), dt
        return None

    if schedule_type == ScheduleType.DAY:
        return stop - timedelta(days=1), stop
    if schedule_type == ScheduleType.WEEK:
        if dt.weekday() != 0:
            return None
        return stop - timedelta(days=7), stop
    if schedule_type == ScheduleType.MONTH:
        if dt.day != 1:
            return None
        last_month = stop - timedelta(days=1)
        start = last_month.replace(day=1)
        return start, stop
    if schedule_type == ScheduleType.YEAR:
        if dt.month != 1 or dt.day != 1:
            return None
        start = stop.replace(year=stop.year - 1)
        return start, stop
    return None


class Scheduler:
    def __init__(self):
        # 默认定时任务的 key 为 default
        # 其他则为 ISO 8601 格式的时间字符串
        self.schedules: dict[str, Job] = {}

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
        async with get_session() as session:
            statement = (
                select(Schedule.time)
                .group_by(Schedule.time)
                .where(Schedule.time != None)  # noqa: E711
            )
            schedule_times = await session.scalars(statement)
            for schedule_time in schedule_times:
                assert schedule_time is not None
                time_str = schedule_time.isoformat()
                if time_str not in self.schedules:
                    # 转换到 APScheduler 的时区，因为数据库中的时间是 UTC 时间
                    scheduler_time = get_time_with_scheduler_timezone(
                        schedule_time.replace(tzinfo=ZoneInfo("UTC"))
                    )
                    self.schedules[time_str] = scheduler.add_job(
                        self.run_task,
                        "cron",
                        hour=scheduler_time.hour,
                        minute=scheduler_time.minute,
                        second=scheduler_time.second,
                        args=(schedule_time,),
                    )
                    logger.debug(f"已添加词云定时发送任务，发送时间：{time_str} UTC")

    async def get_target_schedule(
        self,
        target: Target,
        session: AsyncSession,
        schedule_type: ScheduleType = ScheduleType.DAY,
    ) -> Schedule | None:
        statement = (
            select(Schedule)
            .where(Schedule.schedule_type == schedule_type)
            .where(Schedule.target["id"].as_string() == target.id)
            .where(Schedule.target["channel"].as_boolean() == target.channel)
            .where(Schedule.target["private"].as_boolean() == target.private)
            .order_by(Schedule.id)
        )
        results = await session.scalars(statement)
        schedules = results.all()
        return next(
            (
                schedule
                for schedule in reversed(schedules)
                if schedule.alc_target == target
            ),
            None,
        )

    async def run_task(self, time: time | None = None):
        """执行定时任务

        时间为 UTC 时间，并且没有时区信息
        如果没有传入时间，则执行默认定时任务
        """
        async with get_session() as session:
            statement = (
                select(Schedule).where(Schedule.time == time).order_by(Schedule.id)
            )
            results = await session.scalars(statement)
            schedules = results.all()
            # 如果该时间没有需要执行的定时任务，且不是默认任务则从任务列表中删除该任务
            if time and not schedules:
                self.schedules.pop(time.isoformat()).remove()
                return
            logger.info(f"开始发送定时词云，时间为 {time or '默认时间'}")
            for schedule in schedules:
                dt = get_datetime_now_with_timezone()
                if not (
                    time_range := get_schedule_time_range(
                        schedule.schedule_type,
                        dt,
                        schedule.schedule_mode,
                    )
                ):
                    continue
                start, stop = time_range
                target = schedule.alc_target
                messages = await get_messages_plain_text(
                    scopes=[target.scope] if target.scope else None,
                    scene_types=[get_target_scene_type(target)],
                    scene_ids=[target.id],
                    filter_self_id=False,
                    filter_adapter=False,
                    filter_user=False,
                    types=["message"],
                    time_start=start,
                    time_stop=stop,
                    exclude_user_ids=plugin_config.wordcloud_exclude_user_ids,
                )
                mask_key = get_mask_key(target)

                if image := await get_wordcloud(messages, mask_key):
                    msg = Image(raw=image)
                else:
                    msg = Text(
                        "今天没有足够的数据生成词云"
                        if schedule.schedule_mode == ScheduleMode.PERIOD_END
                        and schedule.schedule_type == ScheduleType.DAY
                        else "这段时间没有足够的数据生成词云"
                    )

                try:
                    await target.send(UniMessage(msg))
                except Exception:
                    logger.exception(
                        f"{target} 发送{schedule.schedule_type.value}词云失败"
                    )

    async def get_schedule(
        self, target: Target, schedule_type: ScheduleType = ScheduleType.DAY
    ) -> time | None:
        """获取定时任务时间"""
        if schedule_info := await self.get_schedule_info(target, schedule_type):
            return schedule_info[0]

    async def get_schedule_info(
        self, target: Target, schedule_type: ScheduleType = ScheduleType.DAY
    ) -> tuple[time, ScheduleMode] | None:
        """获取定时任务时间与发送模式"""
        async with get_session() as db_session:
            if schedule := await self.get_target_schedule(
                target, db_session, schedule_type
            ):
                if schedule.time:
                    # 将时间转换为本地时间
                    schedule_time = time_astimezone(
                        schedule.time.replace(tzinfo=ZoneInfo("UTC"))
                    )
                else:
                    schedule_time = plugin_config.wordcloud_default_schedule_time
                return schedule_time, schedule.schedule_mode

    async def add_schedule(
        self,
        target: Target,
        *,
        time: time | None = None,
        schedule_type: ScheduleType = ScheduleType.DAY,
        schedule_mode: ScheduleMode = ScheduleMode.COMPLETE,
    ):
        """添加定时任务

        时间需要带时区信息
        """
        # 将时间转换为 UTC 时间
        if time:
            time = time_astimezone(time, ZoneInfo("UTC"))

        async with get_session() as db_session:
            if schedule := await self.get_target_schedule(
                target, db_session, schedule_type
            ):
                schedule.time = time
                schedule.target = dump_target(target)
                schedule.schedule_mode = schedule_mode
            else:
                schedule = Schedule(
                    time=time,
                    target=dump_target(target),
                    schedule_type=schedule_type,
                    schedule_mode=schedule_mode,
                )
                db_session.add(schedule)
            await db_session.commit()
        await self.update()

    async def remove_schedule(
        self, target: Target, schedule_type: ScheduleType = ScheduleType.DAY
    ):
        """删除定时任务"""
        async with get_session() as db_session:
            if schedule := await self.get_target_schedule(
                target, db_session, schedule_type
            ):
                await db_session.delete(schedule)
                await db_session.commit()


schedule_service = Scheduler()
