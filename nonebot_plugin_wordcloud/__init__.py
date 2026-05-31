"""词云"""

import re
from datetime import datetime, timedelta
from io import BytesIO
from typing import Any

import PIL.Image
from nonebot import require

require("nonebot_plugin_apscheduler")
require("nonebot_plugin_alconna")
require("nonebot_plugin_uninfo")
require("nonebot_plugin_chatrecorder")
require("nonebot_plugin_permission")
from arclet.alconna import ArparmaBehavior
from arclet.alconna.arparma import Arparma
from nonebot import get_driver
from nonebot.adapters import Bot, Event, Message
from nonebot.params import Arg, Depends
from nonebot.permission import SUPERUSER
from nonebot.plugin import PluginMetadata, inherit_supported_adapters
from nonebot.typing import T_State
from nonebot_plugin_alconna import (
    Alconna,
    AlconnaMatch,
    AlconnaMatcher,
    AlconnaQuery,
    Args,
    AtID,
    CommandMeta,
    Image,
    Match,
    MessageTarget,
    Option,
    Query,
    Target,
    image_fetch,
    on_alconna,
    store_true,
)
from nonebot_plugin_chatrecorder import get_messages_plain_text
from nonebot_plugin_uninfo import Session, UniSession

from .config import Config, plugin_config
from .data_source import get_wordcloud
from .model import ScheduleMode, ScheduleType
from .schedule import schedule_service
from .utils import (
    WORDCLOUD_DEFAULT_MASK_PERMISSION,
    WORDCLOUD_MASK_PERMISSION,
    WORDCLOUD_QUERY_OTHER_PERMISSION,
    WORDCLOUD_QUERY_PERMISSION,
    WORDCLOUD_SCHEDULE_PERMISSION,
    admin_permission,
    check_wordcloud_permission,
    ensure_group,
    get_current_period_range,
    get_datetime_fromisoformat_with_timezone,
    get_datetime_now_with_timezone,
    get_mask_key,
    get_previous_period_range,
    get_time_fromisoformat_with_timezone,
    legacy_admin_permission,
    wordcloud_permission,
)

get_driver().on_startup(schedule_service.update)


def get_usage() -> str:
    """根据当前配置生成插件完整使用说明。

    Returns:
        面向用户展示的插件使用说明。
    """
    if plugin_config.wordcloud_default_personal:
        # 默认个人数据
        default_behavior = '- 默认获取个人数据，如需获取群组数据请添加前缀"本群"'
        prefix_examples = """\
格式：/本群<时间段>词云
示例：/本群今日词云
/本群年度词云
- 在上方所给的命令格式基础上，还可以添加前缀"我的"，以明确获取自己的词云
格式：/我的<基本命令格式>
示例：/我的今日词云
/我的昨日词云"""
    else:
        # 默认群组数据
        default_behavior = '- 默认获取群组数据，如需获取个人数据请添加前缀"我的"'
        prefix_examples = """\
格式：/我的<时间段>词云
示例：/我的今日词云
/我的昨日词云
- 在上方所给的命令格式基础上，还可以添加前缀"本群"，以明确获取群组数据
格式：/本群<基本命令格式>
示例：/本群今日词云
/本群年度词云"""

    return f"""\
- 通过快捷命令，以获取常见时间段内的词云
格式：/<时间段>词云
时间段关键词有：今日，昨日，本周，上周，本月，上月，年度
示例：/今日词云，/昨日词云
超级用户或拥有 command.wordcloud.query_other 权限的用户可以通过 @群友 获取该群友的词云
示例：/今日词云 @群友

- 提供日期与时间，以获取指定时间段内的词云
（支持 ISO8601 格式的日期与时间，如 2022-02-22T22:22:22）
格式：/历史词云 [日期或时间段]
示例：/历史词云
/历史词云 2022-01-01
/历史词云 2022-01-01~2022-02-22
/历史词云 2022-02-22T11:11:11~2022-02-22T22:22:22

{default_behavior}
{prefix_examples}

- 设置自定义词云形状
格式：/设置词云形状
/设置词云形状

- 设置默认词云形状（仅超级用户或拥有 command.wordcloud.default_mask 权限）
格式：/设置词云默认形状
/删除词云默认形状

- 设置定时发送词云
格式：/词云每日定时发送状态
/词云每周定时发送状态
/开启词云每日定时发送
/开启词云每月定时发送
/开启词云每日定时发送 23:59
/开启词云每周周期末定时发送
/开启词云每周完整周期定时发送
/关闭词云每日定时发送
/关闭词云每年定时发送
支持类型：每日，每周，每月，每年
没有指定模式时使用默认发送模式，添加 --last 或“周期末”可在周期最后一天发送，
添加 --complete 或“完整周期”可发送上一完整周期"""


