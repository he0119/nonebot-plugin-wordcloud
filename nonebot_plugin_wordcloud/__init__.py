""" 词云
"""
import re
from base64 import b64decode
from datetime import datetime, timedelta
from io import BytesIO
from typing import Tuple, Union, cast

from nonebot import CommandGroup, require
from nonebot.adapters import Message, MessageSegment
from nonebot.matcher import Matcher
from nonebot.params import Arg, Command, CommandArg, Depends
from nonebot.permission import SUPERUSER
from nonebot.plugin import PluginMetadata
from nonebot.typing import T_State
from PIL import Image

require("nonebot_plugin_apscheduler")
require("nonebot_plugin_chatrecorder")
require("nonebot_plugin_datastore")
require("nonebot_plugin_saa")
import nonebot_plugin_saa as saa
from nonebot_plugin_chatrecorder import __plugin_meta__ as chatrecorder_meta
from nonebot_plugin_chatrecorder.record import get_messages_plain_text
from nonebot_plugin_datastore.db import post_db_init
from nonebot_plugin_session import Session, SessionIdType, SessionLevel, extract_session

from .config import Config, plugin_config, plugin_data
from .data_source import get_wordcloud
from .schedule import schedule_service
from .utils import (
    get_datetime_fromisoformat_with_timezone,
    get_datetime_now_with_timezone,
    get_time_fromisoformat_with_timezone,
)

post_db_init(schedule_service.update)

