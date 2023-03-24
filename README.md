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
  <a href="https://jq.qq.com/?_wv=1027&k=7zQUpiGp">
    <img src="https://img.shields.io/badge/QQ%E7%BE%A4-730374631-orange?style=flat-square" alt="QQ Chat Group">
  </a>
</p>

## 1. 简介

插件依赖 [nonebot-plugin-chatrecorder](https://github.com/MeetWq/nonebot-plugin-chatrecorder) 提供消息存储。

## 2. 指令

- 查看帮助

待插件启动完成后，发送 `/词云` 可获取插件使用方法。发送 `/词云` 可获取插件使用方法

- 查看词云

| 功能         | 指令          | 权限   |
| :----------- | :------------ | :----- |
| 查看今日词云 | `/今日词云` | 所有人 |
| 查看昨日词云 | `/昨日词云` | 所有人 |
| 查看本周词云 | `/本周词云` | 所有人 |
| 查看上周词云 | `/上周词云` | 所有人 |
| 查看本月词云 | `/本月词云` | 所有人 |
| 查看上月词云 | `/上月词云` | 所有人 |
| 查看年度词云 | `/年度词云` | 所有人 |
| 查看历史词云 | `/历史词云` | 所有人 |

> 补充： 如果想获取自己的词云，可在上述命令前添加 `我的`，如 `/我的今日词云`。

- 管理词云

| 功能                     | 指令                                                                     | 权限                 | 说明                                                                                                                                                                                                                                                                                      |
| :----------------------- | ------------------------------------------------------------------------ | :------------------- | :---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| 设置词云形状             | `/设置词云形状`                                                        | 超级用户             | 发送一张png图片作为当前群词云形状，每个群各自独立                                                                                                                                                                                                                                         |
| 删除词云形状             | `/删除词云形状`                                                        | 超级用户             | 删除本群词云形状                                                                                                                                                                                                                                                                          |
| 设置词云默认形状         | `/设置词云默认形状`                                                    | 超级用户             | 发送一张png图片作为所有词云的默认形状，每个群都会改变                                                                                                                                                                                                                                     |
| 删除词云默认形状         | `/删除词云默认形状`                                                    | 超级用户             | 删除默认词云形状，继续使用词云默认的矩形                                                                                                                                                                                                                                                  |
| 开启词云每日定时发送     | `/开启词云每日定时发送` 或<br />`/开启词云每日定时发送` + `[时间]` | 超级用户/群主/管理员 | 1. 设置本群每日定时发送词云，默认22:00:00 + utc-0，<br />时区需要通过配置项 `wordcloud_timezone `设置，<br />默认将在每天 [wordcloud_default_schedule_time](#wordcloud_default_schedule_time) 设置的时间发送今日词云。<br />2. `[时间]`格式: hh:mm, 例如 `/开启词云每日定时发送 23:59` |
| 关闭词云每日定时发送     | `/关闭词云每日定时发送`                                                | 超级用户/群主/管理员 | 关闭本群词云每日定时发送                                                                                                                                                                                                                                                                  |
| 查看词云每日定时发送状态 | `/词云每日定时发送状态`                                                | 超级用户/群主/管理员 | 查看定时发送状态                                                                                                                                                                                                                                                                          |

## 3. 配置项

配置方式：直接在 NoneBot **全局配置文件(.env)**中添加以下配置项或在**系统环境变量**中配置，

优先级：系统环境变量 > 全局配置文件(.env)

- 词云形状

| 配置项                     | 类型 | 默认值      | 说明                                                                                   |
| :------------------------- | ---- | :---------- | :------------------------------------------------------------------------------------- |
| wordcloud_width            | int  | `1920`    | 生成图片的宽度                                                                         |
| wordcloud_height           | int  | `1200`    | 生成图片的高度                                                                         |
| wordcloud_background_color | str  | `black`   | 生成图片的背景颜色                                                                     |
| wordcloud_colormap         | str  | `viridis` | 生成图片的字体[色彩映射表](https://matplotlib.org/stable/tutorials/colors/colormaps.html) |

- 文件路径

| 配置项                   | 类型 | 默认                   | 说明                                                                                                                                                                                                                                                                                                                                                                      |
| :----------------------- | :--- | :--------------------- | :------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| wordcloud_font_path      | str  | 自带的字体（思源黑体） | 生成图片的字体文件位置                                                                                                                                                                                                                                                                                                                                                    |
| wordcloud_stopwords_path | str  | None                   | 结巴分词的[停用词表](https://github.com/fxsjy/jieba#%E5%9F%BA%E4%BA%8E-tf-idf-%E7%AE%97%E6%B3%95%E7%9A%84%E5%85%B3%E9%94%AE%E8%AF%8D%E6%8A%BD%E5%8F%96) 位置, 用来屏蔽某些词语<br />例如：`"./wordcloud_extra_dict/stopword.txt"`<br />表示屏蔽*stopword.txt*中的词语，<br />格式参考[stop_words.txt](https://github.com/fxsjy/jieba/blob/master/extra_dict/stop_words.txt) |
| wordcloud_userdict_path  | str  | None                   | 结巴分词的[自定义词典](https://github.com/fxsjy/jieba#%E8%BD%BD%E5%85%A5%E8%AF%8D%E5%85%B8) 位置                                                                                                                                                                                                                                                                             |

- 定时任务

| 配置项                          | 类型 | 默认      | 说明                                                                                                                                                                                  |
| :------------------------------ | :--- | :-------- | :------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| wordcloud_timezone              | str  | None      | 用户自定义的[时区](https://docs.python.org/zh-cn/3/library/zoneinfo.html)，留空则使用系统时区，时区列表可参考：[时区列表](https://timezonedb.com/time-zones)，<br />例如：`Asia/Shanghai` |
| wordcloud_default_schedule_time | str  | `22:00` | 默认定时发送时间，当开启词云每日定时发送时没有提供具体时间，<br />将会在这个时间发送每日词云                                                                                          |

- WordCloud 参数

| 配置项                     | 类型               | 默认      | 说明                                                                                                                                                                                                                                                                        |
| :------------------------- | :----------------- | :-------- | :-------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| wordcloud_options          | `Dict[str, Any]` | `{}`    | 向[WordCloud](https://amueller.github.io/word_cloud/generated/wordcloud.WordCloud.html#wordcloud.WordCloud) 传递的参数。拥有最高优先级，将会覆盖以上词云的配置项，<br />例如：`{"background_color":"black","max_words":2000,"contour_width":3, "contour_color":"steelblue"}` |
| wordcloud_exclude_user_ids | `Set[str]`       | `set()` | 排除的用户 ID(QQ号) 列表（全局，不区分平台），<br />例如：`["123456","456789"]`                                                                                                                                                                                           |