def get_wordcloud_cmd_usage() -> str:
    """根据当前配置生成词云命令的简短使用说明。

    Returns:
        面向命令帮助展示的简短使用说明。
    """

    usage = (
        "- 通过快捷命令，以获取常见时间段内的词云\n"
        "格式：/<时间段>词云\n"
        "时间段关键词有：今日，昨日，本周，上周，本月，上月，年度\n"
        "- 提供日期与时间，以获取指定时间段内的词云\n"
        "（支持 ISO8601 格式的日期与时间，如 2022-02-22T22:22:22）\n"
        "格式：/历史词云 [日期或时间段]\n"
    )

    if plugin_config.wordcloud_default_personal:
        usage += (
            "- 默认获取个人数据，如需获取群组数据请使用'本群'前缀\n"
            "- 可以添加前缀'我的'来明确获取个人数据"
        )
    else:
        usage += (
            "- 默认获取群组数据，如需获取个人数据请使用'我的'前缀\n"
            "- 可以添加前缀'本群'来明确获取群组数据"
        )

    return usage


__plugin_meta__ = PluginMetadata(
    name="词云",
    description="利用群消息生成词云",
    usage=get_usage(),
    homepage="https://github.com/he0119/nonebot-plugin-wordcloud",
    type="application",
    supported_adapters=inherit_supported_adapters(
        "nonebot_plugin_chatrecorder",
        "nonebot_plugin_uninfo",
        "nonebot_plugin_alconna",
        "nonebot_plugin_permission",
    ),
    config=Config,
)


class SameTime(ArparmaBehavior):
    def operate(self, interface: Arparma):
        """阻止只传入时间但未传入词云类型的命令。

        Args:
            interface: Alconna 解析结果操作接口。
        """
        type = interface.query("type")
        time = interface.query("time")
        if type is None and time:
            interface.behave_fail()


wordcloud_cmd = on_alconna(
    Alconna(
        "词云",
        Option(
            "--my",
            default=False,
            action=store_true,
            help_text="获取自己的词云",
        ),
        Option(
            "--group",
            default=False,
            action=store_true,
            help_text="获取群组的词云",
        ),
        Args["type?", ["今日", "昨日", "本周", "上周", "本月", "上月", "年度", "历史"]][
            "time?", str
        ]["user?", AtID],
        behaviors=[SameTime()],
        meta=CommandMeta(
            description="利用群消息生成词云",
            usage=get_wordcloud_cmd_usage(),
            example=(
                "/今日词云\n"
                "/我的昨日词云\n"
                "/本群今日词云\n"
                "/历史词云\n"
                "/历史词云 2022-01-01\n"
                "/历史词云 2022-01-01~2022-02-22\n"
                "/历史词云 2022-02-22T11:11:11~2022-02-22T22:22:22\n"
                "/今日词云 @群友"
            ),
        ),
    ),
    permission=wordcloud_permission(WORDCLOUD_QUERY_PERMISSION),
    use_cmd_start=True,
    block=True,
)


def wrapper(slot: int | str, content: str | None, context: dict[str, Any]) -> str:
    """将快捷命令捕获的分组转换为真实命令参数。

    Args:
        slot: 当前处理的快捷命令槽位。
        content: 槽位捕获到的文本内容。
        context: 快捷命令解析上下文。

    Returns:
        传递给 Alconna 的命令参数片段。
    """
    if slot == "my" and content:
        return "--my"
    elif slot == "group" and content:
        return "--group"
    elif slot == "type" and content:
        return content
    return ""  # pragma: no cover


