import contextlib
from datetime import datetime, time, tzinfo
from zoneinfo import ZoneInfo

from nonebot.matcher import Matcher
from nonebot.permission import SUPERUSER
from nonebot_plugin_alconna import Target
from nonebot_plugin_apscheduler import scheduler
from nonebot_plugin_uninfo import SceneType, Session, UniSession

from .config import plugin_config


def get_datetime_now_with_timezone() -> datetime:
    """获取包含时区信息的当前时间。

    Returns:
        根据插件配置时区或系统本地时区生成的当前时间。
    """
    if plugin_config.wordcloud_timezone:
        return datetime.now(ZoneInfo(plugin_config.wordcloud_timezone))
    else:
        return datetime.now().astimezone()


def get_datetime_fromisoformat_with_timezone(date_string: str) -> datetime:
    """从 ISO-8601 字符串中解析包含时区信息的时间。

    Args:
        date_string: ISO-8601 日期时间字符串。

    Returns:
        根据插件配置时区或输入时区规范化后的 datetime。
    """
    if not plugin_config.wordcloud_timezone:
        return datetime.fromisoformat(date_string).astimezone()
    raw = datetime.fromisoformat(date_string)
    return (
        raw.astimezone(ZoneInfo(plugin_config.wordcloud_timezone))
        if raw.tzinfo
        else raw.replace(tzinfo=ZoneInfo(plugin_config.wordcloud_timezone))
    )


def time_astimezone(time: time, tz: tzinfo | None = None) -> time:
    """将 time 对象转换为指定时区。

    Args:
        time: 需要转换的时间。
        tz: 目标时区；为空时转换为系统本地时区。

    Returns:
        转换到目标时区后的 time 对象。
    """
    local_time = datetime.combine(datetime.today(), time)
    return local_time.astimezone(tz).timetz()


def get_time_fromisoformat_with_timezone(time_string: str) -> time:
    """从 ISO-8601 字符串中解析包含时区信息的时间。

    Args:
        time_string: ISO-8601 时间字符串。

    Returns:
        根据插件配置时区或输入时区规范化后的 time 对象。
    """
    if not plugin_config.wordcloud_timezone:
        return time_astimezone(time.fromisoformat(time_string))
    raw = time.fromisoformat(time_string)
    return (
        time_astimezone(raw, ZoneInfo(plugin_config.wordcloud_timezone))
        if raw.tzinfo
        else raw.replace(tzinfo=ZoneInfo(plugin_config.wordcloud_timezone))
    )


def get_time_with_scheduler_timezone(time: time) -> time:
    """将时间转换到 APScheduler 使用的时区。

    Args:
        time: 需要转换的时间。

    Returns:
        转换到 APScheduler 时区后的 time 对象。
    """
    return time_astimezone(time, scheduler.timezone)


def admin_permission():
    """构造管理词云命令所需的权限。

    Returns:
        超级用户权限，以及可用时的 OneBot V11 群主和管理员权限。
    """
    permission = SUPERUSER
    with contextlib.suppress(ImportError):
        from nonebot.adapters.onebot.v11.permission import GROUP_ADMIN, GROUP_OWNER

        permission = permission | GROUP_ADMIN | GROUP_OWNER

    return permission


def get_mask_key(session: Session | Target = UniSession()) -> str:
    """获取会话对应的 mask key。

    平台名称和会话场景 ID 组成，例如 `QQClient_123456789`。

    Args:
        session: 统一会话或 Alconna 发送目标。

    Returns:
        用于存储和读取 mask 文件的 key。
    """
    if isinstance(session, Target):
        scope = getattr(session.scope, "value", session.scope)
        scene_path = (
            f"{session.parent_id}_{session.id}" if session.parent_id else session.id
        )
        return f"{scope}_{scene_path}" if scope else scene_path

    scope = getattr(session.scope, "value", session.scope)
    return f"{scope}_{session.scene_path}"


async def ensure_group(matcher: Matcher, session: Session = UniSession()):
    """确保命令在群组、频道或频道文字场景中使用。

    Args:
        matcher: 当前 matcher。
        session: 当前统一会话信息。
    """
    if session.scene.type not in [
        SceneType.GROUP,
        SceneType.GUILD,
        SceneType.CHANNEL_TEXT,
    ]:
        await matcher.finish("请在群组中使用！")
