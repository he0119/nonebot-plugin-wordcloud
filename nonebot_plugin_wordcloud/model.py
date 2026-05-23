from datetime import time

from nonebot_plugin_alconna import Target
from nonebot_plugin_orm import Model
from sqlalchemy import JSON
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column


class Schedule(Model):
    """定时发送"""

    id: Mapped[int] = mapped_column(primary_key=True)
    target: Mapped[dict] = mapped_column(JSON().with_variant(JSONB, "postgresql"))
    """发送目标"""
    time: Mapped[time | None]
    """ UTC 时间 """

    @property
    def alc_target(self) -> Target:
        return Target.load(self.target.copy())