wordcloud_cmd.shortcut(
    r"(?P<group>本群)?(?P<my>我的)?(?P<type>今日|昨日|本周|上周|本月|上月|年度|历史)词云",
    {
        "prefix": True,
        "command": "词云",
        "wrapper": wrapper,
        "args": ["{group}", "{my}", "{type}"],
        "humanized": "[本群|我的]<类型>词云",
    },
)


def parse_datetime(key: str):
    """构造日期参数解析器，并将结果存入 matcher state。

    Args:
        key: 需要解析并写入 state 的参数名。

    Returns:
        用于 ``got`` 参数校验的异步解析函数。
    """

    async def _key_parser(
        matcher: AlconnaMatcher,
        state: T_State,
        input: datetime | Message = Arg(key),
    ):
        """解析用户输入的 ISO-8601 日期时间文本。

        Args:
            matcher: 当前 Alconna matcher。
            state: NoneBot matcher state。
            input: 已解析的 datetime 或用户输入消息。
        """
        if isinstance(input, datetime):
            return

        plaintext = input.extract_plain_text()
        try:
            state[key] = get_datetime_fromisoformat_with_timezone(plaintext)
        except ValueError:
            await matcher.reject_arg(key, "请输入正确的日期，不然我没法理解呢！")

    return _key_parser


@wordcloud_cmd.handle(parameterless=[Depends(ensure_group)])
async def handle_first_receive(
    state: T_State, type: str | None = None, time: str | None = None
):
    """处理词云命令首次接收并推导查询时间范围。

    Args:
        state: NoneBot matcher state，用于保存查询起止时间。
        type: 用户请求的时间段类型。
        time: 历史词云命令携带的日期或日期范围文本。
    """
    dt = get_datetime_now_with_timezone()

    if not type:
        await wordcloud_cmd.finish(__plugin_meta__.usage)

    match type:
        case "今日":
            state["start"], state["stop"] = get_current_period_range(
                dt, ScheduleType.DAY
            )
        case "昨日":
            state["start"], state["stop"] = get_previous_period_range(
                dt, ScheduleType.DAY
            )
        case "本周":
            state["start"], state["stop"] = get_current_period_range(
                dt, ScheduleType.WEEK
            )
        case "上周":
            state["start"], state["stop"] = get_previous_period_range(
                dt, ScheduleType.WEEK
            )
        case "本月":
            state["start"], state["stop"] = get_current_period_range(
                dt, ScheduleType.MONTH
            )
        case "上月":
            state["start"], state["stop"] = get_previous_period_range(
                dt, ScheduleType.MONTH
            )
        case "年度":
            state["start"], state["stop"] = get_current_period_range(
                dt, ScheduleType.YEAR
            )
        case "历史":
            if time:
                plaintext = time
                if match := re.match(r"^(.+?)(?:~(.+))?$", plaintext):
                    start = match[1]
                    stop = match[2]
                    try:
                        state["start"] = get_datetime_fromisoformat_with_timezone(start)
                        if stop:
                            state["stop"] = get_datetime_fromisoformat_with_timezone(
                                stop
                            )
                        else:
                            # 如果没有指定结束日期，则认为是所给日期的当天的词云
                            state["start"] = state["start"].replace(
                                hour=0, minute=0, second=0, microsecond=0
                            )
                            state["stop"] = state["start"] + timedelta(days=1)
                    except ValueError:
                        await wordcloud_cmd.finish(
                            "请输入正确的日期，不然我没法理解呢！"
                        )


