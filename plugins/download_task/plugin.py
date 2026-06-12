"""下载任务管理插件"""

from pathlib import Path

from plugins.base_plugin import BasePlugin
from plugins.download_task.ui.download_page import DownloadPage


class DownloadTaskPlugin(BasePlugin):
    name = "下载管理"
    version = "0.1.0"

    def __init__(self):
        self._download_page: DownloadPage | None = None
        self._engine = None
        self._event_bus = None
        self._download_dir = ""
        self._pending_installs: dict[str, dict] = {}  # gid -> install_info

    def register(self, main_window, event_bus):
        self._event_bus = event_bus

        # 创建下载页面
        self._download_page = DownloadPage()
        main_window.add_nav_item("下载", self._download_page)

        # 监听安装请求（来自软件商店）
        event_bus.install_request.connect(self._on_install_request)

        print("[DownloadTask] 已注册")

    def start(self):
        pass

    def stop(self):
        pass

    def set_engine(self, engine, download_dir: str):
        """设置下载引擎实例（由 main_window 注入）"""
        self._engine = engine
        self._download_dir = download_dir

        # 连接引擎信号
        engine.download_progress.connect(self._on_progress)
        engine.download_finished.connect(self._on_finished)

    # ─── 事件处理 ────────────────────────────────────────

    def _on_install_request(self, data: dict):
        """接收到安装请求，开始下载"""
        if not self._engine:
            return

        name = data.get("name", "")
        url = data.get("url", "")

        try:
            gid = self._engine.add_download(url, name, self._download_dir)

            # 存储安装信息，供下载完成时使用
            self._pending_installs[gid] = {
                "name": name,
                "install_args": data.get("install_args", ""),
                "install_method": data.get("install_method", "silent"),
                "fallback": data.get("fallback", "manual"),
            }

            # 添加到 UI 列表
            if self._download_page:
                widget = self._download_page.add_download(gid, name)

            print(f"[DownloadTask] 开始下载: {name} (gid={gid})")

        except Exception as e:
            print(f"[DownloadTask] 添加下载失败 ({name}): {e}")
            self._event_bus.install_result.emit({
                "name": name,
                "success": False,
                "message": f"下载启动失败: {e}",
            })

    def _on_progress(self, gid: str, name: str, percent: int, speed: str):
        """下载进度回调"""
        if self._download_page:
            widget = self._download_page.get_download_item(gid)
            if widget:
                widget.update_progress(percent, speed)
        # 转发到事件总线，供商店卡片等订阅
        self._event_bus.download_progress.emit(name, percent, speed)

    def _on_finished(self, gid: str, file_path: str):
        """下载完成回调"""
        print(f"[DownloadTask] 下载完成: gid={gid}, path={file_path}")

        if self._download_page:
            self._download_page.remove_download(gid)

        # 取出安装信息
        install_info = self._pending_installs.pop(gid, {})

        # 通知安装插件
        self._event_bus.download_complete.emit({
            "gid": gid,
            "file_path": file_path,
            "name": install_info.get("name", ""),
            "install_args": install_info.get("install_args", ""),
            "install_method": install_info.get("install_method", "silent"),
            "fallback": install_info.get("fallback", "manual"),
        })
