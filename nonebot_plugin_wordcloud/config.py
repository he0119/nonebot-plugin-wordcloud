from datetime import datetime, time
from pathlib import Path
from typing import Optional

from nonebot import get_driver
from nonebot_plugin_datastore import PluginData
from pydantic import BaseModel, Extra, root_validator

try:
    from zoneinfo import ZoneInfo
except ImportError:
    from backports.zoneinfo import ZoneInfo  # type: ignore

DATA = PluginData("wordcloud")

MASK_PATH = DATA.data_dir / "mask.png"


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

    如果群内不单独设置则使用这个值，默认为晚上 10 点
    """

    @root_validator(pre=True, allow_reuse=True)
    def set_default_values(cls, values):
        if "wordcloud_font_path" not in values:
            values["wordcloud_font_path"] = str(
                Path(__file__).parent / "SourceHanSans.otf"
            )
        if "wordcloud_timezone" in values:
            default_schedule_time = values["wordcloud_default_schedule_time"].replace(
                tzinfo=ZoneInfo(values["wordcloud_timezone"])
            )
        else:
            default_schedule_time = time(
                22, 0, 0, tzinfo=datetime.now().astimezone().tzinfo
            )
        values["wordcloud_default_schedule_time"] = default_schedule_time
        return values


global_config = get_driver().config
plugin_config = Config.parse_obj(global_config)
