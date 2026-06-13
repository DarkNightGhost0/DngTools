"""主页 UI"""

import platform
import os
from PySide6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout,
                                QLabel, QPushButton, QFrame, QMessageBox)
from PySide6.QtGui import QPixmap
from PySide6.QtCore import Qt, Signal, QThread


class InitWorker(QThread):
    """后台执行初始化流程"""
    finished = Signal(str)  # 结果消息

    def __init__(self, flow_path: str):
        super().__init__()
        self.flow_path = flow_path

    def run(self):
        try:
            import importlib.util
            spec = importlib.util.spec_from_file_location("init_flow", self.flow_path)
            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)
            result = module.run()
            self.finished.emit(result)
        except Exception as e:
            self.finished.emit(f"初始化失败: {e}")


class HomePage(QWidget):
    """主页"""

    init_requested = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self._worker: InitWorker | None = None
        self._init_btn: QPushButton | None = None

        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(20)

        # ── 顶部图片 ──
        banner = QLabel()
        banner.setAlignment(Qt.AlignCenter)
        banner.setFixedHeight(200)
        banner.setStyleSheet("background: #2b2b2b; border-radius: 8px;")
        pixmap = QPixmap()
        # 尝试加载占位图
        img_path = os.path.join(os.path.dirname(__file__), "..", "..", "..", "data", "banner.png")
        if os.path.exists(img_path):
            pixmap.load(img_path)
        if pixmap.isNull():
            # 没有图片则显示占位文字
            banner.setText("工具箱")
            banner.setStyleSheet(
                "background: #2b2b2b; border-radius: 8px; color: #888; "
                "font-size: 32px; font-weight: bold;"
            )
        else:
            banner.setPixmap(pixmap.scaledToWidth(800, Qt.SmoothTransformation))
        layout.addWidget(banner)

        # ── 下方左右布局 ──
        row = QHBoxLayout()
        row.setSpacing(20)
        layout.addLayout(row)

        # 左侧：系统信息
        info_card = self._build_info_card()
        row.addWidget(info_card, stretch=2)

        # 右侧：初始化按钮
        action_card = self._build_action_card()
        row.addWidget(action_card, stretch=1)

    def _build_info_card(self) -> QFrame:
        card = QFrame()
        card.setStyleSheet(
            "QFrame { background: #2b2b2b; border-radius: 8px; padding: 20px; }"
        )
        layout = QVBoxLayout(card)
        layout.setSpacing(12)

        title = QLabel("系统信息")
        title.setStyleSheet("font-size: 18px; font-weight: bold; color: #fff;")
        layout.addWidget(title)

        info = [
            ("CPU", self._get_cpu()),
            ("内存", self._get_memory()),
            ("系统", f"{self._get_os_name()} {platform.release()}"),
            ("架构", platform.machine()),
            ("计算机名", platform.node()),
        ]

        for label, value in info:
            row = QHBoxLayout()
            row.setSpacing(8)
            key_lbl = QLabel(label)
            key_lbl.setStyleSheet("color: #888; font-size: 13px; min-width: 60px;")
            val_lbl = QLabel(value)
            val_lbl.setStyleSheet("color: #ddd; font-size: 13px;")
            val_lbl.setWordWrap(True)
            row.addWidget(key_lbl)
            row.addWidget(val_lbl, 1)
            layout.addLayout(row)

        layout.addStretch()
        return card

    def _build_action_card(self) -> QFrame:
        card = QFrame()
        card.setStyleSheet(
            "QFrame { background: #2b2b2b; border-radius: 8px; padding: 20px; }"
        )
        layout = QVBoxLayout(card)
        layout.setAlignment(Qt.AlignCenter)

        self._init_btn = QPushButton("初始化")
        self._init_btn.setFixedSize(160, 48)
        self._init_btn.setStyleSheet(
            "QPushButton {"
            "  background: #0078d4; color: #fff; border: none; border-radius: 6px;"
            "  font-size: 16px; font-weight: bold;"
            "}"
            "QPushButton:hover { background: #1a8fe3; }"
            "QPushButton:pressed { background: #005a9e; }"
            "QPushButton:disabled { background: #555; color: #999; }"
        )
        self._init_btn.clicked.connect(self._on_init_clicked)
        layout.addWidget(self._init_btn)

        return card

    def _on_init_clicked(self):
        self._init_btn.setEnabled(False)
        self._init_btn.setText("执行中...")

        flow_path = os.path.join(
            os.path.dirname(__file__), "..", "..", "..", "data", "init_flow.py"
        )
        self._worker = InitWorker(flow_path)
        self._worker.finished.connect(self._on_init_finished)
        self._worker.start()

    def _on_init_finished(self, result: str):
        self._init_btn.setEnabled(True)
        self._init_btn.setText("初始化")
        QMessageBox.information(self, "初始化结果", result)

    @staticmethod
    def _get_cpu() -> str:
        cpu = platform.processor()
        if not cpu:
            cpu = os.environ.get("PROCESSOR_IDENTIFIER", "未知")
        return cpu.strip()

    @staticmethod
    def _get_memory() -> str:
        try:
            import ctypes
            kernel32 = ctypes.windll.kernel32
            mem_total = ctypes.c_ulonglong()
            ctypes.windll.kernel32.GetPhysicallyInstalledSystemMemory(ctypes.byref(mem_total))
            gb = mem_total.value / (1024 * 1024)
            return f"{gb:.1f} GB"
        except Exception:
            return "未知"

    @staticmethod
    def _get_os_name() -> str:
        ver = platform.version()
        if "10.0.26" in ver:
            return "Windows 11"
        elif "10.0.22" in ver or "10.0.21" in ver:
            return "Windows 11"
        return "Windows"
