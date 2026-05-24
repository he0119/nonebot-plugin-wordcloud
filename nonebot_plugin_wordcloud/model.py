from datetime import time
from enum import Enum

from nonebot_plugin_alconna import Target
from nonebot_plugin_orm import Model
from sqlalchemy import JSON
from sqlalchemy import Enum as SQLAlchemyEnum
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column


class ScheduleType(str, Enum):
    """定时发送类型"""

    DAY = "每日"
    WEEK = "每周"
    MONTH = "每月"
    YEAR = "每年"


class ScheduleMode(str, Enum):
    """定时发送模式"""

    COMPLETE = "完整周期"
    PERIOD_END = "周期末"


def _enum_values(enum_class) -> list[str]:
    return [enum_item.value for enum_item in enum_class]


class Schedule(Model):
    """定时发送"""

    id: Mapped[int] = mapped_column(primary_key=True)
    target: Mapped[dict] = mapped_column(JSON().with_variant(JSONB, "postgresql"))
    """发送目标"""
    schedule_type: Mapped[ScheduleType] = mapped_column(
        SQLAlchemyEnum(
            ScheduleType,
            values_callable=_enum_values,
            native_enum=False,
        ),
        default=ScheduleType.DAY,
        server_default=ScheduleType.DAY.value,
    )
    """定时发送类型"""
    schedule_mode: Mapped[ScheduleMode] = mapped_column(
        SQLAlchemyEnum(
            ScheduleMode,
            values_callable=_enum_values,
            native_enum=False,
        ),
        default=ScheduleMode.COMPLETE,
        server_default=ScheduleMode.COMPLETE.value,
    )
    """定时发送模式"""
    time: Mapped[time | None]
    """ UTC 时间 """

    @property
    def alc_target(self) -> Target:
        return Target.load(self.target.copy())
