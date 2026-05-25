import contextlib
from datetime import datetime, time, timedelta, tzinfo
from zoneinfo import ZoneInfo

from nonebot.matcher import Matcher
from nonebot.permission import SUPERUSER
from nonebot_plugin_alconna import Target
from nonebot_plugin_apscheduler import scheduler
from nonebot_plugin_uninfo import SceneType, Session, UniSession

from .config import plugin_config
from .model import ScheduleType


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


def get_period_start(dt: datetime, schedule_type: ScheduleType) -> datetime:
    """获取当前周期的起始时间。

    Args:
        dt: 用于计算周期的基准时间。
        schedule_type: 周期类型。

    Returns:
        当前周期的起始时间。
    """
    current_day_start = dt.replace(hour=0, minute=0, second=0, microsecond=0)
    if schedule_type == ScheduleType.DAY:
        return current_day_start
    if schedule_type == ScheduleType.WEEK:
        return current_day_start - timedelta(days=dt.weekday())
    if schedule_type == ScheduleType.MONTH:
        return current_day_start.replace(day=1)
    if schedule_type == ScheduleType.YEAR:
        return current_day_start.replace(month=1, day=1)
    raise ValueError(f"未知的周期类型：{schedule_type}")


def get_current_period_range(
    dt: datetime, schedule_type: ScheduleType
) -> tuple[datetime, datetime]:
    """获取当前周期从开始到基准时间的范围。

    Args:
        dt: 用于计算周期的基准时间。
        schedule_type: 周期类型。

    Returns:
        当前周期的起止时间。
    """
    return get_period_start(dt, schedule_type), dt


def get_previous_period_range(
    dt: datetime, schedule_type: ScheduleType
) -> tuple[datetime, datetime]:
    """获取上一完整周期的时间范围。

    Args:
        dt: 用于计算周期的基准时间。
        schedule_type: 周期类型。

    Returns:
        上一完整周期的起止时间。
    """
    stop = get_period_start(dt, schedule_type)
    if schedule_type == ScheduleType.DAY:
        return stop - timedelta(days=1), stop
    if schedule_type == ScheduleType.WEEK:
        return stop - timedelta(days=7), stop
    if schedule_type == ScheduleType.MONTH:
        last_month = stop - timedelta(days=1)
        return last_month.replace(day=1), stop
    if schedule_type == ScheduleType.YEAR:
        return stop.replace(year=stop.year - 1), stop
    raise ValueError(f"未知的周期类型：{schedule_type}")


def is_period_start(dt: datetime, schedule_type: ScheduleType) -> bool:
    """判断基准时间是否位于周期开始日。

    Args:
        dt: 用于判断的基准时间。
        schedule_type: 周期类型。

    Returns:
        当前日期是否为对应周期的开始日。
    """
    if schedule_type == ScheduleType.DAY:
        return True
    if schedule_type == ScheduleType.WEEK:
        return dt.weekday() == 0
    if schedule_type == ScheduleType.MONTH:
        return dt.day == 1
    if schedule_type == ScheduleType.YEAR:
        return dt.month == 1 and dt.day == 1
    return False


def is_period_end(dt: datetime, schedule_type: ScheduleType) -> bool:
    """判断基准时间是否位于周期结束日。

    Args:
        dt: 用于判断的基准时间。
        schedule_type: 周期类型。

    Returns:
        当前日期是否为对应周期的结束日。
    """
    if schedule_type == ScheduleType.DAY:
        return True
    if schedule_type == ScheduleType.WEEK:
        return dt.weekday() == 6
    if schedule_type == ScheduleType.MONTH:
        current_day_start = dt.replace(hour=0, minute=0, second=0, microsecond=0)
        return (current_day_start + timedelta(days=1)).day == 1
    if schedule_type == ScheduleType.YEAR:
        return dt.month == 12 and dt.day == 31
    return False


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
