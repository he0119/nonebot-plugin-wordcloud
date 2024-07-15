from nonebug import App


async def test_remove_emoji(app: App):
    """测试移除 emoji"""
    from nonebot_plugin_wordcloud.processors.sanitizer import Processor

    processor = Processor()

    msgs = ["1😅🟨二", "1👨🏿‍🔧👨‍👨‍👧‍👧🛀🏽🧑🏽‍❤️‍🧑🏾1"]
    msgs = processor.process_msgs(msgs)
    assert msgs == ["1二", "11"]


async def test_remove_http(app: App):
    """测试移除网址"""
    from nonebot_plugin_wordcloud.processors.sanitizer import Processor

    processor = Processor()

    msgs = [
        "1  2",
        "1 http://v2.nonebot.dev/ 2",
        "1 https://v2.nonebot.dev/ 2",
        "1 https://api.weibo.cn/share/312975272,47087.html?weibo_id=4770873388 2",
    ]
    msgs = processor.process_msgs(msgs)
    assert msgs == [
        "1  2",
        "1  2",
        "1  2",
        "1  2",
    ]
