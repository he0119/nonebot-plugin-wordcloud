from zoneinfo import ZoneInfo

import pytest
from nonebot.compat import type_validate_python
from nonebug import App


async def test_default_schedule_time_config(app: App):
    """测试默认定时发送时间"""
    from nonebot_plugin_wordcloud.config import Config
    from nonebot_plugin_wordcloud.model import ScheduleMode

    config = type_validate_python(Config, {})

    default_time = config.wordcloud_default_schedule_time
    assert default_time.isoformat() == "00:00:00+08:00"
    assert config.wordcloud_default_schedule_mode == ScheduleMode.COMPLETE
    assert (
        config.get_default_schedule_time(ScheduleMode.COMPLETE).isoformat()
        == "00:00:00+08:00"
    )
    assert (
        config.get_default_schedule_time(ScheduleMode.PERIOD_END).isoformat()
        == "23:59:59+08:00"
    )


@pytest.mark.parametrize(
    ("default_config", "default_time"),
    [
        pytest.param(
            {"wordcloud_default_schedule_mode": "完整周期"},
            "00:00:00+08:00",
            id="complete",
        ),
        pytest.param(
            {"wordcloud_default_schedule_mode": "周期末"},
            "23:59:59+08:00",
            id="period_end",
        ),
    ],
)
async def test_default_schedule_mode(
    app: App, default_config: dict[str, str], default_time: str
):
    """测试设置默认定时发送模式"""
    from nonebot_plugin_wordcloud.config import Config

    config = type_validate_python(Config, default_config)

    assert config.wordcloud_default_schedule_time.isoformat() == default_time


@pytest.mark.parametrize(
    "default_config",
    [
        pytest.param(
            {"wordcloud_default_schedule_time": "20:00"}, id="without_timezone"
        ),
        pytest.param(
            {"wordcloud_default_schedule_time": "20:00:00+08:00"}, id="with_timezone"
        ),
    ],
)
async def test_default_schedule_time(app: App, default_config: dict[str, str]):
    """测试设置默认定时发送时间"""
    from nonebot_plugin_wordcloud.config import Config
    from nonebot_plugin_wordcloud.model import ScheduleMode

    config = type_validate_python(Config, default_config)

    default_time = config.wordcloud_default_schedule_time
    assert default_time.isoformat() == "20:00:00+08:00"
    assert config.get_default_schedule_time().isoformat() == "20:00:00+08:00"
    assert (
        config.get_default_schedule_time(ScheduleMode.PERIOD_END).isoformat()
        == "20:00:00+08:00"
    )


@pytest.mark.parametrize(
    "default_config",
    [
        pytest.param(
            {
                "wordcloud_default_schedule_time": "20:00",
                "wordcloud_timezone": "Asia/Tokyo",
            },
            id="without_timezone",
        ),
        pytest.param(
            {
                "wordcloud_default_schedule_time": "20:00:00+09:00",
                "wordcloud_timezone": "Asia/Tokyo",
            },
            id="with_timezone",
        ),
    ],
)
async def test_default_schedule_time_with_timezone(
    app: App, default_config: dict[str, str]
):
    """测试设置默认定时发送时间，同时设置时区"""
    from nonebot_plugin_wordcloud.config import Config

    config = type_validate_python(Config, default_config)

    default_time = config.wordcloud_default_schedule_time
    assert default_time.isoformat() == "20:00:00"
    assert default_time.tzinfo == ZoneInfo("Asia/Tokyo")
