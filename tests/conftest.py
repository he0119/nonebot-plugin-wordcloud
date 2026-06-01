import os
from pathlib import Path

import nonebot
import pytest
from nonebot.adapters.onebot.v11 import Adapter as OnebotV11Adapter
from nonebot.adapters.onebot.v12 import Adapter as OnebotV12Adapter
from nonebug import NONEBOT_INIT_KWARGS, NONEBOT_START_LIFESPAN, App
from pytest_asyncio import is_async_test
from pytest_mock import MockerFixture
from sqlalchemy import delete
from sqlalchemy.pool import NullPool, StaticPool

POOL_CLASSES = {
    "NullPool": NullPool,
    "StaticPool": StaticPool,
}


def get_database_url() -> str:
    url = os.getenv("SQLALCHEMY_DATABASE_URL", "sqlite+aiosqlite://")
    if url != "sqlite+aiosqlite://":
        return url

    worker_id = os.getenv("PYTEST_XDIST_WORKER", "master")
    database = Path(".pytest_cache") / f"{worker_id}.sqlite3"
    database.parent.mkdir(exist_ok=True)
    database.unlink(missing_ok=True)
    return f"sqlite+aiosqlite:///{database.as_posix()}"


def pytest_configure(config: pytest.Config) -> None:
    pool_class = POOL_CLASSES[os.getenv("SQLALCHEMY_POOL_CLASS", "StaticPool")]

    config.stash[NONEBOT_INIT_KWARGS] = {
        "sqlalchemy_database_url": get_database_url(),
        "sqlalchemy_engine_options": {"poolclass": pool_class},
        "driver": "~fastapi+~httpx",
        "alembic_startup_check": False,
        "command_start": {"/", ""},
        "permission_superusers": [],
    }
    config.stash[NONEBOT_START_LIFESPAN] = False


def pytest_collection_modifyitems(items: list[pytest.Item]):
    pytest_asyncio_tests = (item for item in items if is_async_test(item))
    session_scope_marker = pytest.mark.asyncio(loop_scope="session")
    for async_test in pytest_asyncio_tests:
        async_test.add_marker(session_scope_marker, append=False)


def reset_permission_system(permission_system):
    from arclet.cithun import Role, User
    from arclet.cithun.model import Track

    roles = {
        role_id: permission_system.roles.get(role_id) or Role(role_id, name)
        for role_id, name in permission_system._predefine_roles
    }
    users = {
        user_id: permission_system.users.get(user_id) or User(user_id, name)
        for user_id, name in permission_system._predefine_users
    }
    tracks = {
        track_id: permission_system.tracks.get(track_id)
        or Track(track_id, name or track_id)
        for track_id, name in permission_system._predefine_tracks
    }

    permission_system.loaded.clear()
    permission_system.resources.clear()
    permission_system.users.clear()
    permission_system.users.update(users)
    permission_system.roles.clear()
    permission_system.roles.update(roles)
    permission_system.acls.clear()
    permission_system.tracks.clear()
    permission_system.tracks.update(tracks)


async def clear_database():
    from nonebot_plugin_chatrecorder.model import MessageRecord
    from nonebot_plugin_orm import get_session
    from nonebot_plugin_permission.model import (
        AclDependencyModel,
        AclEntryModel,
        ResourceModel,
        RoleInheritsModel,
        RoleModel,
        TrackLevelModel,
        TrackModel,
        UserModel,
        UserRolesModel,
    )
    from nonebot_plugin_uninfo.orm import SessionModel
    from nonebot_plugin_user.models import Bind
    from nonebot_plugin_user.models import User as UserModelByPluginUser

    from nonebot_plugin_wordcloud.model import Schedule

    async with get_session() as session, session.begin():
        await session.execute(delete(MessageRecord))
        await session.execute(delete(Schedule))
        await session.execute(delete(SessionModel))

        await session.execute(delete(AclDependencyModel))
        await session.execute(delete(AclEntryModel))
        await session.execute(delete(TrackLevelModel))
        await session.execute(delete(TrackModel))
        await session.execute(delete(UserRolesModel))
        await session.execute(delete(RoleInheritsModel))
        await session.execute(delete(ResourceModel))
        await session.execute(delete(UserModel))
        await session.execute(delete(RoleModel))

        await session.execute(delete(Bind))
        await session.execute(delete(UserModelByPluginUser))


@pytest.fixture(scope="session", autouse=True)
async def after_nonebot_init(after_nonebot_init: None):
    # 加载适配器
    driver = nonebot.get_driver()
    driver.register_adapter(OnebotV11Adapter)
    driver.register_adapter(OnebotV12Adapter)

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
    orm_dir = tmp_path / "orm"
    orm_dir.mkdir()

    mocker.patch("nonebot_plugin_localstore.BASE_CACHE_DIR", tmp_path / "cache")
    mocker.patch("nonebot_plugin_localstore.BASE_CONFIG_DIR", tmp_path / "config")
    mocker.patch("nonebot_plugin_localstore.BASE_DATA_DIR", tmp_path / "data")
    mocker.patch("nonebot_plugin_wordcloud.config.DATA_DIR", wordcloud_dir)
    mocker.patch("nonebot_plugin_orm._data_dir", orm_dir)
    from nonebot_plugin_orm import init_orm

    from nonebot_plugin_wordcloud.schedule import schedule_service

    await init_orm()

    from nonebot_plugin_permission import system as permission_system

    await clear_database()
    reset_permission_system(permission_system)
    await permission_system.load()

    yield app

    await clear_database()
    reset_permission_system(permission_system)

    keys = [
        key
        for key in schedule_service.schedules.keys()
        if not key.startswith("default:")
    ]
    for key in keys:
        schedule_service.schedules.pop(key)
