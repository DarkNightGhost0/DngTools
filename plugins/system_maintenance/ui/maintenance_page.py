"""系统维护 UI"""

from __future__ import annotations

import os
import json
import base64
import subprocess
import urllib.request
from datetime import datetime

from PySide6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout,
                                QLabel, QPushButton, QMessageBox,
                                QTextEdit, QToolButton, QMenu, QSizePolicy)
from PySide6.QtGui import QFont, QAction
from PySide6.QtCore import Qt, QThread, Signal


# ── 路径 ──────────────────────────────────────────────

DATA_DIR = os.path.join(os.path.dirname(__file__), "..", "..", "..", "data")
COUNTER_FILE = os.path.join(DATA_DIR, "maintenance_counter.json")
DOWNLOAD_DIR = os.path.join(DATA_DIR, "downloads")
DEFENDER_EXE = os.path.join(DOWNLOAD_DIR, "DefenderRemover.exe")
PS1_PATH = os.path.join(DATA_DIR, "defender_prep.ps1")
CLONE_DIR = os.path.join(DATA_DIR, "windows-defender-remover")

DEFENDER_URL = (
    "https://github.com/ionuttbara/windows-defender-remover/"
    "releases/download/release13/DefenderRemover.exe"
)
DEFENDER_MIRROR = "https://gh-proxy.com/" + DEFENDER_URL
DEFENDER_REPO = "https://github.com/ionuttbara/windows-defender-remover.git"


# ── 提权工具（进程已在管理员权限下）─────────────────

def _b64(script: str) -> str:
    return base64.b64encode(script.encode("utf-16-le")).decode()


def run_ps_silent(script: str, wait: bool = False) -> int:
    args = ["powershell", "-ExecutionPolicy", "Bypass", "-NoProfile",
            "-EncodedCommand", _b64(script)]
    if wait:
        p = subprocess.run(args, capture_output=True, text=True,
                           creationflags=subprocess.CREATE_NO_WINDOW)
        if p.returncode != 0:
            print(f"[PS ERROR] {p.stderr.strip()}")
        return p.returncode
    else:
        subprocess.Popen(args, creationflags=subprocess.CREATE_NO_WINDOW)
        return 0


def run_ps_visible(script: str) -> None:
    subprocess.Popen(
        ["powershell", "-ExecutionPolicy", "Bypass", "-NoProfile",
         "-NoExit", "-EncodedCommand", _b64(script)],
        creationflags=subprocess.CREATE_NEW_CONSOLE,
    )


def run_exe_silent(exe_path: str, args: str = "") -> None:
    cmd = [exe_path]
    if args:
        cmd.append(args)
    si = subprocess.STARTUPINFO()
    si.dwFlags |= subprocess.STARTF_USESHOWWINDOW
    si.wShowWindow = subprocess.SW_HIDE
    subprocess.Popen(cmd, startupinfo=si)


def run_exe_visible(exe_path: str, args: str = "") -> None:
    cmd = [exe_path]
    if args:
        cmd.append(args)
    subprocess.Popen(cmd)


# ── 前置步骤脚本 ─────────────────────────────────────

DISABLE_RT = "Set-MpPreference -DisableRealtimeMonitoring $true"
ADD_EXCLUSION = "Add-MpPreference -ExclusionPath 'C:\\'"

# ── 注册表修改 ───────────────────────────────────────

REG_FILE_PATH = os.path.join(DATA_DIR, "ps1_run_as_admin.reg")

# .reg 文件内容：将 .ps1 双击行为从"编辑"改为"PowerShell 管理员执行"
REG_FILE_CONTENT = (
    'Windows Registry Editor Version 5.00\r\n'
    '\r\n'
    '[HKEY_CLASSES_ROOT\\Microsoft.PowerShellScript.1\\Shell\\Open\\Command]\r\n'
    '@="\\"C:\\\\Windows\\\\System32\\\\WindowsPowerShell\\\\v1.0\\\\powershell.exe\\"'
    ' -NoExit -ExecutionPolicy Bypass -File \\"%1\\""\r\n'
)


