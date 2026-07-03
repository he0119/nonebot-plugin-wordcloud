from __future__ import annotations

import importlib.util
from datetime import time
from pathlib import Path
from typing import TYPE_CHECKING

from sqlalchemy import (
    JSON,
    Column,
    ForeignKey,
    Integer,
    MetaData,
    Table,
    Time,
    create_engine,
    select,
)

if TYPE_CHECKING:
    from types import ModuleType

    import pytest


def _load_migration(filename: str) -> ModuleType:
    path = (
        Path(__file__).parents[1] / "nonebot_plugin_wordcloud" / "migrations" / filename
    )
    spec = importlib.util.spec_from_file_location(f"test_{filename}", path)
    assert spec is not None
    assert spec.loader is not None

    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _create_tables(metadata: MetaData) -> Table:
    schedule = Table(
        "nonebot_plugin_wordcloud_schedule",
        metadata,
        Column("id", Integer, primary_key=True),
        Column("target", JSON),
        Column("time", Time),
    )
    role = Table(
        "nonebot_plugin_permission_rolemodel",
        metadata,
        Column("id", Integer, primary_key=True),
    )
    Table(
        "nonebot_plugin_permission_roleinheritsmodel",
        metadata,
        Column("source_id", ForeignKey(role.c.id), primary_key=True),
        Column("target_id", ForeignKey(role.c.id), primary_key=True),
    )
    return schedule


def test_migrate_target_upgrade_limits_automap_reflection(
    monkeypatch: pytest.MonkeyPatch,
):
    migration = _load_migration("4f1a6b35e888_migrate_target.py")
    engine = create_engine("sqlite://")
    metadata = MetaData()
    schedule = _create_tables(metadata)
    metadata.create_all(engine)

    with engine.connect() as conn:
        conn.execute(
            schedule.insert().values(
                id=1,
                target={"platform_type": "QQ Group", "group_id": 10000},
                time=time(8, 0),
            )
        )
        conn.commit()
        monkeypatch.setattr(migration.op, "get_bind", lambda: conn)

        migration.upgrade()

        target = conn.execute(select(schedule.c.target)).scalar_one()

    assert target == {
        "id": "10000",
        "parent_id": "",
        "channel": False,
        "private": False,
        "source": "",
        "extra": {},
        "scope": "QQClient",
    }


def test_migrate_target_downgrade_limits_automap_reflection(
    monkeypatch: pytest.MonkeyPatch,
):
    migration = _load_migration("4f1a6b35e888_migrate_target.py")
    engine = create_engine("sqlite://")
    metadata = MetaData()
    schedule = _create_tables(metadata)
    metadata.create_all(engine)

    with engine.connect() as conn:
        conn.execute(
            schedule.insert().values(
                id=1,
                target={
                    "id": "10000",
                    "parent_id": "",
                    "channel": False,
                    "private": False,
                    "source": "",
                    "extra": {},
                    "scope": "QQClient",
                },
                time=time(8, 0),
            )
        )
        conn.commit()
        monkeypatch.setattr(migration.op, "get_bind", lambda: conn)

        migration.downgrade()

        target = conn.execute(select(schedule.c.target)).scalar_one()

    assert target == {"platform_type": "QQ Group", "group_id": "10000"}
