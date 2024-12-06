from datetime import time
from typing import Optional

from nonebot_plugin_orm import Model
from nonebot_plugin_saa import PlatformTarget
from sqlalchemy import JSON
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column


class Schedule(Model):
    """定时发送"""

    id: Mapped[int] = mapped_column(primary_key=True)
    target: Mapped[dict] = mapped_column(JSON().with_variant(JSONB, "postgresql"))
    time: Mapped[Optional[time]]
    """ UTC 时间 """

    @property
    def saa_target(self) -> PlatformTarget:
        return PlatformTarget.deserialize(self.target)
