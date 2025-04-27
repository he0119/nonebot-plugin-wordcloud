# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/zh-CN/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/lang/zh-CN/spec/v2.0.0.html).

## [Unreleased]

### Added

- 添加是否发送词云图片时回复消息的配置项

## [0.9.0] - 2025-01-14

### Added

- 适配 chatrecorder 0.7.0

## [0.8.1] - 2024-12-24

### Added

- 给快捷命令添加人类可读描述

### Fixed

- 限制 chatrecorder 的版本并添加 session 依赖

## [0.8.0] - 2024-08-15

### Added

- 添加命令的帮助信息

### Changed

- 事件响应器现在将阻断事件的传播

## [0.7.3] - 2024-07-13

### Fixed

- 适配 Alconna 0.49.0

## [0.7.2] - 2024-04-29

### Fixed

- 修复某个群组定时发送词云失败时影响其他群组的问题

## [0.7.1] - 2024-03-24

### Fixed

- 修复 shortcut 匹配问题

## [0.7.0] - 2024-03-01

### Added

- 适配 Pydantic V2

## [0.6.1] - 2023-10-24

### Added

- 升级 orm 版本

## [0.6.0] - 2023-10-18

### Changed

- 直接使用 cesaa 中的函数替代 chatrecorder
- 使用 alconna 新提供的依赖注入
- 迁移至 nb orm
- 如果安装有 datastore 则从中迁移数据

## [0.5.2] - 2023-08-26

### Fixed

- 提高 NoneBot 版本限制修复报错问题

## [0.5.1] - 2023-08-26

### Fixed

- 修复默认不遵守 nb 的 command_start 配置的问题

## [0.5.0] - 2023-08-24

### Added

- 支持多适配器
- 支持随机选择色彩映射表的值

### Changed

- 使用 Alconna 快捷指令简化代码

### Fixed

- 修复定时发送的词云没有排除指定用户的问题

## [0.4.9] - 2023-06-27

### Added

- 适配最新插件元数据

## [0.4.8] - 2023-03-19

### Added

- 支持直接向词云传递参数
- 支持排除特定用户

### Fixed

- 修复运行迁移脚本出错的问题

## [0.4.7] - 2023-03-12

### Fixed

- 修复默认词云形状无效的问题

## [0.4.6] - 2023-03-07

### Fixed

- 修复 UniqueConstraint 失效的问题
- 修复无法在 PostgreSQL 与 MySQL 上使用的问题

## [0.4.5] - 2023-03-04

### Fixed

- 修复 OneBot 12 协议下下载图片出错的问题

## [0.4.4] - 2023-02-02

### Fixed

- 通过每次关闭线程池修复内存泄漏问题

## [0.4.3] - 2023-02-01

### Fixed

- 修复 GROUP BY 在 PostgreSQL 上的用法错误
- 设置/删除词云默认形状的权限调整为仅超级用户

## [0.4.2] - 2023-01-23

### Fixed

- 修复 OneBot 适配器依赖问题

## [0.4.1] - 2023-01-23

### Fixed

- 修复迁移脚本没有给之前的数据设置默认值的问题

## [0.4.0] - 2023-01-22

### Added

- 支持 OneBot 12 适配器
- 添加 `上周词云` 和 `上月词云`

## [0.3.1] - 2022-12-27

### Added

- 支持定时发送每日词云
- 支持每个群单独设置词云形状

### Fixed

- 修复发送 `/词云` 后帮助信息为空的问题

## [0.3.0] - 2022-10-06

### Added

- 支持自定义词云形状

### Changed

- 仅支持 NoneBot2 RC1 及以上版本

## [0.2.4] - 2022-07-07

### Fixed

- 修复无法正确获取到消息的问题

## [0.2.3] - 2022-07-03

### Added

- 适配插件元数据

### Changed

- 调整 `font_path` 默认配置设置方法

### Fixed

- 修复网址预处理无法处理掉微博国际版分享地址的问题

## [0.2.2] - 2022-06-10

### Added

- 添加字体色彩映射表配置项

## [0.2.1] - 2022-05-25

### Changed

- 将函数放在执行器中运行防止生成词云时阻塞事件循环

## [0.2.0] - 2022-05-25

### Changed

- 直接使用基于 TF-IDF 算法的关键词抽取
- 不需要限制 tzdata 的版本

### Removed

- 删除 Python 3.7 的支持

## [0.1.2] - 2022-05-21

### Changed

- 调整插件加载方式，并删除 numpy 依赖

## [0.1.1] - 2022-04-16

### Changed

- 仅当消息为词云两字时才发送帮助

## [0.1.0] - 2022-02-26

### Changed

- 历史词云支持直接输入日期和时间，不局限于日期

### Removed

- 移除迁移词云命令

## [0.0.8] - 2022-02-23

### Added

- 支持查询本周与本月词云

### Changed

- 我的词云系列命令，回复消息时将会@用户

## [0.0.7] - 2022-02-23

### Added

- 支持查询我的词云
- 支持查询年度词云

## [0.0.6] - 2022-02-04

### Added

- 支持设置时区

### Fixed

- 修复 emoji 去除不全的问题
- 修复日期错误时报错的问题

## [0.0.5] - 2022-02-02

### Added

- 支持添加用户词典
- 新增历史词云功能
- 新增回复帮助信息

### Changed

- 结巴分词使用精确模式替代之前的全模式
- 使用 nonebot-plugin-chatrecorder 作为数据源

## [0.0.4] - 2022-01-30

### Changed

