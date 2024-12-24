"""词云"""

from nonebot import require

require("nonebot_plugin_apscheduler")
require("nonebot_plugin_alconna")
require("nonebot_plugin_session")
require("nonebot_plugin_cesaa")

import re
from datetime import datetime, timedelta
from io import BytesIO
from typing import Any, Optional, Union

import nonebot_plugin_alconna as alc
import nonebot_plugin_saa as saa
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
    CommandMeta,
    Match,
    Option,
    Query,
    image_fetch,
    on_alconna,
    store_true,
)
from nonebot_plugin_cesaa import get_messages_plain_text
from nonebot_plugin_session import Session, SessionIdType, extract_session
from PIL import Image

from . import migrations
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

get_driver().on_startup(schedule_service.update)

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
/关闭词云每日定时发送""",  # noqa: E501
    homepage="https://github.com/he0119/nonebot-plugin-wordcloud",
    type="application",
    supported_adapters=inherit_supported_adapters(
        "nonebot_plugin_chatrecorder", "nonebot_plugin_saa", "nonebot_plugin_alconna"
    ),
    config=Config,
    extra={"orm_version_location": migrations},
)


class SameTime(ArparmaBehavior):
    def operate(self, interface: Arparma):
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
        Args["type?", ["今日", "昨日", "本周", "上周", "本月", "上月", "年度", "历史"]][
            "time?", str
        ],
        behaviors=[SameTime()],
        meta=CommandMeta(
            description="利用群消息生成词云",
            usage=(
                "- 通过快捷命令，以获取常见时间段内的词云\n"
                "格式：/<时间段>词云\n"
                "时间段关键词有：今日，昨日，本周，上周，本月，上月，年度\n"
                "- 提供日期与时间，以获取指定时间段内的词云\n"
                "（支持 ISO8601 格式的日期与时间，如 2022-02-22T22:22:22）\n"
                "格式：/历史词云 [日期或时间段]"
            ),
            example=(
                "/今日词云\n"
                "/昨日词云\n"
                "/历史词云\n"
                "/历史词云 2022-01-01\n"
                "/历史词云 2022-01-01~2022-02-22\n"
                "/历史词云 2022-02-22T11:11:11~2022-02-22T22:22:22"
            ),
        ),
    ),
    use_cmd_start=True,
    block=True,
)


def wrapper(
    slot: Union[int, str], content: Optional[str], context: dict[str, Any]
) -> str:
    if slot == "my" and content:
        return "--my"
    elif slot == "type" and content:
        return content
    return ""  # pragma: no cover


wordcloud_cmd.shortcut(
    r"(?P<my>我的)?(?P<type>今日|昨日|本周|上周|本月|上月|年度|历史)词云",
    {
        "prefix": True,
        "command": "词云",
        "wrapper": wrapper,
        "args": ["{my}", "{type}"],
        "humanized": "[我的]<类型>词云",
    },
)


def parse_datetime(key: str):
    """解析数字，并将结果存入 state 中"""

    async def _key_parser(
        matcher: AlconnaMatcher,
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
    state: T_State, type: Optional[str] = None, time: Optional[str] = None
):
    dt = get_datetime_now_with_timezone()

    if not type:
        await wordcloud_cmd.finish(__plugin_meta__.usage)

    if type == "今日":
        state["start"] = dt.replace(hour=0, minute=0, second=0, microsecond=0)
        state["stop"] = dt
    elif type == "昨日":
        state["stop"] = dt.replace(hour=0, minute=0, second=0, microsecond=0)
        state["start"] = state["stop"] - timedelta(days=1)
    elif type == "本周":
        state["start"] = dt.replace(
            hour=0, minute=0, second=0, microsecond=0
        ) - timedelta(days=dt.weekday())
        state["stop"] = dt
    elif type == "上周":
        state["stop"] = dt.replace(
            hour=0, minute=0, second=0, microsecond=0
        ) - timedelta(days=dt.weekday())
        state["start"] = state["stop"] - timedelta(days=7)
    elif type == "本月":
        state["start"] = dt.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        state["stop"] = dt
    elif type == "上月":
        state["stop"] = dt.replace(
            day=1, hour=0, minute=0, second=0, microsecond=0
        ) - timedelta(microseconds=1)
        state["start"] = state["stop"].replace(
            day=1, hour=0, minute=0, second=0, microsecond=0
        )
    elif type == "年度":
        state["start"] = dt.replace(
            month=1, day=1, hour=0, minute=0, second=0, microsecond=0
        )
        state["stop"] = dt
    elif type == "历史":
        if time:
            plaintext = time
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
    my: Query[bool] = AlconnaQuery("my.value", False),
    session: Session = Depends(extract_session),
    start: datetime = Arg(),
    stop: datetime = Arg(),
    mask_key: str = Depends(get_mask_key),
):
    """生成词云"""
    messages = await get_messages_plain_text(
        session=session,
        id_type=SessionIdType.GROUP_USER if my.result else SessionIdType.GROUP,
        include_bot_id=False,
        include_bot_type=False,
        types=["message"],  # 排除机器人自己发的消息
        time_start=start,
        time_stop=stop,
        exclude_id1s=plugin_config.wordcloud_exclude_user_ids,
    )

    if not (image := await get_wordcloud(messages, mask_key)):
        await wordcloud_cmd.finish("没有足够的数据生成词云", at_sender=my.result)
        return  # pragma: no cover

    await saa.Image(image, "wordcloud.png").finish(at_sender=my.result)


set_mask_cmd = on_alconna(
    Alconna(
        "设置词云形状",
        Option("--default", default=False, action=store_true, help_text="默认形状"),
        Args["img?", alc.Image],
        meta=CommandMeta(
            description="设置自定义词云形状",
            example="/设置词云形状\n/设置词云默认形状",
        ),
    ),
    permission=admin_permission(),
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
    if img.available:
        matcher.set_path_arg("img", img.result)


@set_mask_cmd.got_path("img", "请发送一张图片作为词云形状", image_fetch)
async def handle_save_mask(
    bot: Bot,
    event: Event,
    img: bytes,
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
    permission=admin_permission(),
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


schedule_cmd = on_alconna(
    Alconna(
        "词云定时发送",
        Option(
            "--action",
            Args["action_type", ["状态", "开启", "关闭"]],
            default="状态",
            help_text="操作类型",
        ),
        Args["type", ["每日"]]["time?", str],
        meta=CommandMeta(
            description="设置定时发送词云",
            usage="当前仅支持每日定时发送",
            example=(
                "/词云每日定时发送状态\n"
                "/开启词云每日定时发送\n"
                "/开启词云每日定时发送 23:59\n"
                "/关闭词云每日定时发送"
            ),
        ),
    ),
    permission=admin_permission(),
    use_cmd_start=True,
    block=True,
)
schedule_cmd.shortcut(
    r"词云(?P<type>每日)定时发送状态",
    {
        "prefix": True,
        "command": "词云定时发送",
        "args": ["--action", "状态", "{type}"],
        "humanized": "词云每日定时发送状态",
    },
)
schedule_cmd.shortcut(
    r"(?P<action>开启|关闭)词云(?P<type>每日)定时发送",
    {
        "prefix": True,
        "command": "词云定时发送",
        "args": ["--action", "{action}", "{type}"],
        "humanized": "<开启|关闭>词云每日定时发送",
    },
)


@schedule_cmd.handle(parameterless=[Depends(ensure_group)])
async def _(
    time: Optional[str] = None,
    action_type: Query[str] = AlconnaQuery("action.action_type.value", "状态"),
    target: saa.PlatformTarget = Depends(saa.get_target),
):
    if action_type.result == "状态":
        schedule_time = await schedule_service.get_schedule(target)
        await schedule_cmd.finish(
            f"词云每日定时发送已开启，发送时间为：{schedule_time}"
            if schedule_time
            else "词云每日定时发送未开启"
        )
    elif action_type.result == "开启":
        schedule_time = None
        if time:
            try:
                schedule_time = get_time_fromisoformat_with_timezone(time)
            except ValueError:
                await schedule_cmd.finish("请输入正确的时间，不然我没法理解呢！")
        await schedule_service.add_schedule(target, time=schedule_time)
        await schedule_cmd.finish(
            f"已开启词云每日定时发送，发送时间为：{schedule_time}"
            if schedule_time
            else f"已开启词云每日定时发送，发送时间为：{plugin_config.wordcloud_default_schedule_time}"  # noqa: E501
        )
    elif action_type.result == "关闭":
        await schedule_service.remove_schedule(target)
        await schedule_cmd.finish("已关闭词云每日定时发送")