__plugin_meta__ = PluginMetadata(
    name="词云",
    description="利用群消息生成词云",
    usage="""\
- 通过快捷命令，以获取常见时间段内的词云
格式：/<时间段>词云
时间段关键词有：今日，昨日，本周，上周，本月，上月，年度
示例：/今日词云，/昨日词云

- 提供日期与时间，以获取指定时间段内的词云（支持 ISO8601 格式的日期与时间，如 2022-02-22T22:22:22）
格式：/历史词云 [日期或时间段]
示例：/历史词云
/历史词云 2022-01-01
/历史词云 2022-01-01~2022-02-22
/历史词云 2022-02-22T11:11:11~2022-02-22T22:22:22

- 在上方所给的命令格式基础上，还可以添加前缀“我的”，以获取自己的词云
格式：/我的<基本命令格式>
示例：/我的今日词云
/我的昨日词云

- 设置自定义词云形状
格式：/设置词云形状
/设置词云形状

- 设置默认词云形状（仅超级用户）
格式：/设置词云默认形状
/删除词云默认形状

- 设置定时发送每日词云
格式：/词云每日定时发送状态
/开启词云每日定时发送
/开启词云每日定时发送 23:59
/关闭词云每日定时发送""",
    homepage="https://github.com/he0119/nonebot-plugin-wordcloud",
    type="application",
    supported_adapters=(saa.__plugin_meta__.supported_adapters or set())
    & (chatrecorder_meta.supported_adapters or set()),
    config=Config,
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
    state: T_State,
    session: Session = Depends(extract_session),
    commands: Tuple[str, ...] = Command(),
    args: Message = CommandArg(),
):
    if session.level not in [SessionLevel.LEVEL2, SessionLevel.LEVEL3]:
        await wordcloud_cmd.finish("请在群组中使用！")

    command = commands[0][:-2]  # 去除后缀

    state["my"] = command.startswith("我的")
    if state["my"]:
        command = command[2:]

    dt = get_datetime_now_with_timezone()
    if command == "今日":
        state["start"] = dt.replace(hour=0, minute=0, second=0, microsecond=0)
        state["stop"] = dt
    elif command == "昨日":
        state["stop"] = dt.replace(hour=0, minute=0, second=0, microsecond=0)
        state["start"] = state["stop"] - timedelta(days=1)
    elif command == "本周":
        state["start"] = dt.replace(
            hour=0, minute=0, second=0, microsecond=0
        ) - timedelta(days=dt.weekday())
        state["stop"] = dt
    elif command == "上周":
        state["stop"] = dt.replace(
            hour=0, minute=0, second=0, microsecond=0
        ) - timedelta(days=dt.weekday())
        state["start"] = state["stop"] - timedelta(days=7)
    elif command == "本月":
        state["start"] = dt.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        state["stop"] = dt
    elif command == "上月":
        state["stop"] = dt.replace(
            day=1, hour=0, minute=0, second=0, microsecond=0
        ) - timedelta(microseconds=1)
        state["start"] = state["stop"].replace(
            day=1, hour=0, minute=0, second=0, microsecond=0
        )
    elif command == "年度":
        state["start"] = dt.replace(
            month=1, day=1, hour=0, minute=0, second=0, microsecond=0
        )
        state["stop"] = dt
    elif command == "历史":
        plaintext = args.extract_plain_text().strip()
        if match := re.match(r"^(.+?)(?:~(.+))?$", plaintext):
            start = match[1]
            stop = match[2]
            try:
                state["start"] = get_datetime_fromisoformat_with_timezone(start)
                if stop:
                    state["stop"] = get_datetime_fromisoformat_with_timezone(stop)
                else:
                    # 如果没有指定结束日期，则认为是所给日期的当天的词云
                    state["start"] = state["start"].replace(
                        hour=0, minute=0, second=0, microsecond=0
                    )
                    state["stop"] = state["start"] + timedelta(days=1)
            except ValueError:
                await wordcloud_cmd.finish("请输入正确的日期，不然我没法理解呢！")
    else:
        # 当完整匹配词云的时候才输出帮助信息
        if not args.extract_plain_text():
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
async def handle_wordcloud(
    session: Session = Depends(extract_session),
    start: datetime = Arg(),
    stop: datetime = Arg(),
    my: bool = Arg(),
):
    """生成词云"""
    messages = await get_messages_plain_text(
        session=session,
        id_type=SessionIdType.GROUP_USER if my else SessionIdType.GROUP,
        include_bot_id=False,
        include_bot_type=False,
        types=["message"],  # 排除机器人自己发的消息
        time_start=start,
        time_stop=stop,
        exclude_id1s=plugin_config.wordcloud_exclude_user_ids,
    )

    mask_key = session.get_id(
        SessionIdType.GROUP, include_bot_type=False, include_bot_id=False
    )

    if not (image := await get_wordcloud(messages, mask_key)):
        await wordcloud_cmd.finish("没有足够的数据生成词云", at_sender=my)

    await saa.Image(image, "wordcloud.png").finish()


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


# mask_cmd = wordcloud.command(
#     "mask",
#     aliases={
#         "设置词云形状",
#         "设置词云默认形状",
#         "删除词云形状",
#         "删除词云默认形状",
#     },
#     permission=SUPERUSER | GROUP_OWNER | GROUP_ADMIN,
# )


# @mask_cmd.handle()
# async def _(
#     bot: Union[BotV11, BotV12],
#     event: Union[GroupMessageEventV11, GroupMessageEventV12, ChannelMessageEvent],
#     state: T_State,
#     args: Message = CommandArg(),
#     commands: Tuple[str, ...] = Command(),
# ):
#     if isinstance(event, GroupMessageEventV11):
#         mask_key = get_mask_key("qq", group_id=event.group_id)
#         msg = f"群 {event.group_id}"
#     elif isinstance(event, GroupMessageEventV12):
#         bot = cast(BotV12, bot)
#         mask_key = get_mask_key(bot.platform, group_id=event.group_id)
#         msg = f"群 {event.group_id}"
#     else:
#         bot = cast(BotV12, bot)
#         mask_key = get_mask_key(bot.platform, guild_id=event.guild_id)
#         msg = f"频道 {event.guild_id}"

