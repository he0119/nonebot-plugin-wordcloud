"""测试使用说明生成功能"""

import pytest
from nonebug import App


@pytest.mark.parametrize(
    "default_personal",
    [
        pytest.param(False, id="default_group"),
        pytest.param(True, id="default_personal"),
    ],
)
async def test_get_usage_both_modes(app: App, default_personal: bool):
    """测试不同默认模式下的使用说明"""
    from nonebot_plugin_wordcloud import get_usage
    from nonebot_plugin_wordcloud.config import plugin_config

    # 备份原始配置
    original_config = plugin_config.wordcloud_default_personal

    try:
        # 设置测试模式
        plugin_config.wordcloud_default_personal = default_personal

        usage = get_usage()

        # 检查基本命令说明（在两种模式下都应该存在）
        assert "通过快捷命令，以获取常见时间段内的词云" in usage
        assert "格式：/<时间段>词云" in usage
        assert "时间段关键词有：今日，昨日，本周，上周，本月，上月，年度" in usage
        assert "示例：/今日词云，/昨日词云" in usage

        # 检查历史词云说明
        assert "提供日期与时间，以获取指定时间段内的词云" in usage
        assert "格式：/历史词云 [日期或时间段]" in usage
        assert "示例：/历史词云" in usage
        assert "/历史词云 2022-01-01" in usage
        assert "/历史词云 2022-01-01~2022-02-22" in usage

        # 检查设置和定时功能说明
        assert "设置自定义词云形状" in usage
        assert "设置默认词云形状（仅超级用户）" in usage
        assert "设置定时发送每日词云" in usage

        # 检查模式特定的说明
        if default_personal:
            # 默认个人模式
            assert '默认获取个人数据，如需获取群组数据请添加前缀"本群"' in usage
            assert "格式：/本群<时间段>词云" in usage
            assert "示例：/本群今日词云" in usage
            assert "格式：/我的<基本命令格式>" in usage
            assert "示例：/我的今日词云" in usage
        else:
            # 默认群组模式
            assert '默认获取群组数据，如需获取个人数据请添加前缀"我的"' in usage
            assert "格式：/我的<时间段>词云" in usage
            assert "示例：/我的今日词云" in usage
            assert "格式：/本群<基本命令格式>" in usage
            assert "示例：/本群今日词云" in usage

    finally:
        # 恢复原始配置
        plugin_config.wordcloud_default_personal = original_config


@pytest.mark.parametrize(
    "default_personal",
    [
        pytest.param(False, id="default_group"),
        pytest.param(True, id="default_personal"),
    ],
)
async def test_get_wordcloud_cmd_usage_both_modes(app: App, default_personal: bool):
    """测试不同默认模式下的词云命令简短使用说明"""
    from nonebot_plugin_wordcloud import get_wordcloud_cmd_usage
    from nonebot_plugin_wordcloud.config import plugin_config

    # 备份原始配置
    original_config = plugin_config.wordcloud_default_personal

    try:
        # 设置测试模式
        plugin_config.wordcloud_default_personal = default_personal

        usage = get_wordcloud_cmd_usage()

        # 检查基本说明（在两种模式下都应该存在）
        assert "通过快捷命令，以获取常见时间段内的词云" in usage
        assert "格式：/<时间段>词云" in usage
        assert "时间段关键词有：今日，昨日，本周，上周，本月，上月，年度" in usage
        assert "提供日期与时间，以获取指定时间段内的词云" in usage
        assert "格式：/历史词云 [日期或时间段]" in usage

        # 检查模式特定的说明
        if default_personal:
            # 默认个人模式
            assert "默认获取个人数据，如需获取群组数据请使用'本群'前缀" in usage
            assert "可以添加前缀'我的'来明确获取个人数据" in usage
        else:
            # 默认群组模式
            assert "默认获取群组数据，如需获取个人数据请使用'我的'前缀" in usage
            assert "可以添加前缀'本群'来明确获取群组数据" in usage

    finally:
        # 恢复原始配置
        plugin_config.wordcloud_default_personal = original_config


