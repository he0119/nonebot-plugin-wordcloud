import random
import shutil
from io import BytesIO
from pathlib import Path

import respx
from httpx import Response
from nonebot import get_adapter, get_driver
from nonebot.adapters.onebot.v11 import Adapter, Bot, Message, MessageSegment
from nonebug import App
from nonebug_saa import should_send_saa
from PIL import Image, ImageChops
from pytest_mock import MockerFixture

from .utils import fake_group_message_event_v11, fake_private_message_event_v11


async def test_masked(app: App, mocker: MockerFixture):
    """测试自定义图片形状"""
    from nonebot_plugin_wordcloud.config import DATA_DIR, plugin_config
    from nonebot_plugin_wordcloud.data_source import get_wordcloud

    mocker.patch.object(plugin_config, "wordcloud_background_color", "white")

    mask_path = Path(__file__).parent / "mask.png"
    shutil.copy(mask_path, DATA_DIR / "mask.png")

    mocked_random = mocker.patch("wordcloud.wordcloud.Random")
    mocked_random.return_value = random.Random(0)

    image_byte = await get_wordcloud(["示例", "插件", "测试"], "")

    assert image_byte is not None

    # 比较生成的图片是否相同
    test_image_path = Path(__file__).parent / "test_masked.png"
    test_image = Image.open(test_image_path)
    image = Image.open(BytesIO(image_byte))
    diff = ImageChops.difference(image, test_image)
    assert diff.getbbox() is None

    mocked_random.assert_called()


async def test_masked_by_command(app: App, mocker: MockerFixture):
    """测试自定义图片形状"""
    from nonebot_plugin_saa import Image, MessageFactory

    from nonebot_plugin_wordcloud import wordcloud_cmd
    from nonebot_plugin_wordcloud.config import DATA_DIR, plugin_config

    mocker.patch.object(plugin_config, "wordcloud_background_color", "white")

    mask_path = Path(__file__).parent / "mask.png"
    shutil.copy(mask_path, DATA_DIR / "mask.png")

    mocked_random = mocker.patch("wordcloud.wordcloud.Random")
    mocked_random.return_value = random.Random(0)

    mocked_get_messages_plain_text = mocker.patch(
        "nonebot_plugin_wordcloud.get_messages_plain_text",
        return_value=["示例", "插件", "测试"],
    )

    test_image_path = Path(__file__).parent / "test_masked.png"
    with test_image_path.open("rb") as f:
        test_image = f.read()

    async with app.test_matcher(wordcloud_cmd) as ctx:
        bot = ctx.create_bot(base=Bot)
        event = fake_group_message_event_v11(message=Message("/今日词云"))

        ctx.receive_event(bot, event)
        should_send_saa(
            ctx,
            MessageFactory(Image(test_image, "wordcloud.png")),
            bot,
            event=event,
        )
        ctx.should_finished()

    mocked_random.assert_called()
    mocked_get_messages_plain_text.assert_called_once()


async def test_masked_group(app: App, mocker: MockerFixture):
    """测试不同群的自定义图片形状"""
    from nonebot_plugin_wordcloud.config import DATA_DIR, plugin_config
    from nonebot_plugin_wordcloud.data_source import get_wordcloud

    mocker.patch.object(plugin_config, "wordcloud_background_color", "white")

    mask_path = Path(__file__).parent / "mask.png"
    shutil.copy(mask_path, DATA_DIR / "mask-10000.png")

    mocked_random = mocker.patch("wordcloud.wordcloud.Random")
    mocked_random.return_value = random.Random(0)

    image_byte = await get_wordcloud(["示例", "插件", "测试"], "10000")

    assert image_byte is not None

    # 比较生成的图片是否相同
    test_image_path = Path(__file__).parent / "test_masked.png"
    test_image = Image.open(test_image_path)
    image = Image.open(BytesIO(image_byte))
    diff = ImageChops.difference(image, test_image)
    assert diff.getbbox() is None

    mocked_random.assert_called()


