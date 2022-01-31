import pytest
from nonebug import App


@pytest.mark.asyncio
async def test_userdict(app: App):
    """测试添加用户词典"""

    from nonebot_plugin_datastore import PluginData

    from nonebot_plugin_wordcloud.config import plugin_config
    from nonebot_plugin_wordcloud.data import cut_message

    data = PluginData("wordcloud")
    with data.open("userdict.txt", "w", encoding="utf8") as f:
        f.write("小脑芙")

    message = "小脑芙真可爱！"
    words = cut_message(message)
    assert words == ["小脑", "芙真", "可爱"]

    plugin_config.wordcloud_userdict_path = data.data_dir / "userdict.txt"

    words = cut_message(message)
    assert words == ["小脑芙", "真", "可爱"]
