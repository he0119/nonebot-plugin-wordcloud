"""结巴分词

https://github.com/fxsjy/jieba
"""

from collections.abc import Iterable
from functools import cache
from typing import Union

import jieba
import jieba.analyse

from ..config import plugin_config
from . import Processor as BaseProcessor


class Processor(BaseProcessor):
    @cache
    def process_msg(self, msg: str) -> Union[str, list[str]]:
        return msg

    def process_msgs(self, msgs: Iterable[str]) -> dict[str, float]:
        # 将字符拼接在一起，模拟以前的行为
        concat_msg = " ".join(msgs)

        # 设置停用词表
        if plugin_config.wordcloud_stopwords_path:
            jieba.analyse.set_stop_words(plugin_config.wordcloud_stopwords_path)

        # 加载用户词典
        if plugin_config.wordcloud_userdict_path:
            jieba.load_userdict(str(plugin_config.wordcloud_userdict_path))

        # 基于 TF-IDF 算法的关键词抽取
        # 返回所有关键词，因为设置了数量其实也只是 tags[:topK]，不如交给词云库处理
        words = jieba.analyse.extract_tags(concat_msg, topK=0, withWeight=True)
        return dict(words)
