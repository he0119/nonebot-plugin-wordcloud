from pathlib import Path

from nonebug import App
from PIL import Image
from pytest_mock import MockerFixture

from .utils import fake_group_message_event


async def test_masked(app: App, mocker: MockerFixture):
    """测试自定义图片形状"""
    import random
    import shutil

    from PIL import ImageChops

    from nonebot_plugin_wordcloud.config import plugin_config, plugin_data
    from nonebot_plugin_wordcloud.data_source import get_wordcloud

    plugin_config.wordcloud_background_color = "white"

    mask_path = Path(__file__).parent / "mask.png"
    shutil.copy(mask_path, plugin_data.data_dir / "mask.png")

    mocked_random = mocker.patch("wordcloud.wordcloud.Random")
    mocked_random.return_value = random.Random(0)

    image_byte = await get_wordcloud(["示例", "插件", "测试"])

    assert image_byte is not None

    # 比较生成的图片是否相同
    test_image_path = Path(__file__).parent / "test_masked.png"
    test_image = Image.open(test_image_path)
    image = Image.open(image_byte)
    diff = ImageChops.difference(image, test_image)
    assert diff.getbbox() is None

    mocked_random.assert_called()


async def test_masked_group(app: App, mocker: MockerFixture):
    """测试不同群的自定义图片形状"""
    import random
    import shutil

    from PIL import ImageChops

    from nonebot_plugin_wordcloud.config import plugin_config, plugin_data
    from nonebot_plugin_wordcloud.data_source import get_wordcloud

    plugin_config.wordcloud_background_color = "white"

    mask_path = Path(__file__).parent / "mask.png"
    shutil.copy(mask_path, plugin_data.data_dir / "mask-10000.png")

    mocked_random = mocker.patch("wordcloud.wordcloud.Random")
    mocked_random.return_value = random.Random(0)

    image_byte = await get_wordcloud(["示例", "插件", "测试"], "10000")

    assert image_byte is not None

    # 比较生成的图片是否相同
    test_image_path = Path(__file__).parent / "test_masked.png"
    test_image = Image.open(test_image_path)
    image = Image.open(image_byte)
    diff = ImageChops.difference(image, test_image)
    assert diff.getbbox() is None

    mocked_random.assert_called()


async def test_set_mask(app: App, mocker: MockerFixture):
    """测试自定义图片形状"""
    from nonebot.adapters.onebot.v11 import Bot, Message, MessageSegment

    from nonebot_plugin_wordcloud import mask_cmd, plugin_data

    mocked_download = mocker.patch("nonebot_plugin_wordcloud.plugin_data.download_file")
    mocked_download.return_value = (Path(__file__).parent / "mask.png").read_bytes()

    async with app.test_matcher(mask_cmd) as ctx:
        bot = ctx.create_bot(base=Bot)
        message = Message("/设置词云默认形状") + MessageSegment(
            "image", {"url": "https://test"}
        )
        event = fake_group_message_event(message=message, sender={"role": "owner"})

        ctx.receive_event(bot, event)
        ctx.should_call_send(event, "词云默认形状设置成功", True)
        ctx.should_finished()

    mocked_download.assert_called_once_with("https://test", "masked", cache=True)
    assert plugin_data.exists("mask.png")

    async with app.test_matcher(mask_cmd) as ctx:
        bot = ctx.create_bot(base=Bot)
        message = Message("/设置词云形状") + MessageSegment("image", {"url": "https://test"})
        event = fake_group_message_event(message=message, sender={"role": "owner"})

        ctx.receive_event(bot, event)
        ctx.should_call_send(event, "群 10000 的词云形状设置成功", True)
        ctx.should_finished()

    mocked_download.assert_has_calls(
        [
            mocker.call("https://test", "masked", cache=True),
            mocker.call("https://test", "masked", cache=True),
        ]  # type: ignore
    )
    assert plugin_data.exists("mask-qq-group-10000.png")


