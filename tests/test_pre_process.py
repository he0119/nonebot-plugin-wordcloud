import pytest
from nonebug import App


@pytest.mark.asyncio
async def test_remove_emoji(app: App):
    """测试移除 emoji"""

    from nonebot_plugin_wordcloud.data_source import pre_precess

    msg = "1😅🟨二"
    msg = pre_precess(msg)
    assert msg == "1二"


@pytest.mark.asyncio
async def test_remove_http(app: App):
    """测试移除网址"""

    from nonebot_plugin_wordcloud.data_source import pre_precess

    msg = "1 https://v2.nonebot.dev/ 2"
    msg = pre_precess(msg)
    assert msg == "1  2"
