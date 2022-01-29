import pytest
from nonebug import App
from sqlmodel import select

from .utils import fake_group_message_event


@pytest.mark.asyncio
async def test_save_message(app: App):
    """测试保存数据"""
    from nonebot.adapters.onebot.v11 import Message
    from nonebot_plugin_datastore import create_session

    from nonebot_plugin_wordcloud import GroupMessage, save_message

    async with app.test_matcher(save_message) as ctx:
        bot = ctx.create_bot()
        event = fake_group_message_event(message=Message("今天的天气真好呀"))

        ctx.receive_event(bot, event)

    async with create_session() as session:
        statement = select(GroupMessage).limit(1)
        m = (await session.exec(statement)).first()  # type: ignore
        assert m.message == "今天的天气真好呀"  # type: ignore
