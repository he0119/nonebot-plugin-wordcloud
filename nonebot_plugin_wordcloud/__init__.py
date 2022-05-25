""" 词云
"""
import re
from datetime import datetime, timedelta
from inspect import cleandoc
from io import BytesIO
from typing import Tuple, Union

from nonebot.utils import run_sync

try:
    from zoneinfo import ZoneInfo
except ImportError:
    from backports.zoneinfo import ZoneInfo  # type: ignore

from nonebot import on_command, require
from nonebot.adapters import Bot
from nonebot.adapters.onebot.v11 import Message, MessageSegment
from nonebot.adapters.onebot.v11.event import GroupMessageEvent
from nonebot.matcher import Matcher
from nonebot.params import Arg, Command, CommandArg, Depends
from nonebot.typing import T_State

require("nonebot_plugin_chatrecorder")
from nonebot_plugin_chatrecorder import get_message_records

from .config import plugin_config
from .data_source import get_wordcloud

wordcloud_cmd = on_command(
    "wordcloud",
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
wordcloud_cmd.__doc__ = """
词云

获取今天的词云
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
"""


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


def get_datetime_now_with_timezone() -> datetime:
    """获取当前时间，并包含时区信息"""
    if plugin_config.wordcloud_timezone:
        return datetime.now(ZoneInfo(plugin_config.wordcloud_timezone))
    else:
        return datetime.now().astimezone()


def get_datetime_fromisoformat_with_timezone(date_string: str) -> datetime:
    """从 iso8601 格式字符串中获取时间，并包含时区信息"""
    if plugin_config.wordcloud_timezone:
        return datetime.fromisoformat(date_string).astimezone(
            ZoneInfo(plugin_config.wordcloud_timezone)
        )
    else:
        return datetime.fromisoformat(date_string).astimezone()


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
            help_msg = cleandoc(wordcloud_cmd.__doc__) if wordcloud_cmd.__doc__ else ""
            await wordcloud_cmd.finish(help_msg)
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
    image = await run_sync(get_wordcloud)(messages)
    if image:
        image_bytes = BytesIO()
        image.save(image_bytes, format="PNG")
        await wordcloud_cmd.finish(MessageSegment.image(image_bytes), at_sender=my)
    else:
        await wordcloud_cmd.finish("没有足够的数据生成词云", at_sender=my)
