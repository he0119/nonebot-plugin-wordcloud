import random
import shutil
from io import BytesIO
from pathlib import Path

import respx
from httpx import Response
from nonebot import get_adapter
from nonebot.adapters.onebot.v11 import Adapter, Bot, Message, MessageSegment
from nonebug import App
from PIL import Image as PILImage
from PIL import ImageChops
from pytest_mock import MockerFixture

from .utils import (
    cache_onebot11_session,
    fake_group_message_event_v11,
    fake_private_message_event_v11,
    grant_wordcloud_permission,
    should_send_image,
)


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
    test_image = PILImage.open(test_image_path)
    image = PILImage.open(BytesIO(image_byte))
    diff = ImageChops.difference(image, test_image)
    assert diff.getbbox() is None

    mocked_random.assert_called()


async def test_masked_by_command(app: App, mocker: MockerFixture):
    """测试自定义图片形状"""

    from nonebot_plugin_wordcloud import wordcloud_cmd
    from nonebot_plugin_wordcloud.config import DATA_DIR, plugin_config

    mocker.patch.object(plugin_config, "wordcloud_background_color", "white")

    mask_path = Path(__file__).parent / "mask.png"
    shutil.copy(mask_path, DATA_DIR / "mask.png")

    mocked_get_messages_plain_text = mocker.patch(
        "nonebot_plugin_wordcloud.get_messages_plain_text",
        return_value=["示例", "插件", "测试"],
    )

    test_image_path = Path(__file__).parent / "test_masked.png"
    with test_image_path.open("rb") as f:
        test_image = f.read()

    mocked_get_wordcloud = mocker.patch(
        "nonebot_plugin_wordcloud.get_wordcloud",
        return_value=test_image,
    )

    async with app.test_matcher(wordcloud_cmd) as ctx:
        adapter = get_adapter(Adapter)
        bot = ctx.create_bot(base=Bot, adapter=adapter, auto_connect=False)
        event = fake_group_message_event_v11(message=Message("/今日词云"))

        ctx.receive_event(bot, event)
        should_send_image(ctx, bot, event, test_image, name="wordcloud.png")
        ctx.should_finished(wordcloud_cmd)

    mocked_get_messages_plain_text.assert_called_once()
    mocked_get_wordcloud.assert_called_once_with(
        ["示例", "插件", "测试"], "QQClient_10000"
    )


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
    test_image = PILImage.open(test_image_path)
    image = PILImage.open(BytesIO(image_byte))
    diff = ImageChops.difference(image, test_image)
    assert diff.getbbox() is None

    mocked_random.assert_called()


@respx.mock(assert_all_called=True)
async def test_set_mask_default(app: App, respx_mock: respx.MockRouter):
    """测试自定义图片形状"""
    from nonebot_plugin_wordcloud import set_mask_cmd
    from nonebot_plugin_wordcloud.config import DATA_DIR
    from nonebot_plugin_wordcloud.permissions import (
        WORDCLOUD_DEFAULT_MASK_PERMISSION,
        WORDCLOUD_MASK_PERMISSION,
    )

    mask_path = Path(__file__).parent / "mask.png"
    with mask_path.open("rb") as f:
        mask_image = f.read()

    image_url = respx_mock.get("https://test").mock(
        return_value=Response(200, content=mask_image)
    )

    session = cache_onebot11_session(20)
    await grant_wordcloud_permission(session.scope, 20, WORDCLOUD_MASK_PERMISSION)

    async with app.test_matcher(set_mask_cmd) as ctx:
        adapter = get_adapter(Adapter)
        bot = ctx.create_bot(base=Bot, adapter=adapter, auto_connect=False)
        message = Message("/设置词云默认形状") + MessageSegment(
            "image", {"url": "https://test", "file": ""}
        )
        event = fake_group_message_event_v11(user_id=20, message=message)

        ctx.receive_event(bot, event)
        ctx.should_call_send(
            event,
            f"仅拥有 {WORDCLOUD_DEFAULT_MASK_PERMISSION} 权限的用户可设置词云默认形状",
            True,
        )
        ctx.should_finished()

    assert image_url.call_count == 1

    await grant_wordcloud_permission(
        session.scope, 20, WORDCLOUD_DEFAULT_MASK_PERMISSION
    )

    async with app.test_matcher(set_mask_cmd) as ctx:
        adapter = get_adapter(Adapter)
        bot = ctx.create_bot(base=Bot, adapter=adapter, auto_connect=False)
        message = Message("/设置词云默认形状") + MessageSegment(
            "image", {"url": "https://test", "file": ""}
        )
        event = fake_group_message_event_v11(
            user_id=20, message=message, sender={"role": "owner"}
        )

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
    from nonebot_plugin_wordcloud.permissions import WORDCLOUD_MASK_PERMISSION

    image_url = respx_mock.get("https://test").mock(
        return_value=Response(
            200, content=(Path(__file__).parent / "mask.png").read_bytes()
        )
    )

    assert not (DATA_DIR / "mask-QQClient_10000.png").exists()

    session = cache_onebot11_session(21)
    await grant_wordcloud_permission(session.scope, 21, WORDCLOUD_MASK_PERMISSION)

    async with app.test_matcher(set_mask_cmd) as ctx:
        adapter = get_adapter(Adapter)
        bot = ctx.create_bot(base=Bot, adapter=adapter, auto_connect=False)
        message = Message("/设置词云形状") + MessageSegment(
            "image", {"url": "https://test", "file": ""}
        )
        event = fake_group_message_event_v11(
            user_id=21, message=message, sender={"role": "owner"}
        )

        ctx.receive_event(bot, event)
        ctx.should_call_send(event, "词云形状设置成功", True)
        ctx.should_finished()

    assert image_url.call_count == 1
    assert (DATA_DIR / "mask-QQClient_10000.png").exists()


