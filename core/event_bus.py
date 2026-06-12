"""事件总线 - 插件间松耦合通信"""

from PySide6.QtCore import QObject, Signal


class EventBus(QObject):
    """
    全局事件总线，插件间通过信号/槽通信。

    事件定义方式：
        event_bus.install_request.emit(data)
        event_bus.install_request.connect(callback)
    """

    # 软件商店 → 下载插件
    install_request = Signal(dict)

    # 下载完成 → 安装插件
    download_complete = Signal(dict)

    # 安装结果 → 软件商店
    install_result = Signal(dict)

    # 下载进度 → UI 更新
    download_progress = Signal(str, int, str)  # name, percent, speed

    # 安装开始 → UI 更新
    install_started = Signal(str)  # name

    def __init__(self, parent=None):
        super().__init__(parent)


# 全局单例
event_bus = EventBus()