@wordcloud_cmd.got(
    "start",
    prompt="请输入你要查询的起始日期（如 2022-01-01）",
    parameterless=[Depends(parse_datetime("start"))],
)
@wordcloud_cmd.got(
    "stop",
    prompt="请输入你要查询的结束日期（如 2022-02-22）",
    parameterless=[Depends(parse_datetime("stop"))],
)
async def handle_wordcloud(
    bot: Bot,
    event: Event,
    my: Query[bool] = AlconnaQuery("my.value", False),
    group: Query[bool] = AlconnaQuery("group.value", False),
    user: Match[str] = AlconnaMatch("user"),
    session: Session = UniSession(),
    start: datetime = Arg(),
    stop: datetime = Arg(),
    mask_key: str = Depends(get_mask_key),
):
    """查询聊天记录并发送生成的词云图片。

    Args:
        my: 是否显式查询个人词云。
        group: 是否显式查询群组词云。
        user: 可选的被 @ 用户 ID。
        session: 当前统一会话信息。
        start: 查询开始时间。
        stop: 查询结束时间。
        mask_key: 当前会话对应的 mask key。
    """
    # 决定是否过滤用户数据
    # 如果显式指定了 --my，则获取个人数据
    # 如果显式指定了 --group，则获取群组数据
    # 如果都没有指定，则根据配置决定默认行为
    if my.result:
        filter_user = True
    elif group.result:
        filter_user = False
    else:
        # 使用配置中的默认行为
        filter_user = plugin_config.wordcloud_default_personal

    user_ids = None
    at_sender = filter_user
    if user.available:
        user_ids = [user.result]
        filter_user = False
        at_sender = False
        if user.result != session.user.id and not await check_wordcloud_permission(
            WORDCLOUD_QUERY_OTHER_PERMISSION,
            bot,
            event,
            session,
            legacy_permission=SUPERUSER,
        ):
            await wordcloud_cmd.finish("仅超级用户可查看其他群友的词云")

    messages = await get_messages_plain_text(
        session=session,
        filter_user=filter_user,
        filter_self_id=False,
        filter_adapter=False,
        types=["message"],  # 排除机器人自己发的消息
        time_start=start,
        time_stop=stop,
        user_ids=user_ids,
        exclude_user_ids=plugin_config.wordcloud_exclude_user_ids,
    )

    if not (image := await get_wordcloud(messages, mask_key)):
        await wordcloud_cmd.finish(
            "没有足够的数据生成词云",
            at_sender=at_sender,
            reply=plugin_config.wordcloud_reply_message,
        )

    await wordcloud_cmd.finish(
        Image(raw=image, name="wordcloud.png"),
        at_sender=at_sender,
        reply=plugin_config.wordcloud_reply_message,
    )


set_mask_cmd = on_alconna(
    Alconna(
        "设置词云形状",
        Option("--default", default=False, action=store_true, help_text="默认形状"),
        Args["img?", Image],
        meta=CommandMeta(
            description="设置自定义词云形状",
            example="/设置词云形状\n/设置词云默认形状",
        ),
    ),
    permission=admin_permission(WORDCLOUD_MASK_PERMISSION)
    | wordcloud_permission(
        WORDCLOUD_DEFAULT_MASK_PERMISSION,
        legacy_permission=SUPERUSER,
    ),
    use_cmd_start=True,
    block=True,
)
set_mask_cmd.shortcut(
    "设置词云默认形状",
    {
        "prefix": True,
        "command": "设置词云形状",
        "args": ["--default"],
    },
)


@set_mask_cmd.handle(parameterless=[Depends(ensure_group)])
async def _(
    matcher: AlconnaMatcher,
    img: Match[bytes] = AlconnaMatch("img", image_fetch),
):
    """接收可选图片参数并转交给后续路径参数。

    Args:
        matcher: 当前 Alconna matcher。
        img: 命令中直接携带的图片匹配结果。
    """
    if img.available:
        matcher.set_path_arg("img", img.result)


