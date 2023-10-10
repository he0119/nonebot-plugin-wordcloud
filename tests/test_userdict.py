from nonebug import App
from pytest_mock import MockerFixture


async def test_userdict(app: App, mocker: MockerFixture):
    """测试添加用户词典"""
    from nonebot_plugin_localstore import get_data_file

    from nonebot_plugin_wordcloud.config import plugin_config
    from nonebot_plugin_wordcloud.data_source import analyse_message

    data = get_data_file("nonebot_plugin_wordcloud", "userdict.txt")
    with data.open("w", encoding="utf8") as f:
        f.write("小脑芙")

    message = "小脑芙真可爱！"
    frequency = analyse_message(message)
    assert frequency.keys() == {"小脑", "芙真", "可爱"}

    mocker.patch.object(plugin_config, "wordcloud_userdict_path", data)

    frequency = analyse_message(message)
    assert frequency.keys() == {"小脑芙", "可爱"}
