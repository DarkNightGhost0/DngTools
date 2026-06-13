"""安装任务插件"""

from plugins.base_plugin import BasePlugin
from plugins.install_task.silent_installer import SilentInstaller


class InstallTaskPlugin(BasePlugin):
    name = "安装管理"
    version = "0.1.0"

    def __init__(self):
        self._installer: SilentInstaller | None = None
        self._event_bus = None
        self._attempts: dict[str, int] = {}  # name -> 点击次数

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

        # winget 源：直接用 winget 命令安装
        if data.get("source_type") == "winget":
            self._install_winget(data)
            return

        file_path = data.get("file_path", "")

        if not file_path:
            self._event_bus.install_result.emit({
                "name": name,
                "success": False,
                "message": "文件路径为空",
            })
            return

        self._event_bus.install_started.emit(name)

        # 第一次点击 → 静默安装；第二次起 → 手动安装
        self._attempts[name] = self._attempts.get(name, 0) + 1
        attempt = self._attempts[name]
        method = data.get("install_method", "silent") if attempt == 1 else "manual"

        self._installer.install(
            name=name,
            file_path=file_path,
            args=data.get("install_args", ""),
            method=method,
            fallback=data.get("fallback", "manual"),
            verify=data.get("verify"),
        )

    def _install_winget(self, data: dict):
        """使用 winget 命令安装"""
        name = data.get("name", "")
        winget_id = data.get("winget_id", "")

        if not winget_id:
            self._event_bus.install_result.emit({
                "name": name,
                "success": False,
                "message": "winget ID 为空",
            })
            return

        self._event_bus.install_started.emit(name)

        result = SilentInstaller.install_winget(winget_id)

        # 安装后验证
        verify = data.get("verify")
        if result["success"] and verify:
            if not SilentInstaller.check_installed(verify):
                result = {"success": False, "message": "winget 报告成功但验证未通过"}

        result["name"] = name
        self._event_bus.install_result.emit(result)

    def _on_install_result(self, data: dict):
        """安装结果转发到全局事件总线，成功后重置计数器"""
        name = data.get("name", "")
        if data.get("success"):
            self._attempts.pop(name, None)
        self._event_bus.install_result.emit(data)
