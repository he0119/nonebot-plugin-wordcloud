""" 词云
"""
import re
from datetime import datetime, timedelta
from inspect import cleandoc
from io import BytesIO
from typing import Tuple, Union

try:
    from zoneinfo import ZoneInfo
except ImportError:
    from backports.zoneinfo import ZoneInfo  # type: ignore

from nonebot import on_command
from nonebot.adapters import Bot
from nonebot.adapters.onebot.v11 import Message, MessageSegment
from nonebot.adapters.onebot.v11.event import GroupMessageEvent
from nonebot.matcher import Matcher
from nonebot.params import Arg, Command, CommandArg, Depends, State
from nonebot.typing import T_State
from nonebot_plugin_chatrecorder import get_message_records

from .config import plugin_config
from .data import get_wordcloud
from .migrate import migrate_database

wordcloud_cmd = on_command("wordcloud", aliases={"词云", "今日词云", "昨日词云", "历史词云"})
wordcloud_cmd.__doc__ = """
词云

获取今天的词云
/今日词云
获取昨天的词云
/昨日词云
获取历史词云
/历史词云
/历史词云 2022-01-01
"""


def parse_int(key: str):
    """解析数字，并将结果存入 state 中"""

    async def _key_parser(
        matcher: Matcher,
        state: T_State = State(),
        input: Union[int, Message] = Arg(key),
    ):
        if isinstance(input, int):
            return

        plaintext = input.extract_plain_text()
        if not plaintext.isdigit():
            await matcher.reject_arg(key, "请只输入数字，不然我没法理解呢！")
        state[key] = int(plaintext)

    return _key_parser


def get_datetime_now_with_timezone() -> datetime:
    """获取当前时间，并包含时区信息"""
    if plugin_config.wordcloud_timezone:
        return datetime.now(ZoneInfo(plugin_config.wordcloud_timezone))
    else:
        return datetime.now().astimezone()


@wordcloud_cmd.handle()
async def handle_first_receive(
    event: GroupMessageEvent,
    commands: Tuple[str, ...] = Command(),
    state: T_State = State(),
    args: Message = CommandArg(),
):
    command = commands[0]
    if command == "今日词云":
        dt = get_datetime_now_with_timezone()
        state["year"] = dt.year
        state["month"] = dt.month
        state["day"] = dt.day
    elif command == "昨日词云":
        dt = get_datetime_now_with_timezone()
        dt -= timedelta(days=1)
        state["year"] = dt.year
        state["month"] = dt.month
        state["day"] = dt.day
    elif command == "历史词云":
        plaintext = args.extract_plain_text().strip()
        match = re.match(r"^(\d+)(?:\-(\d+)(?:\-(\d+))?)?$", plaintext)
        if match:
            year = match.group(1)
            month = match.group(2)
            day = match.group(3)
            if year:
                state["year"] = int(year)
            if month:
                state["month"] = int(month)
            if day:
                state["day"] = int(day)
    else:
        help_msg = cleandoc(wordcloud_cmd.__doc__) if wordcloud_cmd.__doc__ else ""
        await wordcloud_cmd.finish(help_msg)


@wordcloud_cmd.got(
    "year", prompt="请输入你要查询的年份", parameterless=[Depends(parse_int("year"))]
)
@wordcloud_cmd.got(
    "month", prompt="请输入你要查询的月份", parameterless=[Depends(parse_int("month"))]
)
@wordcloud_cmd.got(
    "day", prompt="请输入你要查询的日期", parameterless=[Depends(parse_int("day"))]
)
async def handle_message(
    bot: Bot,
    event: GroupMessageEvent,
    year: int = Arg(),
    month: int = Arg(),
    day: int = Arg(),
):
    # 获取本地时间
    try:
        if plugin_config.wordcloud_timezone:
            dt = datetime(
                year, month, day, tzinfo=ZoneInfo(plugin_config.wordcloud_timezone)
            )
        else:
            dt = datetime(year, month, day).astimezone()
    except ValueError:
        await wordcloud_cmd.finish("日期错误，请输入正确的日期")

    # 排除机器人自己发的消息
    # 将时间转换到 UTC 时区
    messages = await get_message_records(
        group_ids=[str(event.group_id)],
        exclude_user_ids=[bot.self_id],
        time_start=dt.astimezone(ZoneInfo("UTC")),
        time_stop=(dt + timedelta(days=1)).astimezone(ZoneInfo("UTC")),
        plain_text=True,
    )
    image = get_wordcloud(messages)
    if image:
        image_bytes = BytesIO()
        image.save(image_bytes, format="PNG")
        await wordcloud_cmd.finish(MessageSegment.image(image_bytes))
    else:
        await wordcloud_cmd.finish("没有足够的数据生成词云")


migrate_cmd = on_command("迁移词云")


@migrate_cmd.handle()
async def handle_migrate():
    result = await migrate_database()
    if result:
        await migrate_cmd.finish("数据库迁移成功")
    else:
        await migrate_cmd.finish("旧版本数据库不存在，不需要迁移")
