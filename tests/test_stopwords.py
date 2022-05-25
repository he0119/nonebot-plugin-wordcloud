import pytest
from nonebug import App


@pytest.mark.asyncio
async def test_stopwords(app: App):
    """测试设置停用词表"""

    from nonebot_plugin_datastore import PluginData

    from nonebot_plugin_wordcloud.config import plugin_config
    from nonebot_plugin_wordcloud.data_source import analyse_message

    data = PluginData("wordcloud")
    with data.open("stopwords.txt", "w", encoding="utf8") as f:
        f.write("句子")

    message = "这是一个奇怪的句子。"
    frequency = analyse_message(message)
    assert frequency.keys() == {"这是", "一个", "奇怪", "句子"}

    plugin_config.wordcloud_stopwords_path = data.data_dir / "stopwords.txt"

    frequency = analyse_message(message)
    assert frequency.keys() == {"这是", "一个", "奇怪"}
