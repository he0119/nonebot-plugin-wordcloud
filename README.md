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

因为插件依赖数据库，所以需要在配置文件中添加

```env
DATASTORE_ENABLE_DATABASE=true
```

插件启动完成后，发送 `/今日词云` 或 `/昨日词云` 获取词云。

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
- 默认: 自带的字体
- 说明: 生成图片的字体文件位置

### wordcloud_stopwords_path

- 类型: `str`
- 默认: 自带的停词表
- 说明: 生成图片的停词表位置
