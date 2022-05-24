from pathlib import Path
from typing import Optional

from nonebot import get_driver
from pydantic import BaseModel, Extra


class Config(BaseModel, extra=Extra.ignore):
    wordcloud_width: int = 1920
    wordcloud_height: int = 1200
    wordcloud_background_color: str = "black"
    wordcloud_font_path: str = str(Path(__file__).parent / "SourceHanSans.otf")
    wordcloud_stopwords_path: Optional[Path]
    wordcloud_userdict_path: Optional[Path]
    wordcloud_timezone: Optional[str]


global_config = get_driver().config
plugin_config = Config.parse_obj(global_config)
