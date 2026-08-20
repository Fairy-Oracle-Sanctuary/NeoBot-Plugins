#!/usr/bin/env python3
"""
NeoBot 插件仓库校验脚本（CI 使用）。

职责：
1. 遍历 plugins/ 下每个插件目录，读取 manifest.json
2. 校验 manifest 字段合法性（name / version / api_version / dependencies）
3. 契约边界检查：插件源码不得 import neobot.core.* / neobot.adapters.*
4. 生成 plugins 索引（用于包管理器）

用法：
    python3 scripts/validate_plugins.py            # 校验 + 生成索引
    python3 scripts/validate_plugins.py --check-only   # 只校验，不写索引
"""
import argparse
import hashlib
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
PLUGINS_DIR = ROOT / "plugins"
INDEX_FILE = ROOT / "index.json"

NAME_RE = re.compile(r"^[a-zA-Z][a-zA-Z0-9_-]{0,63}$")
VERSION_RE = re.compile(r"^\d+\.\d+\.\d+$")
API_VERSION = "1"
DEFAULT_LICENSE = "AGPL-3.0"

# 契约允许的命名空间前缀（相对插件自身导入而言）
ALLOWED_IMPORTS = ("neobot.plugin_api", "neobot.models", "neobot.plugins")
FORBIDDEN_PREFIXES = ("neobot.core", "neobot.adapters")


class ValidationError(Exception):
    pass


def validate_manifest(plugin_dir: Path) -> dict:
    """校验单个插件的 manifest.json，返回解析后的 dict。"""
    manifest_file = plugin_dir / "manifest.json"
    if not manifest_file.exists():
        raise ValidationError(f"缺少 manifest.json: {plugin_dir.name}")

    try:
        manifest = json.loads(manifest_file.read_text(encoding="utf-8"))
    except json.JSONDecodeError as e:
        raise ValidationError(f"manifest.json 不是合法 JSON: {plugin_dir.name} ({e})")

    name = manifest.get("name", "")
    if not NAME_RE.match(name):
        raise ValidationError(
            f"[{plugin_dir.name}] 插件名不合法: {name!r} "
            "(需为 1-64 位字母/数字/下划线/连字符,以字母开头)"
        )
    if name != plugin_dir.name:
        raise ValidationError(
            f"[{plugin_dir.name}] 目录名与 manifest.name 不一致: {plugin_dir.name} != {name}"
        )

    version = manifest.get("version", "")
    if not VERSION_RE.match(version):
        raise ValidationError(f"[{name}] 版本不合法: {version!r} (需为 semver,如 0.1.0)")

    api_version = manifest.get("api_version", API_VERSION)
    if api_version != API_VERSION:
        raise ValidationError(
            f"[{name}] 不支持的插件 API 契约版本: {api_version!r} (当前支持 {API_VERSION!r})"
        )

    deps = manifest.get("dependencies", [])
    if not isinstance(deps, list):
        raise ValidationError(f"[{name}] dependencies 必须是数组")

    # 许可证：默认 AGPL-3.0（本仓库插件默认开源协议）
    license_name = manifest.get("license") or DEFAULT_LICENSE
    manifest["license"] = license_name

    # 必填字段
    for field in ("description", "usage"):
        if not manifest.get(field):
            raise ValidationError(f"[{name}] 缺少必填字段: {field}")

    return manifest


def scan_imports(source: str) -> list[str]:
    """AST 扫描源码,返回违规的内部模块导入。"""
    import ast

    try:
        tree = ast.parse(source)
    except SyntaxError:
        return []  # 语法错误由 ruff/py_compile 负责,这里不阻塞

    violations = []
    seen = set()
    for node in ast.walk(tree):
        mods = []
        if isinstance(node, ast.Import):
            mods = [alias.name for alias in node.names]
        elif isinstance(node, ast.ImportFrom):
            if node.module:
                mods = [node.module]
        for mod in mods:
            if mod.startswith(FORBIDDEN_PREFIXES) and mod not in seen:
                seen.add(mod)
                violations.append(mod)
    return violations


def validate_plugin_source(plugin_dir: Path) -> list[str]:
    """扫描插件目录下所有 .py,返回契约边界违规列表。"""
    violations = []
    for py_file in sorted(plugin_dir.rglob("*.py")):
        if "__pycache__" in str(py_file):
            continue
        try:
            source = py_file.read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError):
            continue
        for mod in scan_imports(source):
            violations.append(f"{py_file.relative_to(plugin_dir)}: import {mod}")
    return violations


def collect_plugins() -> list[dict]:
    """校验全部插件,返回索引条目列表。"""
    if not PLUGINS_DIR.exists():
        print("未找到 plugins/ 目录")
        sys.exit(1)

    entries = []
    errors = []

    for plugin_dir in sorted(PLUGINS_DIR.iterdir()):
        if not plugin_dir.is_dir() or plugin_dir.name.startswith((".", "_")):
            continue

        try:
            manifest = validate_manifest(plugin_dir)
        except ValidationError as e:
            errors.append(str(e))
            continue

        violations = validate_plugin_source(plugin_dir)
        if violations:
            errors.append(f"[{plugin_dir.name}] 契约边界违规:\n  " + "\n  ".join(violations))
            continue

        # 入口文件存在性
        entry = plugin_dir / ("__init__.py" if (plugin_dir / "__init__.py").exists() else "plugin.py")
        if not entry.exists():
            errors.append(f"[{plugin_dir.name}] 缺少入口文件 (plugin.py 或 __init__.py)")
            continue

        entries.append(
            {
                "name": manifest["name"],
                "description": manifest.get("description", ""),
                "usage": manifest.get("usage", ""),
                "version": manifest["version"],
                "author": manifest.get("author", ""),
                "api_version": manifest.get("api_version", API_VERSION),
                "license": manifest.get("license", DEFAULT_LICENSE),
                "dependencies": manifest.get("dependencies", []),
                "entry": str(entry.relative_to(plugin_dir)),
                "files": {
                    str(p.relative_to(plugin_dir)): hashlib.sha256(p.read_bytes()).hexdigest()
                    for p in plugin_dir.rglob("*")
                    if p.is_file() and "__pycache__" not in str(p) and p.name != "manifest.json"
                },
            }
        )

    if errors:
        print("❌ 校验失败:")
        for e in errors:
            print(f"  - {e}")
        sys.exit(1)

    return entries


def main():
    parser = argparse.ArgumentParser(description="NeoBot 插件校验")
    parser.add_argument("--check-only", action="store_true", help="只校验,不写 index.json")
    args = parser.parse_args()

    entries = collect_plugins()
    if not entries:
        print("⚠️  plugins/ 下没有插件")
        sys.exit(0)

    print(f"✅ 校验通过: {len(entries)} 个插件")
    for e in entries:
        deps = f" (依赖: {', '.join(e['dependencies'])})" if e["dependencies"] else ""
        print(f"  - {e['name']} v{e['version']}{deps}")

    if not args.check_only:
        index = {
            "schema_version": 1,
            "generated_at": None,  # CI 用运行时日期
            "plugins": entries,
        }
        # generated_at 由 CI 替换为实际时间戳,本地不写死
        INDEX_FILE.write_text(json.dumps(index, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        print(f"📄 索引已写入: {INDEX_FILE}")


if __name__ == "__main__":
    main()
