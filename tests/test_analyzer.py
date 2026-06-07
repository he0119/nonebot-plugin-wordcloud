import sys
from types import SimpleNamespace

import pytest
from nonebug import App
from pytest_mock import MockerFixture


async def test_rjieba_analyzer(app: App, mocker: MockerFixture):
    """测试 rjieba 后端使用词频权重"""
    from nonebot_plugin_wordcloud.config import plugin_config
    from nonebot_plugin_wordcloud.data_source import analyse_message

    class FakeJieba:
        def cut_for_search(self, text: str, hmm: bool):
            assert text == "今天天气不错"
            assert hmm is False
            return ["今天", "天气", "天气", "不错", "。", "a"]

    fake_rjieba = SimpleNamespace(Jieba=FakeJieba)
    mocker.patch.dict(sys.modules, {"rjieba": fake_rjieba})
    mocker.patch.object(plugin_config, "wordcloud_analyzer", "rjieba")
    mocker.patch.object(
        plugin_config,
        "wordcloud_analyzer_options",
        {"mode": "search", "hmm": False},
    )
    mocker.patch.object(plugin_config, "wordcloud_min_word_length", 2)
    mocker.patch.object(plugin_config, "wordcloud_stopwords_path", None)
    mocker.patch.object(plugin_config, "wordcloud_userdict_path", None)

    frequency = analyse_message("今天天气不错")

    assert frequency == {"今天": 1.0, "天气": 2.0, "不错": 1.0}


async def test_rjieba_analyzer_missing_dependency(app: App, mocker: MockerFixture):
    """测试 rjieba 后端缺少依赖时给出明确提示"""
    from nonebot_plugin_wordcloud.config import plugin_config
    from nonebot_plugin_wordcloud.data_source import analyse_message

    mocker.patch.dict(sys.modules, {"rjieba": None})
    mocker.patch.object(plugin_config, "wordcloud_analyzer", "rjieba")
    mocker.patch.object(plugin_config, "wordcloud_analyzer_options", {})
    mocker.patch.object(plugin_config, "wordcloud_stopwords_path", None)
    mocker.patch.object(plugin_config, "wordcloud_userdict_path", None)

    with pytest.raises(RuntimeError, match="nonebot-plugin-wordcloud\\[rjieba\\]"):
        analyse_message("今天天气不错")


async def test_hanlp_analyzer(app: App, mocker: MockerFixture, tmp_path):
    """测试 hanlp 后端使用词频权重并加载停用词与用户词典"""
    from nonebot_plugin_wordcloud.analyzer import clear_analyzer_cache
    from nonebot_plugin_wordcloud.config import plugin_config
    from nonebot_plugin_wordcloud.data_source import analyse_message

    clear_analyzer_cache()

    stopwords_path = tmp_path / "stopwords.txt"
    stopwords_path.write_text("可爱\n", encoding="utf8")
    userdict_path = tmp_path / "userdict.txt"
    userdict_path.write_text("小脑芙 10 n\n", encoding="utf8")

    class FakeTokenizer:
        dict_force = None

        def __call__(self, text: str):
            assert text == "小脑芙真可爱小脑芙"
            return ["小脑芙", "真", "可爱", "小脑芙", "。"]

    fake_tokenizer = FakeTokenizer()

    def fake_load(model: str, **kwargs):
        assert model == "fake-model"
        assert kwargs == {"devices": "cpu"}
        return fake_tokenizer

    fake_hanlp = SimpleNamespace(
        load=fake_load,
        pretrained=SimpleNamespace(
            tok=SimpleNamespace(COARSE_ELECTRA_SMALL_ZH="fake-model")
        ),
    )
    mocker.patch.dict(sys.modules, {"hanlp": fake_hanlp})
    mocker.patch.object(plugin_config, "wordcloud_analyzer", "hanlp")
    mocker.patch.object(
        plugin_config,
        "wordcloud_analyzer_options",
        {"model": "COARSE_ELECTRA_SMALL_ZH", "load_kwargs": {"devices": "cpu"}},
    )
    mocker.patch.object(plugin_config, "wordcloud_min_word_length", 2)
    mocker.patch.object(plugin_config, "wordcloud_stopwords_path", stopwords_path)
    mocker.patch.object(plugin_config, "wordcloud_userdict_path", userdict_path)

    frequency = analyse_message("小脑芙真可爱小脑芙")

    assert fake_tokenizer.dict_force == {"小脑芙"}
    assert frequency == {"小脑芙": 2.0}

    clear_analyzer_cache()
