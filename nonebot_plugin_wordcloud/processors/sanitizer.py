"""清除多余字符"""

import re
from functools import cache
from typing import Union

from emoji import replace_emoji

from . import Processor as BaseProcessor

# https://stackoverflow.com/a/17773849/9212748
URL_REGEX = re.compile(
    r"(https?:\/\/(?:www\.|(?!www))[a-zA-Z0-9][a-zA-Z0-9-]+[a-zA-Z0-9]\.[^\s]{2,}|www\.[a-zA-Z0-9][a-zA-Z0-9-]"
    r"+[a-zA-Z0-9]\.[^\s]{2,}|https?:\/\/(?:www\.|(?!www))[a-zA-Z0-9]+\.[^\s]{2,}|www\.[a-zA-Z0-9]+\.[^\s]{2,})"
)


class Processor(BaseProcessor):
    @cache
    def process_msg(self, msg: str) -> Union[str, list[str]]:
        # 去除网址
        msg = URL_REGEX.sub("", msg)

        # 去除 \u200b
        msg = re.sub(r"\u200b", "", msg)

        # 去除 emoji
        # https://github.com/carpedm20/emoji
        msg = replace_emoji(msg)

        return msg
