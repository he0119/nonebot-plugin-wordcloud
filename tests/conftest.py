from pathlib import Path

import nonebot
import pytest
from nonebot.adapters.onebot.v11 import Adapter as OnebotV11Adapter
from nonebot.adapters.onebot.v12 import Adapter as OnebotV12Adapter
from nonebug import NONEBOT_INIT_KWARGS, App
from sqlalchemy import StaticPool, delete


def pytest_configure(config: pytest.Config) -> None:
    config.stash[NONEBOT_INIT_KWARGS] = {
        "datastore_database_url": "sqlite+aiosqlite://",
        "datastore_engine_options": {"poolclass": StaticPool},
        "alconna_use_command_start": True,
        "driver": "~fastapi+~httpx",
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

    from nonebot_plugin_chatrecorder.model import MessageRecord
    from nonebot_plugin_session.model import SessionModel

    from nonebot_plugin_wordcloud.model import Schedule

    # 清理数据
    async with create_session() as session, session.begin():
        await session.execute(delete(MessageRecord))
        await session.execute(delete(SessionModel))
        await session.execute(delete(Schedule))

    keys = [key for key in schedule_service.schedules.keys() if key != "default"]
    for key in keys:
        schedule_service.schedules.pop(key)


@pytest.fixture(scope="session", autouse=True)
def load_adapters(nonebug_init: None):
    driver = nonebot.get_driver()
    driver.register_adapter(OnebotV11Adapter)
    driver.register_adapter(OnebotV12Adapter)
