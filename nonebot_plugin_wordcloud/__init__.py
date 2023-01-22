""" 词云
"""
import re
from datetime import datetime, timedelta
from io import BytesIO
from typing import List, Tuple, Union, cast

try:
    from zoneinfo import ZoneInfo
except ImportError:
    from backports.zoneinfo import ZoneInfo  # type: ignore

from nonebot import CommandGroup, require
from nonebot.adapters import Message, MessageSegment
from nonebot.adapters.onebot.v11 import Bot as BotV11
from nonebot.adapters.onebot.v11 import GroupMessageEvent as GroupMessageEventV11
from nonebot.adapters.onebot.v11 import MessageSegment as MessageSegmentV11
from nonebot.adapters.onebot.v11.permission import GROUP_ADMIN, GROUP_OWNER
from nonebot.adapters.onebot.v12 import Bot as BotV12
from nonebot.adapters.onebot.v12 import ChannelMessageEvent
from nonebot.adapters.onebot.v12 import GroupMessageEvent as GroupMessageEventV12
from nonebot.adapters.onebot.v12 import MessageSegment as MessageSegmentV12
from nonebot.matcher import Matcher
from nonebot.params import Arg, Command, CommandArg, Depends
from nonebot.permission import SUPERUSER
from nonebot.plugin import PluginMetadata
from nonebot.typing import T_State
from PIL import Image

require("nonebot_plugin_apscheduler")
require("nonebot_plugin_chatrecorder")
require("nonebot_plugin_datastore")
from nonebot_plugin_chatrecorder import get_messages_plain_text
from nonebot_plugin_datastore.db import post_db_init

from .config import plugin_config, plugin_data
from .data_source import get_wordcloud
from .schedule import schedule_service
from .utils import (
    get_datetime_fromisoformat_with_timezone,
    get_datetime_now_with_timezone,
    get_mask_key,
    get_time_fromisoformat_with_timezone,
)

