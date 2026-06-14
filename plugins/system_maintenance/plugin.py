"""系统维护插件"""

from plugins.base_plugin import BasePlugin
from plugins.system_maintenance.ui.maintenance_page import MaintenancePage


class SystemMaintenancePlugin(BasePlugin):
    name = "系统维护"
    version = "0.1.0"

    def __init__(self):
        self._page: MaintenancePage | None = None

    def register(self, main_window, event_bus):
        self._page = MaintenancePage()
        main_window.add_nav_item("系统维护", self._page)
        print("[SystemMaintenance] 已注册")

    def start(self):
        pass

    def stop(self):
        pass
