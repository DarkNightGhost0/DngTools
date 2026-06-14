"""VTuber Tools 插件"""

from pathlib import Path

from plugins.base_plugin import BasePlugin
from plugins.software_store.repo.software_repo import SoftwareRepo
from plugins.vtuber_tools.download_config import DownloadConfig
from plugins.vtuber_tools.ui.vtuber_tools_page import VtuberToolsPage


class VtuberToolsPlugin(BasePlugin):
    name = "VTuber Tools"
    version = "0.1.0"

    def __init__(self):
        self._page: VtuberToolsPage | None = None
        self._repo: SoftwareRepo | None = None
        self._download_config: DownloadConfig | None = None
        self._event_bus = None

    def register(self, main_window, event_bus):
        self._event_bus = event_bus

        project_root = Path(__file__).parent.parent.parent
        data_dir = project_root / "data"

        self._repo = SoftwareRepo(data_dir)
        self._repo.load()

        config_path = Path(__file__).parent / "downloads.json"
        self._download_config = DownloadConfig(config_path)

        self._page = VtuberToolsPage(
            self._repo, self._event_bus,
            download_config=self._download_config,
        )
        main_window.add_nav_item("VTuber Tools", self._page)

        # 监听安装结果和进度，同步到卡片
        event_bus.install_result.connect(self._on_install_result)
        event_bus.download_progress.connect(self._on_download_progress)
        event_bus.install_started.connect(self._on_install_started)

        print("[VtuberTools] 已注册")

    def start(self):
        pass

    def stop(self):
        pass

    # ── 事件回调 ──────────────────────────────────────

    def _on_install_result(self, data: dict):
        name = data.get("name", "")
        success = data.get("success", False)
        if name and self._page:
            card = self._page.get_card(name)
            if card:
                card.set_installed(success)

    def _on_download_progress(self, name: str, percent: int, speed: str):
        if self._page:
            card = self._page.get_card(name)
            if card:
                card.set_downloading(percent)

    def _on_install_started(self, name: str):
        if self._page:
            card = self._page.get_card(name)
            if card:
                card.set_installing()