post_db_init(schedule_service.update)

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
/上周词云
获取上周词云
/本月词云
获取年度词云
/上月词云
获取上月词云
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
/开启词云每日定时发送 23:59
/关闭词云每日定时发送""",
)

wordcloud = CommandGroup("词云")


wordcloud_cmd = wordcloud.command(
    "main",
    aliases={
        "词云",
        "今日词云",
        "昨日词云",
        "本周词云",
        "上周词云",
        "本月词云",
        "上月词云",
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
    event: Union[GroupMessageEventV11, GroupMessageEventV12, ChannelMessageEvent],
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
    elif command == "上周词云":
        dt = get_datetime_now_with_timezone()
        state["stop"] = dt.replace(
            hour=0, minute=0, second=0, microsecond=0
        ) - timedelta(days=dt.weekday())
        state["start"] = state["stop"] - timedelta(days=7)
    elif command == "本月词云":
        dt = get_datetime_now_with_timezone()
        state["start"] = dt.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        state["stop"] = dt
    elif command == "上月词云":
        dt = get_datetime_now_with_timezone()
        state["stop"] = dt.replace(
            day=1, hour=0, minute=0, second=0, microsecond=0
        ) - timedelta(microseconds=1)
        state["start"] = state["stop"].replace(
            day=1, hour=0, minute=0, second=0, microsecond=0
        )
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
async def handle_get_messages_group_message(
    bot: Union[BotV11, BotV12],
    event: Union[GroupMessageEventV11, GroupMessageEventV12],
    state: T_State,
    start: datetime = Arg(),
    stop: datetime = Arg(),
    my: bool = Arg(),
):
    platform = "qq" if isinstance(bot, BotV11) else bot.platform
    # 将时间转换到 UTC 时区
    state["messages"] = await get_messages_plain_text(
        platforms=[platform],
        user_ids=[str(event.user_id)] if my else None,  # 是否只查询自己的记录
        group_ids=[str(event.group_id)],
        types=["message"],  # 排除机器人自己发的消息
        time_start=start.astimezone(ZoneInfo("UTC")),
        time_stop=stop.astimezone(ZoneInfo("UTC")),
    )
    state["mask_key"] = (
        get_mask_key("qq", group_id=event.group_id)
        if isinstance(bot, BotV11)
        else get_mask_key(bot.platform, group_id=event.group_id)
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
async def handle_get_messages_channel_message(
    bot: BotV12,
    event: ChannelMessageEvent,
    state: T_State,
    start: datetime = Arg(),
    stop: datetime = Arg(),
    my: bool = Arg(),
):
    state["messages"] = await get_messages_plain_text(
        platforms=[bot.platform],
        user_ids=[event.user_id] if my else None,
        guild_ids=[event.guild_id],
        channel_ids=[event.channel_id],
        types=["message"],
        time_start=start.astimezone(ZoneInfo("UTC")),
        time_stop=stop.astimezone(ZoneInfo("UTC")),
    )
    state["mask_key"] = get_mask_key(bot.platform, guild_id=event.guild_id)


@wordcloud_cmd.handle()
async def handle_send_message(
    bot: Union[BotV11, BotV12],
    messages: List[str] = Arg(),
    mask_key: str = Arg(),
    my: bool = Arg(),
):
    image = await get_wordcloud(messages, mask_key)
    if not image:
        await wordcloud_cmd.finish("没有足够的数据生成词云", at_sender=my)

    if isinstance(bot, BotV11):
        await wordcloud_cmd.finish(MessageSegmentV11.image(image), at_sender=my)
    else:
        resp = await bot.upload_file(
            type="data", name="wordcloud", data=image.getvalue()
        )
        file_id = resp["file_id"]
        await wordcloud_cmd.finish(MessageSegmentV12.image(file_id), at_sender=my)


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
    bot: Union[BotV11, BotV12],
    event: Union[GroupMessageEventV11, GroupMessageEventV12, ChannelMessageEvent],
    state: T_State,
    args: Message = CommandArg(),
    commands: Tuple[str, ...] = Command(),
):
    command = commands[0]

    if isinstance(event, GroupMessageEventV11):
        mask_key = get_mask_key("qq", group_id=event.group_id)
        msg = f"群 {event.group_id}"
    elif isinstance(event, GroupMessageEventV12):
        bot = cast(BotV12, bot)
        mask_key = get_mask_key(bot.platform, group_id=event.group_id)
        msg = f"群 {event.group_id}"
    else:
        bot = cast(BotV12, bot)
        mask_key = get_mask_key(bot.platform, guild_id=event.guild_id)
        msg = f"频道 {event.guild_id}"

    if command == "设置词云默认形状":
        state["default"] = True
        state["mask_key"] = "default"
    elif command == "设置词云形状":
        state["default"] = False
        state["mask_key"] = mask_key
    elif command == "删除词云默认形状":
        mask_path = plugin_config.get_mask_path()
        mask_path.unlink(missing_ok=True)
        await mask_cmd.finish("词云默认形状已删除")
    elif command == "删除词云形状":
        mask_path = plugin_config.get_mask_path(mask_key)
        mask_path.unlink(missing_ok=True)
        await mask_cmd.finish(f"{msg} 的词云形状已删除")

    if images := args["image"]:
        state["image"] = images[0]

    state["msg"] = msg


@mask_cmd.got(
    "image",
    prompt="请发送一张图片作为词云形状",
    parameterless=[Depends(parse_image("image"))],
)
async def handle_get_image_v11(
    bot: BotV11, state: T_State, image: MessageSegment = Arg()
):
    state["image_bytes"] = await plugin_data.download_file(
        image.data["url"], "masked", cache=True
    )


@mask_cmd.got(
    "image",
    prompt="请发送一张图片作为词云形状",
    parameterless=[Depends(parse_image("image"))],
)
async def handle_get_image_v12(
    bot: BotV12, state: T_State, image: MessageSegment = Arg()
):
    file_id = image.data["file_id"]
    result = await bot.get_file(type="data", file_id=file_id)
    state["image_bytes"] = result["data"]


@mask_cmd.handle()
async def handle_save_mask(
    image_bytes: bytes = Arg(),
    default: bool = Arg(),
    mask_key: str = Arg(),
    msg: str = Arg(),
):
    mask = Image.open(BytesIO(image_bytes))
    if default:
        mask.save(plugin_config.get_mask_path(), format="PNG")
        await mask_cmd.finish("词云默认形状设置成功")
    else:
        mask.save(plugin_config.get_mask_path(mask_key), format="PNG")
        await mask_cmd.finish(f"{msg} 的词云形状设置成功")


schedule_cmd = wordcloud.command(
    "schedule",
    aliases={"词云每日定时发送状态", "开启词云每日定时发送", "关闭词云每日定时发送"},
    permission=SUPERUSER | GROUP_OWNER | GROUP_ADMIN,
)


@schedule_cmd.handle()
async def _(
    bot: Union[BotV11, BotV12],
    event: Union[GroupMessageEventV11, GroupMessageEventV12, ChannelMessageEvent],
    commands: Tuple[str, ...] = Command(),
    args: Message = CommandArg(),
):
    command = commands[0]

    group_id = None
    guild_id = None
    channel_id = None
    if isinstance(event, GroupMessageEventV11):
        group_id = str(event.group_id)
        platform = "qq"
    elif isinstance(event, GroupMessageEventV12):
        bot = cast(BotV12, bot)
        group_id = event.group_id
        platform = bot.platform
    else:
        bot = cast(BotV12, bot)
        guild_id = event.guild_id
        channel_id = event.channel_id
        platform = bot.platform

    if command == "词云每日定时发送状态":
        schedule_time = await schedule_service.get_schedule(
            bot.self_id,
            platform,
            group_id=group_id,
            guild_id=guild_id,
            channel_id=channel_id,
        )
        if schedule_time:
            await schedule_cmd.finish(f"词云每日定时发送已开启，发送时间为：{schedule_time}")
        else:
            await schedule_cmd.finish("词云每日定时发送未开启")
    elif command == "开启词云每日定时发送":
        schedule_time = None
        if time_str := args.extract_plain_text().strip():
            try:
                schedule_time = get_time_fromisoformat_with_timezone(time_str)
            except ValueError:
                await schedule_cmd.finish("请输入正确的时间，不然我没法理解呢！")
        await schedule_service.add_schedule(
            bot.self_id,
            platform,
            time=schedule_time,
            group_id=group_id,
            guild_id=guild_id,
            channel_id=channel_id,
        )
        if schedule_time:
            await schedule_cmd.finish(f"已开启词云每日定时发送，发送时间为：{schedule_time}")
        else:
            await schedule_cmd.finish(
                f"已开启词云每日定时发送，发送时间为：{plugin_config.wordcloud_default_schedule_time}"
            )
    elif command == "关闭词云每日定时发送":
        await schedule_service.remove_schedule(
            bot.self_id,
            platform,
            group_id=group_id,
            guild_id=guild_id,
            channel_id=channel_id,
        )
        await schedule_cmd.finish("已关闭词云每日定时发送")
