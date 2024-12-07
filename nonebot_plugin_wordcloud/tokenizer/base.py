import abc
from collections import Counter
from functools import cache
from typing import Union


class Tokenizer(abc.ABC):
    @abc.abstractmethod
    @cache
    def cut_msg(self, msg: str) -> Union[str, list[str]]:
        """分词"""
        raise NotImplementedError

    @abc.abstractmethod
    def cut_msgs(self, msgs: list[str]) -> dict[str, float]:
        """批量分词

        返回值为词频字典，key 为词，value 为词频
        """
        raise NotImplementedError

    def _count_words(self, words: list[str]) -> dict[str, float]:
        """统计词频"""
        counts = Counter(words)
        return dict(counts.items())