@respx.mock(assert_all_called=True)
async def test_set_mask_default(
    app: App, mocker: MockerFixture, respx_mock: respx.MockRouter
):
    """测试自定义图片形状"""
    from nonebot_plugin_wordcloud import set_mask_cmd
    from nonebot_plugin_wordcloud.config import DATA_DIR

    mask_path = Path(__file__).parent / "mask.png"
    with mask_path.open("rb") as f:
        mask_image = f.read()

    image_url = respx_mock.get("https://test").mock(
        return_value=Response(200, content=mask_image)
    )

    config = get_driver().config

    async with app.test_matcher(set_mask_cmd) as ctx:
        adapter = get_adapter(Adapter)
        bot = ctx.create_bot(base=Bot, adapter=adapter, auto_connect=False)
        message = Message("/设置词云默认形状") + MessageSegment(
            "image", {"url": "https://test", "file": ""}
        )
        event = fake_group_message_event_v11(message=message, sender={"role": "owner"})

        ctx.receive_event(bot, event)
        ctx.should_call_send(event, "仅超级用户可设置词云默认形状", True)
        ctx.should_finished()

    assert image_url.call_count == 1

    mocker.patch.object(config, "superusers", {"10"})

    async with app.test_matcher(set_mask_cmd) as ctx:
        adapter = get_adapter(Adapter)
        bot = ctx.create_bot(base=Bot, adapter=adapter, auto_connect=False)
        message = Message("/设置词云默认形状") + MessageSegment(
            "image", {"url": "https://test", "file": ""}
        )
        event = fake_group_message_event_v11(message=message, sender={"role": "owner"})

        ctx.receive_event(bot, event)
        ctx.should_call_send(event, "词云默认形状设置成功", True)
        ctx.should_finished()

    assert (DATA_DIR / "mask.png").exists()
    assert image_url.call_count == 2


@respx.mock(assert_all_called=True)
async def test_set_mask(app: App, respx_mock: respx.MockRouter):
    """测试自定义图片形状"""
    from nonebot_plugin_wordcloud import set_mask_cmd
    from nonebot_plugin_wordcloud.config import DATA_DIR

    image_url = respx_mock.get("https://test").mock(
        return_value=Response(
            200, content=(Path(__file__).parent / "mask.png").read_bytes()
        )
    )

    assert not (DATA_DIR / "mask-qq_group-group_id=10000.png").exists()

    async with app.test_matcher(set_mask_cmd) as ctx:
        adapter = get_adapter(Adapter)
        bot = ctx.create_bot(base=Bot, adapter=adapter, auto_connect=False)
        message = Message("/设置词云形状") + MessageSegment(
            "image", {"url": "https://test", "file": ""}
        )
        event = fake_group_message_event_v11(message=message, sender={"role": "owner"})

        ctx.receive_event(bot, event)
        ctx.should_call_send(event, "词云形状设置成功", True)
        ctx.should_finished()

    assert image_url.call_count == 1
    assert (DATA_DIR / "mask-qq_group-group_id=10000.png").exists()


@respx.mock(assert_all_called=True)
async def test_set_mask_get_args(app: App, respx_mock: respx.MockRouter):
    """测试自定义图片形状，需要额外获取图片时的情况"""
    from nonebot_plugin_wordcloud import set_mask_cmd
    from nonebot_plugin_wordcloud.config import DATA_DIR

    image_url = respx_mock.get("https://test").mock(
        return_value=Response(
            200, content=(Path(__file__).parent / "mask.png").read_bytes()
        )
    )

    async with app.test_matcher(set_mask_cmd) as ctx:
        bot = ctx.create_bot(base=Bot)
        message = Message("/设置词云形状")
        event = fake_group_message_event_v11(message=message, sender={"role": "owner"})

        ctx.receive_event(bot, event)
        ctx.should_call_send(event, "请发送一张图片作为词云形状", True)
        ctx.should_rejected()

        invalid_message = Message(MessageSegment.text("test"))
        invalid_event = fake_group_message_event_v11(
            message=invalid_message, sender={"role": "owner"}
        )
        ctx.receive_event(bot, invalid_event)
        ctx.should_call_send(invalid_event, "请发送一张图片作为词云形状", True)
        ctx.should_rejected()

        image_message = Message(
            MessageSegment("image", {"url": "https://test", "file": ""})
        )
        image_event = fake_group_message_event_v11(
            message=image_message, sender={"role": "owner"}
        )
        ctx.receive_event(bot, image_event)
        ctx.should_call_send(image_event, "词云形状设置成功", True)
        ctx.should_finished()

    assert (DATA_DIR / "mask-qq_group-group_id=10000.png").exists()
    assert image_url.call_count == 1


