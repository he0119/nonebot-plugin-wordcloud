<!-- markdownlint-disable MD033 MD036 MD041 -->

<p align="center">
  <a href="https://v2.nonebot.dev/"><img src="https://v2.nonebot.dev/logo.png" width="200" height="200" alt="nonebot"></a>
</p>

<div align="center">

# NoneBot Plugin WordCloud

_✨ NoneBot 词云插件 ✨_

</div>

<p align="center">
  <a href="https://raw.githubusercontent.com/he0119/nonebot-plugin-wordcloud/master/LICENSE">
    <img src="https://img.shields.io/github/license/he0119/nonebot-plugin-wordcloud.svg" alt="license">
  </a>
  <a href="https://pypi.python.org/pypi/nonebot-plugin-wordcloud">
    <img src="https://img.shields.io/pypi/v/nonebot-plugin-wordcloud.svg" alt="pypi">
  </a>
  <img src="https://img.shields.io/badge/python-3.7.3+-blue.svg" alt="python">
</p>

## 使用方式

插件依赖 [nonebot-plugin-chatrecorder](https://github.com/MeetWq/nonebot-plugin-chatrecorder) 提供消息存储。

待插件启动完成后，发送 `/今日词云`、`/昨日词云` 或 `/历史词云` 即可获取词云。

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

### wordcloud_font_path

- 类型: `str`
- 默认: 自带的字体（思源黑体）
- 说明: 生成图片的字体文件位置

### wordcloud_stopwords_path

- 类型: `str`
- 默认: 自带的停用词表
- 说明: 生成图片的停用词表位置

### wordcloud_userdict_path

- 类型: `str`
- 默认: `None`
- 说明: 结巴分词的 [自定义词典](https://github.com/fxsjy/jieba#%E8%BD%BD%E5%85%A5%E8%AF%8D%E5%85%B8) 位置

### wordcloud_timezone

- 类型: `str`
- 默认: `None`
- 说明: 用户自定义的 [时区](https://docs.python.org/zh-cn/3/library/zoneinfo.html)，留空则使用系统时区

## 迁移数据

从 `0.0.4` 及以下版本升级至 `0.0.5` 之后，可以通过发送 `/迁移词云` 迁移数据。

注意：这个命令将会在 `0.1.0` 版本删除。
