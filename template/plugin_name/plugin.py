# -*- coding: utf-8 -*-
"""
示例插件 —— 插件 API 契约 (plugin-api-v1) 写法。

规则：
- 只允许从 neobot.plugin_api 导入（装饰器 / 模型 / 服务 / 工具）
- 禁止 import neobot.core.* / neobot.adapters.*（CI 会拒绝）
- manifest.json 的 name 必须与插件目录名一致
"""
from neobot.plugin_api import (
    Bot,
    MessageEvent,
    ModuleLogger,
    command,
    define_plugin,
    platform_command,
)

logger = ModuleLogger("MyPlugin")

# manifest.json 是权威清单,这里重复声明 name 用于运行时一致性检查
plugin_manifest = define_plugin(
    name="plugin_name",
    description="一句话功能描述",
    usage="/mycmd [参数] - 功能说明",
    version="0.1.0",
    author="你的名字",
)


@command("mycmd", "我的命令")
async def handle_mycmd(bot: Bot, event: MessageEvent, args: list[str]):
    """模块级函数命令：/mycmd 触发。"""
    await event.reply("你好！这是插件模板。")


@platform_command(["qq", "discord"], "mycmd2")
async def handle_mycmd2(bot: Bot, event: MessageEvent, args: list[str]):
    """平台感知命令：仅 QQ / Discord 生效。"""
    await event.reply("平台感知命令示例。")
