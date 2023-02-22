from typing import Dict

import pytest
from nonebug import App

try:
    from zoneinfo import ZoneInfo
except ImportError:
    from backports.zoneinfo import ZoneInfo  # type: ignore


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
async def test_default_schedule_time(app: App, default_config: Dict):
    """测试设置默认定时发送时间"""
    from nonebot_plugin_wordcloud.config import Config

    config = Config.parse_obj(default_config)

    default_time = config.wordcloud_default_schedule_time
    assert default_time.isoformat() == "20:00:00+08:00"


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
async def test_default_schedule_time_with_timezone(app: App, default_config: Dict):
    """测试设置默认定时发送时间，同时设置时区"""
    from nonebot_plugin_wordcloud.config import Config

    config = Config.parse_obj(default_config)

    default_time = config.wordcloud_default_schedule_time
    assert default_time.isoformat() == "20:00:00"
    assert default_time.tzinfo == ZoneInfo("Asia/Tokyo")