@respx.mock(assert_all_called=True)
async def test_set_mask_without_mask_permission(app: App, respx_mock: respx.MockRouter):
    from nonebot_plugin_wordcloud import set_mask_cmd
    from nonebot_plugin_wordcloud.config import DATA_DIR
    from nonebot_plugin_wordcloud.permissions import (
        WORDCLOUD_DEFAULT_MASK_PERMISSION,
        WORDCLOUD_MASK_PERMISSION,
    )

    image_url = respx_mock.get("https://test").mock(
        return_value=Response(
            200, content=(Path(__file__).parent / "mask.png").read_bytes()
        )
    )

    mask_path = DATA_DIR / "mask-QQClient_10000.png"
    assert not mask_path.exists()

    session = cache_onebot11_session(27)
    await grant_wordcloud_permission(
        session.scope, 27, WORDCLOUD_DEFAULT_MASK_PERMISSION
    )

    async with app.test_matcher(set_mask_cmd) as ctx:
        adapter = get_adapter(Adapter)
        bot = ctx.create_bot(base=Bot, adapter=adapter, auto_connect=False)
        message = Message("/设置词云形状") + MessageSegment(
            "image", {"url": "https://test", "file": ""}
        )
        event = fake_group_message_event_v11(user_id=27, message=message)

        ctx.receive_event(bot, event)
        ctx.should_call_send(
            event,
            f"仅拥有 {WORDCLOUD_MASK_PERMISSION} 权限的用户可设置词云形状",
            True,
        )
        ctx.should_finished()

    assert image_url.call_count == 1
    assert not mask_path.exists()


@respx.mock(assert_all_called=True)
async def test_set_mask_get_args(app: App, respx_mock: respx.MockRouter):
    """测试自定义图片形状，需要额外获取图片时的情况"""
    from nonebot_plugin_wordcloud import set_mask_cmd
    from nonebot_plugin_wordcloud.config import DATA_DIR
    from nonebot_plugin_wordcloud.permissions import WORDCLOUD_MASK_PERMISSION

    image_url = respx_mock.get("https://test").mock(
        return_value=Response(
            200, content=(Path(__file__).parent / "mask.png").read_bytes()
        )
    )

    session = cache_onebot11_session(22)
    await grant_wordcloud_permission(session.scope, 22, WORDCLOUD_MASK_PERMISSION)

    async with app.test_matcher(set_mask_cmd) as ctx:
        adapter = get_adapter(Adapter)
        bot = ctx.create_bot(base=Bot, adapter=adapter, auto_connect=False)
        message = Message("/设置词云形状")
        event = fake_group_message_event_v11(
            user_id=22, message=message, sender={"role": "owner"}
        )

        ctx.receive_event(bot, event)
        ctx.should_call_send(event, "请发送一张图片作为词云形状", True)
        ctx.should_rejected()

        invalid_message = Message(MessageSegment.text("test"))
        invalid_event = fake_group_message_event_v11(
            user_id=22, message=invalid_message, sender={"role": "owner"}
        )
        ctx.receive_event(bot, invalid_event)
        ctx.should_call_send(invalid_event, "请发送一张图片作为词云形状", True)
        ctx.should_rejected()

        image_message = Message(
            MessageSegment("image", {"url": "https://test", "file": ""})
        )
        image_event = fake_group_message_event_v11(
            user_id=22, message=image_message, sender={"role": "owner"}
        )
        ctx.receive_event(bot, image_event)
        ctx.should_call_send(image_event, "词云形状设置成功", True)
        ctx.should_finished()

    assert (DATA_DIR / "mask-QQClient_10000.png").exists()
    assert image_url.call_count == 1


