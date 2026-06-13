"""主页插件"""

from plugins.base_plugin import BasePlugin
from plugins.home_page.ui.home_page import HomePage


class HomePagePlugin(BasePlugin):
    name = "主页"
    version = "0.1.0"

    def __init__(self):
        self._home_page: HomePage | None = None

    def register(self, main_window, event_bus):
        self._home_page = HomePage()
        main_window.add_nav_item("主页", self._home_page)
        print("[HomePage] 已注册")

    def start(self):
        pass

    def stop(self):
        pass
