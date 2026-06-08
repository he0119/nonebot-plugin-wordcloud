import sys
from types import SimpleNamespace

import pytest
from nonebug import App
from pytest_mock import MockerFixture


async def test_rjieba_analyzer(app: App, mocker: MockerFixture):
    """测试 rjieba 后端使用词频权重"""
    from nonebot_plugin_wordcloud.config import plugin_config
    from nonebot_plugin_wordcloud.data_source import analyse_message

    original_analyzer = plugin_config.wordcloud_analyzer
    original_options = plugin_config.wordcloud_analyzer_options
    original_min_word_length = plugin_config.wordcloud_min_word_length
    original_stopwords_path = plugin_config.wordcloud_stopwords_path
    original_userdict_path = plugin_config.wordcloud_userdict_path

    class FakeJieba:
        def cut_for_search(self, text: str, hmm: bool):
            assert text == "今天天气不错"
            assert hmm is False
            return ["今天", "天气", "天气", "不错", "。", "a"]

    fake_rjieba = SimpleNamespace(Jieba=FakeJieba)
    mocker.patch.dict(sys.modules, {"rjieba": fake_rjieba})
    try:
        plugin_config.wordcloud_analyzer = "rjieba"
        plugin_config.wordcloud_analyzer_options = {"mode": "search", "hmm": False}
        plugin_config.wordcloud_min_word_length = 2
        plugin_config.wordcloud_stopwords_path = None
        plugin_config.wordcloud_userdict_path = None

        frequency = analyse_message("今天天气不错")

        assert frequency == {"今天": 1.0, "天气": 2.0, "不错": 1.0}
    finally:
        plugin_config.wordcloud_analyzer = original_analyzer
        plugin_config.wordcloud_analyzer_options = original_options
        plugin_config.wordcloud_min_word_length = original_min_word_length
        plugin_config.wordcloud_stopwords_path = original_stopwords_path
        plugin_config.wordcloud_userdict_path = original_userdict_path


async def test_rjieba_analyzer_missing_dependency(app: App, mocker: MockerFixture):
    """测试 rjieba 后端缺少依赖时给出明确提示"""
    from nonebot_plugin_wordcloud.config import plugin_config
    from nonebot_plugin_wordcloud.data_source import analyse_message

    original_analyzer = plugin_config.wordcloud_analyzer
    original_options = plugin_config.wordcloud_analyzer_options
    original_stopwords_path = plugin_config.wordcloud_stopwords_path
    original_userdict_path = plugin_config.wordcloud_userdict_path

    mocker.patch.dict(sys.modules, {"rjieba": None})
    try:
        plugin_config.wordcloud_analyzer = "rjieba"
        plugin_config.wordcloud_analyzer_options = {}
        plugin_config.wordcloud_stopwords_path = None
        plugin_config.wordcloud_userdict_path = None

        with pytest.raises(RuntimeError, match="nonebot-plugin-wordcloud\\[rjieba\\]"):
            analyse_message("今天天气不错")
    finally:
        plugin_config.wordcloud_analyzer = original_analyzer
        plugin_config.wordcloud_analyzer_options = original_options
        plugin_config.wordcloud_stopwords_path = original_stopwords_path
        plugin_config.wordcloud_userdict_path = original_userdict_path
