import shutil
from pathlib import Path

import nonebot
import pytest
from nonebug import NONEBOT_INIT_KWARGS, App
from sqlmodel import text


def pytest_configure(config: pytest.Config) -> None:
    config.stash[NONEBOT_INIT_KWARGS] = {
        "datastore_database_url": "sqlite+aiosqlite:///:memory:",
    }


@pytest.fixture
async def app(tmp_path: Path):
    # 加载插件
    nonebot.require("nonebot_plugin_wordcloud")
    from nonebot_plugin_datastore.config import plugin_config
    from nonebot_plugin_datastore.db import create_session, init_db

    from nonebot_plugin_wordcloud.schedule import schedule_service

    plugin_config.datastore_cache_dir = tmp_path / "cache"
    plugin_config.datastore_config_dir = tmp_path / "config"
    plugin_config.datastore_data_dir = tmp_path / "data"

    await init_db()

    yield App()

    # 清理数据
    async with create_session() as session:
        await session.execute(
            text("DROP TABLE IF EXISTS nonebot_plugin_wordcloud_schedule")
        )
        await session.execute(
            text("DROP TABLE IF EXISTS nonebot_plugin_wordcloud_alembic_version")
        )
        await session.execute(
            text("DROP TABLE IF EXISTS nonebot_plugin_chatrecorder_messagerecord")
        )
        await session.execute(
            text("DROP TABLE IF EXISTS nonebot_plugin_chatrecorder_alembic_version")
        )

    keys = [key for key in schedule_service.schedules.keys() if key != "default"]
    for key in keys:
        schedule_service.schedules.pop(key)