#     if (command := commands[0]) == "设置词云默认形状":
#         if not await SUPERUSER(bot, event):
#             await mask_cmd.finish("仅超级用户可设置词云默认形状")
#         state["default"] = True
#         state["mask_key"] = "default"
#     elif command == "删除词云默认形状":
#         if not await SUPERUSER(bot, event):
#             await mask_cmd.finish("仅超级用户可删除词云默认形状")
#         mask_path = plugin_config.get_mask_path()
#         mask_path.unlink(missing_ok=True)
#         await mask_cmd.finish("词云默认形状已删除")
#     elif command == "设置词云形状":
#         state["default"] = False
#         state["mask_key"] = mask_key
#     elif command == "删除词云形状":
#         mask_path = plugin_config.get_mask_path(mask_key)
#         mask_path.unlink(missing_ok=True)
#         await mask_cmd.finish(f"{msg} 的词云形状已删除")

#     if images := args["image"]:
#         state["image"] = images[0]

#     state["msg"] = msg


# @mask_cmd.got(
#     "image",
#     prompt="请发送一张图片作为词云形状",
#     parameterless=[Depends(parse_image("image"))],
# )
# async def handle_get_image_v11(
#     bot: BotV11, state: T_State, image: MessageSegment = Arg()
# ):
#     state["image_bytes"] = await plugin_data.download_file(
#         image.data["url"], "masked", cache=True
#     )


# @mask_cmd.got(
#     "image",
#     prompt="请发送一张图片作为词云形状",
#     parameterless=[Depends(parse_image("image"))],
# )
# async def handle_get_image_v12(
#     bot: BotV12, state: T_State, image: MessageSegment = Arg()
# ):
#     file_id = image.data["file_id"]
#     result = await bot.get_file(type="data", file_id=file_id)
#     data = result["data"]
#     # json 中的数据为 base64 编码的字符串
#     state["image_bytes"] = b64decode(data) if isinstance(data, str) else data


# @mask_cmd.handle()
# async def handle_save_mask(
#     image_bytes: bytes = Arg(),
#     default: bool = Arg(),
#     mask_key: str = Arg(),
#     msg: str = Arg(),
# ):
#     mask = Image.open(BytesIO(image_bytes))
#     if default:
#         mask.save(plugin_config.get_mask_path(), format="PNG")
#         await mask_cmd.finish("词云默认形状设置成功")
#     else:
#         mask.save(plugin_config.get_mask_path(mask_key), format="PNG")
#         await mask_cmd.finish(f"{msg} 的词云形状设置成功")


schedule_cmd = wordcloud.command(
    "schedule", aliases={"词云每日定时发送状态", "开启词云每日定时发送", "关闭词云每日定时发送"}, permission=SUPERUSER
)


@schedule_cmd.handle()
async def _(
    target: saa.PlatformTarget = Depends(saa.get_target),
    commands: Tuple[str, ...] = Command(),
    args: Message = CommandArg(),
):
    command = commands[0]

    if command == "词云每日定时发送状态":
        schedule_time = await schedule_service.get_schedule(target)
        await schedule_cmd.finish(
            f"词云每日定时发送已开启，发送时间为：{schedule_time}" if schedule_time else "词云每日定时发送未开启"
        )
    elif command == "开启词云每日定时发送":
        schedule_time = None
        if time_str := args.extract_plain_text().strip():
            try:
                schedule_time = get_time_fromisoformat_with_timezone(time_str)
            except ValueError:
                await schedule_cmd.finish("请输入正确的时间，不然我没法理解呢！")
        await schedule_service.add_schedule(target, time=schedule_time)
        await schedule_cmd.finish(
            f"已开启词云每日定时发送，发送时间为：{schedule_time}"
            if schedule_time
            else f"已开启词云每日定时发送，发送时间为：{plugin_config.wordcloud_default_schedule_time}"
        )
    elif command == "关闭词云每日定时发送":
        await schedule_service.remove_schedule(target)
        await schedule_cmd.finish("已关闭词云每日定时发送")