@set_mask_cmd.got_path("img", "请发送一张图片作为词云形状", image_fetch)
async def handle_save_mask(
    bot: Bot,
    event: Event,
    img: bytes,
    default: Query[bool] = AlconnaQuery("default.value", default=False),
    session: Session = UniSession(),
    mask_key: str = Depends(get_mask_key),
):
    """保存用户上传的词云 mask 图片。

    Args:
        bot: 当前机器人实例。
        event: 当前消息事件。
        img: 用户发送的图片原始字节。
        default: 是否设置为全局默认 mask。
        mask_key: 当前会话对应的 mask key。
    """
    mask = PIL.Image.open(BytesIO(img))
    if default.result:
        if not await check_wordcloud_permission(
            WORDCLOUD_DEFAULT_MASK_PERMISSION,
            bot,
            event,
            session,
            legacy_permission=SUPERUSER,
        ):
            await set_mask_cmd.finish("仅超级用户可设置词云默认形状")
        mask.save(plugin_config.get_mask_path(), format="PNG")
        await set_mask_cmd.finish("词云默认形状设置成功")
    else:
        if not await check_wordcloud_permission(
            WORDCLOUD_MASK_PERMISSION,
            bot,
            event,
            session,
            legacy_permission=legacy_admin_permission(),
        ):
            await set_mask_cmd.finish("仅超级用户、群主或管理员可设置词云形状")
        mask.save(plugin_config.get_mask_path(mask_key), format="PNG")
        await set_mask_cmd.finish("词云形状设置成功")


remove_mask_cmd = on_alconna(
    Alconna(
        "删除词云形状",
        Option("--default", default=False, action=store_true, help_text="默认形状"),
        meta=CommandMeta(
            description="删除自定义词云形状",
            example="/删除词云形状\n/删除词云默认形状",
        ),
    ),
    permission=admin_permission(WORDCLOUD_MASK_PERMISSION)
    | wordcloud_permission(
        WORDCLOUD_DEFAULT_MASK_PERMISSION,
        legacy_permission=SUPERUSER,
    ),
    use_cmd_start=True,
    block=True,
)
remove_mask_cmd.shortcut(
    "删除词云默认形状",
    {
        "prefix": True,
        "command": "删除词云形状",
        "args": ["--default"],
    },
)


@remove_mask_cmd.handle(parameterless=[Depends(ensure_group)])
async def _(
    bot: Bot,
    event: Event,
    default: Query[bool] = AlconnaQuery("default.value", default=False),
    session: Session = UniSession(),
    mask_key: str = Depends(get_mask_key),
):
    """删除当前会话或全局默认的词云 mask 图片。

    Args:
        bot: 当前机器人实例。
        event: 当前消息事件。
        default: 是否删除全局默认 mask。
        mask_key: 当前会话对应的 mask key。
    """
    if default.result:
        if not await check_wordcloud_permission(
            WORDCLOUD_DEFAULT_MASK_PERMISSION,
            bot,
            event,
            session,
            legacy_permission=SUPERUSER,
        ):
            await remove_mask_cmd.finish("仅超级用户可删除词云默认形状")
        mask_path = plugin_config.get_mask_path()
        mask_path.unlink(missing_ok=True)
        await remove_mask_cmd.finish("词云默认形状已删除")
    else:
        if not await check_wordcloud_permission(
            WORDCLOUD_MASK_PERMISSION,
            bot,
            event,
            session,
            legacy_permission=legacy_admin_permission(),
        ):
            await remove_mask_cmd.finish("仅超级用户、群主或管理员可删除词云形状")
        mask_path = plugin_config.get_mask_path(mask_key)
        mask_path.unlink(missing_ok=True)
        await remove_mask_cmd.finish("词云形状已删除")


schedule_cmd = on_alconna(
    Alconna(
        "词云定时发送",
        Option(
            "--last",
            default=False,
            action=store_true,
            help_text="在周期最后一天发送",
        ),
        Option(
            "--complete",
            default=False,
            action=store_true,
            help_text="发送上一完整周期",
        ),
        Option(
            "--action",
            Args["action_type", ["状态", "开启", "关闭"]],
            default="状态",
            help_text="操作类型",
        ),
        Args["type", ["每日", "每周", "每月", "每年"]]["time?", str],
        meta=CommandMeta(
            description="设置定时发送词云",
            usage="支持每日、每周、每月、每年定时发送",
            example=(
                "/词云每日定时发送状态\n"
                "/词云每周定时发送状态\n"
                "/开启词云每日定时发送\n"
                "/开启词云每月定时发送\n"
                "/开启词云每日定时发送 23:59\n"
                "/开启词云每周周期末定时发送\n"
                "/关闭词云每日定时发送\n"
                "/关闭词云每年定时发送"
            ),
        ),
    ),
    permission=admin_permission(WORDCLOUD_SCHEDULE_PERMISSION),
    use_cmd_start=True,
    block=True,
)


