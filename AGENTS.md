# NoneBot 词云插件 AI 编码指南

欢迎来到 `nonebot-plugin-wordcloud` 项目！本指南旨在帮助 AI 编码代理快速理解项目结构、关键组件和开发工作流程。

## 1. 项目概述

本项目是一个为 [NoneBot2](https://v2.nonebot.dev/) 框架开发的词云插件。它能够收集聊天记录，并根据消息生成词云图片。

- **核心功能**: 从聊天记录中提取文本，使用 `wordcloud` 和 `jieba` 分词生成词云图。
- **命令系统**: 使用 `nonebot-plugin-alconna` 定义和解析用户命令。
- **消息记录**: 通过 `nonebot-plugin-chatrecorder` 读取聊天记录；本插件不再直接维护聊天消息表。
- **数据持久化**: 使用 `nonebot-plugin-orm` (基于 SQLAlchemy) 存储插件自身数据，例如每日定时发送配置。
- **跨平台支持**: 通过 `nonebot-plugin-uninfo` 标识会话，并使用 `nonebot-plugin-alconna` 的 `Target`、`UniMessage`、`Image` 等能力发送跨平台消息。
- **定时任务**: 使用 `nonebot-plugin-apscheduler` 实现每日定时发送词云。

## 2. 关键模块与代码结构

理解以下文件是快速上手的关键：

- **`nonebot_plugin_wordcloud/__init__.py`**: 插件主入口。定义了所有用户命令（如 `/今日词云`），并使用 `on_alconna` 注册匹配器。这是理解用户交互逻辑的起点。生成词云时通过 `get_messages_plain_text` 从 `nonebot-plugin-chatrecorder` 查询消息。
- **`nonebot_plugin_wordcloud/data_source.py`**: 词云生成的核心逻辑。`get_wordcloud` 函数负责：
  1.  过滤命令消息并预处理文本。
  2.  使用 `jieba` 进行中文分词和 TF-IDF 关键词提取。
  3.  调用 `wordcloud` 库生成 PNG 图片。
- **`nonebot_plugin_wordcloud/model.py`**: 定义插件自身数据库模型。当前核心模型是 `Schedule`，用于保存每日定时发送目标和时间；聊天消息模型来自 `nonebot-plugin-chatrecorder`。
- **`nonebot_plugin_wordcloud/config.py`**: 定义插件的配置项。所有配置都通过 Pydantic 模型进行管理，并从 NoneBot 的 `.env` 文件加载。
- **`nonebot_plugin_wordcloud/schedule.py`**: 实现定时任务。`schedule_service` 负责管理和执行每日发送词云的计划，数据库中保存的是 Alconna `Target.dump(...)` 后的目标数据。
- **`nonebot_plugin_wordcloud/utils.py`**: 包含各种辅助函数，如权限检查 (`admin_permission`)、时区处理、群组场景校验和基于 `Session`/`Target` 的 mask key 生成。
- **`nonebot_plugin_wordcloud/migrations/`**: 数据库迁移脚本。修改 `Schedule` 等 ORM 模型时，需要同步迁移；当前分支包含从旧目标格式迁移到 Alconna `Target` 格式的脚本。

## 3. 开发工作流

- **依赖管理**: 项目使用 `uv` 管理依赖，构建后端为 `uv_build`。运行时依赖和开发依赖都在 `pyproject.toml` 中定义，开发依赖位于 `[dependency-groups]`。
- **Python 版本**: 当前最低支持 Python 3.10，类型标注可使用 `str | None`、`list[str]` 等现代写法。
- **测试**: 测试使用 `pytest`。运行测试的命令定义在 `pyproject.toml` 的 `[tool.poe.tasks]` 部分。
  - 运行所有测试: `poe test`
- **数据库迁移**: 项目使用 `nonebot-plugin-orm` 管理数据库。如果修改了 `model.py` 中的模型，需要生成新的迁移脚本。

## 4. 重要模式与约定

- **命令处理与 Alconna**:

  - 命令使用 `Alconna` 进行结构化定义，而不是简单的字符串匹配。例如，在 `__init__.py` 中，`/历史词云` 命令可以接受复杂的日期范围参数。
  - 修改或添加命令时，请遵循 `nonebot-plugin-alconna` 的模式，在 `__init__.py` 中定义 `Alconna` 对象和对应的 `AlconnaMatcher`。

- **会话与用户识别 (UniSession)**:

  - 为了跨平台兼容，项目使用 `nonebot-plugin-uninfo` 提供的 `UniSession` 来唯一标识一个会话（私聊或群聊）。
  - 命令处理中的会话信息优先通过依赖注入 `session: Session = UniSession()` 获取。
  - 查询聊天记录时优先调用 `nonebot-plugin-chatrecorder.get_messages_plain_text`，并传入 `session`、`filter_user`、时间范围、排除用户等过滤条件；不要直接查询旧的本插件消息表。

- **发送目标与定时任务 (Target)**:

  - 定时发送命令通过 `MessageTarget()` 获取当前 Alconna `Target`。
  - `Schedule.target` 保存 `Target.dump(only_scope=True, save_self_id=False)` 的结果，读取时使用 `Target.load(...)` 还原。
  - 定时任务发送消息时使用 `target.send(UniMessage(Image(...)))` 或 `target.send(UniMessage(Text(...)))`。
  - 根据 `Target` 查询聊天记录时，需要转换出 `scope`、`scene_type`、`scene_id` 等条件，并保持 `filter_self_id=False`、`filter_adapter=False`。

- **遮罩文件 key**:

  - `get_mask_key` 同时支持 `nonebot-plugin-uninfo` 的 `Session` 和 Alconna `Target`。
  - key 由平台 scope 和场景路径组成，例如 `QQClient_123456789`；涉及定时任务和普通命令时要保持同一规则。

- **配置**:

  - 不要硬编码任何可变值。应将它们添加到 `config.py` 的 `Config` 模型中，并提供合理的默认值。

- **数据存储**:
  - 聊天记录由 `nonebot-plugin-chatrecorder` 存储和查询。
  - 用户上传的词云遮罩图片等文件，通过 `nonebot-plugin-localstore` 存储在 `data/nonebot_plugin_wordcloud` 目录下。

在开始编码前，请确保你已熟悉 NoneBot2 和 Alconna 的基本概念。
