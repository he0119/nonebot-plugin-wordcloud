""" 词云
"""
import re
from datetime import datetime, timedelta
from io import BytesIO
from typing import List, Tuple, Union

try:
    from zoneinfo import ZoneInfo
except ImportError:
    from backports.zoneinfo import ZoneInfo  # type: ignore

from nonebot import on_command, on_message
from nonebot.adapters.onebot.v11 import Message, MessageSegment
from nonebot.adapters.onebot.v11.event import GroupMessageEvent
from nonebot.adapters.onebot.v11.permission import GROUP
from nonebot.matcher import Matcher
from nonebot.params import Arg, Command, CommandArg, Depends, State
from nonebot.typing import T_State
from nonebot_plugin_datastore import get_session
from sqlmodel import select
from sqlmodel.ext.asyncio.session import AsyncSession

from .data import get_wordcloud
from .model import GroupMessage

# region 保存消息
save_message = on_message(permission=GROUP, block=False)


@save_message.handle()
async def save_message_handle(
    event: GroupMessageEvent, session: AsyncSession = Depends(get_session)
):
    message = GroupMessage(
        time=event.time,  # type: ignore
        user_id=event.user_id,  # type: ignore
        group_id=event.group_id,  # type: ignore
        message=event.message.extract_plain_text(),
        platform="qq",
    )
    session.add(message)
    await session.commit()


# endregion
# region 词云
wordcloud_cmd = on_command("词云", aliases={"今日词云", "昨日词云", "历史词云"})
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


@wordcloud_cmd.handle()
async def handle_first_receive(
    event: GroupMessageEvent,
    commands: Tuple[str, ...] = Command(),
    state: T_State = State(),
    args: Message = CommandArg(),
):
    command = commands[0]
    if command == "今日词云":
        dt = datetime.now(ZoneInfo("Asia/Shanghai"))
        state["year"] = dt.year
        state["month"] = dt.month
        state["day"] = dt.day
    elif command == "昨日词云":
        dt = datetime.now(ZoneInfo("Asia/Shanghai")) - timedelta(days=1)
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


@wordcloud_cmd.got(
    "year",
    prompt="请输入你要查询的年份",
    parameterless=[Depends(parse_int("year"))],
)
@wordcloud_cmd.got(
    "month",
    prompt="请输入你要查询的月份",
    parameterless=[Depends(parse_int("month"))],
)
@wordcloud_cmd.got(
    "day",
    prompt="请输入你要查询的日期",
    parameterless=[Depends(parse_int("day"))],
)
async def handle_message(
    event: GroupMessageEvent,
    session: AsyncSession = Depends(get_session),
    year: int = Arg(),
    month: int = Arg(),
    day: int = Arg(),
):
    # 获取中国本地时间
    dt = datetime(year, month, day, tzinfo=ZoneInfo("Asia/Shanghai"))

    # 中国时区差了 8 小时
    statement = select(GroupMessage).where(
        GroupMessage.group_id == str(event.group_id),
        GroupMessage.time >= dt.astimezone(ZoneInfo("UTC")),
        GroupMessage.time <= (dt + timedelta(days=1)).astimezone(ZoneInfo("UTC")),
    )
    messages: List[GroupMessage] = (await session.exec(statement)).all()  # type: ignore

    image = get_wordcloud(messages)
    if image:
        image_bytes = BytesIO()
        image.save(image_bytes, format="PNG")
        await wordcloud_cmd.finish(MessageSegment.image(image_bytes))
    else:
        await wordcloud_cmd.finish("没有足够的数据生成词云")


# endregion
