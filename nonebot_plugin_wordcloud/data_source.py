import asyncio
import concurrent.futures
import contextlib
import re
from functools import partial
from io import BytesIO
from random import choice
from typing import Optional

import numpy as np
from emoji import replace_emoji
from nonebot.utils import resolve_dot_notation
from PIL import Image
from wordcloud import WordCloud

from .config import global_config, plugin_config
from .tokenizer import Tokenizer

tokenizer: Tokenizer = resolve_dot_notation(
    plugin_config.worodcloud_tokenizer,
    "Tokenizer",
    "nonebot_plugin_wordcloud.tokenizer.",
)()


def pre_precess(msg: str) -> str:
    """对消息进行预处理"""
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
    """获取 mask"""
    mask_path = plugin_config.get_mask_path(key)
    if mask_path.exists():
        return np.array(Image.open(mask_path))
    # 如果指定 mask 文件不存在，则尝试默认 mask
    default_mask_path = plugin_config.get_mask_path()
    if default_mask_path.exists():
        return np.array(Image.open(default_mask_path))


def _get_wordcloud(messages: list[str], mask_key: str) -> Optional[bytes]:
    # 过滤掉命令
    command_start = tuple(i for i in global_config.command_start if i)
    message = " ".join(m for m in messages if not m.startswith(command_start))
    # 预处理
    message = pre_precess(message)
    # 分析消息。分词，并统计词频
    frequency = tokenizer.cut_msgs([message])
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


async def get_wordcloud(messages: list[str], mask_key: str) -> Optional[bytes]:
    loop = asyncio.get_running_loop()
    pfunc = partial(_get_wordcloud, messages, mask_key)
    # 虽然不知道具体是哪里泄漏了，但是通过每次关闭线程池可以避免这个问题
    # https://github.com/he0119/nonebot-plugin-wordcloud/issues/99
    with concurrent.futures.ThreadPoolExecutor() as pool:
        return await loop.run_in_executor(pool, pfunc)
