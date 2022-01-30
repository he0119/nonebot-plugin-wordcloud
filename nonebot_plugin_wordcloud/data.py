import re
from collections import Counter
from typing import List, Optional

import jieba
from nonebot.log import logger
from PIL.Image import Image
from wordcloud import WordCloud

from .config import global_config, plugin_config
from .model import GroupMessage


def pre_precess(msg: str) -> str:
    """对消息进行预处理"""
    # 去除网址
    msg = re.sub(r"https?://[\w/:%#\$&\?\(\)~\.=\+\-]+", "", msg)

    # 去除 \u200b
    msg = re.sub(r"\u200b", "", msg)

    # 去除 emoji
    # https://stackoverflow.com/questions/33404752/removing-emojis-from-a-string-in-python
    emoji_pattern = re.compile(
        "["
        u"\U0001F600-\U0001F64F"  # emoticons
        u"\U0001F300-\U0001F5FF"  # symbols & pictographs
        u"\U0001F680-\U0001F6FF"  # transport & map symbols
        u"\U0001F1E0-\U0001F1FF"  # flags (iOS)
        "]+",
        flags=re.UNICODE,
    )
    msg = emoji_pattern.sub(r"", msg)  # no emoji

    return msg


def count_words(words: List[str]) -> Counter:
    """统计词频"""
    with plugin_config.wordcloud_stopwords_path.open("r", encoding="utf8") as f:
        stopwords = [word.strip() for word in f.readlines()]

    cnt = Counter()
    for word in words:
        word = word.strip()
        if word and word not in stopwords:
            cnt[word] += 1
    return cnt


def get_wordcloud(messages: List[GroupMessage]) -> Optional[Image]:
    words = []
    # 过滤掉命令
    command_start = tuple([i for i in global_config.command_start if i])
    msgs = " ".join(
        [m.message for m in messages if not m.message.startswith(command_start)]
    )
    # 分词
    msgs = pre_precess(msgs)
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
