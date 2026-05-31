from datetime import datetime
from io import BytesIO
from itertools import count
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from nonebot.adapters.onebot.v11 import GroupMessageEvent as GroupMessageEventV11
    from nonebot.adapters.onebot.v11 import (
        PrivateMessageEvent as PrivateMessageEventV11,
    )
    from nonebot.adapters.onebot.v12 import (
        ChannelMessageEvent as ChannelMessageEventV12,
    )
    from nonebot.adapters.onebot.v12 import GroupMessageEvent as GroupMessageEventV12
    from nonebot.adapters.onebot.v12 import (
        PrivateMessageEvent as PrivateMessageEventV12,
    )
    from nonebug.mixin.call_api import ApiContext

_message_id_counter = count(1)


def _next_message_id() -> int:
    return next(_message_id_counter)


def fake_group_message_event_v11(**field) -> "GroupMessageEventV11":
    from nonebot.adapters.onebot.v11 import GroupMessageEvent, Message
    from nonebot.adapters.onebot.v11.event import Sender

    fake_field = {
        "time": 1000000,
        "self_id": 1,
        "post_type": "message",
        "sub_type": "normal",
        "user_id": 10,
        "message_type": "group",
        "group_id": 10000,
        "message_id": _next_message_id(),
        "message": Message("test"),
        "raw_message": "test",
        "font": 0,
        "sender": Sender(
            card="",
            nickname="test",
            role="member",
        ),
        "to_me": False,
    }
    fake_field.update(field)

    return GroupMessageEvent(**fake_field)


def fake_private_message_event_v11(**field) -> "PrivateMessageEventV11":
    from nonebot.adapters.onebot.v11 import Message, PrivateMessageEvent
    from nonebot.adapters.onebot.v11.event import Sender

    fake_field = {
        "time": 1000000,
        "self_id": 1,
        "post_type": "message",
        "sub_type": "friend",
        "user_id": 10,
        "message_type": "private",
        "message_id": _next_message_id(),
        "message": Message("test"),
        "raw_message": "test",
        "font": 0,
        "sender": Sender(nickname="test"),
        "to_me": False,
    }
    fake_field.update(field)

    return PrivateMessageEvent(**fake_field)


def fake_group_message_event_v12(**field) -> "GroupMessageEventV12":
    from nonebot.adapters.onebot.v12 import GroupMessageEvent, Message
    from nonebot.adapters.onebot.v12.event import BotSelf

    fake_field = {
        "self": BotSelf(platform="qq", user_id="test"),
        "id": str(_next_message_id()),
        "time": datetime.fromtimestamp(1000000),
        "type": "message",
        "detail_type": "group",
        "sub_type": "normal",
        "message_id": str(_next_message_id()),
        "message": Message("test"),
        "original_message": Message("test"),
        "alt_message": "test",
        "user_id": "100",
        "group_id": "10000",
        "to_me": False,
    }
    fake_field.update(field)

    return GroupMessageEvent(**fake_field)


def fake_private_message_event_v12(**field) -> "PrivateMessageEventV12":
    from nonebot.adapters.onebot.v12 import Message, PrivateMessageEvent
    from nonebot.adapters.onebot.v12.event import BotSelf

    fake_field = {
        "self": BotSelf(platform="qq", user_id="test"),
        "id": str(_next_message_id()),
        "time": datetime.fromtimestamp(1000000),
        "type": "message",
        "detail_type": "private",
        "sub_type": "",
        "message_id": str(_next_message_id()),
        "message": Message("test"),
        "original_message": Message("test"),
        "alt_message": "test",
        "user_id": "100",
        "to_me": False,
    }
    fake_field.update(field)

    return PrivateMessageEvent(**fake_field)


def fake_channel_message_event_v12(**field) -> "ChannelMessageEventV12":
    from nonebot.adapters.onebot.v12 import ChannelMessageEvent, Message
    from nonebot.adapters.onebot.v12.event import BotSelf

    fake_field = {
        "self": BotSelf(platform="qq", user_id="test"),
        "id": str(_next_message_id()),
        "time": datetime.fromtimestamp(1000000),
        "type": "message",
        "detail_type": "channel",
        "sub_type": "",
        "message_id": str(_next_message_id()),
        "message": Message("test"),
        "original_message": Message("test"),
        "alt_message": "test",
        "user_id": "10",
        "guild_id": "10000",
        "channel_id": "100000",
        "to_me": False,
    }
    fake_field.update(field)

    return ChannelMessageEvent(**fake_field)


def make_group_session(
    group_id: int | str = 10000,
    user_id: int | str = 10,
    *,
    self_id: str = "test",
    adapter=None,
    scope=None,
):
    from nonebot_plugin_uninfo import (
        Scene,
        SceneType,
        Session,
        SupportAdapter,
        SupportScope,
        User,
    )

    return Session(
        self_id=self_id,
        adapter=adapter or SupportAdapter.onebot11,
        scope=scope or SupportScope.qq_client,
        scene=Scene(str(group_id), SceneType.GROUP),
        user=User(str(user_id)),
    )


