from datetime import datetime, time
from typing import Optional

from nonebot_plugin_apscheduler import scheduler
from nonebot_plugin_saa import (
    PlatformTarget,
    TargetFeishuGroup,
    TargetFeishuPrivate,
    TargetKaiheilaChannel,
    TargetKaiheilaPrivate,
    TargetOB12Unknow,
    TargetQQGroup,
    TargetQQGuildChannel,
    TargetQQGuildDirect,
    TargetQQPrivate,
)
from nonebot_plugin_session import Session, SessionLevel
from nonebot_plugin_session.const import SupportedPlatform

from .config import plugin_config

try:
    from zoneinfo import ZoneInfo
except ImportError:
    from backports.zoneinfo import ZoneInfo  # type: ignore


def get_datetime_now_with_timezone() -> datetime:
    """获取当前时间，并包含时区信息"""
    if plugin_config.wordcloud_timezone:
        return datetime.now(ZoneInfo(plugin_config.wordcloud_timezone))
    else:
        return datetime.now().astimezone()


def get_datetime_fromisoformat_with_timezone(date_string: str) -> datetime:
    """从 ISO-8601 格式字符串中获取时间，并包含时区信息"""
    if not plugin_config.wordcloud_timezone:
        return datetime.fromisoformat(date_string).astimezone()
    raw = datetime.fromisoformat(date_string)
    return (
        raw.astimezone(ZoneInfo(plugin_config.wordcloud_timezone))
        if raw.tzinfo
        else raw.replace(tzinfo=ZoneInfo(plugin_config.wordcloud_timezone))
    )


def time_astimezone(time: time, tz: Optional[ZoneInfo] = None) -> time:
    """将 time 对象转换为指定时区的 time 对象

    如果 tz 为 None，则转换为本地时区
    """
    local_time = datetime.combine(datetime.today(), time)
    return local_time.astimezone(tz).timetz()


def get_time_fromisoformat_with_timezone(time_string: str) -> time:
    """从 iso8601 格式字符串中获取时间，并包含时区信息"""
    if not plugin_config.wordcloud_timezone:
        return time_astimezone(time.fromisoformat(time_string))
    raw = time.fromisoformat(time_string)
    return (
        time_astimezone(raw, ZoneInfo(plugin_config.wordcloud_timezone))
        if raw.tzinfo
        else raw.replace(tzinfo=ZoneInfo(plugin_config.wordcloud_timezone))
    )


def get_time_with_scheduler_timezone(time: time) -> time:
    """获取转换到 APScheduler 时区的时间"""
    return time_astimezone(time, scheduler.timezone)


def target_to_session(target: PlatformTarget) -> Session:
    """将 PlatformTarget 转换为 Session"""
    bot_id = "saa"
    bot_type = "saa"

    if isinstance(target, TargetQQPrivate):
        return Session(
            bot_id=bot_id,
            bot_type=bot_type,
            platform=SupportedPlatform.qq,
            level=SessionLevel.LEVEL1,
            id1=str(target.user_id),
            id2=None,
            id3=None,
        )
    elif isinstance(target, TargetQQGroup):
        return Session(
            bot_id=bot_id,
            bot_type=bot_type,
            platform=SupportedPlatform.qq,
            level=SessionLevel.LEVEL2,
            id1=None,
            id2=str(target.group_id),
            id3=None,
        )
    elif isinstance(target, TargetQQGuildDirect):
        return Session(
            bot_id=bot_id,
            bot_type=bot_type,
            platform=SupportedPlatform.qqguild,
            level=SessionLevel.LEVEL1,
            id1=str(target.recipient_id),
            id2=None,
            id3=str(target.source_guild_id),
        )
    elif isinstance(target, TargetQQGuildChannel):
        return Session(
            bot_id=bot_id,
            bot_type=bot_type,
            platform=SupportedPlatform.qqguild,
            level=SessionLevel.LEVEL3,
            id1=None,
            id2=str(target.channel_id),
            id3=None,
        )
    elif isinstance(target, TargetKaiheilaPrivate):
        return Session(
            bot_id=bot_id,
            bot_type=bot_type,
            platform=SupportedPlatform.kaiheila,
            level=SessionLevel.LEVEL1,
            id1=str(target.user_id),
            id2=None,
            id3=None,
        )
    elif isinstance(target, TargetKaiheilaChannel):
        return Session(
            bot_id=bot_id,
            bot_type=bot_type,
            platform=SupportedPlatform.kaiheila,
            level=SessionLevel.LEVEL3,
            id1=None,
            id2=str(target.channel_id),
            id3=None,
        )
    elif isinstance(target, TargetFeishuPrivate):
        return Session(
            bot_id=bot_id,
            bot_type=bot_type,
            platform=SupportedPlatform.feishu,
            level=SessionLevel.LEVEL1,
            id1=str(target.open_id),
            id2=None,
            id3=None,
        )
    elif isinstance(target, TargetFeishuGroup):
        return Session(
            bot_id=bot_id,
            bot_type=bot_type,
            platform=SupportedPlatform.feishu,
            level=SessionLevel.LEVEL2,
            id1=None,
            id2=str(target.chat_id),
            id3=None,
        )
    elif isinstance(target, TargetOB12Unknow):
        if target.detail_type == "private":
            return Session(
                bot_id=bot_id,
                bot_type=bot_type,
                platform=target.platform,
                level=SessionLevel.LEVEL1,
                id1=str(target.user_id),
                id2=None,
                id3=None,
            )
        elif target.detail_type == "group":
            return Session(
                bot_id=bot_id,
                bot_type=bot_type,
                platform=target.platform,
                level=SessionLevel.LEVEL2,
                id1=None,
                id2=str(target.group_id),
                id3=None,
            )
        else:
            return Session(
                bot_id=bot_id,
                bot_type=bot_type,
                platform=target.platform,
                level=SessionLevel.LEVEL3,
                id1=None,
                id2=target.channel_id,
                id3=target.guild_id,
            )

    raise ValueError(f"不支持的 PlatformTarget 类型：{target}")
