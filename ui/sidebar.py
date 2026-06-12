"""左侧导航栏"""

from PySide6.QtCore import Signal
from PySide6.QtGui import QFont
from PySide6.QtWidgets import (
    QPushButton,
    QVBoxLayout,
    QWidget,
)


class Sidebar(QWidget):
    """左侧导航栏，按钮列表"""

    nav_changed = Signal(int)  # index

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedWidth(120)
        self.setStyleSheet("""
            Sidebar {
                background-color: #f0f0f0;
                border-right: 1px solid #ddd;
            }
            QPushButton {
                text-align: left;
                padding: 10px 12px;
                border: none;
                border-radius: 4px;
                margin: 2px 6px;
                font-size: 13px;
            }
            QPushButton:hover {
                background-color: #e0e0e0;
            }
            QPushButton:checked {
                background-color: #d0d0d0;
                font-weight: bold;
            }
        """)

        self._layout = QVBoxLayout(self)
        self._layout.setContentsMargins(0, 8, 0, 8)
        self._layout.setSpacing(0)

        self._buttons: list[QPushButton] = []
        self._button_group: list[QPushButton] = []

    def add_item(self, text: str) -> int:
        """添加导航项，返回索引"""
        btn = QPushButton(text)
        btn.setCheckable(True)
        btn.setFont(QFont("Microsoft YaHei UI", 9))

        index = len(self._buttons)
        btn.clicked.connect(lambda: self._on_click(index))

        self._layout.addWidget(btn)
        self._buttons.append(btn)
        self._button_group.append(btn)

        # 第一个自动选中
        if len(self._buttons) == 1:
            btn.setChecked(True)

        return index

    def _on_click(self, index: int):
        for i, btn in enumerate(self._buttons):
            btn.setChecked(i == index)
        self.nav_changed.emit(index)

    def select(self, index: int):
        """程序化选中导航项"""
        if 0 <= index < len(self._buttons):
            self._on_click(index)
