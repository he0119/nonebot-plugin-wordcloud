""" 词云
"""
import re
from datetime import datetime, timedelta
from io import BytesIO
from typing import Tuple, Union

try:
    from zoneinfo import ZoneInfo
except ImportError:
    from backports.zoneinfo import ZoneInfo  # type: ignore

from nonebot import CommandGroup, get_driver, require
from nonebot.adapters import Bot
from nonebot.adapters.onebot.v11 import GroupMessageEvent, Message, MessageSegment
from nonebot.adapters.onebot.v11.permission import GROUP_ADMIN, GROUP_OWNER
from nonebot.matcher import Matcher
from nonebot.params import Arg, Command, CommandArg, Depends
from nonebot.permission import SUPERUSER
from nonebot.plugin import PluginMetadata
from nonebot.typing import T_State
from PIL import Image

require("nonebot_plugin_apscheduler")
require("nonebot_plugin_chatrecorder")
require("nonebot_plugin_datastore")
from nonebot_plugin_chatrecorder import get_message_records

from .config import DATA, plugin_config
from .data_source import get_wordcloud
from .schedule import schedule_service
from .utils import (
    get_datetime_fromisoformat_with_timezone,
    get_datetime_now_with_timezone,
    get_time_fromisoformat_with_timezone,
)

driver = get_driver()
driver.on_startup(schedule_service.update)

__plugin_meta__ = PluginMetadata(
    name="词云",
    description="利用群消息生成词云",
    usage="""获取今天的词云
/今日词云
获取昨天的词云
/昨日词云
获取本周词云
/本周词云
获取本月词云
/本月词云
获取年度词云
/年度词云

历史词云(支持 ISO8601 格式的日期与时间，如 2022-02-22T22:22:22)
获取某日的词云
/历史词云 2022-01-01
获取指定时间段的词云
/历史词云
/历史词云 2022-01-01~2022-02-22
/历史词云 2022-02-22T11:11:11~2022-02-22T22:22:22

如果想要获取自己的发言，可在命令前添加 我的
/我的今日词云

自定义词云形状
/设置词云形状
/设置词云默认形状
/删除词云形状
/删除词云默认形状

设置定时发送每日词云
/词云每日定时发送状态
/开启词云每日定时发送
/关闭词云每日定时发送
""",
)

wordcloud = CommandGroup("wordcloud")


wordcloud_cmd = wordcloud.command(
    "main",
    aliases={
        "词云",
        "今日词云",
        "昨日词云",
        "本周词云",
        "本月词云",
        "年度词云",
        "历史词云",
        "我的今日词云",
        "我的昨日词云",
        "我的本周词云",
        "我的本月词云",
        "我的年度词云",
        "我的历史词云",
    },
)


def parse_datetime(key: str):
    """解析数字，并将结果存入 state 中"""

    async def _key_parser(
        matcher: Matcher,
        state: T_State,
        input: Union[datetime, Message] = Arg(key),
    ):
        if isinstance(input, datetime):
            return

        plaintext = input.extract_plain_text()
        try:
            state[key] = get_datetime_fromisoformat_with_timezone(plaintext)
        except ValueError:
            await matcher.reject_arg(key, "请输入正确的日期，不然我没法理解呢！")

    return _key_parser


@wordcloud_cmd.handle()
async def handle_first_receive(
    event: GroupMessageEvent,
    state: T_State,
    commands: Tuple[str, ...] = Command(),
    args: Message = CommandArg(),
):
    command = commands[0]

    if command.startswith("我的"):
        state["my"] = True
        command = command[2:]
    else:
        state["my"] = False

    if command == "今日词云":
        dt = get_datetime_now_with_timezone()
        state["start"] = dt.replace(hour=0, minute=0, second=0, microsecond=0)
        state["stop"] = dt
    elif command == "昨日词云":
        dt = get_datetime_now_with_timezone()
        state["stop"] = dt.replace(hour=0, minute=0, second=0, microsecond=0)
        state["start"] = state["stop"] - timedelta(days=1)
    elif command == "本周词云":
        dt = get_datetime_now_with_timezone()
        state["start"] = dt.replace(
            hour=0, minute=0, second=0, microsecond=0
        ) - timedelta(days=dt.weekday())
        state["stop"] = dt
    elif command == "本月词云":
        dt = get_datetime_now_with_timezone()
        state["start"] = dt.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        state["stop"] = dt
    elif command == "年度词云":
        dt = get_datetime_now_with_timezone()
        state["start"] = dt.replace(
            month=1, day=1, hour=0, minute=0, second=0, microsecond=0
        )
        state["stop"] = dt
    elif command == "历史词云":
        plaintext = args.extract_plain_text().strip()
        match = re.match(r"^(.+?)(?:~(.+))?$", plaintext)
        if match:
            start = match.group(1)
            stop = match.group(2)
            try:
                state["start"] = get_datetime_fromisoformat_with_timezone(start)
                if stop:
                    state["stop"] = get_datetime_fromisoformat_with_timezone(stop)
                else:
                    # 如果没有指定结束日期，则认为是指查询这一天的词云
                    state["start"] = state["start"].replace(
                        hour=0, minute=0, second=0, microsecond=0
                    )
                    state["stop"] = state["start"] + timedelta(days=1)
            except ValueError:
                await wordcloud_cmd.finish("请输入正确的日期，不然我没法理解呢！")
    else:
        plaintext = args.extract_plain_text()
        # 当完整匹配词云的时候才输出帮助信息
        if not plaintext:
            await wordcloud_cmd.finish(__plugin_meta__.usage)
        else:
            await wordcloud_cmd.finish()


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
async def handle_message(
    bot: Bot,
    event: GroupMessageEvent,
    start: datetime = Arg(),
    stop: datetime = Arg(),
    my: bool = Arg(),
):
    # 是否只查询自己的记录
    if my:
        user_ids = [str(event.user_id)]
    else:
        user_ids = None

    # 排除机器人自己发的消息
    # 将时间转换到 UTC 时区
    messages = await get_message_records(
        user_ids=user_ids,
        group_ids=[str(event.group_id)],
        exclude_user_ids=[bot.self_id],
        time_start=start.astimezone(ZoneInfo("UTC")),
        time_stop=stop.astimezone(ZoneInfo("UTC")),
        plain_text=True,
    )
    image = await get_wordcloud(messages, str(event.group_id))
    if image:
        await wordcloud_cmd.finish(MessageSegment.image(image), at_sender=my)
    else:
        await wordcloud_cmd.finish("没有足够的数据生成词云", at_sender=my)


