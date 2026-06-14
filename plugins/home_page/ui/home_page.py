"""主页 UI"""

import os
import subprocess
from PySide6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout,
                                QLabel, QPushButton, QFrame, QTextEdit,
                                QLineEdit, QMessageBox)
from PySide6.QtGui import QPixmap, QFont
from PySide6.QtCore import Qt, Signal, QThread, QTimer


# ── 终端查询命令 ──────────────────────────────────────

SYSTEM_COMMANDS = [
    ("主机名", ["hostname"]),
    ("操作系统", [
        "powershell", "-Command",
        "Get-CimInstance Win32_OperatingSystem | "
        "ForEach-Object { $_.Caption + ' ' + $_.Version + ' ' + $_.OSArchitecture }",
    ]),
    ("CPU", [
        "powershell", "-Command",
        "(Get-CimInstance Win32_Processor).Name.Trim()",
    ]),
    ("内存 (GB)", [
        "powershell", "-Command",
        "[math]::Round((Get-CimInstance Win32_ComputerSystem).TotalPhysicalMemory/1GB,1)",
    ]),
    ("GPU", [
        "powershell", "-Command",
        '(Get-CimInstance Win32_VideoController | Where-Object {$_.Name -notlike "*Remote*"}).Name.Trim()',
    ]),
    ("磁盘", [
        "powershell", "-Command",
        'Get-PSDrive -PSProvider FileSystem | Where-Object {$_.Used -gt 0} | '
        'ForEach-Object {"{0}: {1}GB / {2}GB" -f $_.Name, '
        '[math]::Round($_.Used/1GB,1), [math]::Round(($_.Used+$_.Free)/1GB,1)}',
    ]),
]


# ── Workers ───────────────────────────────────────────

class InitWorker(QThread):
    finished = Signal(str)

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


class TerminalWorker(QThread):
    """收集全部命令输出，一次性返回"""
    result = Signal(str)

    def __init__(self, commands: list[tuple[str, list[str]]]):
        super().__init__()
        self.commands = commands

    def run(self):
        lines = []
        for name, cmd_parts in self.commands:
            lines.append(f"\nPS> {name}")
            try:
                r = subprocess.run(
                    cmd_parts, capture_output=True, text=True,
                    timeout=15, creationflags=subprocess.CREATE_NO_WINDOW
                )
                out = (r.stdout or r.stderr or "").strip()
                lines.append(out if out else "(无输出)")
            except subprocess.TimeoutExpired:
                lines.append("(超时)")
            except Exception as e:
                lines.append(f"(错误: {e})")
        self.result.emit("\n".join(lines))


class SingleCommandWorker(QThread):
    """执行单条用户输入命令"""
    result = Signal(str, str)  # (cmd, output)

    def __init__(self, command: str):
        super().__init__()
        self.command = command

    def run(self):
        try:
            r = subprocess.run(
                self.command, shell=True, capture_output=True, text=True,
                timeout=30, creationflags=subprocess.CREATE_NO_WINDOW
            )
            out = (r.stdout or r.stderr or "").strip()
            self.result.emit(self.command, out if out else "(无输出)")
        except subprocess.TimeoutExpired:
            self.result.emit(self.command, "(超时)")
        except Exception as e:
            self.result.emit(self.command, f"(错误: {e})")


# ── 主页 ──────────────────────────────────────────────

