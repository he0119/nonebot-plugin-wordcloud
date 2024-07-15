import pytest
from nonebug import App


@pytest.mark.skip("需要申请密钥")
async def test_hanlp_restful(app: App):
    """hanlp 分词"""
    from nonebot_plugin_wordcloud.processors.hanlp_restful import Processor

    processor = Processor()

    msgs = [
        "小脑芙真可爱！",
        "小脑芙可爱！",
        "小脑芙",
    ]
    msgs = processor.process_msgs(msgs)
    assert msgs == ["小", "脑芙", "真", "可爱", "！", "小脑芙", "可爱", "！", "小脑芙"]
