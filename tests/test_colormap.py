from io import BytesIO
from pathlib import Path

from nonebug import App
from PIL import Image
from pytest_mock import MockerFixture


async def test_colormap(app: App, mocker: MockerFixture):
    """测试设置色彩映射表"""
    import random

    from PIL import ImageChops

    from nonebot_plugin_wordcloud.config import plugin_config
    from nonebot_plugin_wordcloud.data_source import get_wordcloud

    mocker.patch.object(plugin_config, "wordcloud_colormap", "Pastel1")

    mocked_random = mocker.patch("wordcloud.wordcloud.Random")
    mocked_random.return_value = random.Random(0)

    image_byte = await get_wordcloud(["天气"], "")

    assert image_byte is not None

    # 比较生成的图片是否相同
    test_image_path = Path(__file__).parent / "test_colormap.png"
    test_image = Image.open(test_image_path)
    image = Image.open(BytesIO(image_byte))
    diff = ImageChops.difference(image, test_image)
    assert diff.getbbox() is None

    mocked_random.assert_called_once_with()


async def test_colormap_by_options(app: App, mocker: MockerFixture):
    """测试通过 options 设置色彩映射表"""
    import random

    from PIL import ImageChops

    from nonebot_plugin_wordcloud.config import plugin_config
    from nonebot_plugin_wordcloud.data_source import get_wordcloud

    mocker.patch.object(plugin_config, "wordcloud_options", {"colormap": "Pastel1"})

    mocked_random = mocker.patch("wordcloud.wordcloud.Random")
    mocked_random.return_value = random.Random(0)

    image_byte = await get_wordcloud(["天气"], "")

    assert image_byte is not None

    # 比较生成的图片是否相同
    test_image_path = Path(__file__).parent / "test_colormap.png"
    test_image = Image.open(test_image_path)
    image = Image.open(BytesIO(image_byte))
    diff = ImageChops.difference(image, test_image)
    assert diff.getbbox() is None

    mocked_random.assert_called_once_with()


async def test_colormap_random(app: App, mocker: MockerFixture):
    """测试随机选择色彩映射表"""
    import random

    from PIL import ImageChops

    from nonebot_plugin_wordcloud.config import plugin_config
    from nonebot_plugin_wordcloud.data_source import get_wordcloud

    mocker.patch.object(plugin_config, "wordcloud_colormap", ["Pastel1", "plasma"])

    mocked_choice = mocker.patch("nonebot_plugin_wordcloud.data_source.choice")
    mocked_choice.return_value = "Pastel1"

    mocked_random = mocker.patch("wordcloud.wordcloud.Random")
    mocked_random.return_value = random.Random(0)

    image_byte = await get_wordcloud(["天气"], "")

    assert image_byte is not None

    # 比较生成的图片是否相同
    test_image_path = Path(__file__).parent / "test_colormap.png"
    test_image = Image.open(test_image_path)
    image = Image.open(BytesIO(image_byte))
    diff = ImageChops.difference(image, test_image)
    assert diff.getbbox() is None

    mocked_choice.assert_called_once_with(["Pastel1", "plasma"])
    mocked_random.assert_called_once_with()
