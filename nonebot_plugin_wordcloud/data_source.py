import asyncio
import concurrent.futures
import contextlib
import re
from functools import partial
from io import BytesIO
from random import choice

import numpy as np
from emoji import replace_emoji
from PIL import Image
from wordcloud import WordCloud

from .analyzer import analyse_message
from .config import global_config, plugin_config


def pre_precess(msg: str) -> str:
    """对消息文本进行预处理。

    Args:
        msg: 原始消息文本。

    Returns:
        去除 URL、零宽字符和 emoji 后的消息文本。
    """
    # 去除网址
    # https://stackoverflow.com/a/17773849/9212748
    url_regex = re.compile(
        r"(https?:\/\/(?:www\.|(?!www))[a-zA-Z0-9][a-zA-Z0-9-]+[a-zA-Z0-9]\.[^\s]{2,}|www\.[a-zA-Z0-9][a-zA-Z0-9-]"
        r"+[a-zA-Z0-9]\.[^\s]{2,}|https?:\/\/(?:www\.|(?!www))[a-zA-Z0-9]+\.[^\s]{2,}|www\.[a-zA-Z0-9]+\.[^\s]{2,})"
    )
    msg = url_regex.sub("", msg)

    # 去除 \u200b
    msg = re.sub(r"\u200b", "", msg)

    # 去除 emoji
    # https://github.com/carpedm20/emoji
    msg = replace_emoji(msg)

    return msg


def get_mask(key: str):
    """读取指定会话或默认的词云 mask。

    Args:
        key: 会话 mask key。

    Returns:
        mask 图片对应的 numpy 数组；没有可用 mask 时返回 None。
    """
    mask_path = plugin_config.get_mask_path(key)
    if mask_path.exists():
        return np.array(Image.open(mask_path))
    # 如果指定 mask 文件不存在，则尝试默认 mask
    default_mask_path = plugin_config.get_mask_path()
    if default_mask_path.exists():
        return np.array(Image.open(default_mask_path))


def _get_wordcloud(messages: list[str], mask_key: str) -> bytes | None:
    """在线程池中同步生成词云图片。

    Args:
        messages: 用于生成词云的消息文本列表。
        mask_key: 当前会话对应的 mask key。

    Returns:
        PNG 图片字节；数据不足或生成失败时返回 None。
    """
    # 过滤掉命令
    command_start = tuple(i for i in global_config.command_start if i)
    message = " ".join(m for m in messages if not m.startswith(command_start))
    # 预处理
    message = pre_precess(message)
    # 分析消息。分词，并统计词频
    frequency = analyse_message(message)
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
        image = wordcloud.generate_from_frequencies(frequency).to_image()
        image_bytes = BytesIO()
        image.save(image_bytes, format="PNG")
        return image_bytes.getvalue()


async def get_wordcloud(messages: list[str], mask_key: str) -> bytes | None:
    """异步生成词云图片。

    Args:
        messages: 用于生成词云的消息文本列表。
        mask_key: 当前会话对应的 mask key。

    Returns:
        PNG 图片字节；数据不足或生成失败时返回 None。
    """
    loop = asyncio.get_running_loop()
    pfunc = partial(_get_wordcloud, messages, mask_key)
    # 虽然不知道具体是哪里泄漏了，但是通过每次关闭线程池可以避免这个问题
    # https://github.com/he0119/nonebot-plugin-wordcloud/issues/99
    with concurrent.futures.ThreadPoolExecutor() as pool:
        return await loop.run_in_executor(pool, pfunc)
