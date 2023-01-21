from datetime import datetime, time
from typing import Optional, Union

from nonebot.adapters import Bot
from nonebot.adapters.onebot.v11 import Bot as BotV11
from nonebot.adapters.onebot.v11 import Message as MessageV11
from nonebot.adapters.onebot.v12 import Bot as BotV12
from nonebot.adapters.onebot.v12 import Message as MessageV12
from nonebot_plugin_apscheduler import scheduler

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
    """从 iso8601 格式字符串中获取时间，并包含时区信息"""
    if plugin_config.wordcloud_timezone:
        raw = datetime.fromisoformat(date_string)
        if raw.tzinfo:
            return raw.astimezone(ZoneInfo(plugin_config.wordcloud_timezone))
        else:
            return raw.replace(tzinfo=ZoneInfo(plugin_config.wordcloud_timezone))
    else:
        return datetime.fromisoformat(date_string).astimezone()


def time_astimezone(time: time, tz: Optional[ZoneInfo] = None) -> time:
    """将 time 对象转换为指定时区的 time 对象

    如果 tz 为 None，则转换为本地时区
    """
    local_time = datetime.combine(datetime.today(), time)
    return local_time.astimezone(tz).timetz()


def get_time_fromisoformat_with_timezone(time_string: str) -> time:
    """从 iso8601 格式字符串中获取时间，并包含时区信息"""
    if plugin_config.wordcloud_timezone:
        raw = time.fromisoformat(time_string)
        if raw.tzinfo:
            return time_astimezone(raw, ZoneInfo(plugin_config.wordcloud_timezone))
        else:
            return raw.replace(tzinfo=ZoneInfo(plugin_config.wordcloud_timezone))
    else:
        return time_astimezone(time.fromisoformat(time_string))


def get_time_with_scheduler_timezone(time: time) -> time:
    """获取转换到 APScheduler 时区的时间"""
    return time_astimezone(time, scheduler.timezone)


async def send_message(
    bot: Bot,
    message: Union[str, MessageV11, MessageV12],
    group_id: Optional[str] = None,
    guild_id: Optional[str] = None,
    channel_id: Optional[str] = None,
) -> None:
    if isinstance(bot, BotV11) and group_id:
        if isinstance(message, str):
            message = MessageV11(message)
        if isinstance(message, MessageV11):
            await bot.send_group_msg(group_id=int(group_id), message=message)
            return

    if isinstance(bot, BotV12):
        if isinstance(message, str):
            message = MessageV12(message)
        if isinstance(message, MessageV12):
            await bot.send_message(
                detail_type="group" if group_id else "channel",
                group_id=group_id,  # type: ignore
                guild_id=guild_id,  # type: ignore
                channel_id=channel_id,  # type: ignore
                message=message,
            )


def get_mask_key(
    platform: str,
    *,
    group_id: Optional[Union[str, int]] = None,
    guild_id: Optional[Union[str, int]] = None,
) -> str:
    if group_id:
        return f"{platform}-group-{group_id}"
    else:
        return f"{platform}-guild-{guild_id}"
