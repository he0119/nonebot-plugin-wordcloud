import shutil
from pathlib import Path

import pytest
from nonebug import App

from .utils import fake_group_message_event


@pytest.mark.asyncio
async def test_migrate(app: App):
    """测试迁移数据"""
    from nonebot.adapters.onebot.v11 import Message
    from nonebot_plugin_chatrecorder import get_message_records
    from nonebot_plugin_datastore.config import plugin_config

    from nonebot_plugin_wordcloud import migrate_cmd

    mock_db = Path(__file__).parent / "mock" / "migrate_test.db"
    shutil.copyfile(mock_db, plugin_config.datastore_data_dir / "data.db")

    records = await get_message_records(plain_text=True)
    assert records == []

    async with app.test_matcher(migrate_cmd) as ctx:
        bot = ctx.create_bot()
        event = fake_group_message_event(message=Message("/迁移词云"))

        ctx.receive_event(bot, event)
        ctx.should_call_send(event, "数据库迁移成功", True)
        ctx.should_finished()

    records = await get_message_records(plain_text=True)
    assert records == ["test"]


@pytest.mark.asyncio
async def test_migrate_not_exist(app: App):
    """测试迁移数据，旧版本数据库不存在"""
    from nonebot.adapters.onebot.v11 import Message

    from nonebot_plugin_wordcloud import migrate_cmd

    async with app.test_matcher(migrate_cmd) as ctx:
        bot = ctx.create_bot()
        event = fake_group_message_event(message=Message("/迁移词云"))

        ctx.receive_event(bot, event)
        ctx.should_call_send(event, "旧版本数据库不存在，不需要迁移", True)
        ctx.should_finished()
