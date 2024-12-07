"""HanLP

https://github.com/hankcs/HanLP
"""

from functools import cache, reduce
from typing import Union

from hanlp_restful import HanLPClient

from .base import Tokenizer as BaseTokenizer

HanLP = HanLPClient(
    "https://www.hanlp.com/api",
    auth=None,  # type: ignore
    language="zh",
)  # auth不填则匿名，zh中文，mul多语种


class Tokenizer(BaseTokenizer):
    @cache
    def cut_msg(self, msg: str) -> Union[str, list[str]]:
        if not msg:
            return ""

        words = HanLP.tokenize(msg)
        return reduce(lambda x, y: x + y, words)

    def cut_msgs(self, msgs: list[str]) -> dict[str, float]:
        # TODO: 还应该支持用户词典和停用词表
        words = []
        for msg in msgs:
            words.extend(self.cut_msg(msg))
        return self._count_words(words)
