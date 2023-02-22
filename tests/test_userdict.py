from nonebug import App
from pytest import MonkeyPatch


async def test_userdict(app: App, monkeypatch: MonkeyPatch):
    """测试添加用户词典"""

    from nonebot_plugin_datastore import PluginData

    from nonebot_plugin_wordcloud.config import plugin_config
    from nonebot_plugin_wordcloud.data_source import analyse_message

    with monkeypatch.context() as m:
        data = PluginData("wordcloud")
        with data.open("userdict.txt", "w", encoding="utf8") as f:
            f.write("小脑芙")

        message = "小脑芙真可爱！"
        frequency = analyse_message(message)
        assert frequency.keys() == {"小脑", "芙真", "可爱"}

        m.setattr(
            plugin_config, "wordcloud_userdict_path", data.data_dir / "userdict.txt"
        )

        frequency = analyse_message(message)
        assert frequency.keys() == {"小脑芙", "可爱"}
