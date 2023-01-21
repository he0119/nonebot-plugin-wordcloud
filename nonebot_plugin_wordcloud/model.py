from datetime import time
from typing import Optional

from sqlmodel import Field, UniqueConstraint

from .config import plugin_data


class Schedule(plugin_data.Model, table=True):
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

    id: Optional[int] = Field(default=None, primary_key=True)
    bot_id: str
    platform: str
    group_id: Optional[str] = Field(default=None)
    guild_id: Optional[str] = Field(default=None)
    channel_id: Optional[str] = Field(default=None)
    time: Optional["time"] = Field(default=None)
    """ UTC 时间 """
