"""工具箱入口"""

import ctypes
import sys
from pathlib import Path

from ui.main_window import MainWindow, QApplication


def is_admin() -> bool:
    try:
        return bool(ctypes.windll.shell32.IsUserAnAdmin())
    except Exception:
        return False


def elevate():
    """重新以管理员权限启动自身"""
    ctypes.windll.shell32.ShellExecuteW(
        None, "runas", sys.executable, " ".join(sys.argv), None, 1
    )


def main():
    if not is_admin():
        elevate()
        sys.exit()

    app = QApplication(sys.argv)
    project_root = Path(__file__).parent
    window = MainWindow(project_root)
    window.show()
    window.start_aria2()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
