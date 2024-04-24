from datetime import datetime, time
from pathlib import Path
from typing import Any, Optional, Union
from zoneinfo import ZoneInfo

from nonebot import get_driver, get_plugin_config
from nonebot_plugin_localstore import get_data_dir
from pydantic import BaseModel

from .compat import model_validator

DATA_DIR = get_data_dir("nonebot_plugin_wordcloud")


class Config(BaseModel):
    wordcloud_width: int = 1920
    wordcloud_height: int = 1200
    wordcloud_background_color: str = "black"
    wordcloud_colormap: Union[str, list[str]] = "viridis"
    wordcloud_font_path: str
    wordcloud_stopwords_path: Optional[Path] = None
    wordcloud_userdict_path: Optional[Path] = None
    wordcloud_timezone: Optional[str] = None
    wordcloud_default_schedule_time: time
    """ 默认定时发送时间

    如果群内不单独设置则使用这个值，默认为晚上 10 点，时区为设定的时区
    """
    wordcloud_options: dict[str, Any] = {}
    wordcloud_exclude_user_ids: set[str] = set()
    """排除的用户 ID 列表（全局，不区分平台）"""

    @model_validator(mode="before")
    def set_default_values(cls, values):
        if not values.get("wordcloud_font_path"):
            values["wordcloud_font_path"] = str(
                Path(__file__).parent / "SourceHanSans.otf"
            )

        default_schedule_time = (
            time.fromisoformat(wordcloud_default_schedule_time)
            if (
                wordcloud_default_schedule_time := values.get(
                    "wordcloud_default_schedule_time"
                )
            )
            else time(22, 0, 0)
        )

        default_schedule_time = (
            default_schedule_time.replace(tzinfo=ZoneInfo(wordcloud_timezone))
            if (wordcloud_timezone := values.get("wordcloud_timezone"))
            else default_schedule_time.replace(
                tzinfo=datetime.now().astimezone().tzinfo
            )
        )
        values["wordcloud_default_schedule_time"] = default_schedule_time
        return values

    def get_mask_path(self, key: Optional[str] = None) -> Path:
        """获取 mask 文件路径"""
        if key is None:
            return DATA_DIR / "mask.png"
        return DATA_DIR / f"mask-{key}.png"


global_config = get_driver().config
plugin_config = get_plugin_config(Config)
