#!/usr/bin/env python3
"""
CI 插件测试脚本：有 tests/ 跑 pytest,否则做导入检查。

环境要求（由 workflow 设置）：
- PYTHONPATH 包含 $PWD、$PWD/plugins、$PWD/_neobot/src
- neobot 依赖已安装
"""
import pathlib
import subprocess
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
PLUGINS = ROOT / "plugins"


def run_pytest() -> int:
    """插件自带 tests/ 时跑 pytest。"""
    result = subprocess.run(
        [sys.executable, "-m", "pytest", str(PLUGINS), "-v", "--tb=short"],
        cwd=ROOT,
    )
    return result.returncode


def import_check() -> int:
    """无测试时做最小导入检查：每个插件入口能 import 即契约可解析。"""
    import importlib

    failed = 0
    for plugin_dir in sorted(PLUGINS.iterdir()):
        if not plugin_dir.is_dir() or plugin_dir.name.startswith((".", "_")):
            continue
        entry_name = None
        if (plugin_dir / "__init__.py").exists():
            entry_name = "__init__"
        elif (plugin_dir / "plugin.py").exists():
            entry_name = "plugin"

        if entry_name is None:
            print(f"  ⚠️  {plugin_dir.name}: 无入口 (plugin.py / __init__.py)")
            continue

        try:
            importlib.import_module(f"{plugin_dir.name}.{entry_name}")
            print(f"  ✓ {plugin_dir.name} imports OK")
        except Exception as e:
            failed += 1
            print(f"  ✗ {plugin_dir.name}: {type(e).__name__}: {e}")

    if failed:
        print(f"\n❌ {failed} 个插件导入失败")
        return 1
    print("\n✅ 全部插件导入成功")
    return 0


def main() -> int:
    has_tests = any(p.is_dir() and p.name == "tests" for p in PLUGINS.iterdir())
    if has_tests:
        print("检测到插件测试目录,运行 pytest...")
        return run_pytest()
    print("无插件测试,执行导入检查...")
    return import_check()


if __name__ == "__main__":
    sys.exit(main())
