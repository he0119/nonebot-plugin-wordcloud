from nonebug import App


async def test_stopwords(app: App):
    """测试设置停用词表"""
    from nonebot_plugin_localstore import get_data_file

    from nonebot_plugin_wordcloud.config import plugin_config
    from nonebot_plugin_wordcloud.data_source import analyse_messages

    data = get_data_file("nonebot_plugin_wordcloud", "stopwords.txt")
    with data.open("w", encoding="utf8") as f:
        f.write("句子")

    msgs = ["这是一个奇怪的句子。"]
    frequencies = analyse_messages(msgs)
    assert frequencies.keys() == {"这是", "一个", "奇怪", "句子"}

    plugin_config.wordcloud_stopwords_path = data

    frequencies = analyse_messages(msgs)
    assert frequencies.keys() == {"这是", "一个", "奇怪"}
