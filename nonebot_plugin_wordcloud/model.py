from datetime import time
from typing import Optional

from nonebot_plugin_orm import Model
from sqlalchemy.orm import Mapped, mapped_column


class Schedule(Model):
    """定时发送"""

    id: Mapped[int] = mapped_column(primary_key=True)
    session_persist_id: Mapped[int]
    """ 会话持久化 ID"""
    time: Mapped[Optional[time]]
    """ UTC 时间 """
