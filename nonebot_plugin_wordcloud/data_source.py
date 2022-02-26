import re
from collections import Counter
from typing import List, Optional

import jieba
from emoji import replace_emoji  # type: ignore
from PIL.Image import Image
from wordcloud import WordCloud

from .config import global_config, plugin_config


def pre_precess(msg: str) -> str:
    """对消息进行预处理"""
    # 去除网址
    msg = re.sub(r"https?://[\w/:%#\$&\?\(\)~\.=\+\-]+", "", msg)

    # 去除 \u200b
    msg = re.sub(r"\u200b", "", msg)

    # 去除 emoji
    # https://github.com/carpedm20/emoji
    msg = replace_emoji(msg)

    return msg


def cut_message(msg: str) -> List[str]:
    """分词"""
    with plugin_config.wordcloud_stopwords_path.open("r", encoding="utf8") as f:
        stopwords = [word.strip() for word in f.readlines()]
    # 加载用户词典
    if plugin_config.wordcloud_userdict_path:
        jieba.load_userdict(str(plugin_config.wordcloud_userdict_path))
    words = jieba.lcut(msg)
    return [word.strip() for word in words if word.strip() not in stopwords]


def count_words(words: List[str]) -> Counter:
    """统计词频"""
    cnt = Counter()
    for word in words:
        if word:
            cnt[word] += 1
    return cnt


def get_wordcloud(messages: List[str]) -> Optional[Image]:
    # 过滤掉命令
    command_start = tuple([i for i in global_config.command_start if i])
    message = " ".join([m for m in messages if not m.startswith(command_start)])
    # 预处理
    message = pre_precess(message)
    # 分词
    words = cut_message(message)
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
        pass
