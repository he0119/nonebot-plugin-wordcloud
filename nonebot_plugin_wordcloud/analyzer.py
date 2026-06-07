from __future__ import annotations

import json
from collections import Counter
from collections.abc import Iterable, Mapping
from functools import lru_cache
from typing import TYPE_CHECKING, Any, Protocol, cast

from nonebot import logger

from .config import plugin_config

if TYPE_CHECKING:
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
        min_word_length: int,
        userdict_path: Path | None,
    ) -> None:
        self.options = dict(options)
        self.stopwords = stopwords
        self.min_word_length = min_word_length
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
        return _count_words(words, self.stopwords, self.min_word_length)


class HanlpAnalyzer:
    def __init__(
        self,
        options: Mapping[str, Any],
        stopwords: set[str],
        min_word_length: int,
        userdict_path: Path | None,
    ) -> None:
        self.options = dict(options)
        self.stopwords = stopwords
        self.min_word_length = min_word_length
        self.userdict_path = userdict_path
        self.tokenizer = _load_hanlp_tokenizer(
            _get_hanlp_model_name(self.options),
            _dump_options(cast("dict[str, Any]", self.options.get("load_kwargs", {}))),
        )

    def analyse(self, text: str) -> dict[str, float]:
        _set_hanlp_userdict(self.tokenizer, self.userdict_path)
        tokens = _extract_hanlp_tokens(
            self.tokenizer(text),
            str(self.options.get("output_key", "")) or None,
        )
        return _count_words(tokens, self.stopwords, self.min_word_length)


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
    min_word_length = plugin_config.wordcloud_min_word_length
    if analyzer == "rjieba":
        return RjiebaAnalyzer(
            plugin_config.wordcloud_analyzer_options,
            stopwords,
            min_word_length,
            userdict_path,
        )
    if analyzer == "hanlp":
        return HanlpAnalyzer(
            plugin_config.wordcloud_analyzer_options,
            stopwords,
            min_word_length,
            userdict_path,
        )
    raise ValueError(f"不支持的词云分析后端: {analyzer}")


def analyse_message(msg: str) -> dict[str, float]:
    """分析消息文本并统计关键词权重。"""
    return get_word_analyzer().analyse(msg)


def _count_words(
    words: Iterable[str],
    stopwords: set[str],
    min_word_length: int,
) -> dict[str, float]:
    counter = Counter(
        word for word in _iter_valid_words(words, stopwords, min_word_length)
    )
    return {word: float(count) for word, count in counter.items()}


def _iter_valid_words(
    words: Iterable[str],
    stopwords: set[str],
    min_word_length: int,
) -> Iterable[str]:
    for word in words:
        word = word.strip()
        if (
            word
            and len(word) >= min_word_length
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


def _get_hanlp_model_name(options: Mapping[str, Any]) -> str:
    return str(options.get("model", "COARSE_ELECTRA_SMALL_ZH"))


@lru_cache
def _load_hanlp_tokenizer(model_name: str, load_options: str):
    try:
        import hanlp
    except ImportError as e:
        raise RuntimeError(
            "当前配置使用 hanlp 分析后端，但未安装 hanlp。"
            "请安装 nonebot-plugin-wordcloud[hanlp]。"
        ) from e

    load_kwargs = json.loads(load_options)
    model = getattr(hanlp.pretrained.tok, model_name, model_name)
    return hanlp.load(model, **load_kwargs)


def _set_hanlp_userdict(tokenizer, userdict_path: Path | None) -> None:
    userdict = _load_word_file(userdict_path)
    if hasattr(tokenizer, "dict_force"):
        tokenizer.dict_force = userdict or None
    elif userdict:
        logger.warning("当前 hanlp 模型不支持 wordcloud_userdict_path，已忽略用户词典")


def _extract_hanlp_tokens(result: Any, output_key: str | None) -> list[str]:
    if isinstance(result, Mapping):
        keys = [output_key] if output_key else []
        keys.extend(["tok/coarse", "tok/fine", "tok"])
        for key in keys:
            if key and key in result:
                return _extract_hanlp_tokens(result[key], None)
        return []
    if isinstance(result, str):
        return [result]
    if isinstance(result, Iterable):
        tokens: list[str] = []
        for item in result:
            tokens.extend(_extract_hanlp_tokens(item, None))
        return tokens
    return []


def _dump_options(options: Mapping[str, Any]) -> str:
    return json.dumps(options, sort_keys=True)


def clear_analyzer_cache() -> None:
    _load_hanlp_tokenizer.cache_clear()
