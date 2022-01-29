from datetime import datetime
from typing import Optional

from sqlmodel import Field, SQLModel


class GroupMessage(SQLModel, table=True):
    """消息记录"""

    __tablename__: str = "wordcloud_group_message"
    # FIXME: 在 Linux 上如果不添加这句测试时会报错
    # sqlalchemy.exc.InvalidRequestError: Table 'message' is already defined for this MetaData instance.
    # Specify 'extend_existing=True' to redefine options and columns on an existing Table object.
    __table_args__ = {"extend_existing": True}

    id: Optional[int] = Field(default=None, primary_key=True)
    time: datetime
    """ 消息时间

    存放 UTC 时间
    """
    user_id: str
    group_id: str
    message: str
    platform: str
