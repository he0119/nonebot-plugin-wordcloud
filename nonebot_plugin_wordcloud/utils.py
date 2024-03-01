import contextlib
from datetime import datetime, time, tzinfo
from typing import Optional
from zoneinfo import ZoneInfo

from nonebot.compat import model_dump
from nonebot.matcher import Matcher
from nonebot.params import Depends
from nonebot.permission import SUPERUSER
from nonebot_plugin_apscheduler import scheduler
from nonebot_plugin_saa import PlatformTarget, get_target
from nonebot_plugin_session import Session, SessionLevel, extract_session

from .config import plugin_config


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


def time_astimezone(time: time, tz: Optional[tzinfo] = None) -> time:
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


def admin_permission():
    permission = SUPERUSER
    with contextlib.suppress(ImportError):
        from nonebot.adapters.onebot.v11.permission import GROUP_ADMIN, GROUP_OWNER

        permission = permission | GROUP_ADMIN | GROUP_OWNER

    return permission


def get_mask_key(target: PlatformTarget = Depends(get_target)) -> str:
    """获取 mask key

    例如：
    qq_group-group_id=10000
    qq_guild_channel-channel_id=100000
    """
    mask_keys = [f"{target.platform_type.name}"]
    mask_keys.extend(
        [
            f"{key}={value}"
            for key, value in model_dump(target, exclude={"platform_type"}).items()
            if value is not None
        ]
    )
    return "-".join(mask_keys)


async def ensure_group(matcher: Matcher, session: Session = Depends(extract_session)):
    """确保在群组中使用"""
    if session.level not in [SessionLevel.LEVEL2, SessionLevel.LEVEL3]:
        await matcher.finish("请在群组中使用！")
