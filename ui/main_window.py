"""主窗口"""

import sys
from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtGui import QFont
from PySide6.QtWidgets import (
    QApplication,
    QHBoxLayout,
    QLabel,
    QMainWindow,
    QStackedWidget,
    QStatusBar,
    QVBoxLayout,
    QWidget,
)

from core.config_manager import ConfigManager
from core.download_engine import DownloadEngine
from core.event_bus import event_bus
from core.plugin_manager import PluginManager
from ui.sidebar import Sidebar


class MainWindow(QMainWindow):
    """工具箱主窗口"""

    def __init__(self, project_root: Path):
        super().__init__()

        self.project_root = project_root
        self.data_dir = project_root / "data"
        self.plugins_dir = project_root / "plugins"

        # 核心组件
        self.config = ConfigManager(self.data_dir)
        self.engine = DownloadEngine()

        # 页面管理
        self._pages: list[QWidget] = []
        self._page_names: list[str] = []

        self._init_ui()
        self._init_plugins()

    def _init_ui(self):
        """初始化 UI 布局"""
        self.setWindowTitle("工具箱")
        self.resize(900, 600)
        self.setMinimumSize(700, 450)

        # 全局字体
        font = QFont("Microsoft YaHei UI", 9)
        QApplication.setFont(font)

        # 中央 widget
        central = QWidget()
        self.setCentralWidget(central)

        main_layout = QHBoxLayout(central)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        # 左侧导航
        self.sidebar = Sidebar()
        main_layout.addWidget(self.sidebar)

        # 右侧内容区
        self._stack = QStackedWidget()
        self._stack.setStyleSheet("background-color: #fafafa;")
        main_layout.addWidget(self._stack)

        self.sidebar.nav_changed.connect(self._on_nav_changed)

        # 状态栏
        self.status_bar = QStatusBar()
        self.setStatusBar(self.status_bar)
        self._status_label = QLabel("Aria2: 未启动")
        self.status_bar.addPermanentWidget(self._status_label)

    def _init_plugins(self):
        """初始化插件系统"""
        self.plugin_manager = PluginManager(
            self.plugins_dir, self, event_bus
        )
        self.plugin_manager.discover()
        self.plugin_manager.register_all()

        # 连接引擎状态到状态栏
        self.engine.aria2_started.connect(
            lambda: self._status_label.setText("Aria2: 运行中")
        )
        self.engine.aria2_stopped.connect(
            lambda: self._status_label.setText("Aria2: 已停止")
        )

        # 启动所有插件
        self.plugin_manager.start_all()

    # ─── 公开接口（供插件调用）──────────────────────────

    def add_nav_item(self, text: str, page: QWidget):
        """添加导航项和对应页面"""
        index = self.sidebar.add_item(text)
        self._stack.addWidget(page)
        self._pages.append(page)
        self._page_names.append(text)

    def _on_nav_changed(self, index: int):
        """导航切换"""
        if 0 <= index < self._stack.count():
            self._stack.setCurrentIndex(index)

    # ─── 生命周期 ────────────────────────────────────────

    def start_aria2(self):
        """启动 Aria2 下载引擎"""
        aria2c_path = str(self.data_dir / "aria2c.exe")
        download_dir = self.config.download_dir

        try:
            self.engine.start(aria2c_path, download_dir)

            # 注入 engine 到下载插件
            for plugin in self.plugin_manager.plugins:
                if plugin.name == "下载管理":
                    plugin.set_engine(self.engine, download_dir)
                    break

        except FileNotFoundError:
            self._status_label.setText("Aria2: aria2c.exe 未找到（请放到 data/ 目录）")
        except Exception as e:
            self._status_label.setText(f"Aria2: 启动失败 ({e})")

    def closeEvent(self, event):
        """窗口关闭时清理"""
        self.plugin_manager.stop_all()
        self.engine.stop()
        event.accept()


def main():
    app = QApplication(sys.argv)

    # 项目根目录
    project_root = Path(__file__).parent.parent
    window = MainWindow(project_root)
    window.show()

    # 自动启动 Aria2
    window.start_aria2()

    sys.exit(app.exec())


if __name__ == "__main__":
    main()