async def test_usage_consistency(app: App):
    """测试两种使用说明的一致性"""
    from nonebot_plugin_wordcloud import get_usage, get_wordcloud_cmd_usage
    from nonebot_plugin_wordcloud.config import plugin_config

    # 备份原始配置
    original_config = plugin_config.wordcloud_default_personal

    try:
        for mode in [True, False]:
            plugin_config.wordcloud_default_personal = mode

            full_usage = get_usage()
            short_usage = get_wordcloud_cmd_usage()

            # 检查短版本的内容是否在完整版本中
            assert "通过快捷命令，以获取常见时间段内的词云" in full_usage
            assert "通过快捷命令，以获取常见时间段内的词云" in short_usage

            assert "格式：/<时间段>词云" in full_usage
            assert "格式：/<时间段>词云" in short_usage

            assert "格式：/历史词云 [日期或时间段]" in full_usage
            assert "格式：/历史词云 [日期或时间段]" in short_usage

            # 检查模式特定的说明
            if mode:  # 个人模式
                assert "默认获取个人数据" in full_usage
                assert "默认获取个人数据" in short_usage
                assert '"本群"' in full_usage
                assert "'本群'前缀" in short_usage
            else:  # 群组模式
                assert "默认获取群组数据" in full_usage
                assert "默认获取群组数据" in short_usage
                assert '"我的"' in full_usage
                assert "'我的'前缀" in short_usage

    finally:
        # 恢复原始配置
        plugin_config.wordcloud_default_personal = original_config


async def test_usage_format_structure(app: App):
    """测试使用说明的格式结构"""
    from nonebot_plugin_wordcloud import get_usage

    usage = get_usage()

    # 检查是否包含所有主要功能模块
    sections = [
        "通过快捷命令，以获取常见时间段内的词云",
        "提供日期与时间，以获取指定时间段内的词云",
        "设置自定义词云形状",
        "设置默认词云形状",
        "设置定时发送每日词云",
    ]

    for section in sections:
        assert section in usage

    # 检查是否包含必要的示例
    examples = [
        "/今日词云",
        "/昨日词云",
        "/历史词云",
        "/历史词云 2022-01-01",
        "/历史词云 2022-01-01~2022-02-22",
        "/设置词云形状",
        "/设置词云默认形状",
        "/删除词云默认形状",
        "/词云每日定时发送状态",
        "/开启词云每日定时发送",
        "/关闭词云每日定时发送",
    ]

    for example in examples:
        assert example in usage


async def test_usage_iso8601_format_mention(app: App):
    """测试使用说明中是否正确提及ISO8601格式"""
    from nonebot_plugin_wordcloud import get_usage, get_wordcloud_cmd_usage

    full_usage = get_usage()
    short_usage = get_wordcloud_cmd_usage()

    # 检查是否提及ISO8601格式
    assert "ISO8601" in full_usage
    assert "ISO8601" in short_usage
    assert "2022-02-22T22:22:22" in full_usage
    assert "2022-02-22T22:22:22" in short_usage


async def test_usage_time_keywords(app: App):
    """测试使用说明中的时间关键词"""
    from nonebot_plugin_wordcloud import get_usage, get_wordcloud_cmd_usage

    full_usage = get_usage()
    short_usage = get_wordcloud_cmd_usage()

    # 检查所有时间关键词
    time_keywords = ["今日", "昨日", "本周", "上周", "本月", "上月", "年度"]
    time_keywords_text = "，".join(time_keywords)

    assert time_keywords_text in full_usage
    assert time_keywords_text in short_usage

    # 检查时间关键词的具体使用示例
    # 根据实际使用说明，只有少数几个关键词有具体示例
    basic_examples = ["/今日词云", "/昨日词云"]
    for example in basic_examples:
        assert example in full_usage


async def test_usage_completeness(app: App):
    """测试使用说明的完整性"""
    from nonebot_plugin_wordcloud import get_usage

    usage = get_usage()

    # 检查是否包含所有必要的命令类型
    command_types = [
        "/<时间段>词云",
        "/历史词云",
        "/设置词云形状",
        "/设置词云默认形状",
        "/删除词云默认形状",
        "/词云每日定时发送状态",
        "/开启词云每日定时发送",
        "/关闭词云每日定时发送",
    ]

    for cmd_type in command_types:
        assert cmd_type in usage

    # 检查是否包含时间格式说明
    assert "ISO8601" in usage
    assert "2022-02-22T22:22:22" in usage

    # 检查是否包含权限说明
    assert "仅超级用户" in usage
