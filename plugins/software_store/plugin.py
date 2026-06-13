"""软件商店插件"""

import os
from pathlib import Path

from plugins.base_plugin import BasePlugin
from plugins.software_store.repo.software_repo import SoftwareRepo
from plugins.software_store.ui.store_page import StorePage


class SoftwareStorePlugin(BasePlugin):
    name = "软件商店"
    version = "0.1.0"

    def __init__(self):
        self._store_page: StorePage | None = None
        self._repo: SoftwareRepo | None = None
        self._event_bus = None
        self._data_dir: Path | None = None

    def register(self, main_window, event_bus):
        self._event_bus = event_bus

        # 确定 data 目录（在项目根目录下）
        project_root = Path(__file__).parent.parent.parent
        self._data_dir = project_root / "data"

        # 加载软件源
        self._repo = SoftwareRepo(self._data_dir)
        self._repo.load()

        # 创建商店页面
        self._store_page = StorePage()
        self._store_page.set_software(
            self._repo.list_all(),
            self._repo.get_categories(),
        )
        self._store_page.install_requested.connect(self._on_install_request)

        # 注册到主窗口
        main_window.add_nav_item("商店", self._store_page)

        # 监听安装结果
        event_bus.install_result.connect(self._on_install_result)
        event_bus.download_progress.connect(self._on_download_progress)
        event_bus.install_started.connect(self._on_install_started)

        # 列表刷新后重新检查安装状态（分类切换/搜索后状态保持）
        self._store_page.list_refreshed.connect(self._check_all_installed)

        # 启动时检测已安装软件
        self._check_all_installed()

        print(f"[SoftwareStore] 已注册，共 {len(self._repo.list_all())} 款软件")

    def start(self):
        pass

    def stop(self):
        pass

    # ─── 事件处理 ────────────────────────────────────────

    def _on_install_request(self, name: str):
        """用户点击安装按钮"""
        software = self._repo.get_software(name)
        if not software:
            return

        # 获取下载源
        result = self._repo.get_download_url(software)
        if not result:
            print(f"[SoftwareStore] {name} 无可用的下载源")
            return

        url, source_type = result
        install_info = self._repo.get_install_info(software)
        verify = self._repo.get_verify(software)

        # 获取 winget_id（winget 源时使用）
        winget_id = ""
        if source_type == "winget":
            for source in software.get("sources", []):
                if source.get("type") == "winget":
                    winget_id = source.get("id", "")
                    break

        # 发布安装请求
        self._event_bus.install_request.emit({
            "name": name,
            "url": url,
            "source_type": source_type,
            "winget_id": winget_id,
            "install_args": install_info["args"],
            "install_method": install_info["method"],
            "fallback": install_info["fallback"],
            "verify": verify,
        })

    def _on_install_started(self, name: str):
        """安装开始回调"""
        if self._store_page:
            card = self._store_page.get_card_by_name(name)
            if card:
                card.set_installing()

    def _on_install_result(self, data: dict):
        """安装结果回调"""
        name = data.get("name", "")
        success = data.get("success", False)
        if name and self._store_page:
            card = self._store_page.get_card_by_name(name)
            if card:
                if success:
                    card.set_installed(True)
                else:
                    card.set_installed(False)

    def _on_download_progress(self, name: str, percent: int, speed: str):
        """下载进度回调"""
        if self._store_page:
            card = self._store_page.get_card_by_name(name)
            if card:
                card.set_downloading(percent)

    def _check_all_installed(self):
        """启动时检查所有软件是否已安装"""
        from plugins.install_task.silent_installer import SilentInstaller

        for sw in self._repo.list_all():
            verify = sw.get("verify")
            if verify and SilentInstaller.check_installed(verify):
                name = sw.get("name", "")
                if name and self._store_page:
                    card = self._store_page.get_card_by_name(name)
                    if card:
                        card.set_installed(True)
