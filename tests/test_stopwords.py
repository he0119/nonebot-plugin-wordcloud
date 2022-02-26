import pytest
from nonebug import App


@pytest.mark.asyncio
async def test_stopwords(app: App):
    """测试消息均是 stopwords 的情况"""

    from nonebot_plugin_wordcloud.data_source import cut_message

    words = cut_message("你我他")

    assert words == []
