from datetime import time
from typing import Optional

from sqlalchemy import UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from .config import plugin_data


class Schedule(plugin_data.Model):
    """定时发送"""

    __table_args__ = (
        UniqueConstraint(
            "bot_id",
            "platform",
            "group_id",
            "guild_id",
            "channel_id",
            name="unique_schedule",
        ),
        {"extend_existing": True},
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    bot_id: Mapped[str]
    platform: Mapped[str]
    group_id: Mapped[Optional[str]]
    guild_id: Mapped[Optional[str]]
    channel_id: Mapped[Optional[str]]
    time: Mapped[Optional["time"]]
    """ UTC 时间 """
