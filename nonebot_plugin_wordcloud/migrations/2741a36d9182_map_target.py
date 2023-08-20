"""map_target

Revision ID: 2741a36d9182
Revises: dc39d67fb62e
Create Date: 2023-08-10 19:27:51.655052

"""
import sqlalchemy as sa
from alembic import op
from sqlalchemy.ext.automap import automap_base
from sqlalchemy.orm import Session

# revision identifiers, used by Alembic.
revision = "2741a36d9182"
down_revision = "dc39d67fb62e"
branch_labels = None
depends_on = None


def upgrade() -> None:
    Base = automap_base()
    Base.prepare(op.get_bind())
    Schedule = Base.classes.nonebot_plugin_wordcloud_schedule
    with Session(op.get_bind()) as session:
        schedules = session.scalars(sa.select(Schedule)).all()
        for schedule in schedules:
            if schedule.platform == "qq":
                schedule.target = {
                    "platform_type": "QQ Group",
                    "group_id": int(schedule.group_id),
                }
            elif schedule.platform == "qqguild":
                schedule.target = {
                    "platform_type": "QQ Guild Channel",
                    "channel_id": int(schedule.channel_id),
                }
            elif schedule.platform == "kaiheila":
                schedule.target = {
                    "platform_type": "Kaiheila Channel",
                    "channel_id": schedule.channel_id,
                }
            elif schedule.platform == "telegram":
                if schedule.channel_id is None:
                    schedule.target = {
                        "platform_type": "Telegram Common",
                        "chat_id": schedule.group_id,
                    }
                else:
                    schedule.target = {
                        "platform_type": "Telegram Forum",
                        "chat_id": int(schedule.guild_id),
                        "message_thread_id": int(schedule.channel_id),
                    }
            elif schedule.platform == "feishu":
                schedule.target = {
                    "platform_type": "Feishu Group",
                    "chat_id": schedule.group_id,
                }
            else:
                schedule.target = {
                    "platform_type": "Unknow Onebot 12 Platform",
                    "platform": schedule.platform,
                    "detail_type": "group" if schedule.group_id else "channel",
                    "group_id": schedule.group_id,
                    "guild_id": schedule.guild_id,
                    "channel_id": schedule.channel_id,
                }

        session.add_all(schedules)
        session.commit()


def downgrade() -> None:
    Base = automap_base()
    Base.prepare(op.get_bind())
    Schedule = Base.classes.nonebot_plugin_wordcloud_schedule
    with Session(op.get_bind()) as session:
        schedules = session.scalars(sa.select(Schedule)).all()
        for schedule in schedules:
            platform_type = schedule.target["platform_type"]
            if platform_type == "QQ Group":
                schedule.group_id = str(schedule.target["group_id"])
            elif platform_type == "QQ Guild Channel":
                schedule.channel_id = str(schedule.target["channel_id"])
            elif platform_type == "Kaiheila Channel":
                schedule.channel_id = schedule.target["channel_id"]
            elif platform_type == "Telegram Common":
                schedule.group_id = str(schedule.target["chat_id"])
                schedule.channel_id = None
            elif platform_type == "Telegram Forum":
                schedule.guild_id = str(schedule.target["chat_id"])
                schedule.channel_id = str(schedule.target["message_thread_id"])
            elif platform_type == "Feishu Group":
                schedule.group_id = schedule.target["chat_id"]
            else:
                schedule.platform = schedule.target["platform"]
                schedule.group_id = schedule.target["group_id"]
                schedule.guild_id = schedule.target["guild_id"]
                schedule.channel_id = schedule.target["channel_id"]

        session.add_all(schedules)
        session.commit()
