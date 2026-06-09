from __future__ import annotations

from collections import Counter
from typing import TYPE_CHECKING, Any, Protocol

from nonebot import logger

from .config import plugin_config

if TYPE_CHECKING:
    from collections.abc import Iterable, Mapping
    from pathlib import Path


class WordAnalyzer(Protocol):
    """分析消息文本并返回词云使用的词权重。"""

    def analyse(self, text: str) -> dict[str, float]: ...


class JiebaAnalyzer:
    def __init__(
        self,
        options: Mapping[str, Any],
        stopwords_path: Path | None,
        userdict_path: Path | None,
    ) -> None:
        self.options = dict(options)
        self.stopwords_path = stopwords_path
        self.userdict_path = userdict_path

    def analyse(self, text: str) -> dict[str, float]:
        import jieba
        import jieba.analyse

        if self.stopwords_path:
            jieba.analyse.set_stop_words(str(self.stopwords_path))
        if self.userdict_path:
            jieba.load_userdict(str(self.userdict_path))

        options = dict(self.options)
        top_k = options.pop("top_k", options.pop("topK", 0))
        options.pop("withWeight", None)
        words = jieba.analyse.extract_tags(text, topK=top_k, withWeight=True, **options)
        return dict(words)


class RjiebaAnalyzer:
    def __init__(
        self,
        options: Mapping[str, Any],
        stopwords: set[str],
        userdict_path: Path | None,
    ) -> None:
        self.options = dict(options)
        self.stopwords = stopwords
        self.userdict_path = userdict_path

    def analyse(self, text: str) -> dict[str, float]:
        try:
            import rjieba
        except ImportError as e:
            raise RuntimeError(
                "当前配置使用 rjieba 分析后端，但未安装 rjieba。"
                "请安装 nonebot-plugin-wordcloud[rjieba]。"
            ) from e

        if self.userdict_path:
            logger.warning(
                "rjieba 分析后端暂不支持 wordcloud_userdict_path，已忽略用户词典"
            )

        segmenter = rjieba.Jieba()
        mode = str(self.options.get("mode", "default")).lower()
        hmm = bool(self.options.get("hmm", True))
        if mode == "all":
            words = segmenter.cut_all(text)
        elif mode == "search":
            words = segmenter.cut_for_search(text, hmm)
        else:
            words = segmenter.cut(text, hmm)
        return _count_words(words, self.stopwords)


def get_word_analyzer() -> WordAnalyzer:
    analyzer = plugin_config.wordcloud_analyzer
    stopwords_path = plugin_config.wordcloud_stopwords_path
    userdict_path = plugin_config.wordcloud_userdict_path
    if analyzer == "jieba":
        return JiebaAnalyzer(
            plugin_config.wordcloud_analyzer_options,
            stopwords_path,
            userdict_path,
        )

    stopwords = _load_word_file(stopwords_path)
    if analyzer == "rjieba":
        return RjiebaAnalyzer(
            plugin_config.wordcloud_analyzer_options,
            stopwords,
            userdict_path,
        )
    raise ValueError(f"不支持的词云分析后端: {analyzer}")


def analyse_message(msg: str) -> dict[str, float]:
    """分析消息文本并统计关键词权重。"""
    return get_word_analyzer().analyse(msg)


def _count_words(
    words: Iterable[str],
    stopwords: set[str],
) -> dict[str, float]:
    counter = Counter(word for word in _iter_valid_words(words, stopwords))
    return {word: float(count) for word, count in counter.items()}


def _iter_valid_words(
    words: Iterable[str],
    stopwords: set[str],
) -> Iterable[str]:
    for word in words:
        word = word.strip()
        if (
            word
            and len(word) >= plugin_config.wordcloud_min_word_length
            and word not in stopwords
            and any(char.isalnum() for char in word)
        ):
            yield word


def _load_word_file(path: Path | None) -> set[str]:
    if not path:
        return set()
    with path.open(encoding="utf8") as f:
        return {
            line.split()[0].strip()
            for line in f
            if line.strip() and not line.lstrip().startswith("#")
        }
