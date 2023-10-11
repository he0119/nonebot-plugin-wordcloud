"""migrate datastore data

修订 ID: ade8cdca5470
父修订: 557fef3a156f
创建时间: 2023-10-11 19:57:51.023847

"""
from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from nonebot import logger
from nonebot_plugin_localstore import get_data_file

revision: str = "ade8cdca5470"
down_revision: str | Sequence[str] | None = "557fef3a156f"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade(name: str = "") -> None:
    if name:
        return
    # ### commands auto generated by Alembic - please adjust! ###
    db_file = get_data_file("", "data.db")
    if db_file.exists():
        engine = sa.create_engine(f"sqlite:///{db_file}")
        # 读取数据
        with engine.connect() as conn:
            result = conn.execute(
                sa.text("SELECT * FROM nonebot_plugin_wordcloud_schedule")
            )
            data = result.all()
        # 写入数据
        if not data:
            return
        logger.info("wordcloud: 发现来自 datastore 的数据，正在迁移...")
        op.get_bind().execute(
            sa.text(
                "INSERT INTO nonebot_plugin_wordcloud_schedule (id, target, time) VALUES (:id, :target, :time)"
            ),
            [{"id": i, "target": t, "time": ti} for i, t, ti in data],
        )
        logger.info("wordcloud: 迁移完成")
    # ### end Alembic commands ###


def downgrade(name: str = "") -> None:
    if name:
        return
    # ### commands auto generated by Alembic - please adjust! ###
    pass
    # ### end Alembic commands ###
