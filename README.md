<!-- markdownlint-disable MD033 MD036 MD041 -->

<p align="center">
  <a href="https://v2.nonebot.dev/"><img src="https://v2.nonebot.dev/logo.png" width="200" height="200" alt="nonebot"></a>
</p>

<div align="center">

# NoneBot Plugin WordCloud

_✨ NoneBot 词云插件 ✨_

</div>

<p align="center">
  <a href="https://raw.githubusercontent.com/he0119/nonebot-plugin-wordcloud/main/LICENSE">
    <img src="https://img.shields.io/github/license/he0119/nonebot-plugin-wordcloud.svg" alt="license">
  </a>
  <a href="https://pypi.python.org/pypi/nonebot-plugin-wordcloud">
    <img src="https://img.shields.io/pypi/v/nonebot-plugin-wordcloud.svg" alt="pypi">
  </a>
  <img src="https://img.shields.io/badge/python-3.8+-blue.svg" alt="python">
  <a href="https://codecov.io/gh/he0119/nonebot-plugin-wordcloud">
    <img src="https://codecov.io/gh/he0119/nonebot-plugin-wordcloud/branch/main/graph/badge.svg?token=e2ECtMI91C"/>
  </a>
</p>

## 使用方式

插件依赖 [nonebot-plugin-chatrecorder](https://github.com/MeetWq/nonebot-plugin-chatrecorder) 提供消息存储。

待插件启动完成后，发送 `/今日词云`、`/昨日词云`、`/本周词云`、`/上周词云`、`/本月词云`、`/上月词云`、`/年度词云` 或 `/历史词云` 即可获取词云。

如果想获取自己的词云，可在上述指令前添加 `我的`，如 `/我的今日词云`。

[超级用户](https://v2.nonebot.dev/docs/tutorial/configuration#superusers)，群主或管理员可发送 `/设置词云形状` 设置词云的形状。通过 `/删除词云形状` 删除自定义的词云形状以使用默认形状。

超级用户可发送 `/设置词云默认形状` 设置所有词云的默认形状。通过 `/删除词云默认形状` 删除自定义的词云默认形状，继续使用词云默认的矩形。

超级用户，群主或管理员可发送 `/开启词云每日定时发送` 开启每日定时发送，默认将在每天 [wordcloud_default_schedule_time](#wordcloud_default_schedule_time) 设置的时间发送今日词云。通过 `/开启词云每日定时发送 23:59` 设置自定义的发送时间。发送 `/关闭词云每日定时发送` 关闭每日定时发送。发送 `/词云每日定时发送状态` 查询当前的设置。

## 配置项

配置方式：直接在 `NoneBot` 全局配置文件中添加以下配置项即可。

### wordcloud_width

- 类型: `int`
- 默认: `1920`
- 说明: 生成图片的宽度

### wordcloud_height

- 类型: `int`
- 默认: `1200`
- 说明: 生成图片的高度

### wordcloud_background_color

- 类型: `str`
- 默认: `black`
- 说明: 生成图片的背景颜色

### wordcloud_colormap

- 类型: `str`
- 默认: `viridis`
- 说明: 生成图片的字体 [色彩映射表](https://matplotlib.org/stable/tutorials/colors/colormaps.html)

### wordcloud_font_path

- 类型: `str`
- 默认: 自带的字体（思源黑体）
- 说明: 生成图片的字体文件位置

### wordcloud_stopwords_path

- 类型: `str`
- 默认: `None`
- 说明: 结巴分词的 [停用词表](https://github.com/fxsjy/jieba#%E5%9F%BA%E4%BA%8E-tf-idf-%E7%AE%97%E6%B3%95%E7%9A%84%E5%85%B3%E9%94%AE%E8%AF%8D%E6%8A%BD%E5%8F%96) 位置

### wordcloud_userdict_path

- 类型: `str`
- 默认: `None`
- 说明: 结巴分词的 [自定义词典](https://github.com/fxsjy/jieba#%E8%BD%BD%E5%85%A5%E8%AF%8D%E5%85%B8) 位置

### wordcloud_timezone

- 类型: `str`
- 默认: `None`
- 说明: 用户自定义的 [时区](https://docs.python.org/zh-cn/3/library/zoneinfo.html)，留空则使用系统时区

### wordcloud_default_schedule_time

- 类型: `str`
- 默认: `22:00`
- 说明: 默认定时发送时间，当开启词云每日定时发送时没有提供具体时间，将会在这个时间发送每日词云
