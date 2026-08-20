# NeoBot Plugins

**NeoBot 官方插件仓库 / 插件 Registry**

基于 [NeoBot](https://github.com/Fairy-Oracle-Sanctuary/NeoBot) 的 **plugin-api-v1** 契约开发的插件收录仓库。
每个插件声明自己的 `plugin_manifest`，通过 CI 校验后收录进 `index.json`，供未来的包管理器（`neobot plugin install`）分发。

## 仓库结构

```
.
├── plugins/               # 插件源码（每个插件一个子目录）
│   └── <plugin-name>/     # 插件名 = manifest.name
│       ├── plugin.py      # 插件入口（或包式插件 __init__.py）
│       ├── manifest.json  # 插件清单（CI 校验）
│       └── ...            # 插件私有模块
├── template/              # 新插件模板（复制即用）
├── index.json             # 自动生成的插件索引（勿手改，CI 生成）
└── .github/workflows/     # CI：校验 + 测试 + 索引生成
```

## 插件开发快速开始

1. 复制模板：

```bash
cp -r template/plugin_name plugins/my_plugin
```

2. 编辑 `manifest.json` 与 `plugin.py`（只允许 import `neobot.plugin_api` 命名空间）。

3. 提交推送，CI 自动校验（manifest 合法性 / 契约边界 / ruff / pytest），通过后自动收录进 `index.json`。

## 插件清单格式

```json
{
  "name": "my_plugin",
  "description": "一句话功能描述",
  "usage": "/mycmd - 用法",
  "version": "0.1.0",
  "author": "镀铬酸钾",
  "api_version": "1",
  "dependencies": []
}
```

## 契约规则（摘要）

- 插件**只允许**从 `neobot.plugin_api` 命名空间导入（装饰器 / 模型 / 服务 / 工具）
- **禁止**直接 import `neobot.core.*` / `neobot.adapters.*`（CI 会拒绝）
- `name` 需为 1-64 位字母/数字/下划线/连字符，字母开头
- `version` 遵循 semver（如 `0.1.0`）

详见 [NeoBot docs/plugin-api.md](https://github.com/Fairy-Oracle-Sanctuary/NeoBot/blob/main/docs/plugin-api.md)。

## 收录流程

1. PR / push 到 `main` 分支，`plugins/` 下有改动
2. CI 对每个改动插件运行：manifest 校验 → 契约边界扫描 → ruff → pytest
3. 全部通过后生成/更新 `index.json`
4. 包管理器可读取 `index.json` 获取插件列表与版本

## 许可证

MIT（见 [LICENSE](LICENSE)）。插件本身的许可证由各插件 manifest 声明。
