""" 词云
"""
import re
from datetime import datetime, timedelta
from io import BytesIO
from typing import Tuple, Union

from nonebot import CommandGroup, require
from nonebot.adapters import Bot, Event, Message
from nonebot.matcher import Matcher
from nonebot.params import Arg, Command, CommandArg, Depends
from nonebot.permission import SUPERUSER
from nonebot.plugin import PluginMetadata, inherit_supported_adapters
from nonebot.typing import T_State
from PIL import Image

require("nonebot_plugin_apscheduler")
require("nonebot_plugin_chatrecorder")
require("nonebot_plugin_datastore")
require("nonebot_plugin_saa")
require("nonebot_plugin_alconna")
require("nonebot_plugin_cesaa")
import nonebot_plugin_alconna as alc
import nonebot_plugin_saa as saa
from nonebot_plugin_alconna import (
    Alconna,
    AlconnaArg,
    AlconnaMatch,
    AlconnaMatcher,
    AlconnaQuery,
    Args,
    Match,
    Option,
    Query,
    image_fetch,
    on_alconna,
    store_true,
)
from nonebot_plugin_chatrecorder.record import get_messages_plain_text
from nonebot_plugin_datastore.db import post_db_init
from nonebot_plugin_session import Session, SessionIdType, extract_session

from .config import Config, plugin_config
from .data_source import get_wordcloud
from .schedule import schedule_service
from .utils import (
    admin_permission,
    ensure_group,
    get_datetime_fromisoformat_with_timezone,
    get_datetime_now_with_timezone,
    get_mask_key,
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
    supported_adapters=inherit_supported_adapters(
        "nonebot_plugin_chatrecorder", "nonebot_plugin_saa", "nonebot_plugin_alconna"
    ),
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


@wordcloud_cmd.handle(parameterless=[Depends(ensure_group)])
async def handle_first_receive(
    state: T_State,
    commands: Tuple[str, ...] = Command(),
    args: Message = CommandArg(),
):
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
    mask_key: str = Depends(get_mask_key),
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

    if not (image := await get_wordcloud(messages, mask_key)):
        await wordcloud_cmd.finish("没有足够的数据生成词云", at_sender=my)

    await saa.Image(image, "wordcloud.png").finish(at_sender=my)


set_mask_cmd = on_alconna(
    Alconna(
        "设置词云形状",
        Option("--default", default=False, action=store_true),
        Args["img?", alc.Image],
    ),
    permission=admin_permission(),
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
    if img.available:
        matcher.set_path_arg("img", img.result)


@set_mask_cmd.got_path("img", "请发送一张图片作为词云形状", image_fetch)
async def handle_save_mask(
    bot: Bot,
    event: Event,
    img: bytes = AlconnaArg("img"),
    default: Query[bool] = AlconnaQuery("default.value", default=False),
    mask_key: str = Depends(get_mask_key),
):
    mask = Image.open(BytesIO(img))
    if default.result:
        if not await SUPERUSER(bot, event):
            await set_mask_cmd.finish("仅超级用户可设置词云默认形状")
        mask.save(plugin_config.get_mask_path(), format="PNG")
        await set_mask_cmd.finish("词云默认形状设置成功")
    else:
        mask.save(plugin_config.get_mask_path(mask_key), format="PNG")
        await set_mask_cmd.finish(f"词云形状设置成功")


remove_mask_cmd = on_alconna(
    Alconna(
        "删除词云形状",
        Option("--default", default=False, action=store_true),
    ),
    permission=admin_permission(),
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
    mask_key: str = Depends(get_mask_key),
):
    if default.result:
        if not await SUPERUSER(bot, event):
            await remove_mask_cmd.finish("仅超级用户可删除词云默认形状")
        mask_path = plugin_config.get_mask_path()
        mask_path.unlink(missing_ok=True)
        await remove_mask_cmd.finish("词云默认形状已删除")
    else:
        mask_path = plugin_config.get_mask_path(mask_key)
        mask_path.unlink(missing_ok=True)
        await remove_mask_cmd.finish("词云形状已删除")


schedule_cmd = wordcloud.command(
    "schedule",
    aliases={
        "词云每日定时发送状态",
        "开启词云每日定时发送",
        "关闭词云每日定时发送",
    },
    permission=admin_permission(),
)


@schedule_cmd.handle(parameterless=[Depends(ensure_group)])
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
