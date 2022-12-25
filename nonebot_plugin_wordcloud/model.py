from datetime import time
from typing import Optional

from sqlmodel import Field, SQLModel, UniqueConstraint


class Schedule(SQLModel, table=True):
    """定时发送"""

    __tablename__: str = "wordcloud_schedule"
    __table_args__ = (
        UniqueConstraint("bot_id", "group_id"),
        {"extend_existing": True},
    )

    id: Optional[int] = Field(default=None, primary_key=True)
    bot_id: str
    group_id: str
    time: Optional["time"] = Field(default=None)
    """ UTC 时间 """