async def test_remove_default_mask(app: App, mocker: MockerFixture):
    """移除默认形状"""
    from nonebot_plugin_wordcloud import remove_mask_cmd
    from nonebot_plugin_wordcloud.config import DATA_DIR

    mask_path = Path(__file__).parent / "mask.png"

    mask_default_path = DATA_DIR / "mask.png"
    mask_group_path = DATA_DIR / "mask-qq_group-group_id=10000.png"

    shutil.copy(mask_path, mask_default_path)
    shutil.copy(mask_path, mask_group_path)

    assert mask_default_path.exists()
    assert mask_group_path.exists()

    async with app.test_matcher(remove_mask_cmd) as ctx:
        adapter = get_adapter(Adapter)
        bot = ctx.create_bot(base=Bot, adapter=adapter, auto_connect=False)
        message = Message("/删除词云默认形状")
        event = fake_group_message_event_v11(message=message, sender={"role": "owner"})

        ctx.receive_event(bot, event)
        ctx.should_call_send(event, "仅超级用户可删除词云默认形状", True)
        ctx.should_finished()

    mocker.patch.object(get_driver().config, "superusers", {"10"})

    async with app.test_matcher(remove_mask_cmd) as ctx:
        adapter = get_adapter(Adapter)
        bot = ctx.create_bot(base=Bot, adapter=adapter, auto_connect=False)
        message = Message("/删除词云默认形状")
        event = fake_group_message_event_v11(message=message, sender={"role": "owner"})

        ctx.receive_event(bot, event)
        ctx.should_call_send(event, "词云默认形状已删除", True)
        ctx.should_finished()

    assert not mask_default_path.exists()
    assert mask_group_path.exists()


async def test_remove_mask(app: App):
    from nonebot_plugin_wordcloud import remove_mask_cmd
    from nonebot_plugin_wordcloud.config import DATA_DIR

    mask_path = Path(__file__).parent / "mask.png"

    mask_default_path = DATA_DIR / "mask.png"
    mask_group_path = DATA_DIR / "mask-qq_group-group_id=10000.png"

    shutil.copy(mask_path, mask_default_path)
    shutil.copy(mask_path, mask_group_path)

    assert mask_default_path.exists()
    assert mask_group_path.exists()

    async with app.test_matcher(remove_mask_cmd) as ctx:
        bot = ctx.create_bot(base=Bot)
        message = Message("/删除词云形状")
        event = fake_group_message_event_v11(message=message, sender={"role": "owner"})

        ctx.receive_event(bot, event)
        ctx.should_call_send(event, "词云形状已删除", True)
        ctx.should_finished()

    assert mask_default_path.exists()
    assert not mask_group_path.exists()


async def test_set_mask_private(app: App, mocker: MockerFixture):
    """测试私聊设置词云形状"""
    from nonebot_plugin_wordcloud import set_mask_cmd

    config = get_driver().config

    mocker.patch.object(config, "superusers", {"10"})

    async with app.test_matcher(set_mask_cmd) as ctx:
        bot = ctx.create_bot(base=Bot)
        event = fake_private_message_event_v11(message=Message("/设置词云形状"))

        ctx.receive_event(bot, event)
        ctx.should_call_send(
            event,
            "请在群组中使用！",
            True,
        )
        ctx.should_finished()


async def test_remove_mask_private(app: App, mocker: MockerFixture):
    """测试私聊删除词云形状"""
    from nonebot_plugin_wordcloud import remove_mask_cmd

    config = get_driver().config

    mocker.patch.object(config, "superusers", {"10"})

    async with app.test_matcher(remove_mask_cmd) as ctx:
        bot = ctx.create_bot(base=Bot)
        event = fake_private_message_event_v11(message=Message("/删除词云形状"))

        ctx.receive_event(bot, event)
        ctx.should_call_send(
            event,
            "请在群组中使用！",
            True,
        )
        ctx.should_finished()
