import sys

import pytest
from nonebug import App
from pytest_mock import MockerFixture


@pytest.mark.parametrize(
    ("mode", "expected"),
    [
        (
            "default",
            {"今天天气": 2.0, "不错": 1.0, "真不错": 1.0},
        ),
        (
            "search",
            {
                "今天": 2.0,
                "天天": 2.0,
                "天气": 2.0,
                "今天天气": 2.0,
                "不错": 2.0,
                "真不": 1.0,
                "真不错": 1.0,
            },
        ),
        (
            "all",
            {
                "今天": 2.0,
                "今天天气": 2.0,
                "天天": 2.0,
                "天气": 2.0,
                "不错": 2.0,
                "真不": 1.0,
                "真不错": 1.0,
            },
        ),
    ],
)
async def test_rjieba_analyzer_uses_real_segmentation(
    app: App, mocker: MockerFixture, mode: str, expected: dict[str, float]
):
    """测试 rjieba 后端使用真实 rjieba 分词结果统计词频"""
    from nonebot_plugin_wordcloud.config import plugin_config
    from nonebot_plugin_wordcloud.data_source import analyse_message

    mocker.patch.object(plugin_config, "wordcloud_analyzer", "rjieba")
    mocker.patch.object(plugin_config, "wordcloud_analyzer_options", {"mode": mode})
    mocker.patch.object(plugin_config, "wordcloud_stopwords_path", None)
    mocker.patch.object(plugin_config, "wordcloud_userdict_path", None)

    frequency = analyse_message("今天天气不错，今天天气真不错。")

    assert frequency == expected


async def test_rjieba_analyzer_filters_short_words(app: App, mocker: MockerFixture):
    """测试 rjieba 后端会读取配置过滤过短词语"""
    from nonebot_plugin_wordcloud.config import plugin_config
    from nonebot_plugin_wordcloud.data_source import analyse_message

    mocker.patch.object(plugin_config, "wordcloud_analyzer", "rjieba")
    mocker.patch.object(plugin_config, "wordcloud_analyzer_options", {"mode": "search"})
    mocker.patch.object(plugin_config, "wordcloud_min_word_length", 3)
    mocker.patch.object(plugin_config, "wordcloud_stopwords_path", None)
    mocker.patch.object(plugin_config, "wordcloud_userdict_path", None)

    frequency = analyse_message("今天天气不错，今天天气真不错。")

    assert frequency == {"今天天气": 2.0, "真不错": 1.0}


async def test_rjieba_analyzer_filters_stopwords(app: App, mocker: MockerFixture):
    """测试 rjieba 后端会按停用词过滤真实分词结果"""
    from nonebot_plugin_localstore import get_data_file

    from nonebot_plugin_wordcloud.config import plugin_config
    from nonebot_plugin_wordcloud.data_source import analyse_message

    stopwords = get_data_file("nonebot_plugin_wordcloud", "rjieba-stopwords.txt")
    stopwords.write_text("今天天气\n", encoding="utf8")

    mocker.patch.object(plugin_config, "wordcloud_analyzer", "rjieba")
    mocker.patch.object(plugin_config, "wordcloud_analyzer_options", {})
    mocker.patch.object(plugin_config, "wordcloud_stopwords_path", stopwords)
    mocker.patch.object(plugin_config, "wordcloud_userdict_path", None)

    frequency = analyse_message("今天天气不错，今天天气真不错。")

    assert frequency == {"不错": 1.0, "真不错": 1.0}


async def test_rjieba_analyzer_warns_unsupported_userdict(
    app: App, mocker: MockerFixture
):
    """测试 rjieba 后端使用用户词典时会给出明确警告"""
    from nonebot_plugin_localstore import get_data_file

    from nonebot_plugin_wordcloud.config import plugin_config
    from nonebot_plugin_wordcloud.data_source import analyse_message

    userdict = get_data_file("nonebot_plugin_wordcloud", "rjieba-userdict.txt")
    userdict.write_text("小脑芙\n", encoding="utf8")
    mocked_warning = mocker.patch("nonebot_plugin_wordcloud.analyzer.logger.warning")
    mocker.patch.object(plugin_config, "wordcloud_analyzer", "rjieba")
    mocker.patch.object(plugin_config, "wordcloud_analyzer_options", {})
    mocker.patch.object(plugin_config, "wordcloud_stopwords_path", None)
    mocker.patch.object(plugin_config, "wordcloud_userdict_path", userdict)

    frequency = analyse_message("小脑芙真可爱！")

    assert frequency == {"小脑": 1.0, "芙真": 1.0, "可爱": 1.0}
    mocked_warning.assert_called_once_with(
        "rjieba 分析后端暂不支持 wordcloud_userdict_path，已忽略用户词典"
    )


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


async def test_get_word_analyzer_invalid_backend(app: App, mocker: MockerFixture):
    """测试配置未知后端时给出明确错误"""
    from nonebot_plugin_wordcloud.analyzer import get_word_analyzer
    from nonebot_plugin_wordcloud.config import plugin_config

    mocker.patch.object(plugin_config, "wordcloud_analyzer", "unknown")

    with pytest.raises(ValueError, match="不支持的词云分析后端: unknown"):
        get_word_analyzer()
