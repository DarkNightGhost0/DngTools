"""工具箱入口"""

import sys
from pathlib import Path

from ui.main_window import MainWindow, QApplication


def main():
    app = QApplication(sys.argv)
    project_root = Path(__file__).parent
    window = MainWindow(project_root)
    window.show()
    window.start_aria2()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
