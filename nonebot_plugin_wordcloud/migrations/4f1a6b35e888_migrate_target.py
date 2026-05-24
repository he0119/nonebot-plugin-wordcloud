"""migrate target

迁移 ID: 4f1a6b35e888
父迁移: ade8cdca5470
创建时间: 2025-08-12 12:48:46.578366

"""

from __future__ import annotations

import json
from typing import TYPE_CHECKING

from alembic import op
from nonebot import logger
from nonebot_plugin_alconna import Target
from sqlalchemy.ext.automap import automap_base
from sqlalchemy.orm import Session

if TYPE_CHECKING:
    from collections.abc import Sequence

revision: str = "4f1a6b35e888"
down_revision: str | Sequence[str] | None = "ade8cdca5470"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def _ensure_ob12_scope(platform: str) -> str:
    return {
        "qq": "QQClient",
        "qqguild": "QQGuild",
        "discord": "Discord",
        "wechat": "WeChat",
        "kaiheila": "Kaiheila",
    }.get(platform, "Onebot12")


def _ensure_satori_scope(platform: str) -> str:
    return {
        "red": "QQClient",
        "chronocat": "QQClient",
        "onebot": "QQClient",
        "nekobox": "QQClient",
        "lagrange": "QQClient",
        "lagrange.python": "QQClient",
        "qq": "QQAPI",
        "qqguild": "QQAPI",
        "telegram": "Telegram",
        "discord": "Discord",
        "feishu": "Feishu",
        "wechat-official": "WeChatOfficialAccountPlatform",
        "wecom": "WeCom",
        "kook": "Kaiheila",
        "dingtalk": "Ding",
        "mail": "Mail",
    }.get(platform, "satori")


def _load_target(raw: dict | str) -> dict:
    return json.loads(raw) if isinstance(raw, str) else raw


def _target_id(value) -> str:
    return str(value)


def _target(
    *,
    id,
    scope: str,
    parent_id: str = "",
    channel: bool = False,
    private: bool = False,
    adapter: str | None = None,
    platforms: list[str] | None = None,
    self_id: str | None = None,
    source: str = "",
    extra: dict | None = None,
) -> dict:
    data = {
        "id": _target_id(id),
        "parent_id": parent_id,
        "channel": channel,
        "private": private,
        "source": source,
        "extra": extra or {},
        "scope": scope,
    }
    if adapter:
        data["adapter"] = adapter
    if platforms:
        data["platforms"] = platforms
    if self_id:
        data["self_id"] = _target_id(self_id)
    return data


def _migrate_legacy_target(target: dict) -> dict | None:
    if "scope" in target and "id" in target:
        return target

    platform_type = target.get("platform_type")
    if platform_type == "QQ Group":
        return _target(
            id=target["group_id"],
            scope="QQClient",
        )
    if platform_type == "QQ Guild Channel":
        return _target(
            id=target["channel_id"],
            channel=True,
            scope="QQGuild",
        )
    if platform_type == "QQ Private":
        return _target(
            id=target["user_id"],
            private=True,
            scope="QQClient",
        )
    if platform_type == "QQ Group OpenID":
        return _target(
            id=target["group_openid"],
            scope="QQAPI",
            adapter="QQ",
            self_id=target["bot_id"],
        )
    if platform_type == "QQ Private OpenID":
        return _target(
            id=target["user_openid"],
            private=True,
            scope="QQAPI",
            adapter="QQ",
            self_id=target["bot_id"],
        )
    if platform_type == "QQ Guild Direct":
        return _target(
            id=target["recipient_id"],
            parent_id=_target_id(target["source_guild_id"]),
            channel=True,
            private=True,
            scope="QQAPI",
            adapter="QQ",
        )
    if platform_type == "Unknow Onebot 12 Platform":
        detail_type = target["detail_type"]
        if detail_type == "private":
            target_id = target["user_id"]
        elif detail_type == "channel":
            target_id = target["channel_id"]
        else:
            target_id = target["group_id"]
        platform = target["platform"]
        return _target(
            id=target_id,
            parent_id=_target_id(target.get("guild_id") or ""),
            channel=detail_type == "channel",
            private=detail_type == "private",
            scope=_ensure_ob12_scope(platform),
            adapter="OneBot V12",
            platforms=[platform],
        )
    if platform_type == "Unknown Satori Platform":
        platform = target["platform"]
        channel_id = target.get("channel_id")
        return _target(
            id=channel_id or target["user_id"],
            parent_id=_target_id(target.get("guild_id") or ""),
            private=not channel_id,
            scope=_ensure_satori_scope(platform),
            adapter="Satori",
            platforms=[platform],
        )
    if platform_type == "Kaiheila Channel":
        return _target(
            id=target["channel_id"],
            scope="Kaiheila",
            adapter="Kaiheila",
        )
    if platform_type == "Kaiheila Private":
        return _target(
            id=target["user_id"],
            private=True,
            scope="Kaiheila",
            adapter="Kaiheila",
        )
    if platform_type == "Telegram Common":
        return _target(
            id=target["chat_id"],
            scope="Telegram",
            adapter="Telegram",
        )
    if platform_type == "Telegram Forum":
        return _target(
            id=target["chat_id"],
            scope="Telegram",
            adapter="Telegram",
            extra={"message_thread_id": target["message_thread_id"]},
        )
    if platform_type == "Feishu Private":
        return _target(
            id=target["open_id"],
            private=True,
            scope="Feishu",
            adapter="Feishu",
        )
    if platform_type == "Feishu Group":
        return _target(
            id=target["chat_id"],
            scope="Feishu",
            adapter="Feishu",
        )
    if platform_type == "DoDo Channel":
        return _target(
            id=target["channel_id"],
            parent_id=_target_id(target.get("dodo_source_id") or ""),
            channel=True,
            scope="DoDo",
            adapter="DoDo",
        )
    if platform_type == "DoDo Private":
        return _target(
            id=target["dodo_source_id"],
            parent_id=target["island_source_id"],
            channel=True,
            private=True,
            scope="DoDo",
            adapter="DoDo",
        )
    if platform_type == "Discord Channel":
        return _target(
            id=target["channel_id"],
            channel=True,
            scope="Discord",
            adapter="Discord",
        )