def cache_onebot11_session(user_id: int | str):
    from nonebot_plugin_uninfo.adapters.onebot11.main import fetcher

    session = make_group_session(user_id=user_id)
    fetcher.session_cache[f"group_10000_{user_id}"] = session
    return session


async def grant_wordcloud_permission(scope, user_id: int | str, permission: str):
    from nonebot_plugin_permission import Permission, system
    from nonebot_plugin_user import get_user

    if not system.loaded.is_set():
        await system.load()

    user_model = await get_user(scope, str(user_id))
    owner = await system.get_or_create_user(f"user:{user_model.id}", user_model.name)
    await system.suset(owner, permission, Permission("v-a"))


def make_channel_session(
    channel_id: int | str = 100000,
    guild_id: int | str = 10000,
    user_id: int | str = 10,
    *,
    self_id: str = "test",
):
    from nonebot_plugin_uninfo import (
        Scene,
        SceneType,
        Session,
        SupportAdapter,
        SupportScope,
        User,
    )

    return Session(
        self_id=self_id,
        adapter=SupportAdapter.onebot12,
        scope=SupportScope.qq_guild,
        scene=Scene(
            str(channel_id),
            SceneType.CHANNEL_TEXT,
            parent=Scene(str(guild_id), SceneType.GUILD),
        ),
        user=User(str(user_id)),
    )


def make_group_target(group_id: int | str = 10000):
    from nonebot_plugin_alconna import Target

    return Target(str(group_id), scope="QQClient")


def make_channel_target(
    channel_id: int | str = 100000,
    guild_id: int | str = 10000,
):
    from nonebot_plugin_alconna import Target

    return Target(str(channel_id), str(guild_id), channel=True, scope="QQGuild")


def _image_bytes(image: bytes | BytesIO) -> bytes:
    return image.getvalue() if isinstance(image, BytesIO) else image


def should_send_image(
    ctx: "ApiContext",
    bot,
    event,
    image: bytes | BytesIO,
    *,
    name: str = "wordcloud.png",
    at_sender: bool = False,
    reply: bool = False,
):
    raw = _image_bytes(image)

    if bot.adapter.get_name() == "OneBot V12":
        from nonebot.adapters.onebot.v12 import Message, MessageSegment

        file_id = f"file://{name}"
        ctx.should_call_api(
            "upload_file",
            {"type": "data", "data": raw, "name": name},
            {"file_id": file_id},
        )
        message = Message()
        if at_sender:
            message += MessageSegment.mention(event.user_id)
        message += MessageSegment.image(file_id)
    else:
        from nonebot.adapters.onebot.v11 import Message, MessageSegment

        message = Message()
        if at_sender:
            message += MessageSegment.at(event.user_id)
        message += MessageSegment.image(raw)

    ctx.should_call_send(event, message, True, reply=reply)


def should_send_group_message(
    ctx: "ApiContext",
    message,
    *,
    group_id: int = 10000,
    result=None,
    exception: Exception | None = None,
):
    ctx.should_call_api(
        "send_msg",
        {
            "message_type": "group",
            "group_id": group_id,
            "message": message,
        },
        {"message_id": 1} if result is None else result,
        exception,
    )


def should_send_group_image(
    ctx: "ApiContext",
    image: bytes | BytesIO,
    *,
    group_id: int = 10000,
    exception: Exception | None = None,
):
    from nonebot.adapters.onebot.v11 import Message, MessageSegment

    should_send_group_message(
        ctx,
        Message(MessageSegment.image(_image_bytes(image))),
        group_id=group_id,
        exception=exception,
    )


def should_send_group_text(
    ctx: "ApiContext",
    text: str,
    *,
    group_id: int = 10000,
):
    from nonebot.adapters.onebot.v11 import Message

    should_send_group_message(ctx, Message(text), group_id=group_id)


def should_send_channel_image_v12(
    ctx: "ApiContext",
    image: bytes | BytesIO,
    *,
    guild_id: str = "10000",
    channel_id: str = "100000",
):
    from nonebot.adapters.onebot.v12 import Message, MessageSegment

    raw = _image_bytes(image)
    file_id = "file://image.png"
    ctx.should_call_api(
        "upload_file",
        {"type": "data", "data": raw, "name": "image.png"},
        {"file_id": file_id},
    )
    ctx.should_call_api(
        "send_message",
        {
            "detail_type": "channel",
            "channel_id": channel_id,
            "guild_id": guild_id,
            "message": Message(MessageSegment.image(file_id)),
        },
        {"message_id": "1"},
    )


def should_send_group_image_v12(
    ctx: "ApiContext",
    image: bytes | BytesIO,
    *,
    group_id: str = "10000",
):
    from nonebot.adapters.onebot.v12 import Message, MessageSegment

    raw = _image_bytes(image)
    file_id = "file://image.png"
    ctx.should_call_api(
        "upload_file",
        {"type": "data", "data": raw, "name": "image.png"},
        {"file_id": file_id},
    )
    ctx.should_call_api(
        "send_message",
        {
            "detail_type": "group",
            "group_id": group_id,
            "message": Message(MessageSegment.image(file_id)),
        },
        {"message_id": "1"},
    )
