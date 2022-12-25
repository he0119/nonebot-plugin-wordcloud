from datetime import datetime

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
        return datetime.fromisoformat(date_string).astimezone(
            ZoneInfo(plugin_config.wordcloud_timezone)
        )
    else:
        return datetime.fromisoformat(date_string).astimezone()
