import asyncio
import concurrent.futures
import contextlib
from collections.abc import Iterable
from functools import partial
from io import BytesIO
from random import choice
from typing import Optional

import numpy as np
from nonebot.utils import resolve_dot_notation
from PIL import Image
from wordcloud import WordCloud

from .config import global_config, plugin_config
from .processors import Processor

MSGS_PROCESSORS: list[Processor] = [
    resolve_dot_notation(
        processor,
        "Processor",
        "nonebot_plugin_wordcloud.processors.",
    )()
    for processor in plugin_config.worodcloud_msgs_processors
]


def get_mask(key: str):
    """获取 mask"""
    mask_path = plugin_config.get_mask_path(key)
    if mask_path.exists():
        return np.array(Image.open(mask_path))
    # 如果指定 mask 文件不存在，则尝试默认 mask
    default_mask_path = plugin_config.get_mask_path()
    if default_mask_path.exists():
        return np.array(Image.open(default_mask_path))


def get_frequencies(words: Iterable[str]) -> dict[str, float]:
    """获取词频"""
    stopwords = set()
    if plugin_config.wordcloud_stopwords_path:
        with open(plugin_config.wordcloud_stopwords_path, encoding="utf8") as f:
            stopwords = set(f.read().splitlines())

    frequencies: dict[str, float] = {}
    for word in words:
        if word in stopwords:
            continue
        frequencies[word] = frequencies.get(word, 0) + 1
    return frequencies


def analyse_messages(msgs: Iterable[str]) -> dict[str, float]:
    """分析消息，获取词频"""
    # 过滤掉命令
    command_start = tuple(i for i in global_config.command_start if i)
    msgs = (m for m in msgs if not m.startswith(command_start))
    # 处理消息
    for processor in MSGS_PROCESSORS:
        msgs = processor.process_msgs(msgs)
        if isinstance(msgs, dict):
            return msgs
    # 统计消息频率
    frequencies = get_frequencies(msgs)
    return frequencies


def _get_wordcloud(msgs: list[str], mask_key: str) -> Optional[bytes]:
    frequencies = analyse_messages(msgs)
    # 词云参数
    wordcloud_options = {}
    wordcloud_options.update(plugin_config.wordcloud_options)
    wordcloud_options.setdefault("font_path", str(plugin_config.wordcloud_font_path))
    wordcloud_options.setdefault("width", plugin_config.wordcloud_width)
    wordcloud_options.setdefault("height", plugin_config.wordcloud_height)
    wordcloud_options.setdefault(
        "background_color", plugin_config.wordcloud_background_color
    )
    # 如果 colormap 是列表，则随机选择一个
    colormap = (
        plugin_config.wordcloud_colormap
        if isinstance(plugin_config.wordcloud_colormap, str)
        else choice(plugin_config.wordcloud_colormap)
    )
    wordcloud_options.setdefault("colormap", colormap)
    wordcloud_options.setdefault("mask", get_mask(mask_key))
    with contextlib.suppress(ValueError):
        wordcloud = WordCloud(**wordcloud_options)
        image = wordcloud.generate_from_frequencies(frequencies).to_image()
        image_bytes = BytesIO()
        image.save(image_bytes, format="PNG")
        return image_bytes.getvalue()


async def get_wordcloud(msgs: list[str], mask_key: str) -> Optional[bytes]:
    loop = asyncio.get_running_loop()
    pfunc = partial(_get_wordcloud, msgs, mask_key)
    # 虽然不知道具体是哪里泄漏了，但是通过每次关闭线程池可以避免这个问题
    # https://github.com/he0119/nonebot-plugin-wordcloud/issues/99
    with concurrent.futures.ThreadPoolExecutor() as pool:
        return await loop.run_in_executor(pool, pfunc)