def _downgrade_target(target: dict) -> dict | None:
    if "platform_type" in target:
        return target

    extra = target.get("extra") or {}
    scope = target.get("scope")
    target_id = target.get("id")
    if scope == "QQClient" and target.get("private"):
        return {"platform_type": "QQ Private", "user_id": target_id}
    if scope == "QQClient" and not target.get("channel"):
        return {"platform_type": "QQ Group", "group_id": target_id}
    if scope == "QQGuild" and target.get("channel"):
        return {"platform_type": "QQ Guild Channel", "channel_id": target_id}
    if scope == "Telegram" and "message_thread_id" in extra:
        return {
            "platform_type": "Telegram Forum",
            "chat_id": target_id,
            "message_thread_id": extra.get("message_thread_id"),
        }
    if scope == "Telegram":
        return {"platform_type": "Telegram Common", "chat_id": target_id}
    if scope == "DoDo" and target.get("private"):
        return {
            "platform_type": "DoDo Private",
            "island_source_id": target.get("parent_id"),
            "dodo_source_id": target_id,
        }
    if scope == "DoDo":
        return {
            "platform_type": "DoDo Channel",
            "channel_id": target_id,
            "dodo_source_id": target.get("parent_id"),
        }


def _deduplicate_schedules(schedules) -> None:
    unique_schedules = []
    unique_targets: list[Target] = []

    for schedule in schedules:
        raw_target = _load_target(schedule.target).copy()
        try:
            target = Target.load(raw_target)
        except Exception as e:
            logger.warning(
                f"wordcloud: 目标 {raw_target} 无法解析，已跳过去重: {e}"
            )
            continue

        for index, unique_target in enumerate(unique_targets):
            if target == unique_target:
                unique_schedules[index] = schedule
                unique_targets[index] = target
                break
        else:
            unique_schedules.append(schedule)
            unique_targets.append(target)

    duplicates = [
        schedule for schedule in schedules if schedule not in unique_schedules
    ]
    for schedule in duplicates:
        session = Session.object_session(schedule)
        assert session is not None
        session.delete(schedule)

    if duplicates:
        logger.info(f"wordcloud: 已合并 {len(duplicates)} 个重复定时发送计划")


def upgrade(name: str = "") -> None:
    if name:
        return
    # ### commands auto generated by Alembic - please adjust! ###
    Base = automap_base()
    Base.prepare(op.get_bind())
    Schedule = Base.classes.nonebot_plugin_wordcloud_schedule

    session = Session(op.get_bind())
    schedules = session.query(Schedule).all()
    logger.info(f"wordcloud: 发现 {len(schedules)} 个定时发送计划，正在迁移...")
    for schedule in schedules:
        target = _load_target(schedule.target)
        logger.debug(f"wordcloud: 正在迁移定时发送计划 {schedule.time} {target}")
        if migrated_target := _migrate_legacy_target(target):
            schedule.target = migrated_target
        else:
            logger.warning(
                f"wordcloud: 不支持的目标平台类型 {target.get('platform_type')}，已跳过"
            )
    _deduplicate_schedules(schedules)
    session.commit()

    # ### end Alembic commands ###


def downgrade(name: str = "") -> None:
    if name:
        return
    # ### commands auto generated by Alembic - please adjust! ###
    Base = automap_base()
    Base.prepare(op.get_bind())
    Schedule = Base.classes.nonebot_plugin_wordcloud_schedule

    session = Session(op.get_bind())
    schedules = session.query(Schedule).all()
    logger.info(f"wordcloud: 发现 {len(schedules)} 个定时发送计划，正在回滚迁移...")
    for schedule in schedules:
        target = _load_target(schedule.target)
        if downgraded_target := _downgrade_target(target):
            schedule.target = downgraded_target
        else:
            logger.warning(f"wordcloud: 不支持的目标 {target}，已跳过")
    session.commit()
    # ### end Alembic commands ###