# ── 下载 Worker ───────────────────────────────────────

class DownloadWorker(QThread):
    finished = Signal(bool, str)

    def __init__(self, url: str, dest: str):
        super().__init__()
        self.url = url
        self.dest = dest

    def run(self):
        try:
            os.makedirs(os.path.dirname(self.dest), exist_ok=True)
            urllib.request.urlretrieve(self.url, self.dest)
            self.finished.emit(True, "下载完成")
        except Exception as e:
            self.finished.emit(False, str(e))


# ── 每日计数器 ────────────────────────────────────────

def get_daily_count() -> int:
    today = datetime.now().strftime("%Y-%m-%d")
    try:
        with open(COUNTER_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        data = {}
    return data.get("count", 0) if data.get("date") == today else 0


def increment_daily_count() -> int:
    today = datetime.now().strftime("%Y-%m-%d")
    count = get_daily_count() + 1
    if count >= 3:
        count = 0
    os.makedirs(os.path.dirname(COUNTER_FILE), exist_ok=True)
    with open(COUNTER_FILE, "w", encoding="utf-8") as f:
        json.dump({"date": today, "count": count}, f, ensure_ascii=False)
    return count


# ── 页面 ──────────────────────────────────────────────

class MaintenancePage(QWidget):

    BUTTON_STYLE = (
        "QPushButton {"
        "  background: #252526; color: #ccc; border: none; border-radius: 6px;"
        "  font-size: 15px; font-weight: bold; padding-left: 16px;"
        "  text-align: left;"
        "}"
        "QPushButton:hover { background: #3c3c3c; }"
        "QPushButton:pressed { background: #0078d4; color: #fff; }"
        "QPushButton:disabled { background: #555; color: #999; }"
    )

    DROPDOWN_STYLE = (
        "QToolButton {"
        "  background: #252526; color: #ccc; border: none; border-radius: 6px;"
        "  font-size: 14px; font-weight: bold;"
        "}"
        "QToolButton:hover { background: #3c3c3c; }"
        "QToolButton::menu-indicator { image: none; }"
    )

    MENU_STYLE = (
        "QMenu { background: #252526; color: #ccc; border: 1px solid #404040;"
        "  border-radius: 4px; padding: 4px; }"
        "QMenu::item { padding: 6px 20px; }"
        "QMenu::item:selected { background: #0078d4; color: #fff; }"
    )

    def __init__(self, parent=None):
        super().__init__(parent)
        self._dl_worker: DownloadWorker | None = None
        self._log: QTextEdit | None = None
        self._step_actions: dict[str, list[QAction]] = {}

        layout = QVBoxLayout(self)
        layout.setContentsMargins(32, 24, 32, 24)
        layout.setSpacing(12)

        # 标题
        title = QLabel("系统维护")
        title.setStyleSheet(
            "font-size: 22px; font-weight: bold; color: #ccc; padding-bottom: 8px;"
        )
        layout.addWidget(title)

        # ── 按钮行：禁用 Windows 安全中心 ──
        layout.addWidget(self._build_button_row(
            "禁用安全中心",
            [
                "修改注册表（ps1 双击执行）",
                "解除执行策略限制",
                "关闭实时保护（Set-MpPreference）",
                "添加 C 盘排除项（Add-MpPreference）",
                "下载并执行 DefenderRemover（首次静默 /r）",
                "克隆仓库并执行 Script_Run.bat（第3次+，需 Git）",
            ],
            self._on_disable_defender,
            "defender",
            defaults=[False, False, False, False, True, True],
        ))

        # ── 按钮行：系统激活 ──
        layout.addWidget(self._build_button_row(
            "系统激活",
            ["验证安全中心状态"],
            self._on_activate,
            "activate",
        ))

        # ── 日志区域 ──
        log_label = QLabel("日志")
        log_label.setStyleSheet("color: #ccc; font-size: 13px; font-weight: bold; margin-top: 12px;")
        layout.addWidget(log_label)

        self._log = QTextEdit()
        self._log.setReadOnly(True)
        self._log.setFont(QFont("Consolas", 10))
        self._log.setMaximumHeight(150)
        self._log.setStyleSheet(
            "QTextEdit { background: #0c0c0c; color: #0f0; "
            "border: 1px solid #333; border-radius: 6px; padding: 8px; }"
        )
        layout.addWidget(self._log)

        layout.addStretch()

    # ── 按钮行构建 ────────────────────────────────────

    def _build_button_row(self, title: str, step_labels: list[str],
                          callback, card_id: str,
                          defaults: list[bool] | None = None) -> QWidget:
        row = QWidget()
        h = QHBoxLayout(row)
        h.setContentsMargins(0, 0, 0, 0)
        h.setSpacing(0)

        btn = QPushButton(title)
        btn.setFixedHeight(44)
        btn.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        btn.setStyleSheet(self.BUTTON_STYLE)
        btn.clicked.connect(callback)
        h.addWidget(btn)

        dd = QToolButton()
        dd.setText("\u25be")
        dd.setFixedSize(24, 44)
        dd.setPopupMode(QToolButton.InstantPopup)
        dd.setStyleSheet(self.DROPDOWN_STYLE)

        menu = QMenu(dd)
        menu.setStyleSheet(self.MENU_STYLE)

        actions = []
        for i, label in enumerate(step_labels):
            action = QAction(label, menu)
            action.setCheckable(True)
            action.setChecked(True if defaults is None else defaults[i])
            menu.addAction(action)
            actions.append(action)

        dd.setMenu(menu)
        h.addWidget(dd)

        self._step_actions[card_id] = actions
        return row

    # ── 日志 ──────────────────────────────────────────

    def _log_msg(self, msg: str):
        ts = datetime.now().strftime("%H:%M:%S")
        self._log.append(f"[{ts}] {msg}")

    # ── 禁用 Windows 安全中心 ─────────────────────────

    def _on_disable_defender(self):
        QMessageBox.information(
            self, "手动操作提示",
            "请先手动前往 Windows 安全中心 → 病毒和威胁防护 → 管理设置，"
            "关闭「实时保护」和「篡改防护」后，再继续执行下方步骤。"
        )

        steps = self._step_actions["defender"]
        if not any(a.isChecked() for a in steps):
            self._log_msg("所有步骤均未勾选，操作取消")
            return

        count = get_daily_count()
        new_count = increment_daily_count()
        self._log_msg(f"今日执行次数: {new_count}")

        # Step 1: 修改注册表（.reg 文件导入，避免引号转义问题）
        if steps[0].isChecked():
            self._log_msg("[1/6] 修改注册表 ...")
            reg_file = os.path.join(DATA_DIR, "ps1_run_as_admin.reg")
            os.makedirs(DATA_DIR, exist_ok=True)
            with open(reg_file, "w", encoding="utf-8") as f:
                f.write(REG_FILE_CONTENT)
            result = subprocess.run(
                ["reg", "import", reg_file],
                capture_output=True, text=True,
                creationflags=subprocess.CREATE_NO_WINDOW,
            )
            if result.returncode == 0:
                self._log_msg("注册表已修改：.ps1 双击→PowerShell 管理员执行")
            else:
                self._log_msg(f"注册表修改失败: {result.stderr.strip()}")
                QMessageBox.warning(self, "注册表修改失败", result.stderr.strip())

        # Step 2: 执行策略（已被 GPO 覆盖为 Bypass，无需再设，跳过）
        if steps[1].isChecked():
            self._log_msg("[2/6] 执行策略已为 Bypass（由 GPO 控制），跳过")

        # Step 3-4: 按勾选生成 ps1 + bat 备用启动脚本
        do_rt = steps[2].isChecked()
        do_ex = steps[3].isChecked()
        if do_rt or do_ex:
            lines = []
            if do_rt:
                lines.append(DISABLE_RT)
            if do_ex:
                lines.append(ADD_EXCLUSION)
            ps1_content = "#Requires -RunAsAdministrator\r\n" + "\n".join(lines) + "\n"

            os.makedirs(os.path.dirname(PS1_PATH), exist_ok=True)
            with open(PS1_PATH, "w", encoding="utf-8", newline="") as f:
                f.write(ps1_content)

            # 配套 bat（自提权 + 冗余启动）
            bat_path = os.path.splitext(PS1_PATH)[0] + ".bat"
            with open(bat_path, "w", encoding="ascii") as f:
                f.write(
                    '@echo off\r\n'
                    'net session >nul 2>&1\r\n'
                    'if %errorlevel% neq 0 (\r\n'
                    '    powershell -Command '
                    '"Start-Process \'%~f0\' -Verb RunAs"\r\n'
                    '    exit /b\r\n'
                    ')\r\n'
                    'powershell -ExecutionPolicy Bypass -NoExit '
                    '-File "%~dp0defender_prep.ps1"\r\n'
                )

            self._log_msg("[3/6] defender_prep.ps1 + .bat 已生成，请双击运行后继续")
            subprocess.Popen(["explorer", "/select,", PS1_PATH])

        # Step 5: 下载并执行 DefenderRemover.exe（count < 2）
        if steps[4].isChecked() and count < 2:
            silent = (count == 0)
            if silent:
                self._log_msg("[4/6] 首次执行：下载并静默执行 DefenderRemover.exe /r")
            else:
                self._log_msg(
                    f"[4/6] 第{new_count}次：下载并交互执行 DefenderRemover.exe"
                )
            self._download_and_run(new_count, silent)
            return

        # Step 6: 克隆仓库并执行 Script_Run.bat（count >= 2）
        if steps[5].isChecked() and count >= 2:
            self._log_msg(
                f"[5/6] 第3次：克隆仓库并执行 Script_Run.bat（计数器已归零）"
            )
            self._git_clone_and_run()
            return

        self._log_msg("操作完成")

    # ── 下载 + 执行 DefenderRemover ────────────────────

    def _download_and_run(self, count: int, silent: bool):
        if os.path.exists(DEFENDER_EXE):
            self._log_msg("DefenderRemover.exe 已存在，跳过下载")
            self._run_defender_remover(silent)
            return

        self._log_msg("正在下载 DefenderRemover.exe ...")
        self._dl_worker = DownloadWorker(DEFENDER_URL, DEFENDER_EXE)
        self._dl_worker.finished.connect(
            lambda ok, msg: self._on_download_done(ok, msg, silent)
        )
        self._dl_worker.start()

    def _on_download_done(self, ok: bool, msg: str, silent: bool):
        if ok:
            self._log_msg("下载完成")
            self._run_defender_remover(silent)
        else:
            self._log_msg(f"主站下载失败: {msg}，尝试镜像 ...")
            self._dl_worker = DownloadWorker(DEFENDER_MIRROR, DEFENDER_EXE)
            self._dl_worker.finished.connect(
                lambda ok2, msg2: self._on_mirror_done(ok2, msg2, silent)
            )
            self._dl_worker.start()

    def _on_mirror_done(self, ok: bool, msg: str, silent: bool):
        if ok:
            self._log_msg("镜像下载完成")
            self._run_defender_remover(silent)
        else:
            self._log_msg(f"镜像下载也失败: {msg}")
            QMessageBox.warning(
                self, "下载失败",
                f"无法下载 DefenderRemover.exe\n\n{msg}"
            )

    def _run_defender_remover(self, silent: bool):
        if silent:
            run_exe_silent(DEFENDER_EXE, "/r")
            self._log_msg("DefenderRemover.exe /r 已提交（静默）")
        else:
            run_exe_visible(DEFENDER_EXE)
            self._log_msg("DefenderRemover.exe 已打开，请在窗口中按 Y 确认移除")
            QMessageBox.information(
                self, "提示",
                "DefenderRemover 在管理员窗口中打开。\n请在窗口中按 Y 确认移除。"
            )

    # ── Git 克隆 + Script_Run.bat ─────────────────────

    def _git_clone_and_run(self):
        # 检查 git
        result = subprocess.run(
            ["git", "--version"], capture_output=True, text=True,
            creationflags=subprocess.CREATE_NO_WINDOW,
        )
        if result.returncode != 0:
            self._log_msg("Git 未安装，通过 winget 安装 ...")
            ir = subprocess.run(
                ["winget", "install", "--id", "Git.Git", "-e",
                 "--source", "winget",
                 "--accept-package-agreements",
                 "--accept-source-agreements",
                 "--silent"],
                capture_output=True, text=True,
                creationflags=subprocess.CREATE_NO_WINDOW,
            )
            if ir.returncode != 0:
                self._log_msg(f"winget 安装 Git 失败: {ir.stderr.strip()}")
                QMessageBox.warning(
                    self, "安装失败",
                    f"无法通过 winget 安装 Git\n\n{ir.stderr.strip()}\n"
                    "请手动安装 Git 后重试。"
                )
                return
            self._log_msg("Git 安装完成")

        # 克隆仓库
        if not os.path.exists(CLONE_DIR):
            self._log_msg("克隆 windows-defender-remover ...")
            cr = subprocess.run(
                ["git", "clone", DEFENDER_REPO, CLONE_DIR],
                capture_output=True, text=True,
                creationflags=subprocess.CREATE_NO_WINDOW,
            )
            if cr.returncode != 0:
                self._log_msg(f"克隆失败: {cr.stderr.strip()}")
                QMessageBox.warning(
                    self, "克隆失败",
                    f"无法克隆仓库\n\n{cr.stderr}"
                )
                return
            self._log_msg("克隆完成")
        else:
            self._log_msg("仓库已存在，跳过克隆")
            # git pull 更新
            subprocess.run(
                ["git", "-C", CLONE_DIR, "pull"],
                capture_output=True, text=True,
                creationflags=subprocess.CREATE_NO_WINDOW,
            )

        # 执行 Script_Run.bat
        bat_path = os.path.join(CLONE_DIR, "Script_Run.bat")
        if not os.path.exists(bat_path):
            self._log_msg(f"Script_Run.bat 不存在: {bat_path}")
            QMessageBox.warning(self, "文件缺失", "Script_Run.bat 未找到")
            return

        self._log_msg("执行 Script_Run.bat ...")
        subprocess.Popen(
            ["cmd", "/c", "start", bat_path],
            cwd=CLONE_DIR,
            creationflags=subprocess.CREATE_NEW_CONSOLE,
        )
        self._log_msg("Script_Run.bat 已在新窗口打开，请在窗口中输入 Y 并回车")

    # ── 系统激活 ──────────────────────────────────────

    def _on_activate(self):
        steps = self._step_actions["activate"]

        if steps[0].isChecked():
            self._log_msg("验证安全中心状态 ...")
            result = subprocess.run(
                ["sc", "query", "WinDefend"],
                capture_output=True, text=True,
                creationflags=subprocess.CREATE_NO_WINDOW,
            )
            if "RUNNING" in result.stdout:
                self._log_msg("安全中心正在运行，操作中止")
                QMessageBox.warning(
                    self, "安全中心运行中",
                    "Windows 安全中心仍在运行。\n\n"
                    "请先执行「禁用 Windows 安全中心」后再激活。"
                )
                return
            self._log_msg("安全中心未运行，继续 ...")

        self._log_msg("打开 Microsoft Activation Scripts ...")
        run_ps_visible("irm https://get.activated.win | iex")
        self._log_msg("请在 PowerShell 窗口中操作：输入 1 激活 Windows，输入 2 激活 Office")