- 去除网址与特殊字符（不可见字符与 emoji）

## [0.0.3] - 2022-01-30

### Changed

- 使用思源黑体
- 更新停用词表

## [0.0.2] - 2022-01-29

### Fixed

- 修复 Python 3.9 以下版本无法运行的问题

## [0.0.1] - 2022-01-29

### Added

- 可以使用的版本。

[Unreleased]: https://github.com/he0119/nonebot-plugin-wordcloud/compare/v0.9.0...HEAD
[0.9.0]: https://github.com/he0119/nonebot-plugin-wordcloud/compare/v0.8.1...v0.9.0
[0.8.1]: https://github.com/he0119/nonebot-plugin-wordcloud/compare/v0.8.0...v0.8.1
[0.8.0]: https://github.com/he0119/nonebot-plugin-wordcloud/compare/v0.7.3...v0.8.0
[0.7.3]: https://github.com/he0119/nonebot-plugin-wordcloud/compare/v0.7.2...v0.7.3
[0.7.2]: https://github.com/he0119/nonebot-plugin-wordcloud/compare/v0.7.1...v0.7.2
[0.7.1]: https://github.com/he0119/nonebot-plugin-wordcloud/compare/v0.7.0...v0.7.1
[0.7.0]: https://github.com/he0119/nonebot-plugin-wordcloud/compare/v0.6.1...v0.7.0
[0.6.1]: https://github.com/he0119/nonebot-plugin-wordcloud/compare/v0.6.0...v0.6.1
[0.6.0]: https://github.com/he0119/nonebot-plugin-wordcloud/compare/v0.5.2...v0.6.0
[0.5.2]: https://github.com/he0119/nonebot-plugin-wordcloud/compare/v0.5.1...v0.5.2
[0.5.1]: https://github.com/he0119/nonebot-plugin-wordcloud/compare/v0.5.0...v0.5.1
[0.5.0]: https://github.com/he0119/nonebot-plugin-wordcloud/compare/v0.4.9...v0.5.0
[0.4.9]: https://github.com/he0119/nonebot-plugin-wordcloud/compare/v0.4.8...v0.4.9
[0.4.8]: https://github.com/he0119/nonebot-plugin-wordcloud/compare/v0.4.7...v0.4.8
[0.4.7]: https://github.com/he0119/nonebot-plugin-wordcloud/compare/v0.4.6...v0.4.7
[0.4.6]: https://github.com/he0119/nonebot-plugin-wordcloud/compare/v0.4.5...v0.4.6
[0.4.5]: https://github.com/he0119/nonebot-plugin-wordcloud/compare/v0.4.4...v0.4.5
[0.4.4]: https://github.com/he0119/nonebot-plugin-wordcloud/compare/v0.4.3...v0.4.4
[0.4.3]: https://github.com/he0119/nonebot-plugin-wordcloud/compare/v0.4.2...v0.4.3
[0.4.2]: https://github.com/he0119/nonebot-plugin-wordcloud/compare/v0.4.1...v0.4.2
[0.4.1]: https://github.com/he0119/nonebot-plugin-wordcloud/compare/v0.4.0...v0.4.1
[0.4.0]: https://github.com/he0119/nonebot-plugin-wordcloud/compare/v0.3.1...v0.4.0
[0.3.1]: https://github.com/he0119/nonebot-plugin-wordcloud/compare/v0.3.0...v0.3.1
[0.3.0]: https://github.com/he0119/nonebot-plugin-wordcloud/compare/v0.2.4...v0.3.0
[0.2.4]: https://github.com/he0119/nonebot-plugin-wordcloud/compare/v0.2.3...v0.2.4
[0.2.3]: https://github.com/he0119/nonebot-plugin-wordcloud/compare/v0.2.2...v0.2.3
[0.2.2]: https://github.com/he0119/nonebot-plugin-wordcloud/compare/v0.2.1...v0.2.2
[0.2.1]: https://github.com/he0119/nonebot-plugin-wordcloud/compare/v0.2.0...v0.2.1
[0.2.0]: https://github.com/he0119/nonebot-plugin-wordcloud/compare/v0.1.2...v0.2.0
[0.1.2]: https://github.com/he0119/nonebot-plugin-wordcloud/compare/v0.1.1...v0.1.2
[0.1.1]: https://github.com/he0119/nonebot-plugin-wordcloud/compare/v0.1.0...v0.1.1
[0.1.0]: https://github.com/he0119/nonebot-plugin-wordcloud/compare/v0.0.8...v0.1.0
[0.0.8]: https://github.com/he0119/nonebot-plugin-wordcloud/compare/v0.0.7...v0.0.8
[0.0.7]: https://github.com/he0119/nonebot-plugin-wordcloud/compare/v0.0.6...v0.0.7
[0.0.6]: https://github.com/he0119/nonebot-plugin-wordcloud/compare/v0.0.5...v0.0.6
[0.0.5]: https://github.com/he0119/nonebot-plugin-wordcloud/compare/v0.0.4...v0.0.5
[0.0.4]: https://github.com/he0119/nonebot-plugin-wordcloud/compare/v0.0.3...v0.0.4
[0.0.3]: https://github.com/he0119/nonebot-plugin-wordcloud/compare/v0.0.2...v0.0.3
[0.0.2]: https://github.com/he0119/nonebot-plugin-wordcloud/compare/v0.0.1...v0.0.2
[0.0.1]: https://github.com/he0119/nonebot-plugin-wordcloud/releases/tag/v0.0.1
