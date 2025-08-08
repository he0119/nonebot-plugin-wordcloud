# NoneBot 词云插件 AI 编码指南

欢迎来到 `nonebot-plugin-wordcloud` 项目！本指南旨在帮助 AI 编码代理快速理解项目结构、关键组件和开发工作流程。

## 1. 项目概述

本项目是一个为 [NoneBot2](https://v2.nonebot.dev/) 框架开发的词云插件。它能够收集聊天记录，并根据消息生成词云图片。

- **核心功能**: 从聊天记录中提取文本，使用 `wordcloud` 和 `jieba` 分词生成词云图。
- **命令系统**: 使用 `nonebot-plugin-alconna` 定义和解析用户命令。
- **数据持久化**: 使用 `nonebot-plugin-orm` (基于 SQLAlchemy) 将聊天记录存储在数据库中。
- **跨平台支持**: 通过 `nonebot-plugin-saa` 和 `nonebot-plugin-uninfo` 实现跨聊天平台（如 QQ、OneBot 等）的适配。
- **定时任务**: 使用 `nonebot-plugin-apscheduler` 实现每日定时发送词云。

## 2. 关键模块与代码结构

理解以下文件是快速上手的关键：

- **`nonebot_plugin_wordcloud/__init__.py`**: 插件主入口。定义了所有用户命令（如 `/今日词云`），并使用 `on_alconna` 注册匹配器。这是理解用户交互逻辑的起点。
- **`nonebot_plugin_wordcloud/data_source.py`**: 词云生成的核心逻辑。`get_wordcloud` 函数负责：
  1.  从数据库查询消息。
  2.  使用 `jieba` 进行中文分词。
  3.  调用 `wordcloud` 库生成图片。
- **`nonebot_plugin_wordcloud/model.py`**: 定义数据库模型。`MessageRecord` 表是核心，用于存储消息内容和会话信息。
- **`nonebot_plugin_wordcloud/config.py`**: 定义插件的配置项。所有配置都通过 Pydantic 模型进行管理，并从 NoneBot 的 `.env` 文件加载。
- **`nonebot_plugin_wordcloud/schedule.py`**: 实现定时任务。`schedule_service` 负责管理和执行每日发送词云的计划。
- **`nonebot_plugin_wordcloud/utils.py`**: 包含各种辅助函数，如权限检查 (`admin_permission`) 和时区处理。

## 3. 开发工作流

- **依赖管理**: 项目使用 `uv` 管理依赖。所有依赖项都在 `pyproject.toml` 中定义。
- **测试**: 测试使用 `pytest`。运行测试的命令定义在 `pyproject.toml` 的 `[tool.poe.tasks]` 部分。
  - 运行所有测试: `poe test`
- **数据库迁移**: 项目使用 `nonebot-plugin-orm` 管理数据库。如果修改了 `model.py` 中的模型，需要生成新的迁移脚本。

## 4. 重要模式与约定

- **命令处理与 Alconna**:

  - 命令使用 `Alconna` 进行结构化定义，而不是简单的字符串匹配。例如，在 `__init__.py` 中，`/历史词云` 命令可以接受复杂的日期范围参数。
  - 修改或添加命令时，请遵循 `nonebot-plugin-alconna` 的模式，在 `__init__.py` 中定义 `Alconna` 对象和对应的 `AlconnaMatcher`。

- **会话与用户识别 (UniSession)**:

  - 为了跨平台兼容，项目使用 `nonebot-plugin-uninfo` 提供的 `UniSession` 来唯一标识一个会话（私聊或群聊）。
  - 在处理数据时，应始终通过 `UniSession.get` 来获取会话实例，并使用其 `session.id` 作为数据库查询的依据。

- **配置**:

  - 不要硬编码任何可变值。应将它们添加到 `config.py` 的 `Config` 模型中，并提供合理的默认值。

- **数据存储**:
  - 聊天记录存储在数据库中。
  - 用户上传的词云遮罩图片等文件，通过 `nonebot-plugin-localstore` 存储在 `data/nonebot_plugin_wordcloud` 目录下。

在开始编码前，请确保你已熟悉 NoneBot2 和 Alconna 的基本概念。