async def test_remove_default_mask(app: App):
    """移除默认形状"""
    from nonebot_plugin_wordcloud import remove_mask_cmd
    from nonebot_plugin_wordcloud.config import DATA_DIR
    from nonebot_plugin_wordcloud.permissions import (
        WORDCLOUD_DEFAULT_MASK_PERMISSION,
        WORDCLOUD_MASK_PERMISSION,
    )

    mask_path = Path(__file__).parent / "mask.png"

    mask_default_path = DATA_DIR / "mask.png"
    mask_group_path = DATA_DIR / "mask-QQClient_10000.png"

    shutil.copy(mask_path, mask_default_path)
    shutil.copy(mask_path, mask_group_path)

    assert mask_default_path.exists()
    assert mask_group_path.exists()

    session = cache_onebot11_session(23)
    await grant_wordcloud_permission(session.scope, 23, WORDCLOUD_MASK_PERMISSION)

    async with app.test_matcher(remove_mask_cmd) as ctx:
        adapter = get_adapter(Adapter)
        bot = ctx.create_bot(base=Bot, adapter=adapter, auto_connect=False)
        message = Message("/删除词云默认形状")
        event = fake_group_message_event_v11(user_id=23, message=message)

        ctx.receive_event(bot, event)
        ctx.should_call_send(
            event,
            f"仅拥有 {WORDCLOUD_DEFAULT_MASK_PERMISSION} 权限的用户可删除词云默认形状",
            True,
        )
        ctx.should_finished()

    await grant_wordcloud_permission(
        session.scope, 23, WORDCLOUD_DEFAULT_MASK_PERMISSION
    )

    async with app.test_matcher(remove_mask_cmd) as ctx:
        adapter = get_adapter(Adapter)
        bot = ctx.create_bot(base=Bot, adapter=adapter, auto_connect=False)
        message = Message("/删除词云默认形状")
        event = fake_group_message_event_v11(
            user_id=23, message=message, sender={"role": "owner"}
        )

        ctx.receive_event(bot, event)
        ctx.should_call_send(event, "词云默认形状已删除", True)
        ctx.should_finished()

    assert not mask_default_path.exists()
    assert mask_group_path.exists()


async def test_remove_mask(app: App):
    from nonebot_plugin_wordcloud import remove_mask_cmd
    from nonebot_plugin_wordcloud.config import DATA_DIR
    from nonebot_plugin_wordcloud.permissions import WORDCLOUD_MASK_PERMISSION

    mask_path = Path(__file__).parent / "mask.png"

    mask_default_path = DATA_DIR / "mask.png"
    mask_group_path = DATA_DIR / "mask-QQClient_10000.png"

    shutil.copy(mask_path, mask_default_path)
    shutil.copy(mask_path, mask_group_path)

    assert mask_default_path.exists()
    assert mask_group_path.exists()

    session = cache_onebot11_session(24)
    await grant_wordcloud_permission(session.scope, 24, WORDCLOUD_MASK_PERMISSION)

    async with app.test_matcher(remove_mask_cmd) as ctx:
        adapter = get_adapter(Adapter)
        bot = ctx.create_bot(base=Bot, adapter=adapter, auto_connect=False)
        message = Message("/删除词云形状")
        event = fake_group_message_event_v11(
            user_id=24, message=message, sender={"role": "owner"}
        )

        ctx.receive_event(bot, event)
        ctx.should_call_send(event, "词云形状已删除", True)
        ctx.should_finished()

    assert mask_default_path.exists()
    assert not mask_group_path.exists()


async def test_set_mask_private(app: App):
    """测试私聊设置词云形状"""
    from nonebot_plugin_wordcloud import set_mask_cmd
    from nonebot_plugin_wordcloud.permissions import WORDCLOUD_MASK_PERMISSION

    session = cache_onebot11_session(25)
    await grant_wordcloud_permission(session.scope, 25, WORDCLOUD_MASK_PERMISSION)

    async with app.test_matcher(set_mask_cmd) as ctx:
        adapter = get_adapter(Adapter)
        bot = ctx.create_bot(base=Bot, adapter=adapter, auto_connect=False)
        event = fake_private_message_event_v11(
            user_id=25, message=Message("/设置词云形状")
        )

        ctx.receive_event(bot, event)
        ctx.should_call_send(
            event,
            "请在群组中使用！",
            True,
        )
        ctx.should_finished()


async def test_remove_mask_private(app: App):
    """测试私聊删除词云形状"""
    from nonebot_plugin_wordcloud import remove_mask_cmd
    from nonebot_plugin_wordcloud.permissions import WORDCLOUD_MASK_PERMISSION

    session = cache_onebot11_session(26)
    await grant_wordcloud_permission(session.scope, 26, WORDCLOUD_MASK_PERMISSION)

    async with app.test_matcher(remove_mask_cmd) as ctx:
        adapter = get_adapter(Adapter)
        bot = ctx.create_bot(base=Bot, adapter=adapter, auto_connect=False)
        event = fake_private_message_event_v11(
            user_id=26, message=Message("/删除词云形状")
        )

        ctx.receive_event(bot, event)
        ctx.should_call_send(
            event,
            "请在群组中使用！",
            True,
        )
        ctx.should_finished()
