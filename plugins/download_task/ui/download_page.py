"""下载任务管理页面 UI"""

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QFont
from PySide6.QtWidgets import (
    QHBoxLayout,
    QLabel,
    QListWidget,
    QListWidgetItem,
    QProgressBar,
    QPushButton,
    QVBoxLayout,
    QWidget,
)


class DownloadItem(QWidget):
    """单个下载任务卡片"""

    pause_clicked = Signal(str)  # gid
    cancel_clicked = Signal(str)  # gid

    def __init__(self, gid: str, name: str, parent=None):
        super().__init__(parent)
        self.gid = gid
        self.name = name

        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 4, 8, 4)

        # 第一行：名称 + 按钮
        row1 = QHBoxLayout()
        name_label = QLabel(name)
        name_label.setFont(QFont("Microsoft YaHei UI", 10))
        row1.addWidget(name_label)
        row1.addStretch()

        self._pause_btn = QPushButton("暂停")
        self._pause_btn.clicked.connect(lambda: self.pause_clicked.emit(self.gid))

        self._cancel_btn = QPushButton("取消")
        self._cancel_btn.clicked.connect(lambda: self.cancel_clicked.emit(self.gid))

        row1.addWidget(self._pause_btn)
        row1.addWidget(self._cancel_btn)
        layout.addLayout(row1)

        # 进度条
        self._progress = QProgressBar()
        self._progress.setRange(0, 100)
        layout.addWidget(self._progress)

        # 速度标签
        self._speed_label = QLabel("等待中...")
        self._speed_label.setStyleSheet("color: #888;")
        layout.addWidget(self._speed_label)

    def update_progress(self, percent: int, speed: str):
        self._progress.setValue(percent)
        self._speed_label.setText(f"{speed}  •  {percent}%")

    def set_paused(self, paused: bool):
        self._pause_btn.setText("继续" if paused else "暂停")


class DownloadPage(QWidget):
    """下载任务列表页面"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self._gid_to_item: dict[str, QListWidgetItem] = {}

        layout = QVBoxLayout(self)

        # 标题
        title = QLabel("下载任务")
        title.setFont(QFont("Microsoft YaHei UI", 14))
        layout.addWidget(title)

        self._list_widget = QListWidget()
        self._list_widget.setSpacing(4)
        layout.addWidget(self._list_widget)

        # 空状态提示
        self._empty_label = QLabel("暂无下载任务")
        self._empty_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._empty_label.setStyleSheet("color: #aaa; font-size: 14px;")
        layout.addWidget(self._empty_label)

    def add_download(self, gid: str, name: str) -> DownloadItem:
        """添加下载任务到列表"""
        self._empty_label.hide()

        widget = DownloadItem(gid, name)
        item = QListWidgetItem()
        item.setSizeHint(widget.sizeHint())
        self._list_widget.addItem(item)
        self._list_widget.setItemWidget(item, widget)

        item.setData(Qt.UserRole, widget)
        self._gid_to_item[gid] = item
        return widget

    def remove_download(self, gid: str):
        """从列表移除下载任务"""
        item = self._gid_to_item.pop(gid, None)
        if item:
            row = self._list_widget.row(item)
            self._list_widget.takeItem(row)

        if not self._gid_to_item:
            self._empty_label.show()

    def get_download_item(self, gid: str) -> DownloadItem | None:
        """获取下载控件"""
        item = self._gid_to_item.get(gid)
        if item:
            return item.data(Qt.UserRole)
        return None
