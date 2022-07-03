from pathlib import Path
from typing import Optional

from nonebot import get_driver
from pydantic import BaseModel, Extra, root_validator


class Config(BaseModel, extra=Extra.ignore):
    wordcloud_width: int = 1920
    wordcloud_height: int = 1200
    wordcloud_background_color: str = "black"
    wordcloud_colormap: str = "viridis"
    wordcloud_font_path: str
    wordcloud_stopwords_path: Optional[Path]
    wordcloud_userdict_path: Optional[Path]
    wordcloud_timezone: Optional[str]

    @root_validator(pre=True, allow_reuse=True)
    def set_default_values(cls, values):
        if "wordcloud_font_path" not in values:
            values["wordcloud_font_path"] = str(
                Path(__file__).parent / "SourceHanSans.otf"
            )
        return values


global_config = get_driver().config
plugin_config = Config.parse_obj(global_config)
