from datetime import datetime, time
from pathlib import Path
from typing import Any
from zoneinfo import ZoneInfo

from nonebot import get_driver, get_plugin_config
from nonebot.compat import model_validator
from nonebot_plugin_localstore import get_data_dir
from pydantic import BaseModel, Field

from .model import ScheduleMode

DATA_DIR = get_data_dir("nonebot_plugin_wordcloud")
DEFAULT_SCHEDULE_TIME_BY_MODE = {
    ScheduleMode.COMPLETE: time(0, 0, 0),
    ScheduleMode.PERIOD_END: time(23, 59, 59),
}


def _parse_schedule_mode(value: str | ScheduleMode | None) -> ScheduleMode:
    """解析默认定时发送模式配置。

    Args:
        value: 配置中读取到的模式值。

    Returns:
        规范化后的定时发送模式。
    """
    if value is None:
        return ScheduleMode.COMPLETE
    if isinstance(value, ScheduleMode):
        return value
    return ScheduleMode(value)


def _parse_schedule_time(value: str | time) -> time:
    """解析默认定时发送时间配置。

    Args:
        value: 配置中读取到的时间字符串或 time 对象。

    Returns:
        规范化后的 time 对象。
    """
    return time.fromisoformat(value) if isinstance(value, str) else value


def _set_timezone(schedule_time: time, timezone: str | None) -> time:
    """为定时发送时间设置时区。

    Args:
        schedule_time: 需要设置时区的时间。
        timezone: 配置指定的时区名称；为空时使用系统本地时区。

    Returns:
        带时区信息的定时发送时间。
    """
    return (
        schedule_time.replace(tzinfo=ZoneInfo(timezone))
        if timezone
        else schedule_time.replace(tzinfo=datetime.now().astimezone().tzinfo)
    )


class Config(BaseModel):
    wordcloud_width: int = 1920
    wordcloud_height: int = 1200
    wordcloud_background_color: str = "black"
    wordcloud_colormap: str | list[str] = "viridis"
    wordcloud_font_path: str
    wordcloud_stopwords_path: Path | None = None
    wordcloud_userdict_path: Path | None = None
    wordcloud_timezone: str | None = None
    wordcloud_default_schedule_mode: ScheduleMode = ScheduleMode.COMPLETE
    """默认定时发送模式"""
    wordcloud_default_schedule_time: time
    """ 默认定时发送时间

    如果群内不单独设置则使用这个值，默认为根据定时发送模式确定，时区为设定的时区
    """
    wordcloud_default_schedule_time_override: bool = Field(default=False, exclude=True)
    wordcloud_options: dict[str, Any] = {}
    wordcloud_exclude_user_ids: set[str] = set()
    """排除的用户 ID 列表（全局，不区分平台）"""
    wordcloud_reply_message: bool = False
    """是否回复消息，默认不回复"""
    wordcloud_default_personal: bool = False
    """是否默认个人词云，默认为群组词云"""

    @model_validator(mode="before")
    def set_default_values(cls, values):
        """填充配置默认值并规范化定时发送配置。

        Args:
            values: Pydantic 校验前的原始配置字典。

        Returns:
            填充默认值后的配置字典。
        """
        if not values.get("wordcloud_font_path"):
            values["wordcloud_font_path"] = str(
                Path(__file__).parent / "SourceHanSans.otf"
            )

        default_schedule_mode = _parse_schedule_mode(
            values.get("wordcloud_default_schedule_mode")
        )
        values["wordcloud_default_schedule_mode"] = default_schedule_mode

        wordcloud_timezone = values.get("wordcloud_timezone")
        default_schedule_time_override = bool(
            values.get("wordcloud_default_schedule_time")
        )
        if wordcloud_default_schedule_time := values.get(
            "wordcloud_default_schedule_time"
        ):
            default_schedule_time = _set_timezone(
                _parse_schedule_time(wordcloud_default_schedule_time),
                wordcloud_timezone,
            )
        else:
            default_schedule_time = _set_timezone(
                DEFAULT_SCHEDULE_TIME_BY_MODE[default_schedule_mode],
                wordcloud_timezone,
            )

        values["wordcloud_default_schedule_time_override"] = (
            default_schedule_time_override
        )
        values["wordcloud_default_schedule_time"] = default_schedule_time
        return values

    def get_default_schedule_time(
        self, schedule_mode: ScheduleMode | None = None
    ) -> time:
        """获取指定发送模式对应的默认定时发送时间。

        Args:
            schedule_mode: 需要查询的发送模式；为空时使用配置中的默认模式。

        Returns:
            对应发送模式的默认定时发送时间。
        """
        if self.wordcloud_default_schedule_time_override:
            return self.wordcloud_default_schedule_time
        return _set_timezone(
            DEFAULT_SCHEDULE_TIME_BY_MODE[
                schedule_mode or self.wordcloud_default_schedule_mode
            ],
            self.wordcloud_timezone,
        )

    def get_mask_path(self, key: str | None = None) -> Path:
        """获取 mask 文件路径。

        Args:
            key: 会话 mask key；为空时返回全局默认 mask 路径。

        Returns:
            mask 图片的存储路径。
        """
        if key is None:
            return DATA_DIR / "mask.png"
        return DATA_DIR / f"mask-{key}.png"


global_config = get_driver().config
plugin_config = get_plugin_config(Config)
