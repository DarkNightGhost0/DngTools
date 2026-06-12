"""安装任务插件"""

from plugins.base_plugin import BasePlugin
from plugins.install_task.silent_installer import SilentInstaller


class InstallTaskPlugin(BasePlugin):
    name = "安装管理"
    version = "0.1.0"

    def __init__(self):
        self._installer: SilentInstaller | None = None
        self._event_bus = None

    def register(self, main_window, event_bus):
        self._event_bus = event_bus
        self._installer = SilentInstaller()

        # 监听下载完成事件
        event_bus.download_complete.connect(self._on_download_complete)

        # 安装结果转发到事件总线
        self._installer.install_result.connect(self._on_install_result)

        print("[InstallTask] 已注册")

    def start(self):
        pass

    def stop(self):
        pass

    # ─── 事件处理 ────────────────────────────────────────

    def _on_download_complete(self, data: dict):
        """下载完成，开始安装"""
        name = data.get("name", "")
        file_path = data.get("file_path", "")

        if not file_path:
            self._event_bus.install_result.emit({
                "name": name,
                "success": False,
                "message": "文件路径为空",
            })
            return

        self._event_bus.install_started.emit(name)

        self._installer.install(
            name=name,
            file_path=file_path,
            args=data.get("install_args", ""),
            method=data.get("install_method", "silent"),
            fallback=data.get("fallback", "manual"),
            verify=data.get("verify"),
        )

    def _on_install_result(self, data: dict):
        """安装结果转发到全局事件总线"""
        self._event_bus.install_result.emit(data)