class HomePage(QWidget):

    def __init__(self, parent=None):
        super().__init__(parent)
        self._init_btn: QPushButton | None = None
        self._init_worker: InitWorker | None = None
        self._term_worker: TerminalWorker | None = None
        self._cmd_worker: SingleCommandWorker | None = None
        self._terminal: QTextEdit | None = None
        self._cmd_input: QLineEdit | None = None
        self._term_running = False

        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(20)

        # ── 顶部图片 ──
        banner = QLabel()
        banner.setAlignment(Qt.AlignCenter)
        banner.setFixedHeight(180)
        banner.setStyleSheet("background: #252526; border-radius: 10px; margin-bottom: 6px;")
        pixmap = QPixmap()
        img_path = os.path.join(os.path.dirname(__file__), "..", "..", "..", "data", "banner.png")
        if os.path.exists(img_path):
            pixmap.load(img_path)
        if pixmap.isNull():
            banner.setText("工具箱")
            banner.setStyleSheet(
                "background: #252526; border-radius: 10px; margin-bottom: 6px;"
                "color: #888; font-size: 32px; font-weight: bold;"
            )
        else:
            banner.setPixmap(pixmap.scaledToWidth(800, Qt.SmoothTransformation))
        layout.addWidget(banner)

        # ── 下方左右布局 ──
        row = QHBoxLayout()
        row.setSpacing(20)
        layout.addLayout(row)

        # 左侧：终端
        terminal_card = self._build_terminal()
        row.addWidget(terminal_card, stretch=2)

        # 右侧：初始化按钮
        action_card = self._build_action_card()
        row.addWidget(action_card, stretch=1)

        QTimer.singleShot(400, self._run_system_commands)

    # ── 终端 ──────────────────────────────────────────

    def _build_terminal(self) -> QFrame:
        card = QFrame()
        card.setStyleSheet("QFrame { background: #0c0c0c; border-radius: 8px; }")
        layout = QVBoxLayout(card)
        layout.setContentsMargins(12, 12, 12, 8)
        layout.setSpacing(6)

        self._terminal = QTextEdit()
        self._terminal.setReadOnly(True)
        self._terminal.setFont(QFont("Consolas", 11))
        self._terminal.setStyleSheet(
            "QTextEdit { background: #0c0c0c; color: #0f0; border: none; }"
        )
        layout.addWidget(self._terminal, stretch=1)

        # 输入栏
        self._cmd_input = QLineEdit()
        self._cmd_input.setPlaceholderText("输入命令后回车执行 ...")
        self._cmd_input.setFont(QFont("Consolas", 11))
        self._cmd_input.setStyleSheet(
            "QLineEdit { background: #1a1a1a; color: #0f0; border: 1px solid #333; "
            "border-radius: 4px; padding: 6px 10px; }"
            "QLineEdit:focus { border-color: #0078d4; }"
        )
        self._cmd_input.returnPressed.connect(self._on_cmd_submit)
        layout.addWidget(self._cmd_input)
        return card

    def _run_system_commands(self):
        if self._term_running:
            return
        self._term_running = True
        self._terminal.clear()
        self._terminal.append("DngTools 工具箱 v0.1.0")
        self._terminal.append("=" * 50)
        self._term_worker = TerminalWorker(SYSTEM_COMMANDS)
        self._term_worker.result.connect(self._on_sys_result)
        self._term_worker.start()

    def _on_sys_result(self, text: str):
        self._terminal.append(text)
        self._terminal.append("=" * 50)
        self._terminal.append("系统信息查询完毕。")

    def _on_cmd_submit(self):
        cmd = self._cmd_input.text().strip()
        if not cmd:
            return
        self._cmd_input.setEnabled(False)
        self._terminal.append(f"\nPS> {cmd}")
        self._cmd_worker = SingleCommandWorker(cmd)
        self._cmd_worker.result.connect(self._on_cmd_result)
        self._cmd_worker.start()

    def _on_cmd_result(self, cmd: str, output: str):
        self._terminal.append(output)
        self._cmd_input.clear()
        self._cmd_input.setEnabled(True)
        self._cmd_input.setFocus()

    # ── 初始化按钮 ────────────────────────────────────

    def _build_action_card(self) -> QFrame:
        card = QFrame()
        card.setStyleSheet(
            "QFrame { background: #252526; border-radius: 10px; }"
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
        self._init_worker = InitWorker(flow_path)
        self._init_worker.finished.connect(self._on_init_finished)
        self._init_worker.start()

    def _on_init_finished(self, result: str):
        self._init_btn.setEnabled(True)
        self._init_btn.setText("初始化")
        QMessageBox.information(self, "初始化结果", result)
