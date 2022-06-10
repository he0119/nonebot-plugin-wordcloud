from pathlib import Path

import pytest
from nonebug import App
from PIL import Image
from pytest_mock import MockerFixture


@pytest.mark.asyncio
async def test_colormap(app: App, mocker: MockerFixture):
    """测试设置颜色图"""
    import random

    from PIL import ImageChops

    from nonebot_plugin_wordcloud.config import plugin_config
    from nonebot_plugin_wordcloud.data_source import get_wordcloud

    plugin_config.wordcloud_colormap = "Pastel1"

    mocked_random = mocker.patch("wordcloud.wordcloud.Random")
    mocked_random.return_value = random.Random(0)

    image = get_wordcloud(["天气"])

    assert image is not None

    # 比较生成的图片是否相同
    test_image_path = Path(__file__).parent / "test_colormap.png"
    test_image = Image.open(test_image_path)
    diff = ImageChops.difference(image, test_image)
    assert diff.getbbox() is None

    mocked_random.assert_called_once_with()
