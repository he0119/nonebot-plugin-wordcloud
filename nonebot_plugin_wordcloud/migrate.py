from datetime import datetime

from nonebot.adapters.onebot.v11 import Message
from nonebot_plugin_chatrecorder import MessageRecord, serialize_message
from nonebot_plugin_datastore import create_session
from pydantic import BaseModel
from sqlalchemy.exc import OperationalError
from sqlmodel import text


class GroupMessage(BaseModel):
    """消息记录"""

    time: datetime
    """ 消息时间

    存放 UTC 时间
    """
    user_id: str
    group_id: str
    message: str
    platform: str


async def migrate_database() -> bool:
    """迁移数据库"""
    async with create_session() as session:
        try:
            statement = text(
                "SELECT time,user_id,group_id,message,platform FROM wordcloud_group_message"
            )
            data = await session.execute(statement)
        except OperationalError:
            return False
        messages = data.fetchall()
        messages = map(GroupMessage.parse_obj, messages)
        for message in messages:
            record = MessageRecord(
                platform="qq",
                time=message.time,
                type="message",
                detail_type="group",
                message_id="",
                message=serialize_message(Message(message.message)),
                alt_message=message.message,
                user_id=message.user_id,
                group_id=message.group_id,
            )
            session.add(record)
        await session.commit()
        # 删除旧表
        await session.execute(text("DROP TABLE wordcloud_group_message"))
        return True
