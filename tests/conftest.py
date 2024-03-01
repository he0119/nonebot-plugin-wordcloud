from pathlib import Path

import nonebot
import pytest
from nonebot.adapters.onebot.v11 import Adapter as OnebotV11Adapter
from nonebot.adapters.onebot.v12 import Adapter as OnebotV12Adapter
from nonebug import NONEBOT_INIT_KWARGS, App
from pytest_mock import MockerFixture
from sqlalchemy import StaticPool, delete


def pytest_configure(config: pytest.Config) -> None:
    config.stash[NONEBOT_INIT_KWARGS] = {
        "sqlalchemy_database_url": "sqlite+aiosqlite://",
        "sqlalchemy_engine_options": {"poolclass": StaticPool},
        "driver": "~fastapi+~httpx",
        "alembic_startup_check": False,
    }


@pytest.fixture()
async def app(tmp_path: Path, mocker: MockerFixture):
    # 加载插件
    nonebot.require("nonebot_plugin_wordcloud")
    data_dir = tmp_path / "data"
    data_dir.mkdir()
    mocker.patch("nonebot_plugin_wordcloud.config.DATA_DIR", data_dir)
    from nonebot_plugin_orm import get_session, init_orm

    from nonebot_plugin_wordcloud.schedule import schedule_service

    await init_orm()
    yield App()

    from nonebot_plugin_chatrecorder.model import MessageRecord
    from nonebot_plugin_session_orm import SessionModel

    from nonebot_plugin_wordcloud.model import Schedule

    # 清理数据
    async with get_session() as session, session.begin():
        await session.execute(delete(MessageRecord))
        await session.execute(delete(SessionModel))
        await session.execute(delete(Schedule))

    keys = [key for key in schedule_service.schedules.keys() if key != "default"]
    for key in keys:
        schedule_service.schedules.pop(key)


@pytest.fixture(scope="session", autouse=True)
def _load_adapters(nonebug_init: None):
    driver = nonebot.get_driver()
    driver.register_adapter(OnebotV11Adapter)
    driver.register_adapter(OnebotV12Adapter)
