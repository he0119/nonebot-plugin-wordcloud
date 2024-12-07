from pathlib import Path

import nonebot
import pytest
from nonebot.adapters.onebot.v11 import Adapter as OnebotV11Adapter
from nonebot.adapters.onebot.v12 import Adapter as OnebotV12Adapter
from nonebug import NONEBOT_INIT_KWARGS, NONEBOT_START_LIFESPAN, App
from pytest_asyncio import is_async_test
from pytest_mock import MockerFixture
from sqlalchemy import StaticPool, delete


def pytest_configure(config: pytest.Config) -> None:
    config.stash[NONEBOT_INIT_KWARGS] = {
        "sqlalchemy_database_url": "sqlite+aiosqlite://",
        "sqlalchemy_engine_options": {"poolclass": StaticPool},
        "driver": "~fastapi+~httpx",
        "alembic_startup_check": False,
        "command_start": {"/", ""},
    }
    config.stash[NONEBOT_START_LIFESPAN] = False


def pytest_collection_modifyitems(items: list[pytest.Item]):
    pytest_asyncio_tests = (item for item in items if is_async_test(item))
    session_scope_marker = pytest.mark.asyncio(loop_scope="session")
    for async_test in pytest_asyncio_tests:
        async_test.add_marker(session_scope_marker, append=False)


@pytest.fixture(scope="session", autouse=True)
async def after_nonebot_init(after_nonebot_init: None):
    # 加载适配器
    driver = nonebot.get_driver()
    driver.register_adapter(OnebotV11Adapter)
    driver.register_adapter(OnebotV12Adapter)

    # 手动启动生命周期
    # 在加载 orm 之前运行，避免 orm 因未 mock 数据目录导致并发时出错
    await driver._lifespan.startup()

    # 加载插件
    nonebot.load_plugin("nonebot_plugin_wordcloud")


@pytest.fixture
async def app(tmp_path: Path, mocker: MockerFixture):
    wordcloud_dir = tmp_path / "wordcloud"
    wordcloud_dir.mkdir()
    mocker.patch("nonebot_plugin_wordcloud.config.DATA_DIR", wordcloud_dir)
    mocker.patch("nonebot_plugin_orm._data_dir", tmp_path / "orm")
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
