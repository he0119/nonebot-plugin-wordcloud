from datetime import datetime
from io import BytesIO
from zoneinfo import ZoneInfo

from nonebot import get_adapter
from nonebot.adapters.onebot.v11 import Adapter, Bot, Message, MessageSegment
from nonebug import App
from pytest_mock import MockerFixture

from .utils import (
    cache_onebot11_session,
    fake_group_message_event_v11,
    grant_wordcloud_permission,
    should_send_image,
)

FAKE_IMAGE = BytesIO(
    b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01\x08\x02\x00\x00\x00\x90wS\xde\x00\x00\x00\x0cIDATx\x9cc\xf8\xff\xff?\x00\x05\xfe\x02\xfe\r\xefF\xb8\x00\x00\x00\x00IEND\xaeB`\x82"
)


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
