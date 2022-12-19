import pytest
from nonebug import App


async def test_remove_emoji(app: App):
    """测试移除 emoji"""

    from nonebot_plugin_wordcloud.data_source import pre_precess

    msg = "1😅🟨二"
    msg = pre_precess(msg)
    assert msg == "1二"


async def test_remove_http(app: App):
    """测试移除网址"""

    from nonebot_plugin_wordcloud.data_source import pre_precess

    msg = "1 http://v2.nonebot.dev/ 2"
    msg = pre_precess(msg)
    assert msg == "1  2"

    msg = "1 https://v2.nonebot.dev/ 2"
    msg = pre_precess(msg)
    assert msg == "1  2"

    msg = "1 https://share.api.weibo.cn/share/312975272,4779675790873388.html?weibo_id=4779675790873388 2"
    msg = pre_precess(msg)
    assert msg == "1  2"
