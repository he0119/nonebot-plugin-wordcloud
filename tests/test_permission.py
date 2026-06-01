from datetime import datetime
from io import BytesIO
from zoneinfo import ZoneInfo

import pytest
from nonebot import get_adapter
from nonebot.adapters import Bot as BaseBot
from nonebot.adapters import Event
from nonebot.adapters.onebot.v11 import Adapter, Bot, Message, MessageSegment
from nonebot.adapters.onebot.v12 import Adapter as AdapterV12
from nonebot.adapters.onebot.v12 import Bot as BotV12
from nonebot.adapters.onebot.v12 import Message as MessageV12
from nonebug import App
from pytest_mock import MockerFixture

from .utils import (
    cache_onebot11_session,
    fake_channel_message_event_v12,
    fake_group_message_event_v11,
    fake_group_message_event_v12,
    fake_private_message_event_v11,
    grant_wordcloud_permission,
    make_channel_session,
    make_group_session,
    should_send_image,
)

FAKE_IMAGE = BytesIO(
    b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01\x08\x02\x00\x00\x00\x90wS\xde\x00\x00\x00\x0cIDATx\x9cc\xf8\xff\xff?\x00\x05\xfe\x02\xfe\r\xefF\xb8\x00\x00\x00\x00IEND\xaeB`\x82"
)


async def _get_cithun_user(scope, user_id: int | str):
    """获取权限引擎使用的测试用户对象。"""
    from nonebot_plugin_permission import system
    from nonebot_plugin_user import get_user

    if not system.loaded.is_set():
        await system.load()

    user_model = await get_user(scope, str(user_id))
    return await system.get_or_create_user(f"user:{user_model.id}", user_model.name)


async def _has_available_permission(
    bot: BaseBot,
    event: Event,
    session,
    user_id: int | str,
    resource: str,
):
    """按指定事件上下文检查用户是否拥有资源可用权限。"""
    from nonebot_plugin_permission import Permission, system
    from nonebot_plugin_user import get_user
    from nonebot_plugin_user.models import UserSession

    user_model = await get_user(session.scope, str(user_id))
    user = await system.get_or_create_user(f"user:{user_model.id}", user_model.name)
    return await system.has_permission(
        user,
        resource,
        Permission.AVAILABLE,
        context={
            "bot": bot,
            "event": event,
            "session": UserSession(session=session, user=user_model),
        },
    )


async def _deny_available_permission(scope, user_id: int | str, resource):
    """在测试中显式 deny 用户对指定资源的可用权限。"""
    from nonebot_plugin_permission import Permission, system

    user = await _get_cithun_user(scope, user_id)
    await system.suset(user, resource, Permission.AVAILABLE, deny=True)


async def test_schedule_permission_granted_by_permission_plugin(app: App):
    from nonebot_plugin_wordcloud import schedule_cmd
    from nonebot_plugin_wordcloud.permissions import WORDCLOUD_SCHEDULE_PERMISSION

    session = cache_onebot11_session(99)
    await grant_wordcloud_permission(session.scope, 99, WORDCLOUD_SCHEDULE_PERMISSION)

    async with app.test_matcher(schedule_cmd) as ctx:
        adapter = get_adapter(Adapter)
        bot = ctx.create_bot(base=Bot, adapter=adapter, auto_connect=False)
        event = fake_group_message_event_v11(
            user_id=99,
            message=Message("/开启词云每日定时发送"),
        )

        ctx.receive_event(bot, event)
        ctx.should_pass_permission(schedule_cmd)
        ctx.should_call_send(
            event, "已开启词云每日定时发送，发送时间为：00:00:00+08:00", True
        )
        ctx.should_finished(schedule_cmd)


async def test_query_other_permission_granted_by_permission_plugin(
    app: App, mocker: MockerFixture
):
    from nonebot_plugin_wordcloud import wordcloud_cmd
    from nonebot_plugin_wordcloud.permissions import WORDCLOUD_QUERY_OTHER_PERMISSION

    session = cache_onebot11_session(99)
    await grant_wordcloud_permission(
        session.scope, 99, WORDCLOUD_QUERY_OTHER_PERMISSION
    )

    mocker.patch(
        "nonebot_plugin_wordcloud.get_datetime_now_with_timezone",
        return_value=datetime(2022, 1, 2, 23, tzinfo=ZoneInfo("Asia/Shanghai")),
    )
    mocked_get_messages = mocker.patch(
        "nonebot_plugin_wordcloud.get_messages_plain_text",
        return_value=["target-user-message"],
    )
    mocker.patch(
        "nonebot_plugin_wordcloud.get_wordcloud",
        return_value=FAKE_IMAGE,
    )

    async with app.test_matcher(wordcloud_cmd) as ctx:
        adapter = get_adapter(Adapter)
        bot = ctx.create_bot(base=Bot, adapter=adapter, auto_connect=False)
        event = fake_group_message_event_v11(
            user_id=99,
            message=Message("/今日词云 ") + MessageSegment.at(11),
        )

        ctx.receive_event(bot, event)
        should_send_image(ctx, bot, event, FAKE_IMAGE, name="wordcloud.png")
        ctx.should_finished(wordcloud_cmd)

    assert mocked_get_messages.call_args.kwargs["user_ids"] == ["11"]


async def test_uninfo_admin_role_attach_restricted_permissions(app: App):
    from nonebot_plugin_wordcloud.permissions import (
        WORDCLOUD_ADMIN_ATTACH_PERMISSIONS,
        WORDCLOUD_DEFAULT_MASK_PERMISSION,
        WORDCLOUD_QUERY_PERMISSION,
    )

    assert WORDCLOUD_QUERY_PERMISSION not in WORDCLOUD_ADMIN_ATTACH_PERMISSIONS
    assert WORDCLOUD_DEFAULT_MASK_PERMISSION not in WORDCLOUD_ADMIN_ATTACH_PERMISSIONS

    async with app.test_api() as ctx:
        adapter = get_adapter(Adapter)
        bot = ctx.create_bot(base=Bot, adapter=adapter, auto_connect=False)

        for role, user_id in [("owner", 30), ("admin", 31)]:
            session = cache_onebot11_session(user_id, role=role)
            event = fake_group_message_event_v11(
                user_id=user_id,
                sender={"role": "member"},
            )

            for resource in WORDCLOUD_ADMIN_ATTACH_PERMISSIONS:
                assert await _has_available_permission(
                    bot, event, session, user_id, resource
                )
            assert not await _has_available_permission(
                bot, event, session, user_id, WORDCLOUD_DEFAULT_MASK_PERMISSION
            )


async def test_uninfo_member_role_attach_does_not_grant_restricted_permissions(
    app: App,
):
    from nonebot_plugin_wordcloud.permissions import (
        WORDCLOUD_ADMIN_ATTACH_PERMISSIONS,
        WORDCLOUD_QUERY_PERMISSION,
    )

    session = cache_onebot11_session(32, role="member")

    async with app.test_api() as ctx:
        adapter = get_adapter(Adapter)
        bot = ctx.create_bot(base=Bot, adapter=adapter, auto_connect=False)
        event = fake_group_message_event_v11(user_id=32)

        for resource in WORDCLOUD_ADMIN_ATTACH_PERMISSIONS:
            assert not await _has_available_permission(
                bot, event, session, 32, resource
            )

        assert await _has_available_permission(
            bot, event, session, 32, WORDCLOUD_QUERY_PERMISSION
        )


async def test_attach_does_not_grant_without_uninfo_admin_role(app: App):
    from nonebot_plugin_uninfo import SupportAdapter, SupportScope

    from nonebot_plugin_wordcloud.permissions import WORDCLOUD_SCHEDULE_PERMISSION

    onebot11_session = cache_onebot11_session(33)

    async with app.test_api() as ctx:
        adapter = get_adapter(Adapter)
        bot = ctx.create_bot(base=Bot, adapter=adapter, auto_connect=False)
        event = fake_private_message_event_v11(
            user_id=33,
            sender={"role": "owner"},
        )

        assert not await _has_available_permission(
            bot,
            event,
            onebot11_session,
            33,
            WORDCLOUD_SCHEDULE_PERMISSION,
        )

        adapter_v12 = get_adapter(AdapterV12)
        bot_v12 = ctx.create_bot(
            base=BotV12,
            adapter=adapter_v12,
            auto_connect=False,
            platform="qq",
            impl="test",
        )

        group_event_v12 = fake_group_message_event_v12(
            user_id="100",
            message=MessageV12("test"),
        )
        group_session_v12 = make_group_session(
            user_id="100",
            adapter=SupportAdapter.onebot12,
            scope=SupportScope.qq_client,
        )
        assert not await _has_available_permission(
            bot_v12,
            group_event_v12,
            group_session_v12,
            "100",
            WORDCLOUD_SCHEDULE_PERMISSION,
        )

        channel_event_v12 = fake_channel_message_event_v12(
            user_id="10",
            message=MessageV12("test"),
        )
        channel_session_v12 = make_channel_session(user_id="10")
        assert not await _has_available_permission(
            bot_v12,
            channel_event_v12,
            channel_session_v12,
            "10",
            WORDCLOUD_SCHEDULE_PERMISSION,
        )


async def test_uninfo_admin_role_attach_overrides_explicit_deny(app: App):
    from nonebot_plugin_wordcloud.permissions import WORDCLOUD_SCHEDULE_PERMISSION

    session = cache_onebot11_session(34, role="admin")
    await _deny_available_permission(session.scope, 34, WORDCLOUD_SCHEDULE_PERMISSION)

    async with app.test_api() as ctx:
        adapter = get_adapter(Adapter)
        bot = ctx.create_bot(base=Bot, adapter=adapter, auto_connect=False)
        event = fake_group_message_event_v11(
            user_id=34,
            sender={"role": "admin"},
        )

        assert await _has_available_permission(
            bot,
            event,
            session,
            34,
            WORDCLOUD_SCHEDULE_PERMISSION,
        )


@pytest.mark.parametrize(
    ("role", "user_id"),
    [
        pytest.param("owner", 35, id="owner"),
        pytest.param("admin", 36, id="admin"),
    ],
)
async def test_query_other_permission_granted_to_uninfo_admin_role(
    app: App,
    mocker: MockerFixture,
    role: str,
    user_id: int,
):
    from nonebot_plugin_wordcloud import wordcloud_cmd

    cache_onebot11_session(user_id, role=role)

    mocker.patch(
        "nonebot_plugin_wordcloud.get_datetime_now_with_timezone",
        return_value=datetime(2022, 1, 2, 23, tzinfo=ZoneInfo("Asia/Shanghai")),
    )
    mocked_get_messages = mocker.patch(
        "nonebot_plugin_wordcloud.get_messages_plain_text",
        return_value=["target-user-message"],
    )
    mocker.patch("nonebot_plugin_wordcloud.get_wordcloud", return_value=FAKE_IMAGE)

    async with app.test_matcher(wordcloud_cmd) as ctx:
        adapter = get_adapter(Adapter)
        bot = ctx.create_bot(base=Bot, adapter=adapter, auto_connect=False)
        event = fake_group_message_event_v11(
            user_id=user_id,
            message=Message("/今日词云 ") + MessageSegment.at(11),
            sender={"role": "member"},
        )

        ctx.receive_event(bot, event)
        should_send_image(ctx, bot, event, FAKE_IMAGE, name="wordcloud.png")
        ctx.should_finished(wordcloud_cmd)

    assert mocked_get_messages.call_args.kwargs["user_ids"] == ["11"]


async def test_query_other_permission_denied_to_uninfo_member_role(
    app: App,
    mocker: MockerFixture,
):
    from nonebot_plugin_wordcloud import wordcloud_cmd
    from nonebot_plugin_wordcloud.permissions import WORDCLOUD_QUERY_OTHER_PERMISSION

    mocker.patch(
        "nonebot_plugin_wordcloud.get_datetime_now_with_timezone",
        return_value=datetime(2022, 1, 2, 23, tzinfo=ZoneInfo("Asia/Shanghai")),
    )
    mocked_get_wordcloud = mocker.patch("nonebot_plugin_wordcloud.get_wordcloud")

    async with app.test_matcher(wordcloud_cmd) as ctx:
        adapter = get_adapter(Adapter)
        bot = ctx.create_bot(base=Bot, adapter=adapter, auto_connect=False)
        event = fake_group_message_event_v11(
            message=Message("/今日词云 ") + MessageSegment.at(11),
        )

        ctx.receive_event(bot, event)
        ctx.should_call_send(
            event,
            f"仅拥有 {WORDCLOUD_QUERY_OTHER_PERMISSION} 权限的用户可查看其他群友的词云",
            True,
        )
        ctx.should_finished(wordcloud_cmd)

    mocked_get_wordcloud.assert_not_called()
