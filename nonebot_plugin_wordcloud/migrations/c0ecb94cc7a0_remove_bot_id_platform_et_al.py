"""remove bot_id platform et al

Revision ID: c0ecb94cc7a0
Revises: db81e06df0ed
Create Date: 2023-08-13 00:05:16.667668

"""
import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = "c0ecb94cc7a0"
down_revision = "db81e06df0ed"
branch_labels = None
depends_on = None


def upgrade() -> None:
    with op.batch_alter_table(
        "nonebot_plugin_wordcloud_schedule", schema=None
    ) as batch_op:
        batch_op.drop_column("channel_id")
        batch_op.drop_column("guild_id")
        batch_op.drop_column("group_id")
        batch_op.drop_column("platform")
        batch_op.drop_column("bot_id")


def downgrade() -> None:
    with op.batch_alter_table(
        "nonebot_plugin_wordcloud_schedule", schema=None
    ) as batch_op:
        batch_op.add_column(sa.Column("bot_id", sa.String(64), nullable=True))
        batch_op.add_column(sa.Column("platform", sa.String(32), nullable=True))
        batch_op.add_column(sa.Column("group_id", sa.String(64), nullable=True))
        batch_op.add_column(sa.Column("guild_id", sa.String(64), nullable=True))
        batch_op.add_column(sa.Column("channel_id", sa.String(64), nullable=True))
