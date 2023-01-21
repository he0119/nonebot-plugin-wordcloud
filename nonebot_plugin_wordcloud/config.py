from datetime import datetime, time
from pathlib import Path
from typing import Optional

from nonebot import get_driver
from nonebot_plugin_datastore import get_plugin_data
from pydantic import BaseModel, Extra, root_validator

try:
    from zoneinfo import ZoneInfo
except ImportError:
    from backports.zoneinfo import ZoneInfo  # type: ignore

plugin_data = get_plugin_data()


class Config(BaseModel, extra=Extra.ignore):
    wordcloud_width: int = 1920
    wordcloud_height: int = 1200
    wordcloud_background_color: str = "black"
    wordcloud_colormap: str = "viridis"
    wordcloud_font_path: str
    wordcloud_stopwords_path: Optional[Path]
    wordcloud_userdict_path: Optional[Path]
    wordcloud_timezone: Optional[str]
    wordcloud_default_schedule_time: time
    """ 默认定时发送时间

    如果群内不单独设置则使用这个值，默认为晚上 10 点，时区为设定的时区
    """

    @root_validator(pre=True, allow_reuse=True)
    def set_default_values(cls, values):
        if not values.get("wordcloud_font_path"):
            values["wordcloud_font_path"] = str(
                Path(__file__).parent / "SourceHanSans.otf"
            )

        if wordcloud_default_schedule_time := values.get(
            "wordcloud_default_schedule_time"
        ):
            default_schedule_time = time.fromisoformat(wordcloud_default_schedule_time)
        else:
            default_schedule_time = time(22, 0, 0)

        if wordcloud_timezone := values.get("wordcloud_timezone"):
            default_schedule_time = default_schedule_time.replace(
                tzinfo=ZoneInfo(wordcloud_timezone)
            )
        else:
            default_schedule_time = default_schedule_time.replace(
                tzinfo=datetime.now().astimezone().tzinfo
            )
        values["wordcloud_default_schedule_time"] = default_schedule_time
        return values

    def get_mask_path(self, key: Optional[str] = None) -> Path:
        """获取 mask 文件路径"""
        if key is None:
            return plugin_data.data_dir / "mask.png"
        return plugin_data.data_dir / f"mask-{key}.png"


global_config = get_driver().config
plugin_config = Config.parse_obj(global_config)