async def test_set_mask_get_args(app: App, mocker: MockerFixture):
    """测试自定义图片形状，需要额外获取图片时的情况"""
    from nonebot.adapters.onebot.v11 import Bot, Message, MessageSegment

    from nonebot_plugin_wordcloud import mask_cmd, plugin_data

    mocked_download = mocker.patch("nonebot_plugin_wordcloud.plugin_data.download_file")
    mocked_download.return_value = (Path(__file__).parent / "mask.png").read_bytes()

    async with app.test_matcher(mask_cmd) as ctx:
        bot = ctx.create_bot(base=Bot)
        message = Message("/设置词云默认形状")
        event = fake_group_message_event(message=message, sender={"role": "owner"})

        ctx.receive_event(bot, event)
        ctx.should_call_send(event, "请发送一张图片作为词云形状", True)
        ctx.should_rejected()

        invalid_message = Message(MessageSegment.text("test"))
        invalid_event = fake_group_message_event(
            message=invalid_message, sender={"role": "owner"}
        )
        ctx.receive_event(bot, invalid_event)
        ctx.should_call_send(invalid_event, "请发送一张图片，不然我没法理解呢！", True)
        ctx.should_rejected()

        image_message = Message(MessageSegment("image", {"url": "https://test"}))
        image_event = fake_group_message_event(
            message=image_message, sender={"role": "owner"}
        )
        ctx.receive_event(bot, image_event)
        ctx.should_call_send(image_event, "词云默认形状设置成功", True)
        ctx.should_finished()

    mocked_download.assert_called_once_with("https://test", "masked", cache=True)
    assert plugin_data.exists("mask.png")

    async with app.test_matcher(mask_cmd) as ctx:
        bot = ctx.create_bot(base=Bot)
        message = Message("/设置词云形状")
        event = fake_group_message_event(message=message, sender={"role": "owner"})

        ctx.receive_event(bot, event)
        ctx.should_call_send(event, "请发送一张图片作为词云形状", True)
        ctx.should_rejected()

        invalid_message = Message(MessageSegment.text("test"))
        invalid_event = fake_group_message_event(
            message=invalid_message, sender={"role": "owner"}
        )
        ctx.receive_event(bot, invalid_event)
        ctx.should_call_send(invalid_event, "请发送一张图片，不然我没法理解呢！", True)
        ctx.should_rejected()

        image_message = Message(MessageSegment("image", {"url": "https://test"}))
        image_event = fake_group_message_event(
            message=image_message, sender={"role": "owner"}
        )
        ctx.receive_event(bot, image_event)
        ctx.should_call_send(image_event, "群 10000 的词云形状设置成功", True)
        ctx.should_finished()

    mocked_download.assert_has_calls(
        [
            mocker.call("https://test", "masked", cache=True),
            mocker.call("https://test", "masked", cache=True),
        ]  # type: ignore
    )
    assert plugin_data.exists("mask-qq-group-10000.png")


async def test_remove_mask(app: App):
    import shutil

    from nonebot.adapters.onebot.v11 import Bot, Message

    from nonebot_plugin_wordcloud import mask_cmd, plugin_data

    mask_path = Path(__file__).parent / "mask.png"

    mask_default_path = plugin_data.data_dir / "mask.png"
    mask_group_path = plugin_data.data_dir / "mask-qq-group-10000.png"

    shutil.copy(mask_path, mask_default_path)
    shutil.copy(mask_path, mask_group_path)

    assert mask_default_path.exists()
    assert mask_group_path.exists()

    async with app.test_matcher(mask_cmd) as ctx:
        bot = ctx.create_bot(base=Bot)
        message = Message("/删除词云默认形状")
        event = fake_group_message_event(message=message, sender={"role": "owner"})

        ctx.receive_event(bot, event)
        ctx.should_call_send(event, "词云默认形状已删除", True)
        ctx.should_finished()

    assert not mask_default_path.exists()
    assert mask_group_path.exists()

    async with app.test_matcher(mask_cmd) as ctx:
        bot = ctx.create_bot(base=Bot)
        message = Message("/删除词云形状")
        event = fake_group_message_event(message=message, sender={"role": "owner"})

        ctx.receive_event(bot, event)
        ctx.should_call_send(event, "群 10000 的词云形状已删除", True)
        ctx.should_finished()

    assert not mask_default_path.exists()
    assert not mask_group_path.exists()
