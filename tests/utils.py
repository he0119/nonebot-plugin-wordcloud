from datetime import datetime
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
        "message_id": 1,
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
        "message_id": 1,
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
        "id": "1",
        "time": datetime.fromtimestamp(1000000),
        "type": "message",
        "detail_type": "group",
        "sub_type": "normal",
        "message_id": "10",
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
        "id": "1",
        "time": datetime.fromtimestamp(1000000),
        "type": "message",
        "detail_type": "private",
        "sub_type": "",
        "message_id": "10",
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
        "id": "1",
        "time": datetime.fromtimestamp(1000000),
        "type": "message",
        "detail_type": "channel",
        "sub_type": "",
        "message_id": "10",
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