def schedule_wrapper(slot: int | str, content: str | None, context: dict[str, Any]):
    """将定时发送快捷命令中的模式文本转换为选项参数。

    Args:
        slot: 当前处理的快捷命令槽位。
        content: 槽位捕获到的文本内容。
        context: 快捷命令解析上下文。

    Returns:
        传递给 Alconna 的命令参数片段。
    """
    if slot == "mode" and content:
        return "--last" if content == "周期末" else "--complete"
    return content or ""


schedule_cmd.shortcut(
    r"词云(?P<type>每日|每周|每月|每年)定时发送状态",
    {
        "prefix": True,
        "command": "词云定时发送",
        "args": ["--action", "状态", "{type}"],
        "humanized": "词云<类型>定时发送状态",
    },
)
schedule_cmd.shortcut(
    r"(?P<action>开启|关闭)词云(?P<type>每日|每周|每月|每年)(?P<mode>周期末|完整周期)?定时发送(?:\s+(?P<time>\S+))?",
    {
        "prefix": True,
        "command": "词云定时发送",
        "wrapper": schedule_wrapper,
        "args": ["{mode}", "--action", "{action}", "{type}", "{time}"],
        "humanized": "<开启|关闭>词云<类型>定时发送",
    },
)


@schedule_cmd.handle(parameterless=[Depends(ensure_group)])
async def _(
    type: str = "每日",
    time: str | None = None,
    last: Query[bool] = AlconnaQuery("last.value", False),
    complete: Query[bool] = AlconnaQuery("complete.value", False),
    action_type: Query[str] = AlconnaQuery("action.action_type.value", "状态"),
    target: Target = MessageTarget(),
):
    """处理定时发送状态查询、开启和关闭命令。

    Args:
        type: 定时发送类型文本。
        time: 可选的定时发送时间文本。
        last: 是否使用周期末发送模式。
        complete: 是否使用完整周期发送模式。
        action_type: 定时发送操作类型。
        target: 当前消息发送目标。
    """
    schedule_type = ScheduleType(type)
    match action_type.result:
        case "状态":
            schedule_info = await schedule_service.get_schedule_info(
                target, schedule_type
            )
            await schedule_cmd.finish(
                f"词云{schedule_type.value}定时发送已开启，发送时间为：{schedule_info[0]}，发送模式为：{schedule_info[1].value}"
                if schedule_info
                else f"词云{schedule_type.value}定时发送未开启"
            )
        case "开启":
            if last.result and complete.result:
                await schedule_cmd.finish(
                    "请选择一种发送模式，不要同时指定完整周期和周期末"
                )
            if last.result:
                schedule_mode = ScheduleMode.PERIOD_END
            elif complete.result:
                schedule_mode = ScheduleMode.COMPLETE
            else:
                schedule_mode = plugin_config.wordcloud_default_schedule_mode
            schedule_time = None
            if time:
                try:
                    schedule_time = get_time_fromisoformat_with_timezone(time)
                except ValueError:
                    await schedule_cmd.finish("请输入正确的时间，不然我没法理解呢！")
            await schedule_service.add_schedule(
                target,
                time=schedule_time,
                schedule_type=schedule_type,
                schedule_mode=schedule_mode,
            )
            mode_message = (
                f"，发送模式为：{schedule_mode.value}"
                if schedule_mode == ScheduleMode.PERIOD_END
                else ""
            )
            default_schedule_time = plugin_config.get_default_schedule_time(
                schedule_mode
            )
            await schedule_cmd.finish(
                f"已开启词云{schedule_type.value}定时发送，发送时间为：{schedule_time}{mode_message}"
                if schedule_time
                else f"已开启词云{schedule_type.value}定时发送，发送时间为：{default_schedule_time}{mode_message}"  # noqa: E501
            )
        case "关闭":
            await schedule_service.remove_schedule(target, schedule_type)
            await schedule_cmd.finish(f"已关闭词云{schedule_type.value}定时发送")
