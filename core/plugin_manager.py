"""插件管理器 - 发现、加载、管理插件生命周期"""

import importlib
import sys
from pathlib import Path

from plugins.base_plugin import BasePlugin


class PluginManager:
    """扫描 plugins/ 目录，加载并管理所有插件"""

    def __init__(self, plugins_dir: Path, main_window, event_bus):
        self.plugins_dir = plugins_dir
        self.main_window = main_window
        self.event_bus = event_bus
        self.plugins: list[BasePlugin] = []

    def discover(self):
        """扫描 plugins/ 下每个子目录，加载 plugin 模块"""
        if not self.plugins_dir.exists():
            return

        # 确保 plugins 包路径在 sys.path 中
        parent = str(self.plugins_dir.parent)
        if parent not in sys.path:
            sys.path.insert(0, parent)

        for entry in sorted(self.plugins_dir.iterdir()):
            if not entry.is_dir():
                continue
            if entry.name.startswith("_") or entry.name.startswith("."):
                continue

            plugin_file = entry / "plugin.py"
            if not plugin_file.exists():
                continue

            try:
                module_name = f"plugins.{entry.name}.plugin"
                module = importlib.import_module(module_name)
                # 查找继承 BasePlugin 的类
                for attr_name in dir(module):
                    attr = getattr(module, attr_name)
                    if (
                        isinstance(attr, type)
                        and issubclass(attr, BasePlugin)
                        and attr is not BasePlugin
                    ):
                        plugin_instance = attr()
                        self.plugins.append(plugin_instance)
                        print(f"[PluginManager] 发现插件: {plugin_instance.name}")
                        break
            except Exception as e:
                print(f"[PluginManager] 加载插件 {entry.name} 失败: {e}")

    def register_all(self):
        """调用所有插件的 register()"""
        for plugin in self.plugins:
            try:
                plugin.register(self.main_window, self.event_bus)
                print(f"[PluginManager] 注册插件: {plugin.name}")
            except Exception as e:
                print(f"[PluginManager] 注册插件 {plugin.name} 失败: {e}")

    def start_all(self):
        """调用所有插件的 start()"""
        for plugin in self.plugins:
            try:
                plugin.start()
                print(f"[PluginManager] 启动插件: {plugin.name}")
            except Exception as e:
                print(f"[PluginManager] 启动插件 {plugin.name} 失败: {e}")

    def stop_all(self):
        """调用所有插件的 stop()"""
        for plugin in self.plugins:
            try:
                plugin.stop()
                print(f"[PluginManager] 停止插件: {plugin.name}")
            except Exception as e:
                print(f"[PluginManager] 停止插件 {plugin.name} 失败: {e}")
