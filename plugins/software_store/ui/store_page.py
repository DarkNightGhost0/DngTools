"""软件商店页面 UI"""

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QFont
from PySide6.QtWidgets import (
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QPushButton,
    QVBoxLayout,
    QWidget,
)


class SoftwareCard(QWidget):
    """单个软件卡片"""

    install_clicked = Signal(str)  # name

    def __init__(self, name: str, category: str, installed: bool = False, parent=None):
        super().__init__(parent)
        self.name = name
        self._installed = installed

        layout = QHBoxLayout(self)
        layout.setContentsMargins(8, 4, 8, 4)

        name_label = QLabel(name)
        name_label.setFont(QFont("Microsoft YaHei UI", 10))

        cat_label = QLabel(category)
        cat_label.setStyleSheet("color: #888;")

        self._btn = QPushButton()
        self._update_button()
        self._btn.clicked.connect(lambda: self.install_clicked.emit(self.name))

        layout.addWidget(name_label)
        layout.addWidget(cat_label)
        layout.addStretch()
        layout.addWidget(self._btn)

    def _update_button(self):
        if self._installed:
            self._btn.setText("已安装")
            self._btn.setEnabled(False)
        else:
            self._btn.setText("安装")
            self._btn.setEnabled(True)

    def set_installed(self, installed: bool):
        self._installed = installed
        self._update_button()

    def set_downloading(self, percent: int = 0):
        self._btn.setText(f"下载中 {percent}%")
        self._btn.setEnabled(False)

    def set_installing(self):
        self._btn.setText("安装中...")
        self._btn.setEnabled(False)


class StorePage(QWidget):
    """软件商店页面 - 分类标签 + 搜索 + 软件列表"""

    install_requested = Signal(str)  # name
    list_refreshed = Signal()  # 列表刷新后发出，供外部重新检查安装状态

    def __init__(self, parent=None):
        super().__init__(parent)
        self._all_software: list[dict] = []
        self._categories: list[str] = []
        self._current_category = ""

        self._init_ui()

    def _init_ui(self):
        layout = QVBoxLayout(self)

        # 搜索框
        search_layout = QHBoxLayout()
        self._search_input = QLineEdit()
        self._search_input.setPlaceholderText("搜索软件...")
        self._search_input.textChanged.connect(self._on_search)
        search_layout.addWidget(self._search_input)
        layout.addLayout(search_layout)

        # 分类标签行
        self._category_layout = QHBoxLayout()
        self._category_buttons: list[QPushButton] = []
        layout.addLayout(self._category_layout)

        # 软件列表
        self._list_widget = QListWidget()
        self._list_widget.setSpacing(2)
        layout.addWidget(self._list_widget)

    def set_software(self, software_list: list[dict], categories: list[str]):
        """设置软件数据"""
        self._all_software = software_list
        self._categories = categories
        self._build_category_buttons()
        self._refresh_list()

    def _build_category_buttons(self):
        """构建分类按钮"""
        # 清除旧按钮
        for btn in self._category_buttons:
            self._category_layout.removeWidget(btn)
            btn.deleteLater()
        self._category_buttons.clear()

        # "全部" 按钮
        all_btn = QPushButton("全部")
        all_btn.setCheckable(True)
        all_btn.setChecked(True)
        all_btn.clicked.connect(lambda: self._on_category(""))
        self._category_layout.addWidget(all_btn)
        self._category_buttons.append(all_btn)

        for cat in self._categories:
            btn = QPushButton(cat)
            btn.setCheckable(True)
            btn.clicked.connect(lambda checked, c=cat: self._on_category(c))
            self._category_layout.addWidget(btn)
            self._category_buttons.append(btn)

        self._category_layout.addStretch()

    def _on_category(self, category: str):
        self._current_category = category
        # 更新按钮选中状态
        for btn in self._category_buttons:
            btn.setChecked(btn.text() == category or (btn.text() == "全部" and not category))
        self._refresh_list()

    def _on_search(self, text: str):
        self._refresh_list()

    def _refresh_list(self):
        """刷新软件列表"""
        self._list_widget.clear()
        search_text = self._search_input.text().lower().strip()

        for sw in self._all_software:
            name = sw.get("name", "")
            category = sw.get("category", "")

            # 分类过滤
            if self._current_category and category != self._current_category:
                continue

            # 搜索过滤
            if search_text and search_text not in name.lower():
                continue

            card = SoftwareCard(name, category)
            card.install_clicked.connect(self.install_requested.emit)

            item = QListWidgetItem()
            item.setSizeHint(card.sizeHint())
            self._list_widget.addItem(item)
            self._list_widget.setItemWidget(item, card)

            # 存储引用防止被 GC
            item.setData(Qt.UserRole, card)

        self.list_refreshed.emit()

    def get_card_by_name(self, name: str) -> SoftwareCard | None:
        """按名称获取卡片（用于更新状态）"""
        for i in range(self._list_widget.count()):
            item = self._list_widget.item(i)
            card = item.data(Qt.UserRole)
            if card and card.name == name:
                return card
        return None
