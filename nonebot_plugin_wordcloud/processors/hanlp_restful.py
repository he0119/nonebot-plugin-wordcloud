"""HanLP

https://github.com/hankcs/HanLP
"""

from functools import cache
from typing import Union, cast

from hanlp_restful import HanLPClient

from . import Processor as BaseProcessor

HanLP = HanLPClient(
    "https://www.hanlp.com/api",
    auth=None,  # type: ignore
    language="zh",
)  # auth不填则匿名，zh中文，mul多语种


class Processor(BaseProcessor):
    @cache
    def process_msg(self, msg: str) -> Union[str, list[str]]:
        return cast(list[str], HanLP.tokenize(msg))
