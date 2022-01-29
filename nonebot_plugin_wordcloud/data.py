from collections import Counter
from typing import Optional

import jieba
from nonebot.log import logger
from PIL.Image import Image
from wordcloud import WordCloud

from .config import global_config, plugin_config
from .model import GroupMessage


def count_words(words: list[str]) -> Counter:
    """统计词频"""
    with plugin_config.wordcloud_stopwords_path.open("r", encoding="utf8") as f:
        stopwords = [word.strip() for word in f.readlines()]

    cnt = Counter()
    for word in words:
        word = word.strip()
        if word and word not in stopwords:
            cnt[word] += 1
    return cnt


async def get_wordcloud(messages: list[GroupMessage]) -> Optional[Image]:
    words = []
    # 过滤掉命令
    command_start = tuple([i for i in global_config.command_start if i])
    msgs = " ".join(
        [m.message for m in messages if not m.message.startswith(command_start)]
    )
    # 分词
    words = jieba.lcut(msgs, cut_all=True)
    # 统计词频
    frequency = count_words(words)
    try:
        wordcloud = WordCloud(
            font_path=str(plugin_config.wordcloud_font_path),
            width=plugin_config.wordcloud_width,
            height=plugin_config.wordcloud_height,
            background_color=plugin_config.wordcloud_background_color,
        )
        image = wordcloud.generate_from_frequencies(frequency).to_image()
        return image
    except ValueError as e:
        logger.error(e)
