import asyncio
import concurrent.futures
import multiprocessing
import platform
import re
from functools import partial
from io import BytesIO
from typing import Dict, List, Optional

import jieba
import jieba.analyse
import numpy as np
from emoji import replace_emoji
from PIL import Image
from wordcloud import WordCloud

from .config import global_config, plugin_config


def pre_precess(msg: str) -> str:
    """对消息进行预处理"""
    # 去除网址
    # https://stackoverflow.com/a/17773849/9212748
    msg = re.sub(
        r"(https?:\/\/(?:www\.|(?!www))[a-zA-Z0-9][a-zA-Z0-9-]+[a-zA-Z0-9]\.[^\s]{2,}|www\.[a-zA-Z0-9][a-zA-Z0-9-]+[a-zA-Z0-9]\.[^\s]{2,}|https?:\/\/(?:www\.|(?!www))[a-zA-Z0-9]+\.[^\s]{2,}|www\.[a-zA-Z0-9]+\.[^\s]{2,})",
        "",
        msg,
    )

    # 去除 \u200b
    msg = re.sub(r"\u200b", "", msg)

    # 去除 emoji
    # https://github.com/carpedm20/emoji
    msg = replace_emoji(msg)

    return msg


def analyse_message(msg: str) -> Dict[str, float]:
    """分析消息

    分词，并统计词频
    """
    # 设置停用词表
    if plugin_config.wordcloud_stopwords_path:
        jieba.analyse.set_stop_words(plugin_config.wordcloud_stopwords_path)
    # 加载用户词典
    if plugin_config.wordcloud_userdict_path:
        jieba.load_userdict(str(plugin_config.wordcloud_userdict_path))
    # 基于 TF-IDF 算法的关键词抽取
    # 返回所有关键词，因为设置了数量其实也只是 tags[:topK]，不如交给词云库处理
    words = jieba.analyse.extract_tags(msg, topK=0, withWeight=True)
    return {word: weight for word, weight in words}


def get_mask(key: Optional[str] = None):
    """获取 mask"""
    mask_path = plugin_config.get_mask_path(key)
    if mask_path.exists():
        return np.array(Image.open(mask_path))


def _get_wordcloud(
    messages: List[str], mask_key: Optional[str] = None
) -> Optional[BytesIO]:
    # 过滤掉命令
    command_start = tuple([i for i in global_config.command_start if i])
    message = " ".join([m for m in messages if not m.startswith(command_start)])
    # 预处理
    message = pre_precess(message)
    # 分析消息。分词，并统计词频
    frequency = analyse_message(message)
    try:
        wordcloud = WordCloud(
            font_path=str(plugin_config.wordcloud_font_path),
            width=plugin_config.wordcloud_width,
            height=plugin_config.wordcloud_height,
            background_color=plugin_config.wordcloud_background_color,
            colormap=plugin_config.wordcloud_colormap,
            mask=get_mask(mask_key),
        )
        image = wordcloud.generate_from_frequencies(frequency).to_image()
        image_bytes = BytesIO()
        image.save(image_bytes, format="PNG")
        return image_bytes
    except ValueError:
        pass


async def get_wordcloud(
    messages: List[str], mask_key: Optional[str] = None
) -> Optional[BytesIO]:
    loop = asyncio.get_running_loop()
    pfunc = partial(_get_wordcloud, messages, mask_key)
    if platform.system() == "Windows":
        return await loop.run_in_executor(None, pfunc)
    else:
        with concurrent.futures.ProcessPoolExecutor(
            mp_context=multiprocessing.get_context("fork")
        ) as pool:
            return await loop.run_in_executor(pool, pfunc)
