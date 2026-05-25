from datetime import datetime, time
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
    get_current_period_range,
    get_datetime_now_with_timezone,
    get_mask_key,
    get_previous_period_range,
    get_time_with_scheduler_timezone,
    is_period_end,
    is_period_start,
    time_astimezone,
)

if TYPE_CHECKING:
    from apscheduler.job import Job


def dump_target(target: Target) -> dict:
    """序列化 Alconna 发送目标。

    Args:
        target: 需要保存到数据库的发送目标。

    Returns:
        去除 self_id 并仅保留 scope 信息的 target 字典。
    """
    return target.dump(only_scope=True, save_self_id=False)


def get_target_scene_type(target: Target) -> SceneType:
    """根据发送目标判断聊天记录场景类型。

    Args:
        target: Alconna 发送目标。

    Returns:
        用于查询聊天记录的场景类型。
    """
    if target.private:
        return SceneType.PRIVATE
    if target.channel:
        return SceneType.CHANNEL_TEXT
    return SceneType.GROUP


def get_schedule_time_range(
    dt: datetime,
    schedule_type: ScheduleType,
    schedule_mode: ScheduleMode = ScheduleMode.COMPLETE,
) -> tuple[datetime, datetime] | None:
    """获取定时发送对应的词云时间范围。

    Args:
        dt: 当前触发时间。
        schedule_type: 定时发送类型。
        schedule_mode: 定时发送模式。

    Returns:
        词云消息查询的起止时间；当前日期无需发送时返回 None。
    """
    if schedule_mode == ScheduleMode.PERIOD_END:
        if is_period_end(dt, schedule_type):
            return get_current_period_range(dt, schedule_type)
        return None

    if is_period_start(dt, schedule_type):
        return get_previous_period_range(dt, schedule_type)


class Scheduler:
    def __init__(self):
        """初始化默认定时发送任务。"""
        # 默认定时任务的 key 为 default:<mode>
        # 其他则为 ISO 8601 格式的时间字符串
        self.schedules: dict[str, Job] = {}

        for schedule_mode in ScheduleMode:
            # 转换到 APScheduler 的时区
            scheduler_time = get_time_with_scheduler_timezone(
                plugin_config.get_default_schedule_time(schedule_mode)
            )
            # 添加默认定时任务
            self.schedules[self.get_default_schedule_key(schedule_mode)] = (
                scheduler.add_job(
                    self.run_task,
                    "cron",
                    hour=scheduler_time.hour,
                    minute=scheduler_time.minute,
                    second=scheduler_time.second,
                    args=(None, schedule_mode),
                )
            )

    @staticmethod
    def get_default_schedule_key(schedule_mode: ScheduleMode) -> str:
        """获取默认定时任务在内存任务表中的 key。

        Args:
            schedule_mode: 默认定时任务对应的发送模式。

        Returns:
            内存任务表中的默认任务 key。
        """
        return f"default:{schedule_mode.value}"

    async def update(self):
        """根据数据库中的自定义时间更新 APScheduler 任务。"""
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
        """获取指定目标和类型对应的定时发送配置。

        Args:
            target: Alconna 发送目标。
            session: 数据库会话。
            schedule_type: 定时发送类型。

        Returns:
            匹配的定时发送配置；不存在时返回 None。
        """
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

    async def run_task(
        self, time: time | None = None, schedule_mode: ScheduleMode | None = None
    ):
        """执行定时发送任务。

        Args:
            time: 数据库中保存的 UTC 定时时间；为空时执行默认任务。
            schedule_mode: 默认任务需要筛选的发送模式。
        """
        async with get_session() as session:
            statement = select(Schedule).where(Schedule.time == time)
            if time is None and schedule_mode is not None:
                statement = statement.where(Schedule.schedule_mode == schedule_mode)
            statement = statement.order_by(Schedule.id)
            results = await session.scalars(statement)
            schedules = results.all()
            # 如果该时间没有需要执行的定时任务，且不是默认任务则从任务列表中删除该任务
            if time and not schedules:
                self.schedules.pop(time.isoformat()).remove()
                return
            time_text = time or (
                f"默认时间（{schedule_mode.value}）" if schedule_mode else "默认时间"
            )
            logger.info(f"开始发送定时词云，时间为 {time_text}")
            dt = get_datetime_now_with_timezone()
            for schedule in schedules:
                if not (
                    time_range := get_schedule_time_range(
                        dt,
                        schedule.schedule_type,
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
        """获取指定目标和类型的定时发送时间。

        Args:
            target: Alconna 发送目标。
            schedule_type: 定时发送类型。

        Returns:
            本地时区下的定时发送时间；未开启时返回 None。
        """
        if schedule_info := await self.get_schedule_info(target, schedule_type):
            return schedule_info[0]

    async def get_schedule_info(
        self, target: Target, schedule_type: ScheduleType = ScheduleType.DAY
    ) -> tuple[time, ScheduleMode] | None:
        """获取指定目标和类型的定时发送时间与发送模式。

        Args:
            target: Alconna 发送目标。
            schedule_type: 定时发送类型。

        Returns:
            定时发送时间和发送模式；未开启时返回 None。
        """
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
                    schedule_time = plugin_config.get_default_schedule_time(
                        schedule.schedule_mode
                    )
                return schedule_time, schedule.schedule_mode

    async def add_schedule(
        self,
        target: Target,
        *,
        time: time | None = None,
        schedule_type: ScheduleType = ScheduleType.DAY,
        schedule_mode: ScheduleMode | None = None,
    ):
        """添加或更新定时发送配置。

        Args:
            target: Alconna 发送目标。
            time: 带时区信息的定时发送时间；为空时使用默认时间。
            schedule_type: 定时发送类型。
            schedule_mode: 定时发送模式；为空时使用配置默认模式。
        """
        schedule_mode = schedule_mode or plugin_config.wordcloud_default_schedule_mode
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
        """删除指定目标和类型的定时发送配置。

        Args:
            target: Alconna 发送目标。
            schedule_type: 定时发送类型。
        """
        async with get_session() as db_session:
            if schedule := await self.get_target_schedule(
                target, db_session, schedule_type
            ):
                await db_session.delete(schedule)
                await db_session.commit()


schedule_service = Scheduler()
