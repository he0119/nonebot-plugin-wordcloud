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

    # 手动缓存 uninfo 所需信息
    from nonebot_plugin_uninfo import (
        Scene,
        SceneType,
        Session,
        SupportAdapter,
        SupportScope,
        User,
    )
    from nonebot_plugin_uninfo.adapters.onebot11.main import fetcher as onebot11_fetcher
    from nonebot_plugin_uninfo.adapters.onebot12.main import fetcher as onebot12_fetcher

    onebot11_fetcher.session_cache = {
        "group_10000_10": Session(
            self_id="test",
            adapter=SupportAdapter.onebot11,
            scope=SupportScope.qq_client,
            scene=Scene("10000", SceneType.GROUP),
            user=User("10"),
        )
    }
    onebot12_fetcher.session_cache = {
        "group_10000_100": Session(
            self_id="test",
            adapter=SupportAdapter.onebot12,
            scope=SupportScope.qq_client,
            scene=Scene("10000", SceneType.GROUP),
            user=User("100"),
        ),
        "guild_10000_channel_100000_10": Session(
            self_id="test",
            adapter=SupportAdapter.onebot12,
            scope=SupportScope.qq_guild,
            scene=Scene(
                "100000", SceneType.CHANNEL_TEXT, parent=Scene("10000", SceneType.GUILD)
            ),
            user=User("10"),
        ),
    }


@pytest.fixture
async def app(app: App, tmp_path: Path, mocker: MockerFixture):
    wordcloud_dir = tmp_path / "wordcloud"
    wordcloud_dir.mkdir()
    mocker.patch("nonebot_plugin_wordcloud.config.DATA_DIR", wordcloud_dir)
    mocker.patch("nonebot_plugin_orm._data_dir", tmp_path / "orm")
    from nonebot_plugin_orm import get_session, init_orm

    from nonebot_plugin_wordcloud.schedule import schedule_service

    await init_orm()
    yield app

    from nonebot_plugin_chatrecorder.model import MessageRecord
    from nonebot_plugin_uninfo.orm import SessionModel

    from nonebot_plugin_wordcloud.model import Schedule

    # 清理数据
    async with get_session() as session, session.begin():
        await session.execute(delete(MessageRecord))
        await session.execute(delete(Schedule))
        await session.execute(delete(SessionModel))

    keys = [key for key in schedule_service.schedules.keys() if key != "default"]
    for key in keys:
        schedule_service.schedules.pop(key)