def parse_image(key: str):
    """处理图片，并将结果存入 state 中"""

    async def _key_parser(
        matcher: Matcher,
        state: T_State,
        input: Union[MessageSegment, Message] = Arg(key),
    ):
        if isinstance(input, MessageSegment):
            return

        images = input["image"]
        if not images:
            await matcher.reject_arg(key, "请发送一张图片，不然我没法理解呢！")
        else:
            state[key] = images[0]

    return _key_parser


mask_cmd = wordcloud.command(
    "mask",
    aliases={
        "设置词云形状",
        "设置词云默认形状",
        "删除词云形状",
        "删除词云默认形状",
    },
    permission=SUPERUSER | GROUP_OWNER | GROUP_ADMIN,
)


@mask_cmd.handle()
async def _(
    event: GroupMessageEvent,
    state: T_State,
    args: Message = CommandArg(),
    commands: Tuple[str, ...] = Command(),
):
    command = commands[0]
    if command == "设置词云默认形状":
        state["default"] = True
        state["group_id"] = "default"
    elif command == "设置词云形状":
        state["default"] = False
        state["group_id"] = str(event.group_id)
    elif command == "删除词云默认形状":
        mask_path = plugin_config.get_mask_path()
        mask_path.unlink(missing_ok=True)
        await mask_cmd.finish("词云默认形状已删除")
    elif command == "删除词云形状":
        group_id = str(event.group_id)
        mask_path = plugin_config.get_mask_path(group_id)
        mask_path.unlink(missing_ok=True)
        await mask_cmd.finish(f"群 {group_id} 的词云形状已删除")

    if images := args["image"]:
        state["image"] = images[0]


@mask_cmd.got(
    "image",
    prompt="请发送一张图片作为词云形状",
    parameterless=[Depends(parse_image("image"))],
)
async def _(
    image: MessageSegment = Arg(),
    default: bool = Arg(),
    group_id: str = Arg(),
):
    image_bytes = await DATA.download_file(image.data["url"], "masked", cache=True)
    mask = Image.open(BytesIO(image_bytes))
    if default:
        mask.save(plugin_config.get_mask_path(), format="PNG")
        await mask_cmd.finish("词云默认形状设置成功")
    else:
        mask.save(plugin_config.get_mask_path(group_id), format="PNG")
        await mask_cmd.finish(f"群 {group_id} 的词云形状设置成功")


schedule_cmd = wordcloud.command(
    "schedule",
    aliases={"词云每日定时发送状态", "开启词云每日定时发送", "关闭词云每日定时发送"},
    permission=SUPERUSER | GROUP_OWNER | GROUP_ADMIN,
)


@schedule_cmd.handle()
async def _(
    bot: Bot,
    event: GroupMessageEvent,
    commands: Tuple[str, ...] = Command(),
    args: Message = CommandArg(),
):
    command = commands[0]
    schedule_time = None
    if command == "词云每日定时发送状态":
        schedule_time = await schedule_service.get_schedule(
            bot.self_id, str(event.group_id)
        )
        if schedule_time:
            await schedule_cmd.finish(f"词云每日定时发送已开启，发送时间为：{schedule_time}")
        else:
            await schedule_cmd.finish("词云每日定时发送未开启")
    elif command == "开启词云每日定时发送":
        if time_str := args.extract_plain_text().strip():
            try:
                schedule_time = get_time_fromisoformat_with_timezone(time_str)
            except ValueError:
                await schedule_cmd.finish("请输入正确的时间，不然我没法理解呢！")
        await schedule_service.add_schedule(
            bot.self_id, str(event.group_id), schedule_time
        )
        if schedule_time:
            await schedule_cmd.finish(f"已开启词云每日定时发送，发送时间为：{schedule_time}")
        else:
            await schedule_cmd.finish(
                f"已开启词云每日定时发送，发送时间为：{plugin_config.wordcloud_default_schedule_time}"
            )
    elif command == "关闭词云每日定时发送":
        await schedule_service.remove_schedule(bot.self_id, str(event.group_id))
        await schedule_cmd.finish("已关闭词云每日定时发送")
