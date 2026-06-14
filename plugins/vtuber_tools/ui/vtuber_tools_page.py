"""VTuber Tools 页面 UI"""

import os
import shutil
import subprocess
import tempfile
import urllib.request
import webbrowser
import struct
import zipfile
import json
from pathlib import Path
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout,
    QLabel, QPushButton, QToolButton, QFrame, QFileDialog, QMessageBox,
    QMenu, QDialog, QTextEdit, QComboBox, QScrollArea,
)
from PySide6.QtGui import QFont, QAction, QActionGroup
from PySide6.QtCore import Qt, QThread, Signal

from plugins.vtuber_tools.download_config import DownloadConfig


# ── 已知安装路径 ──────────────────────────────────────

KNOWN_PATHS = {
    "Steam": [
        r"C:\Program Files (x86)\Steam\steam.exe",
        r"C:\Program Files\Steam\steam.exe",
    ],
    "VTube Studio": [
        r"C:\Program Files (x86)\Steam\steamapps\common\VTube Studio\VTube Studio.exe",
        r"C:\Program Files\VTube Studio\VTube Studio.exe",
    ],
    "OBS Studio": [
        r"C:\Program Files\obs-studio\bin\64bit\obs64.exe",
        r"C:\Program Files (x86)\obs-studio\bin\64bit\obs64.exe",
    ],
}

VALID_EXE_NAMES = {
    "Steam": ["steam.exe"],
    "VTube Studio": ["VTube Studio.exe"],
    "OBS Studio": ["obs64.exe", "obs32.exe"],
}

# ── Styles ────────────────────────────────────────────

STYLE_PAGE_TITLE = "QLabel { color: #ccc; font-size: 18px; font-weight: bold; }"
STYLE_PATH_FOUND = "QLabel { color: #4caf50; font-size: 12px; background: #2d2d30; border-radius: 4px; padding: 8px 12px; }"
STYLE_PATH_NOT_FOUND = "QLabel { color: #d32f2f; font-size: 12px; background: #2d2d30; border-radius: 4px; padding: 8px 12px; }"
STYLE_PATH_INSTALLING = "QLabel { color: #ffa726; font-size: 12px; background: #2d2d30; border-radius: 4px; padding: 8px 12px; }"
STYLE_CARD = "QFrame#vt_card { background: #252526; border-radius: 10px; }"
STYLE_BTN_SEARCH = """
    QPushButton {
        background: #3a3a3a; color: #ccc; border: 1px solid #505050;
        border-radius: 5px; padding: 6px 16px; font-size: 12px;
    }
    QPushButton:hover { background: #4a4a4a; }
    QPushButton:pressed { background: #2a2a2a; }
    QPushButton:disabled { background: #333; color: #666; }
"""
STYLE_BTN_BROWSE = """
    QPushButton {
        background: #3a3a3a; color: #ccc; border: 1px solid #505050;
        border-radius: 5px; padding: 6px 16px; font-size: 12px;
    }
    QPushButton:hover { background: #4a4a4a; }
    QPushButton:pressed { background: #2a2a2a; }
    QPushButton:disabled { background: #333; color: #666; }
"""
STYLE_BTN_LAUNCH = """
    QToolButton {
        background: #2e7d32; color: #fff; border: none;
        border-radius: 5px; padding: 6px 18px; font-size: 12px; font-weight: bold;
    }
    QToolButton:hover { background: #388e3c; }
    QToolButton:pressed { background: #1b5e20; }
    QToolButton:disabled { background: #333; color: #666; }
"""
STYLE_BTN_INSTALL = """
    QPushButton {
        background: #0078d4; color: #fff; border: none;
        border-radius: 5px; padding: 6px 18px; font-size: 12px; font-weight: bold;
    }
    QPushButton:hover { background: #1a8fe3; }
    QPushButton:pressed { background: #005a9e; }
    QPushButton:disabled { background: #555; color: #999; }
"""
STYLE_BTN_INSTALLED = """
    QPushButton {
        background: #2e7d32; color: #fff; border: none;
        border-radius: 5px; padding: 6px 18px; font-size: 12px; font-weight: bold;
    }
    QPushButton:disabled { background: #2e7d32; color: #fff; }
"""
STYLE_BTN_UPDATE = """
    QPushButton {
        background: #e67e00; color: #fff; border: none;
        border-radius: 5px; padding: 6px 18px; font-size: 12px; font-weight: bold;
    }
    QPushButton:hover { background: #f09020; }
    QPushButton:pressed { background: #b06300; }
    QPushButton:disabled { background: #555; color: #999; }
"""
STYLE_BTN_WATERMARK = """
    QToolButton {
        background: #6a1b9a; color: #fff; border: none;
        border-radius: 5px; padding: 6px 14px; font-size: 12px;
    }
    QToolButton:hover { background: #7b1fa2; }
    QToolButton:pressed { background: #4a148c; }
    QToolButton:disabled { background: #333; color: #666; }
"""
STYLE_BTN_WEBCAM = """
    QToolButton {
        background: #00838f; color: #fff; border: none;
        border-radius: 5px; padding: 6px 14px; font-size: 12px;
    }
    QToolButton:hover { background: #0097a7; }
    QToolButton:pressed { background: #006064; }
    QToolButton:disabled { background: #333; color: #666; }
"""
STYLE_BTN_SPOUT2 = """
    QToolButton {
        background: #bf360c; color: #fff; border: none;
        border-radius: 5px; padding: 6px 14px; font-size: 12px;
    }
    QToolButton:hover { background: #d84315; }
    QToolButton:pressed { background: #8d2a00; }
    QToolButton:disabled { background: #333; color: #666; }
"""

STYLE_BTN_NDI = """
    QToolButton {
        background: #6a1b9a; color: #fff; border: none;
        border-radius: 5px; padding: 6px 14px; font-size: 12px;
    }
    QToolButton:hover { background: #8e24aa; }
    QToolButton:pressed { background: #4a148c; }
    QToolButton:disabled { background: #333; color: #666; }
"""


# ── Spout2 下载配置 ──────────────────────────────────

SPOUT2_URLS = {
    "new": {  # OBS >= 31.0
        "zip": "https://github.com/Off-World-Live/obs-spout2-plugin/releases/download/1.10.0/win-spout-1.9.0-windows-x64.zip",
        "exe": "https://github.com/Off-World-Live/obs-spout2-plugin/releases/download/1.10.0/OBS_Spout2_Plugin_Install_v1.9.0.exe",
    },
    "old": {  # OBS < 31.0
        "zip": "https://github.com/Off-World-Live/obs-spout2-plugin/releases/download/v1.8/OBS_Spout2_Plugin_ManualInstall_v1.8.zip",
        "exe": "https://github.com/Off-World-Live/obs-spout2-plugin/releases/download/v1.8/OBS_Spout2_Plugin_Install_v1.8.exe",
    },
}


# ── 插件列表 ──────────────────────────────────────────

PLUGIN_JSON_PATH = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    "config", "plugin_list.json"
)


def _load_plugins():
    with open(PLUGIN_JSON_PATH, 'r', encoding='utf-8') as f:
        return json.load(f)


PLUGIN_LIST = _load_plugins()


# ── Workers ───────────────────────────────────────────

class SearchWorker(QThread):
    result = Signal(str, str)

    def __init__(self, tool_name: str):
        super().__init__()
        self.tool_name = tool_name

    def run(self):
        paths = KNOWN_PATHS.get(self.tool_name, [])
        for p in paths:
            if os.path.isfile(p):
                self.result.emit(self.tool_name, p)
                return

        exe_names = {
            "Steam": "steam.exe",
            "VTube Studio": "VTube Studio.exe",
            "OBS Studio": "obs64.exe",
        }
        exe = exe_names.get(self.tool_name, "")
        if exe:
            try:
                r = subprocess.run(
                    ["where", exe],
                    capture_output=True, text=True,
                    timeout=10,
                    creationflags=subprocess.CREATE_NO_WINDOW,
                )
                for line in r.stdout.strip().split("\n"):
                    p = line.strip()
                    if os.path.isfile(p):
                        self.result.emit(self.tool_name, p)
                        return
            except Exception:
                pass

        self.result.emit(self.tool_name, "")


class WatermarkWorker(QThread):
    """移除 VTube Studio 水印：三种模式"""
    progress = Signal(str)
    status = Signal(str)
    finished = Signal(bool, str)
    dialog = Signal(str, str)

    def __init__(self, vtube_dir: str, mode: str = "proxy",
                 download_config: DownloadConfig | None = None):
        super().__init__()
        self.vtube_dir = vtube_dir
        self.mode = mode
        self._cancel_flag = False
        self._config = download_config

    @staticmethod
    def _download_with_progress(url: str, dest: str, status_signal):
        """下载文件并通过 status_signal 发送 下载中 xx%"""

        class Reporter:
            def __init__(self):
                self.last_pct = 0

            def __call__(self, block_count, block_size, total_size):
                if total_size > 0:
                    pct = min(int(block_count * block_size * 100 / total_size), 99)
                else:
                    pct = 0
                if pct > self.last_pct:
                    self.last_pct = pct
                    status_signal.emit(f"下载中 {pct}%")

        urllib.request.urlretrieve(url, dest, reporthook=Reporter())

    @staticmethod
    def detect_bitness(exe_path: str) -> str:
        with open(exe_path, 'rb') as f:
            f.seek(0x3C)
            pe_offset = struct.unpack('<I', f.read(4))[0]
            f.seek(pe_offset + 4)
            machine = struct.unpack('<H', f.read(2))[0]
        return '64' if machine == 0x8664 else '32'

    def _stop_vtube(self):
        self.progress.emit("检查 VTube Studio 进程...")
        r = subprocess.run(
            ["tasklist", "/fi", "IMAGENAME eq VTube Studio.exe"],
            capture_output=True, text=True,
            creationflags=subprocess.CREATE_NO_WINDOW,
        )
        if "VTube Studio.exe" in r.stdout:
            self.progress.emit("VTube Studio 正在运行，尝试终止...")
            subprocess.run(
                ["taskkill", "/f", "/im", "VTube Studio.exe"],
                capture_output=True,
                creationflags=subprocess.CREATE_NO_WINDOW,
            )
            self.progress.emit("VTube Studio 已终止")
        else:
            self.progress.emit("VTube Studio 未运行，跳过")

    def _download_smokeapi(self, tmpdir: str) -> str:
        url = None
        if self._config:
            url = self._config.get_latest_url("SmokeAPI")
        if not url:
            url = "https://github.com/acidicoala/SmokeAPI/releases/download/v4.1.3/SmokeAPI-v4.1.3.zip"
        zip_name = os.path.basename(url) or "SmokeAPI.zip"
        zip_path = os.path.join(tmpdir, zip_name)
        self.progress.emit(f"下载 SmokeAPI: {url}")
        self._download_with_progress(url, zip_path, self.status)
        self.progress.emit(f"下载完成 ({os.path.getsize(zip_path)} bytes)")
        self.status.emit("解压中...")
        extract = os.path.join(tmpdir, "SmokeAPI")
        os.makedirs(extract, exist_ok=True)
        self.progress.emit("解压 SmokeAPI...")
        with zipfile.ZipFile(zip_path, 'r') as zf:
            zf.extractall(extract)
        self.progress.emit("SmokeAPI 解压完成")
        return extract

    def _find_smoke_dlls(self, extract_dir: str) -> tuple:
        smoke32, smoke64 = None, None
        all_dlls = []
        for root, dirs, files in os.walk(extract_dir):
            for f in files:
                fl = f.lower()
                if fl.endswith(".dll"):
                    all_dlls.append(os.path.join(root, f))
                if fl == "smoke_api32.dll":
                    smoke32 = os.path.join(root, f)
                elif fl == "smoke_api64.dll":
                    smoke64 = os.path.join(root, f)
        if not smoke32 and not smoke64:
            self.progress.emit(f"SmokeAPI 中未找到目标 DLL，实际内容: {all_dlls}")
        return smoke32, smoke64

    def _pick_smoke_dll(self, smoke32, smoke64, bitness: str):
        if bitness == "64" and smoke64:
            return smoke64
        if bitness == "32" and smoke32:
            return smoke32
        return smoke64 or smoke32

    def run(self):
        tmpdir = tempfile.mkdtemp(prefix="vtube_watermark_")
        try:
            exe_path = os.path.join(self.vtube_dir, "VTube Studio.exe")
            if not os.path.isfile(exe_path):
                self.finished.emit(False, "未找到 VTube Studio.exe")
                return

            mode_label = {"proxy": "代理模式", "selfhook": "自挂模式", "koaloader": "Koaloader 钩子"}
            self.progress.emit(f"模式: {mode_label.get(self.mode, self.mode)}")
            self.progress.emit(f"目录: {self.vtube_dir}")

            self._stop_vtube()

            if self.mode == "proxy":
                self._run_proxy(tmpdir)
            elif self.mode == "selfhook":
                self._run_selfhook(tmpdir, exe_path)
            elif self.mode == "koaloader":
                self._run_koaloader(tmpdir, exe_path)
        except Exception as e:
            self.finished.emit(False, f"移除水印失败: {e}")
        finally:
            try:
                shutil.rmtree(tmpdir, ignore_errors=True)
            except Exception:
                pass

    def _run_proxy(self, tmpdir):
        self.progress.emit("=== 代理模式 ===")
        self.progress.emit("搜索 steam_api.dll / steam_api64.dll ...")
        # {dll_name: directory}  —— 各自可能在不同目录，也可能仅存在其中一个
        dll_map: dict[str, str] = {}
        for root, dirs, files in os.walk(self.vtube_dir):
            for f in files:
                fl = f.lower()
                if fl == "steam_api.dll" and "steam_api.dll" not in dll_map:
                    dll_map["steam_api.dll"] = root
                    self.progress.emit(f"  找到 steam_api.dll → {root}")
                elif fl == "steam_api64.dll" and "steam_api64.dll" not in dll_map:
                    dll_map["steam_api64.dll"] = root
                    self.progress.emit(f"  找到 steam_api64.dll → {root}")

        if not dll_map:
            self.finished.emit(False, "未找到 steam_api.dll 或 steam_api64.dll")
            return

        self.progress.emit("备份原始 DLL ...")
        for dll_name, dll_dir in dll_map.items():
            orig = os.path.join(dll_dir, dll_name)
            if not os.path.isfile(orig):
                self.progress.emit(f"  跳过 {dll_name}（文件不存在）")
                continue
            backup_name = dll_name.replace(".dll", "_o.dll")
            backup = os.path.join(dll_dir, backup_name)
            if os.path.isfile(backup):
                os.remove(backup)
                self.progress.emit(f"  删除旧备份 {backup_name}")
            os.rename(orig, backup)
            self.progress.emit(f"  {dll_name} → {backup_name}")

        smoke_ext = self._download_smokeapi(tmpdir)
        smoke32, smoke64 = self._find_smoke_dlls(smoke_ext)
        if smoke32:
            self.progress.emit(f"SmokeAPI 32位: {smoke32}")
        if smoke64:
            self.progress.emit(f"SmokeAPI 64位: {smoke64}")

        placed = 0
        self.status.emit("安装 DLL...")
        # smoke_api32.dll → steam_api.dll 所在目录
        if smoke32 and "steam_api.dll" in dll_map:
            dst = os.path.join(dll_map["steam_api.dll"], "steam_api.dll")
            shutil.copy2(smoke32, dst)
            self.progress.emit(f"放置 smoke_api32.dll → {dst}")
            placed += 1
        elif "steam_api.dll" in dll_map and not smoke32:
            self.progress.emit("警告: 未在 SmokeAPI 中找到 smoke_api32.dll")
        # smoke_api64.dll → steam_api64.dll 所在目录
        if smoke64 and "steam_api64.dll" in dll_map:
            dst = os.path.join(dll_map["steam_api64.dll"], "steam_api64.dll")
            shutil.copy2(smoke64, dst)
            self.progress.emit(f"放置 smoke_api64.dll → {dst}")
            placed += 1
        elif "steam_api64.dll" in dll_map and not smoke64:
            self.progress.emit("警告: 未在 SmokeAPI 中找到 smoke_api64.dll")

        if placed == 0:
            self.finished.emit(False, "SmokeAPI 中未找到可用的 smoke_api DLL，无法放置")
        else:
            self.finished.emit(True, f"代理模式完成，已处理 {placed} 个 DLL。")

    def _run_selfhook(self, tmpdir, exe_path):
        self.progress.emit("=== 自挂模式 ===")
        bitness = self.detect_bitness(exe_path)
        self.progress.emit(f"VTube Studio 位宽: {bitness} 位")

        smoke_ext = self._download_smokeapi(tmpdir)
        smoke32, smoke64 = self._find_smoke_dlls(smoke_ext)
        src = self._pick_smoke_dll(smoke32, smoke64, bitness)
        if not src:
            self.finished.emit(False, f"未找到适合 {bitness} 位的 smoke_api DLL")
            return

        self.progress.emit(f"源 DLL: {src}")
        self.progress.emit(f"目标目录: {self.vtube_dir}")
        self.status.emit("安装 DLL...")
        for name in ("version.dll", "winhttp.dll", "winmm.dll"):
            dst = os.path.join(self.vtube_dir, name)
            shutil.copy2(src, dst)
            self.progress.emit(f"  {os.path.basename(src)} → {name}")

        self.finished.emit(True, "自挂模式完成。")


    def _run_koaloader(self, tmpdir, exe_path):
        self.progress.emit("=== Koaloader 钩子模式 ===")
        bitness = self.detect_bitness(exe_path)
        self.progress.emit(f"VTube Studio 位宽: {bitness} 位")

        smoke_ext = self._download_smokeapi(tmpdir)

        # 下载 Koaloader
        koa_url = None
        if self._config:
            koa_url = self._config.get_latest_url("Koaloader")
        if not koa_url:
            koa_url = "https://github.com/acidicoala/Koaloader/releases/download/v3.0.4/Koaloader-v3.0.4.zip"
        koa_zip_name = os.path.basename(koa_url) or "Koaloader.zip"
        koa_zip = os.path.join(tmpdir, koa_zip_name)
        self.progress.emit(f"下载 Koaloader: {koa_url}")
        self._download_with_progress(koa_url, koa_zip, self.status)
        self.progress.emit(f"下载完成 ({os.path.getsize(koa_zip)} bytes)")
        self.status.emit("解压中...")
        koa_ext = os.path.join(tmpdir, "Koaloader")
        os.makedirs(koa_ext, exist_ok=True)
        self.progress.emit("解压 Koaloader...")
        with zipfile.ZipFile(koa_zip, 'r') as zf:
            zf.extractall(koa_ext)
        self.progress.emit("Koaloader 解压完成")

        # 查找 d3d11-32 或 d3d11-64
        target = f"d3d11-{bitness}"
        d3d11_src = None
        for root, dirs, files in os.walk(koa_ext):
            for f in files:
                if target.lower() in f.lower():
                    d3d11_src = os.path.join(root, f)
                    break
            if d3d11_src:
                break
        if d3d11_src:
            self.progress.emit(f"Koaloader d3d11: {d3d11_src}")
            self.status.emit("安装 DLL...")
            dst = os.path.join(self.vtube_dir, os.path.basename(d3d11_src))
            shutil.copy2(d3d11_src, dst)
            self.progress.emit(f"  放置 {os.path.basename(d3d11_src)}")
        else:
            self.finished.emit(False, f"Koaloader 中未找到 {target}")
            return

        # 放置 smoke_api
        smoke32, smoke64 = self._find_smoke_dlls(smoke_ext)
        src = self._pick_smoke_dll(smoke32, smoke64, bitness)
        if src:
            dst = os.path.join(self.vtube_dir, os.path.basename(src))
            shutil.copy2(src, dst)
            self.progress.emit(f"  放置 {os.path.basename(src)}")
        else:
            self.finished.emit(False, f"未找到适合 {bitness} 位的 smoke_api DLL")
            return

        self.finished.emit(True, "Koaloader 钩子模式完成。")


# ── Spout2 安装 Worker ───────────────────────────────

class Spout2Worker(QThread):
    progress = Signal(str)
    status = Signal(str)
    finished = Signal(bool, str)

    def __init__(self, mode: str, download_url: str,
                 obs_exe_path: str, is_new_version: bool):
        super().__init__()
        self.mode = mode          # "zip" / "exe"
        self.download_url = download_url
        self.obs_exe_path = obs_exe_path
        self.is_new_version = is_new_version

    def run(self):
        try:
            # 下载
            self.status.emit("下载中...")
            self.progress.emit(f"下载 {os.path.basename(self.download_url)} ...")
            dl_path = os.path.join(tempfile.gettempdir(),
                                   os.path.basename(self.download_url))
            urllib.request.urlretrieve(self.download_url, dl_path)
            self.progress.emit(f"下载完成: {dl_path}")

            if self.mode == "zip":
                self._handle_zip(dl_path)
            else:
                self._handle_exe(dl_path)

        except Exception as e:
            self.finished.emit(False, str(e))

    def _handle_zip(self, zip_path: str):
        self.status.emit("解压中...")
        self.progress.emit("确定解压目标目录...")

        if self.is_new_version:
            # 1.9.0 → C:\ProgramData\obs-studio\plugins
            extract_dir = r"C:\ProgramData\obs-studio\plugins"
        else:
            # 1.8 → OBS 安装目录（obs64.exe 上三级）
            obs_dir = os.path.dirname(os.path.dirname(os.path.dirname(
                self.obs_exe_path)))
            extract_dir = obs_dir

        self.progress.emit(f"解压到: {extract_dir}")
        os.makedirs(extract_dir, exist_ok=True)

        with zipfile.ZipFile(zip_path, 'r') as zf:
            zf.extractall(extract_dir)

        self.progress.emit("Spout2 ZIP 安装完成")
        self.finished.emit(True, f"Spout2 已安装到 {extract_dir}")

    def _handle_exe(self, exe_path: str):
        self.status.emit("打开安装程序...")
        self.progress.emit("启动 Spout2 安装程序...")
        exe_dir = os.path.dirname(exe_path)
        subprocess.Popen(
            ["cmd", "/c", "start", "", exe_path],
            cwd=exe_dir,
            creationflags=subprocess.CREATE_NO_WINDOW,
        )
        self.progress.emit("Spout2 安装程序已启动")
        self.finished.emit(True, "Spout2 安装程序已启动，请在弹出窗口中完成安装。")


class NDIWorker(QThread):
    """通过 winget 安装 NDI 组件的后台线程。"""
    status = Signal(str)
    finished = Signal(bool, str)

    def __init__(self, cmds: list[tuple[str, list[str]]], parent=None):
        super().__init__(parent)
        self._cmds = cmds

    def run(self):
        success_all = True
        messages = []
        for label, cmd in self._cmds:
            self.status.emit(f"正在安装 {label}...")
            try:
                result = subprocess.run(
                    cmd,
                    capture_output=True,
                    text=True,
                    creationflags=subprocess.CREATE_NO_WINDOW,
                )
                if result.returncode == 0:
                    messages.append(f"{label} 安装成功")
                else:
                    err = result.stderr.strip() or result.stdout.strip()
                    messages.append(f"{label} 安装失败: {err}")
                    success_all = False
            except FileNotFoundError:
                messages.append(f"{label} 安装失败: 未找到 winget，请确保系统已安装 winget")
                success_all = False
            except Exception as e:
                messages.append(f"{label} 安装失败: {e}")
                success_all = False
        self.finished.emit(success_all, "\n".join(messages))


# ── 插件安装 Worker ──────────────────────────────────

def _fix_zip_filename(info: zipfile.ZipInfo) -> str:
    """修正 ZIP 中非 UTF-8 编码的中文文件名。

    中文 Windows 下创建的 ZIP，文件名常以 GBK 编码存储，
    但未设置 UTF-8 标志位（bit 11），导致解压后乱码。
    """
    name = info.filename
    # UTF-8 标志位已设置 → 无需修正
    if info.flag_bits & 0x800:
        return name
    # 尝试将 cp437 字节按 GBK / UTF-8 解码
    try:
        raw = name.encode('cp437')
    except (UnicodeEncodeError, LookupError):
        return name
    for enc in ('gbk', 'utf-8'):
        try:
            decoded = raw.decode(enc)
            if any('\u4e00' <= c <= '\u9fff' for c in decoded):
                return decoded
            return decoded
        except UnicodeDecodeError:
            continue
    return name


class PluginInstallWorker(QThread):
    progress = Signal(str)
    status = Signal(str)
    finished = Signal(bool, str)

    def __init__(self, plugin: dict, vtube_exe_path: str):
        super().__init__()
        self.plugin = plugin
        self.vtube_exe_path = vtube_exe_path

    def run(self):
        plugin_name = self.plugin["name"]
        download_url = self.plugin["url"]
        install_dir = self.plugin.get("install_dir", "")
        try:
            # 停止 VTube Studio
            self.status.emit("停止VTube Studio...")
            self.progress.emit("检测 VTube Studio 进程...")
            subprocess.run(
                ["taskkill", "/f", "/im", "VTube Studio.exe"],
                capture_output=True,
                creationflags=subprocess.CREATE_NO_WINDOW,
            )

            # 下载
            self.status.emit("下载中...")
            self.progress.emit(f"下载 {plugin_name} ...")
            dl_path = os.path.join(tempfile.gettempdir(),
                                   os.path.basename(download_url))
            urllib.request.urlretrieve(download_url, dl_path)
            self.progress.emit(f"下载完成: {dl_path}")

            # 解压到 VTube Studio 程序目录（支持指定子目录）
            vtube_dir = os.path.dirname(self.vtube_exe_path)
            extract_dir = os.path.join(vtube_dir, install_dir) if install_dir else vtube_dir
            self.status.emit("解压中...")
            self.progress.emit(f"解压到: {extract_dir}")
            os.makedirs(extract_dir, exist_ok=True)
            with zipfile.ZipFile(dl_path, 'r') as zf:
                for info in zf.infolist():
                    info.filename = _fix_zip_filename(info)
                    zf.extract(info, extract_dir)

            self.progress.emit(f"{plugin_name} 文件解压完成")

            # 后置：写入模板文件
            post_files = self.plugin.get("post_install_files", [])
            post_msg = self.plugin.get("post_install_message", "")
            desktop = os.path.expanduser("~\\Desktop")
            for pf in post_files:
                dest = pf["path"].replace("{desktop}", desktop)
                os.makedirs(os.path.dirname(dest), exist_ok=True)
                with open(dest, 'w', encoding='utf-8') as f:
                    f.write(pf["content"])
                self.progress.emit(f"已创建: {dest}")

            # 仅 BepInEx 安装后通过 Steam 启动 VTube Studio
            if plugin_name == "BepInEx":
                self.status.emit("启动VTube Studio...")
                self.progress.emit("通过 Steam 启动 VTube Studio ...")
                webbrowser.open("steam://rungameid/1325860")
                self.finished.emit(True,
                    f"{plugin_name} 安装完成，VTube Studio 已启动。")
            elif post_msg:
                self.finished.emit(True,
                    f"{plugin_name} 安装完成。\n\n{post_msg}")
            else:
                self.finished.emit(True,
                    f"{plugin_name} 安装完成。")

        except Exception as e:
            self.finished.emit(False, str(e))


class PluginUninstallWorker(QThread):
    finished = Signal(bool, str)

    def __init__(self, plugin_name: str, plugin_cfg: dict, vtube_dir: str,
                 parent=None):
        super().__init__(parent)
        self.plugin_name = plugin_name
        self.plugin_cfg = plugin_cfg
        self.vtube_dir = vtube_dir

    def run(self):
        try:
            # 停止 VTube Studio
            subprocess.run(
                ["taskkill", "/f", "/im", "VTube Studio.exe"],
                capture_output=True,
                creationflags=subprocess.CREATE_NO_WINDOW,
            )

            import time
            time.sleep(0.5)

            errors: list[str] = []

            # 删除文件夹
            for d in self.plugin_cfg.get("uninstall_dirs", []):
                target = os.path.join(self.vtube_dir, d)
                if os.path.isdir(target):
                    try:
                        shutil.rmtree(target)
                    except OSError as e:
                        errors.append(f"删除文件夹 {d}: {e}")

            # 删除文件
            for f in self.plugin_cfg.get("uninstall_files", []):
                target = os.path.join(self.vtube_dir, f)
                if os.path.isfile(target):
                    try:
                        os.remove(target)
                    except OSError as e:
                        errors.append(f"删除文件 {f}: {e}")

            if errors:
                self.finished.emit(False,
                    f"{self.plugin_name} 部分卸载完成，但有错误:\n" +
                    "\n".join(errors))
            else:
                self.finished.emit(True,
                    f"{self.plugin_name} 已卸载。")
        except Exception as e:
            self.finished.emit(False, str(e))


# ── 日志窗口 ─────────────────────────────────────────

class LogWindow(QDialog):
    def __init__(self, title: str, messages: list[str], parent=None):
        super().__init__(parent)
        self.setWindowTitle(f"{title} - 日志")
        self.setMinimumSize(520, 360)
        self.setStyleSheet("QDialog { background: #1e1e1e; }")

        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 12, 12, 12)

        self._text = QTextEdit()
        self._text.setReadOnly(True)
        self._text.setFont(QFont("Consolas", 10))
        self._text.setStyleSheet("""
            QTextEdit {
                background: #0c0c0c; color: #0f0;
                border: 1px solid #505050; border-radius: 6px;
                padding: 8px;
            }
        """)
        layout.addWidget(self._text)

        for msg in messages:
            self._text.append(msg)

        close_btn = QPushButton("关闭")
        close_btn.setStyleSheet("""
            QPushButton {
                background: #3a3a3a; color: #ccc; border: 1px solid #505050;
                border-radius: 5px; padding: 6px 24px; font-size: 12px;
            }
            QPushButton:hover { background: #4a4a4a; }
        """)
        close_btn.clicked.connect(self.close)
        layout.addWidget(close_btn, alignment=Qt.AlignRight)

    def append(self, msg: str):
        self._text.append(msg)


# ── 插件管理窗口 ──────────────────────────────────────

class PluginManagerDialog(QDialog):
    def __init__(self, vtube_exe_path: str, parent=None):
        super().__init__(parent)
        self.vtube_exe_path = vtube_exe_path
        self._vtube_dir = os.path.dirname(vtube_exe_path) if vtube_exe_path else ""
        self._workers = []
        self._install_buttons: dict[str, QPushButton] = {}
        self._installed: dict[str, bool] = {}

        self.setWindowTitle("VTube Studio 插件管理")
        self.setMinimumSize(680, 300)
        self.setStyleSheet("QDialog { background: #1e1e1e; }")

        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(12)

        title = QLabel("VTube Studio 插件管理")
        title.setFont(QFont("Microsoft YaHei UI", 14))
        title.setStyleSheet("color: #ccc; font-weight: bold;")
        layout.addWidget(title)

        note = QLabel("安装插件框架后，可将第三方插件放入 BepInEx/plugins 目录")
        note.setStyleSheet("color: #777; font-size: 11px;")
        layout.addWidget(note)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setStyleSheet("QScrollArea { border: none; background: transparent; }")

        container = QWidget()
        container.setStyleSheet("background: transparent;")
        cl = QVBoxLayout(container)
        cl.setContentsMargins(0, 0, 0, 0)
        cl.setSpacing(8)

        for p in PLUGIN_LIST:
            cl.addWidget(self._make_row(p))

        cl.addStretch()
        scroll.setWidget(container)
        layout.addWidget(scroll, 1)

        self._check_install_status()

    def _make_row(self, p):
        frame = QFrame()
        frame.setStyleSheet("QFrame { background: #252526; border-radius: 8px; }")
        row = QHBoxLayout(frame)
        row.setContentsMargins(16, 10, 16, 10)
        row.setSpacing(12)

        name = QLabel(p["name"])
        name.setFont(QFont("Microsoft YaHei UI", 12))
        name.setStyleSheet("color: #ccc; font-weight: bold;")
        name.setFixedWidth(110)
        row.addWidget(name)

        combo = QComboBox()
        combo.addItem(p["version"])
        combo.setFixedWidth(90)
        combo.setStyleSheet("QComboBox { background: #3a3a3a; color: #ccc; border: 1px solid #505050; border-radius: 4px; padding: 4px 8px; font-size: 11px; } QComboBox:hover { background: #4a4a4a; } QComboBox::drop-down { border: none; width: 20px; } QComboBox QAbstractItemView { background: #2d2d2d; color: #ccc; selection-background-color: #0078d4; }")
        row.addWidget(combo)

        desc = QLabel(p["description"])
        desc.setStyleSheet("color: #999; font-size: 11px;")
        desc.setWordWrap(True)
        row.addWidget(desc, 1)

        btn = QPushButton("安装")
        btn.setFixedWidth(64)
        btn.setStyleSheet("QPushButton { background: #0078d4; color: #fff; border: none; border-radius: 5px; padding: 6px 18px; font-size: 12px; font-weight: bold; } QPushButton:hover { background: #1a8fe3; } QPushButton:disabled { background: #555; color: #999; }")
        btn.clicked.connect(lambda *, p=p, b=btn: self._on_btn_clicked(p, b))
        row.addWidget(btn)

        self._install_buttons[p["name"]] = btn
        return frame

    # ── 安装状态检测 ─────────────────────────────────

    def _check_install_status(self):
        for p in PLUGIN_LIST:
            installed = False
            if self._vtube_dir:
                detect_dir = p.get("detect_dir", "")
                detect_file = p.get("detect_file", "")
                if detect_dir:
                    installed = os.path.isdir(
                        os.path.join(self._vtube_dir, detect_dir))
                elif detect_file:
                    installed = os.path.isfile(
                        os.path.join(self._vtube_dir, detect_file))
            self._installed[p["name"]] = installed
            self._update_button(p["name"])

    def _update_button(self, name: str):
        btn = self._install_buttons.get(name)
        if not btn:
            return
        if self._installed.get(name):
            btn.setText("卸载")
            btn.setStyleSheet("QPushButton { background: #c0392b; color: #fff; border: none; border-radius: 5px; padding: 6px 18px; font-size: 12px; font-weight: bold; } QPushButton:hover { background: #e74c3c; } QPushButton:disabled { background: #555; color: #999; }")
        else:
            btn.setText("安装")
            btn.setStyleSheet("QPushButton { background: #0078d4; color: #fff; border: none; border-radius: 5px; padding: 6px 18px; font-size: 12px; font-weight: bold; } QPushButton:hover { background: #1a8fe3; } QPushButton:disabled { background: #555; color: #999; }")

    def _on_btn_clicked(self, p, btn):
        if self._installed.get(p["name"]):
            self._uninstall(p, btn)
        else:
            self._install(p, btn)

    def _install(self, p, btn):
        if not self.vtube_exe_path:
            QMessageBox.warning(self, "错误", "未找到 VTube Studio 路径")
            return
        btn.setEnabled(False)
        btn.setText("下载中")
        w = PluginInstallWorker(p, self.vtube_exe_path)
        w.finished.connect(lambda ok, msg, p=p: self._done(p, ok, msg))
        self._workers.append(w)
        w.start()

    def _done(self, p, success, message):
        name = p["name"]
        btn = self._install_buttons.get(name)
        if btn:
            btn.setEnabled(True)
            btn.setText("安装")
        if success:
            QMessageBox.information(self, "安装完成", message)
            self._installed[name] = True
            self._update_button(name)
        else:
            QMessageBox.critical(self, "安装失败", f"{name} 安装失败:\n{message}")

    def _uninstall(self, p, btn):
        if not self._vtube_dir:
            QMessageBox.warning(self, "错误", "未找到 VTube Studio 目录")
            return
        name = p["name"]
        reply = QMessageBox.question(
            self, "确认卸载",
            f"确定要卸载 {name} 吗？\n将删除 VTube Studio 目录中的相关文件和文件夹。",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No,
        )
        if reply != QMessageBox.Yes:
            return
        btn.setEnabled(False)
        btn.setText("卸载中")
        w = PluginUninstallWorker(name, p, self._vtube_dir)
        w.finished.connect(
            lambda ok, msg, p=p, name=name: self._uninstall_done(name, p, ok, msg)
        )
        self._workers.append(w)
        w.start()

    def _uninstall_done(self, name, p, success, message):
        btn = self._install_buttons.get(name)
        if btn:
            btn.setEnabled(True)
        if success:
            self._installed[name] = False
            self._update_button(name)
            QMessageBox.information(self, "卸载完成", message)
        else:
            self._update_button(name)
            QMessageBox.critical(self, "卸载失败", f"{name} 卸载失败:\n{message}")


# ── VTuber Tools 卡片 ─────────────────────────────────

class VToolCard(QWidget):

    def __init__(self, tool_name: str,
                 valid_exe_names: list[str] | None = None,
                 install_handler=None,
                 download_config: DownloadConfig | None = None,
                 parent=None):
        super().__init__(parent)
        self.tool_name = tool_name
        self.valid_exe_names = valid_exe_names or []
        self._install_handler = install_handler
        self._download_config = download_config
        self._exe_path = ""
        self._local_version = ""
        self._installed = False
        self._search_worker: SearchWorker | None = None
        self._log_messages: list[str] = []
        self._log_window: LogWindow | None = None

        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 4, 0, 4)

        frame = QFrame()
        frame.setObjectName("vt_card")
        frame.setStyleSheet(STYLE_CARD)
        outer.addWidget(frame)

        layout = QVBoxLayout(frame)
        layout.setContentsMargins(16, 12, 16, 12)
        layout.setSpacing(8)

        # ── 标题行（工具名 + ▼ 下拉菜单）──
        title_row = QHBoxLayout()
        title_row.setSpacing(6)

        self._title_btn = QToolButton()
        self._title_btn.setText(tool_name)
        self._title_btn.setToolButtonStyle(Qt.ToolButtonTextOnly)
        self._title_btn.setPopupMode(QToolButton.MenuButtonPopup)
        self._title_btn.setFont(QFont("Microsoft YaHei UI", 11))
        self._title_btn.setStyleSheet("""
            QToolButton {
                color: #ccc; font-weight: bold; border: none; background: transparent;
                padding: 0px;
            }
            QToolButton::menu-indicator { image: none; width: 10px; }
            QToolButton::menu-button { border: none; width: 14px; }
        """)

        title_menu = QMenu(self._title_btn)
        title_menu.setStyleSheet("""
            QMenu { background: #2d2d30; color: #ccc; border: 1px solid #505050; padding: 4px; }
            QMenu::item { padding: 6px 28px 6px 16px; }
            QMenu::item:selected { background: #0078d4; }
        """)
        act_log = QAction("日志", title_menu)
        act_log.triggered.connect(self._show_log)
        title_menu.addAction(act_log)
        self._title_btn.setMenu(title_menu)

        title_row.addWidget(self._title_btn)
        title_row.addStretch()

        self._version_label = QLabel("")
        self._version_label.setStyleSheet("color: #666; font-size: 11px;")
        title_row.addWidget(self._version_label)

        layout.addLayout(title_row)

        # ── 路径行（地址 + 打开按钮）──
        path_row = QHBoxLayout()
        path_row.setSpacing(8)

        self._path_label = QLabel("未找到")
        self._path_label.setFont(QFont("Consolas", 10))
        self._path_label.setStyleSheet(STYLE_PATH_NOT_FOUND)
        self._path_label.setWordWrap(True)
        self._path_label.setMinimumWidth(300)

        self._btn_open_folder = QPushButton("打开")
        self._btn_open_folder.setFixedWidth(44)
        self._btn_open_folder.setStyleSheet("""
            QPushButton {
                background: #3a3a3a; color: #999; border: 1px solid #505050;
                border-radius: 4px; padding: 4px 0px; font-size: 11px;
            }
            QPushButton:hover { background: #4a4a4a; color: #ccc; }
            QPushButton:disabled { background: #333; color: #555; }
        """)
        self._btn_open_folder.setEnabled(False)
        self._btn_open_folder.clicked.connect(self._open_folder)

        path_row.addWidget(self._path_label)
        path_row.addWidget(self._btn_open_folder)
        layout.addLayout(path_row)

        # 按钮行
        btn_col = QHBoxLayout()
        btn_col.setSpacing(8)

        self._btn_search = QPushButton("自动搜索")
        self._btn_search.setStyleSheet(STYLE_BTN_SEARCH)
        self._btn_search.clicked.connect(self._on_auto_search)

        self._btn_browse = QPushButton("手动查找")
        self._btn_browse.setStyleSheet(STYLE_BTN_BROWSE)
        self._btn_browse.clicked.connect(self._on_browse)

        self._btn_install = QPushButton("安装")
        self._btn_install.setStyleSheet(STYLE_BTN_INSTALL)
        self._btn_install.clicked.connect(self._on_install)

        self._btn_launch = QToolButton()
        self._btn_launch.setText("启动")
        self._btn_launch.setToolButtonStyle(Qt.ToolButtonTextOnly)
        self._btn_launch.setStyleSheet(STYLE_BTN_LAUNCH)
        self._btn_launch.setEnabled(False)
        self._btn_launch.clicked.connect(self._on_launch)

        # VTube Studio 专属
        self._launch_mode = "default"
        self._watermark_mode = "proxy"
        self._webcam_mode = "silent"
        self._btn_watermark = None
        self._btn_webcam = None
        self._btn_plugins = None
        self._btn_spout2 = None
        self._btn_ndi = None
        self._ndi_options = {"distroav": True, "ndi_runtime": False, "ndi_tools": False}
        self._watermark_worker: WatermarkWorker | None = None
        self._spout2_worker: Spout2Worker | None = None
        self._ndi_worker: NDIWorker | None = None
        self._spout2_mode = "zip"
        if tool_name == "VTube Studio":
            self._launch_mode = "steam"
            self._setup_vtube_launch_menu()
            self._btn_watermark = QToolButton()
            self._btn_watermark.setText("移除水印")
            self._btn_watermark.setToolButtonStyle(Qt.ToolButtonTextOnly)
            self._btn_watermark.setStyleSheet(STYLE_BTN_WATERMARK)
            self._btn_watermark.clicked.connect(self._on_remove_watermark)
            self._setup_watermark_menu()

            self._btn_webcam = QToolButton()
            self._btn_webcam.setText("安装虚拟摄像头")
            self._btn_webcam.setToolButtonStyle(Qt.ToolButtonTextOnly)
            self._btn_webcam.setStyleSheet(STYLE_BTN_WEBCAM)
            self._btn_webcam.clicked.connect(self._on_install_webcam)
            self._setup_webcam_menu()

            self._btn_plugins = QPushButton("插件管理")
            self._btn_plugins.setStyleSheet(
                "QPushButton { background: #3a3a3a; color: #ccc; border: 1px solid #505050;"
                " border-radius: 5px; padding: 6px 18px; font-size: 12px; font-weight: bold; }"
                " QPushButton:hover { background: #4a4a4a; }"
            )
            self._btn_plugins.clicked.connect(self._on_manage_plugins)

        # OBS Studio 专属：安装 Spout2
        if tool_name == "OBS Studio":
            self._btn_spout2 = QToolButton()
            self._btn_spout2.setText("安装Spout2")
            self._btn_spout2.setToolButtonStyle(Qt.ToolButtonTextOnly)
            self._btn_spout2.setStyleSheet(STYLE_BTN_SPOUT2)
            self._btn_spout2.setEnabled(False)
            self._btn_spout2.clicked.connect(self._on_install_spout2)
            self._setup_spout2_menu()

            self._btn_ndi = QToolButton()
            self._btn_ndi.setText("安装NDI")
            self._btn_ndi.setToolButtonStyle(Qt.ToolButtonTextOnly)
            self._btn_ndi.setStyleSheet(STYLE_BTN_NDI)
            self._btn_ndi.setEnabled(False)
            self._btn_ndi.clicked.connect(self._on_install_ndi)
            self._setup_ndi_menu()

        btn_col.addWidget(self._btn_search)
        btn_col.addWidget(self._btn_browse)
        btn_col.addWidget(self._btn_install)
        btn_col.addWidget(self._btn_launch)
        if self._btn_watermark:
            btn_col.addWidget(self._btn_watermark)
        if self._btn_webcam:
            btn_col.addWidget(self._btn_webcam)
        if self._btn_plugins:
            btn_col.addWidget(self._btn_plugins)
        if self._btn_spout2:
            btn_col.addWidget(self._btn_spout2)
        if self._btn_ndi:
            btn_col.addWidget(self._btn_ndi)
        btn_col.addStretch()
        layout.addLayout(btn_col)

    # ── 自动搜索 ──────────────────────────────────────

    def _log(self, msg: str):
        self._log_messages.append(msg)
        if self._log_window and self._log_window.isVisible():
            self._log_window.append(msg)

    def _on_auto_search(self):
        self._log(f"[搜索] {self.tool_name} 开始自动搜索...")
        self._btn_search.setEnabled(False)
        self._btn_search.setText("搜索中...")
        self._search_worker = SearchWorker(self.tool_name)
        self._search_worker.result.connect(self._on_search_result)
        self._search_worker.start()

    def _on_search_result(self, tool_name: str, path: str):
        self._btn_search.setEnabled(True)
        self._btn_search.setText("自动搜索")
        if path:
            self._exe_path = path
            self._installed = True
            self._path_label.setText(path)
            self._path_label.setStyleSheet(STYLE_PATH_FOUND)
            self._btn_install.setText("已安装")
            self._btn_install.setStyleSheet(STYLE_BTN_INSTALLED)
            self._btn_install.setEnabled(False)
            self._btn_launch.setEnabled(True)
            self._btn_open_folder.setEnabled(True)
            if self._btn_webcam:
                self._btn_webcam.setEnabled(True)
            if self._btn_spout2:
                self._btn_spout2.setEnabled(True)
            if self._btn_ndi:
                self._btn_ndi.setEnabled(True)
            if self.tool_name == "VTube Studio":
                self._refresh_launch_menu()
            self._log(f"[搜索] {tool_name} 找到: {path}")
        else:
            self._path_label.setText("未找到")
            self._path_label.setStyleSheet(STYLE_PATH_NOT_FOUND)
            self._btn_launch.setEnabled(False)
            self._btn_open_folder.setEnabled(False)
            if self._btn_webcam:
                self._btn_webcam.setEnabled(False)
            if self._btn_spout2:
                self._btn_spout2.setEnabled(False)
            if self._btn_ndi:
                self._btn_ndi.setEnabled(False)
            self._log(f"[搜索] {tool_name} 未找到")
        self._update_version()

    # ── 手动查找 ──────────────────────────────────────

    def _on_browse(self):
        self._log(f"[浏览] {self.tool_name} 打开文件选择...")
        file_path, _ = QFileDialog.getOpenFileName(
            self, f"定位 {self.tool_name} 可执行文件",
            "C:\\Program Files",
            "可执行文件 (*.exe);;所有文件 (*.*)",
        )
        if not file_path or not os.path.isfile(file_path):
            self._log(f"[浏览] {self.tool_name} 用户取消")
            return

        if self.valid_exe_names:
            fname = os.path.basename(file_path)
            if fname.lower() not in [n.lower() for n in self.valid_exe_names]:
                expected = " / ".join(self.valid_exe_names)
                self._log(f"[浏览] {self.tool_name} 文件名不匹配: {fname} (预期 {expected})")
                QMessageBox.warning(
                    self, "文件名不匹配",
                    f"选择的文件「{fname}」与 {self.tool_name} 预期不符。\n"
                    f"预期文件名: {expected}",
                )
                return

        self._exe_path = file_path
        self._installed = True
        self._path_label.setText(file_path)
        self._path_label.setStyleSheet(STYLE_PATH_FOUND)
        self._btn_install.setText("已安装")
        self._btn_install.setStyleSheet(STYLE_BTN_INSTALLED)
        self._btn_install.setEnabled(False)
        self._btn_launch.setEnabled(True)
        self._btn_open_folder.setEnabled(True)
        if self._btn_webcam:
            self._btn_webcam.setEnabled(True)
        if self._btn_spout2:
            self._btn_spout2.setEnabled(True)
        if self._btn_ndi:
            self._btn_ndi.setEnabled(True)
        if self.tool_name == "VTube Studio":
            self._refresh_launch_menu()
        self._log(f"[浏览] {self.tool_name} 手动定位: {file_path}")
        self._update_version()

    # ── 安装 ──────────────────────────────────────────

    def _on_install(self):
        if self._install_handler:
            self._log(f"[安装] {self.tool_name} 触发安装（当前版本: {self._local_version or '未知'}）")
            self._install_handler(self.tool_name)

    def _on_launch(self):
        if not self._exe_path or not os.path.isfile(self._exe_path):
            return
        self._log(f"[启动] {self.tool_name} 启动: {self._exe_path}")
        if self._launch_mode == "steam":
            webbrowser.open("steam://rungameid/1325860")
        elif self._launch_mode == "nosteam":
            exe_dir = os.path.dirname(self._exe_path)
            subprocess.Popen(
                ["cmd", "/c", "start", "", "VTube Studio.exe", "-nosteam"],
                cwd=exe_dir,
                creationflags=subprocess.CREATE_NO_WINDOW,
            )
        elif self._launch_mode == "nosteam_nobili":
            exe_dir = os.path.dirname(self._exe_path)
            bat_path = os.path.join(
                exe_dir, "启动VTS_不通过Steam_不接收B站数据.bat")
            subprocess.Popen(
                ["cmd", "/c", "start", "", bat_path],
                cwd=exe_dir,
                creationflags=subprocess.CREATE_NO_WINDOW,
            )
        else:
            subprocess.Popen(
                ["cmd", "/c", "start", "", self._exe_path],
                cwd=os.path.dirname(self._exe_path),
                creationflags=subprocess.CREATE_NO_WINDOW,
            )

    def _setup_vtube_launch_menu(self):
        menu = QMenu(self._btn_launch)
        menu.setStyleSheet("""
            QMenu { background: #2d2d30; color: #ccc; border: 1px solid #505050; padding: 4px; }
            QMenu::item { padding: 6px 28px 6px 16px; }
            QMenu::item:selected { background: #0078d4; }
            QMenu::separator { height: 1px; background: #505050; margin: 3px 8px; }
        """)

        group = QActionGroup(menu)
        group.setExclusive(True)

        self._act_launch_default = QAction("默认 (cmd start)", menu)
        self._act_launch_default.setCheckable(True)
        self._act_launch_default.triggered.connect(
            lambda: setattr(self, '_launch_mode', 'default'))
        group.addAction(self._act_launch_default)
        menu.addAction(self._act_launch_default)

        act_steam = QAction("Steam 原生启动", menu)
        act_steam.setCheckable(True)
        act_steam.setChecked(True)
        act_steam.triggered.connect(lambda: setattr(self, '_launch_mode', 'steam'))
        group.addAction(act_steam)
        menu.addAction(act_steam)

        act_nosteam = QAction("免 Steam 启动 (-nosteam)", menu)
        act_nosteam.setCheckable(True)
        act_nosteam.triggered.connect(lambda: setattr(self, '_launch_mode', 'nosteam'))
        group.addAction(act_nosteam)
        menu.addAction(act_nosteam)

        self._act_launch_nosteam_nobili = QAction(
            "免 Steam + 不接收B站数据启动", menu)
        self._act_launch_nosteam_nobili.setCheckable(True)
        self._act_launch_nosteam_nobili.setVisible(False)
        self._act_launch_nosteam_nobili.triggered.connect(
            lambda: setattr(self, '_launch_mode', 'nosteam_nobili'))
        group.addAction(self._act_launch_nosteam_nobili)
        menu.addAction(self._act_launch_nosteam_nobili)

        self._launch_menu = menu
        self._btn_launch.setMenu(menu)
        self._btn_launch.setPopupMode(QToolButton.MenuButtonPopup)
        self._btn_launch.setStyleSheet(self._btn_launch.styleSheet() + """
            QToolButton::menu-button { border: none; width: 16px; }
        """)

    def _refresh_launch_menu(self):
        """根据 VTube Studio 目录状态更新启动菜单选项"""
        if self.tool_name != "VTube Studio" or not self._exe_path:
            return
        vtube_dir = os.path.dirname(self._exe_path)

        # BepInEx 存在时禁用 cmd start，若当前选中则自动切回 steam
        has_bepinex = os.path.isdir(os.path.join(vtube_dir, "BepInEx"))
        self._act_launch_default.setEnabled(not has_bepinex)
        if has_bepinex and self._launch_mode == "default":
            self._launch_mode = "steam"

        # 存在不接收B站数据启动 bat 时显示对应选项
        nobili_bat = os.path.join(vtube_dir,
                                   "启动VTS_不通过Steam_不接收B站数据.bat")
        has_nobili = os.path.isfile(nobili_bat)
        self._act_launch_nosteam_nobili.setVisible(has_nobili)

    # ── 移除水印 ──────────────────────────────────────

    def _setup_watermark_menu(self):
        menu = QMenu(self._btn_watermark)
        menu.setStyleSheet("""
            QMenu { background: #2d2d30; color: #ccc; border: 1px solid #505050; padding: 4px; }
            QMenu::item { padding: 6px 28px 6px 16px; }
            QMenu::item:selected { background: #0078d4; }
            QMenu::separator { height: 1px; background: #505050; margin: 3px 8px; }
        """)

        group = QActionGroup(menu)
        group.setExclusive(True)

        act_proxy = QAction("代理模式（替换 steam_api.dll）", menu)
        act_proxy.setCheckable(True)
        act_proxy.setChecked(True)
        act_proxy.triggered.connect(lambda: setattr(self, '_watermark_mode', 'proxy'))
        group.addAction(act_proxy)
        menu.addAction(act_proxy)

        act_selfhook = QAction("自挂模式（version/winhttp/winmm）", menu)
        act_selfhook.setCheckable(True)
        act_selfhook.triggered.connect(lambda: setattr(self, '_watermark_mode', 'selfhook'))
        group.addAction(act_selfhook)
        menu.addAction(act_selfhook)

        act_koa = QAction("Koaloader 钩子模式", menu)
        act_koa.setCheckable(True)
        act_koa.triggered.connect(lambda: setattr(self, '_watermark_mode', 'koaloader'))
        group.addAction(act_koa)
        menu.addAction(act_koa)

        self._btn_watermark.setMenu(menu)
        self._btn_watermark.setPopupMode(QToolButton.MenuButtonPopup)
        self._btn_watermark.setStyleSheet(self._btn_watermark.styleSheet() + """
            QToolButton::menu-button { border: none; width: 16px; }
        """)

    # ── 安装虚拟摄像头 ────────────────────────────────

    def _setup_webcam_menu(self):
        menu = QMenu(self._btn_webcam)
        menu.setStyleSheet("""
            QMenu { background: #2d2d30; color: #ccc; border: 1px solid #505050; padding: 4px; }
            QMenu::item { padding: 6px 28px 6px 16px; }
            QMenu::item:selected { background: #0078d4; }
            QMenu::separator { height: 1px; background: #505050; margin: 3px 8px; }
        """)

        group = QActionGroup(menu)
        group.setExclusive(True)

        act_silent = QAction("静默安装", menu)
        act_silent.setCheckable(True)
        act_silent.setChecked(True)
        act_silent.triggered.connect(lambda: setattr(self, '_webcam_mode', 'silent'))
        group.addAction(act_silent)
        menu.addAction(act_silent)

        act_interactive = QAction("交互式安装", menu)
        act_interactive.setCheckable(True)
        act_interactive.triggered.connect(lambda: setattr(self, '_webcam_mode', 'interactive'))
        group.addAction(act_interactive)
        menu.addAction(act_interactive)

        self._btn_webcam.setMenu(menu)
        self._btn_webcam.setPopupMode(QToolButton.MenuButtonPopup)
        self._btn_webcam.setStyleSheet(self._btn_webcam.styleSheet() + """
            QToolButton::menu-button { border: none; width: 16px; }
        """)

    def _on_install_webcam(self):
        if not self._exe_path or not os.path.isfile(self._exe_path):
            return
        exe_dir = os.path.dirname(self._exe_path)
        if self._webcam_mode == "interactive":
            bat_name = "Install.bat"
        else:
            bat_name = "Install_Silent.bat"
        bat_path = os.path.join(exe_dir, "VTube Studio_Data", "Install_Webcam", bat_name)
        if not os.path.isfile(bat_path):
            QMessageBox.warning(self, "文件不存在", f"未找到安装脚本：\n{bat_path}")
            return
        subprocess.Popen(
            ["powershell", "-Command", f"Start-Process -FilePath '{bat_path}' -Verb RunAs"],
            cwd=exe_dir,
            creationflags=subprocess.CREATE_NO_WINDOW,
        )

    # ── 安装 Spout2 ───────────────────────────────────

    def _setup_spout2_menu(self):
        menu = QMenu(self._btn_spout2)
        menu.setStyleSheet("""
            QMenu { background: #2d2d30; color: #ccc; border: 1px solid #505050; padding: 4px; }
            QMenu::item { padding: 6px 28px 6px 16px; }
            QMenu::item:selected { background: #0078d4; }
            QMenu::separator { height: 1px; background: #505050; margin: 3px 8px; }
        """)

        group = QActionGroup(menu)
        group.setExclusive(True)

        act_zip = QAction("ZIP模式", menu)
        act_zip.setCheckable(True)
        act_zip.setChecked(True)
        act_zip.triggered.connect(lambda: setattr(self, '_spout2_mode', 'zip'))
        group.addAction(act_zip)
        menu.addAction(act_zip)

        act_exe = QAction("EXE模式", menu)
        act_exe.setCheckable(True)
        act_exe.triggered.connect(lambda: setattr(self, '_spout2_mode', 'exe'))
        group.addAction(act_exe)
        menu.addAction(act_exe)

        self._btn_spout2.setMenu(menu)
        self._btn_spout2.setPopupMode(QToolButton.MenuButtonPopup)
        self._btn_spout2.setStyleSheet(self._btn_spout2.styleSheet() + """
            QToolButton::menu-button { border: none; width: 16px; }
        """)

    def _on_install_spout2(self):
        if not self._exe_path or not os.path.isfile(self._exe_path):
            QMessageBox.warning(self, "未找到", "请先定位 OBS Studio 安装目录。")
            return
        if self._spout2_worker and self._spout2_worker.isRunning():
            return

        # 判断 OBS 版本，选择对应 Spout2 版本
        is_new = False
        try:
            parts = self._local_version.split(".")
            if parts:
                major = int(parts[0])
                if major >= 31:
                    is_new = True
        except (ValueError, IndexError):
            pass

        ver_key = "new" if is_new else "old"
        mode_key = "zip" if self._spout2_mode == "zip" else "exe"
        url = SPOUT2_URLS[ver_key][mode_key]
        ver_label = "1.9.0" if is_new else "1.8"
        mode_desc = {"zip": "ZIP模式", "exe": "EXE模式"}
        self._log_messages.clear()
        self._log_messages.append(
            f"开始安装 Spout2 v{ver_label} — {mode_desc.get(self._spout2_mode, self._spout2_mode)}"
        )

        if self._btn_spout2:
            self._btn_spout2.setEnabled(False)

        self._spout2_worker = Spout2Worker(
            self._spout2_mode, url, self._exe_path, is_new,
        )
        self._spout2_worker.progress.connect(self._on_spout2_progress)
        self._spout2_worker.status.connect(self._on_spout2_status)
        self._spout2_worker.finished.connect(self._on_spout2_done)
        self._spout2_worker.start()

    def _on_spout2_progress(self, msg: str):
        self._log_messages.append(msg)
        if self._log_window and self._log_window.isVisible():
            self._log_window.append(msg)

    def _on_spout2_status(self, msg: str):
        if self._btn_spout2:
            self._btn_spout2.setText(msg)

    def _on_spout2_done(self, success: bool, msg: str):
        self._log_messages.append(msg)
        if self._log_window and self._log_window.isVisible():
            self._log_window.append(msg)
        if self._btn_spout2:
            self._btn_spout2.setEnabled(True)
            self._btn_spout2.setText("安装Spout2")
        if success:
            QMessageBox.information(self, "完成", msg)
        else:
            QMessageBox.warning(self, "安装失败", msg)

    # ── NDI 安装 ──────────────────────────────────────

    def _setup_ndi_menu(self):
        menu = QMenu(self._btn_ndi)
        menu.setStyleSheet("""
            QMenu { background: #2d2d30; color: #ccc; border: 1px solid #505050; padding: 4px; }
            QMenu::item { padding: 6px 28px 6px 16px; }
            QMenu::item:selected { background: #0078d4; }
            QMenu::separator { height: 1px; background: #505050; margin: 3px 8px; }
        """)

        self._act_ndi_distroav = QAction("安装 DistroAV", menu)
        self._act_ndi_distroav.setCheckable(True)
        self._act_ndi_distroav.setChecked(self._ndi_options["distroav"])
        self._act_ndi_distroav.triggered.connect(
            lambda: self._ndi_options.update({"distroav": self._act_ndi_distroav.isChecked()}))
        menu.addAction(self._act_ndi_distroav)

        self._act_ndi_runtime = QAction("安装 NDI 运行时", menu)
        self._act_ndi_runtime.setCheckable(True)
        self._act_ndi_runtime.setChecked(self._ndi_options["ndi_runtime"])
        self._act_ndi_runtime.triggered.connect(
            lambda: self._ndi_options.update({"ndi_runtime": self._act_ndi_runtime.isChecked()}))
        menu.addAction(self._act_ndi_runtime)

        self._act_ndi_tools = QAction("安装 NDI 工具", menu)
        self._act_ndi_tools.setCheckable(True)
        self._act_ndi_tools.setChecked(self._ndi_options["ndi_tools"])
        self._act_ndi_tools.triggered.connect(
            lambda: self._ndi_options.update({"ndi_tools": self._act_ndi_tools.isChecked()}))
        menu.addAction(self._act_ndi_tools)

        self._btn_ndi.setMenu(menu)
        self._btn_ndi.setPopupMode(QToolButton.MenuButtonPopup)
        self._btn_ndi.setStyleSheet(self._btn_ndi.styleSheet() + """
            QToolButton::menu-button { border: none; width: 16px; }
        """)

    def _on_install_ndi(self):
        if self._ndi_worker and self._ndi_worker.isRunning():
            return

        cmds = []
        if self._ndi_options["distroav"]:
            cmds.append(("DistroAV", ["winget", "install", "--exact", "--id", "DistroAV.DistroAV"]))
        if self._ndi_options["ndi_runtime"]:
            cmds.append(("NDI 运行时", ["winget", "install", "--exact", "--id", "NDI.NDIRuntime"]))
        if self._ndi_options["ndi_tools"]:
            cmds.append(("NDI 工具", ["winget", "install", "--exact", "--id", "NDI.NDITools"]))

        if not cmds:
            QMessageBox.information(self, "提示", "请至少勾选一项安装内容。")
            return

        self._ndi_worker = NDIWorker(cmds)
        self._ndi_worker.status.connect(self._on_ndi_status)
        self._ndi_worker.finished.connect(self._on_ndi_done)
        self._ndi_worker.start()
        if self._btn_ndi:
            self._btn_ndi.setEnabled(False)

    def _on_ndi_status(self, msg: str):
        if self._btn_ndi:
            self._btn_ndi.setText(msg)

    def _on_ndi_done(self, success: bool, msg: str):
        if self._btn_ndi:
            self._btn_ndi.setEnabled(True)
            self._btn_ndi.setText("安装NDI")
        if success:
            QMessageBox.information(self, "完成", msg)
        else:
            QMessageBox.warning(self, "安装失败", msg)

    # ── 代理检测 ──────────────────────────────────────

    def _handle_proxy_detected(self, backup_path: str) -> bool:
        """检测到 steam_api64_o.dll 时的三按钮处理。始终返回 False 中断去水印流程。"""
        dll_dir = os.path.dirname(backup_path)
        steam_dll = os.path.join(dll_dir, "steam_api64.dll")

        msg = QMessageBox(self)
        msg.setWindowTitle("检测到代理模式残留")
        msg.setText(
            "检测到 steam_api64_o.dll，可能已经执行过代理模式。\n\n"
            "请前往 Steam 找到 VTube Studio，右键属性 → 已安装文件 →\n"
            "验证软件文件的完整性。"
        )
        msg.setIcon(QMessageBox.Warning)
        btn_restore = msg.addButton("强制还原", QMessageBox.ActionRole)
        btn_verified = msg.addButton("已完成验证", QMessageBox.ActionRole)
        btn_close = msg.addButton("关闭", QMessageBox.RejectRole)
        msg.exec()

        clicked = msg.clickedButton()

        if clicked == btn_restore:
            # 删除 steam_api64.dll，将备份还原
            if os.path.isfile(steam_dll):
                os.remove(steam_dll)
            os.rename(backup_path, steam_dll)
            QMessageBox.information(self, "完成", "已强制还原 steam_api64.dll。")

        elif clicked == btn_verified:
            if os.path.isfile(steam_dll):
                size = os.path.getsize(steam_dll)
                if size > 3 * 1024 * 1024:
                    # 验证未生效，DLL 仍然异常
                    os.remove(steam_dll)
                    os.remove(backup_path)
                    QMessageBox.warning(self, "修复失败",
                        "steam_api64.dll 仍然大于 3 MB，请在 Steam 中重新验证软件文件完整性。")
                else:
                    # 验证成功，DLL 已恢复
                    os.remove(backup_path)
                    QMessageBox.information(self, "修复完成",
                        "验证已完成，可以再次执行去水印了。")
            else:
                if os.path.isfile(backup_path):
                    os.remove(backup_path)
                QMessageBox.information(self, "修复完成",
                    "steam_api64.dll 不存在，备份已清理。可以再次执行去水印了。")

        # 无论如何，代理模式检测命中后不继续流程
        return False

    def _precheck_watermark(self, vtube_dir: str) -> bool:
        """所有去水印方案执行前的残留检测。返回 True 继续，False 中止。"""

        # 1) 代理模式残留：遍历检测 steam_api64_o.dll
        for root, dirs, files in os.walk(vtube_dir):
            for f in files:
                if f.lower() == "steam_api64_o.dll":
                    return self._handle_proxy_detected(os.path.join(root, f))

        # 2) 自挂模式残留：在程序根目录检测
        selfhook_names = {"version.dll", "winhttp.dll", "winmm.dll"}
        selfhook_found = [
            os.path.join(vtube_dir, f)
            for f in os.listdir(vtube_dir)
            if f.lower() in selfhook_names
        ]
        if selfhook_found:
            file_list = "\n".join(
                os.path.basename(p) for p in selfhook_found
            )
            msg = QMessageBox(self)
            msg.setWindowTitle("检测到自挂模式残留")
            msg.setText(
                f"可能已经进行过自挂模式，检测到以下文件：\n{file_list}\n\n"
                f"点击「继续」将删除以上文件。"
            )
            msg.setIcon(QMessageBox.Warning)
            btn_continue = msg.addButton("继续", QMessageBox.AcceptRole)
            btn_cancel = msg.addButton("取消", QMessageBox.RejectRole)
            msg.exec()
            if msg.clickedButton() != btn_continue:
                return False
            for p in selfhook_found:
                os.remove(p)

        # 3) Koaloader 残留：在程序根目录检测
        koaloader_names = {"smoke_api32.dll", "smoke_api64.dll",
                           "d3d11-32.dll", "d3d11-64.dll"}
        koaloader_found = [
            os.path.join(vtube_dir, f)
            for f in os.listdir(vtube_dir)
            if f.lower() in koaloader_names
        ]
        if koaloader_found:
            file_list = "\n".join(
                os.path.basename(p) for p in koaloader_found
            )
            msg = QMessageBox(self)
            msg.setWindowTitle("检测到 Koaloader 模式残留")
            msg.setText(
                f"可能已经执行过 Koaloader 钩子模式，检测到以下文件：\n{file_list}\n\n"
                f"点击「继续」将删除以上文件。"
            )
            msg.setIcon(QMessageBox.Warning)
            btn_continue = msg.addButton("继续", QMessageBox.AcceptRole)
            btn_cancel = msg.addButton("取消", QMessageBox.RejectRole)
            msg.exec()
            if msg.clickedButton() != btn_continue:
                return False
            for p in koaloader_found:
                os.remove(p)

        return True

    def _on_remove_watermark(self):
        if not self._exe_path or not os.path.isfile(self._exe_path):
            QMessageBox.warning(self, "未找到", "请先定位 VTube Studio 安装目录。")
            return
        if self._watermark_worker and self._watermark_worker.isRunning():
            return

        vtube_dir = os.path.dirname(self._exe_path)
        if not self._precheck_watermark(vtube_dir):
            return

        # Koaloader 模式需检测 Windows 安全中心
        if self._watermark_mode == "koaloader":
            r = subprocess.run(
                ["tasklist", "/fi", "IMAGENAME eq MsMpEng.exe"],
                capture_output=True, text=True,
                creationflags=subprocess.CREATE_NO_WINDOW,
            )
            if "MsMpEng.exe" in r.stdout:
                QMessageBox.warning(
                    self, "需要临时禁用实时防护",
                    "检测到 Windows 安全中心正在运行。\n"
                    "Koaloader 的 DLL 可能会被杀毒软件拦截删除。\n\n"
                    "请前往「Windows 安全中心 → 病毒和威胁防护 → 管理设置」\n"
                    "临时关闭「实时保护」，完成后再重新开启。",
                )

        mode_desc = {"proxy": "代理模式", "selfhook": "自挂模式", "koaloader": "Koaloader 钩子模式"}
        self._log_messages.clear()
        self._log_messages.append(f"开始移除水印 — {mode_desc.get(self._watermark_mode, self._watermark_mode)}")

        if self._btn_watermark:
            self._btn_watermark.setEnabled(False)

        self._watermark_worker = WatermarkWorker(
            vtube_dir, self._watermark_mode,
            download_config=self._download_config,
        )
        self._watermark_worker.progress.connect(self._on_watermark_progress)
        self._watermark_worker.status.connect(self._on_watermark_status)
        self._watermark_worker.dialog.connect(self._on_watermark_dialog)
        self._watermark_worker.finished.connect(self._on_watermark_done)
        self._watermark_worker.start()

    def _on_watermark_progress(self, msg: str):
        self._log_messages.append(msg)
        if self._log_window and self._log_window.isVisible():
            self._log_window.append(msg)

    def _on_watermark_status(self, msg: str):
        if self._btn_watermark:
            self._btn_watermark.setText(msg)

    def _on_watermark_dialog(self, title: str, msg: str):
        QMessageBox.warning(self, title, msg)

    def _on_watermark_done(self, success: bool, msg: str):
        self._log_messages.append(msg)
        if self._log_window and self._log_window.isVisible():
            self._log_window.append(msg)
        if self._btn_watermark:
            self._btn_watermark.setEnabled(True)
            self._btn_watermark.setText("移除水印")
        if success:
            QMessageBox.information(self, "完成", msg)

    # ── 公开方法 ──────────────────────────────────────

    def set_path(self, path: str):
        self._exe_path = path
        self._installed = True
        self._path_label.setText(path)
        self._path_label.setStyleSheet(STYLE_PATH_FOUND)
        self._btn_install.setText("已安装")
        self._btn_install.setStyleSheet(STYLE_BTN_INSTALLED)
        self._btn_install.setEnabled(False)
        self._btn_launch.setEnabled(True)
        self._btn_open_folder.setEnabled(True)

    def _open_folder(self):
        if self._exe_path and os.path.isfile(self._exe_path):
            folder = os.path.dirname(self._exe_path)
            subprocess.Popen(
                ["explorer", folder],
                creationflags=subprocess.CREATE_NO_WINDOW,
            )

    def _show_log(self):
        if self._log_window:
            self._log_window.close()
        self._log_window = LogWindow(self.tool_name, self._log_messages, self)
        self._log_window.show()

    def _update_version(self):
        self._local_version = ""
        if not self._exe_path or not os.path.isfile(self._exe_path):
            self._version_label.setText("")
            self._log(f"[版本] {self.tool_name} exe 不存在，跳过版本读取")
            self._check_update()
            return
        try:
            result = subprocess.run(
                ["powershell", "-Command",
                 f"(Get-Item '{self._exe_path}').VersionInfo.FileVersion"],
                capture_output=True, text=True,
                creationflags=subprocess.CREATE_NO_WINDOW,
            )
            ver = result.stdout.strip()
            self._local_version = ver
            self._version_label.setText(ver if ver else "")
            self._log(f"[版本] {self.tool_name} 本地版本: {ver or '(空)'}")
        except Exception as e:
            self._version_label.setText("")
            self._log(f"[版本] {self.tool_name} 读取失败: {e}")
        finally:
            self._check_update()

    def _check_update(self):
        """检测配置中是否有比本地更高的版本，有则按钮变为"更新"。"""
        if not self._local_version or not self._download_config:
            self._log(f"[更新检测] {self.tool_name} 跳过（无本地版本或配置）")
            return
        newer = self._download_config.is_newer_than(self.tool_name, self._local_version)
        latest_cfg = self._download_config.get_latest_direct_version(self.tool_name) or "无"
        if newer:
            self._log(f"[更新检测] {self.tool_name} 有更新: 本地={self._local_version} 最新={latest_cfg}")
            self._btn_install.setText("更新")
            self._btn_install.setStyleSheet(STYLE_BTN_UPDATE)
            self._btn_install.setEnabled(True)
        else:
            self._log(f"[更新检测] {self.tool_name} 已最新: 本地={self._local_version} 配置={latest_cfg}")

    def set_installed(self, success: bool):
        if success:
            self._installed = True
            self._btn_install.setText("已安装")
            self._btn_install.setStyleSheet(STYLE_BTN_INSTALLED)
            self._btn_install.setEnabled(False)
            self._path_label.setStyleSheet(STYLE_PATH_FOUND)
            if self._exe_path and os.path.isfile(self._exe_path):
                self._btn_launch.setEnabled(True)
                if self._btn_webcam:
                    self._btn_webcam.setEnabled(True)
                if self._btn_spout2:
                    self._btn_spout2.setEnabled(True)
                if self._btn_ndi:
                    self._btn_ndi.setEnabled(True)
                self._log(f"[安装] {self.tool_name} 安装完成，exe 存在: {self._exe_path}")
                self._update_version()
            elif self._exe_path:
                # 旧路径无效（更新可能变更了安装目录），回退搜索
                self._log(f"[安装] {self.tool_name} 安装完成，但旧路径无效，重新搜索")
                self._on_auto_search()
            else:
                self._log(f"[安装] {self.tool_name} 安装完成，无已知路径，自动搜索")
                self._on_auto_search()
        else:
            self._log(f"[安装] {self.tool_name} 安装失败")
            self._path_label.setStyleSheet(STYLE_PATH_NOT_FOUND)
            self._btn_install.setText("重试安装")
            self._btn_install.setStyleSheet(STYLE_BTN_INSTALL)
            self._btn_install.setEnabled(True)
            self._btn_launch.setEnabled(False)
            if self._btn_webcam:
                self._btn_webcam.setEnabled(False)
            if self._btn_spout2:
                self._btn_spout2.setEnabled(False)
            if self._btn_ndi:
                self._btn_ndi.setEnabled(False)

    def set_downloading(self, percent: int = 0):
        if percent >= 0:
            self._btn_install.setText(f"下载中 {percent}%")
        else:
            self._btn_install.setText("下载中...")
        self._btn_install.setEnabled(False)
        self._path_label.setText("正在下载...")
        self._path_label.setStyleSheet(STYLE_PATH_INSTALLING)
        self._btn_launch.setEnabled(False)
        if self._btn_webcam:
            self._btn_webcam.setEnabled(False)
        if self._btn_spout2:
            self._btn_spout2.setEnabled(False)
        if self._btn_ndi:
            self._btn_ndi.setEnabled(False)
        self._log(f"[下载] {self.tool_name} {percent}%")

    def set_installing(self):
        self._btn_install.setText("安装中...")
        self._btn_install.setEnabled(False)
        self._path_label.setText("正在安装...")
        self._path_label.setStyleSheet(STYLE_PATH_INSTALLING)
        self._btn_launch.setEnabled(False)
        if self._btn_webcam:
            self._btn_webcam.setEnabled(False)
        if self._btn_spout2:
            self._btn_spout2.setEnabled(False)
        if self._btn_ndi:
            self._btn_ndi.setEnabled(False)
        self._log(f"[安装] {self.tool_name} 正在安装中...")

    def get_path(self) -> str:
        return self._exe_path

    def is_installed(self) -> bool:
        return self._installed

    # ── 插件管理 ──────────────────────────────────────

    def _on_manage_plugins(self):
        """打开插件管理窗口。"""
        exe = self._exe_path
        if not exe:
            QMessageBox.warning(self, "提示", "请先定位 VTube Studio 路径")
            return
        dlg = PluginManagerDialog(exe, self)
        dlg.exec()


# ── VTuber Tools 页面 ─────────────────────────────────

class VtuberToolsPage(QWidget):

    def __init__(self, repo, event_bus, download_config: DownloadConfig | None = None, parent=None):
        super().__init__(parent)
        self._repo = repo
        self._event_bus = event_bus
        self._download_config = download_config
        self._cards: dict[str, VToolCard] = {}

        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(2)

        title = QLabel("VTuber Tools")
        title.setFont(QFont("Microsoft YaHei UI", 18))
        title.setStyleSheet(STYLE_PAGE_TITLE)
        layout.addWidget(title)

        desc = QLabel("VTuber 直播常用工具管理与安装")
        desc.setStyleSheet("color: #888; font-size: 12px; margin-bottom: 4px;")
        layout.addWidget(desc)
        layout.addSpacing(12)

        # Steam
        steam_card = VToolCard(
            "Steam",
            valid_exe_names=VALID_EXE_NAMES["Steam"],
            install_handler=self._install_steam_or_obs,
            download_config=download_config,
        )
        self._cards["Steam"] = steam_card
        layout.addWidget(steam_card)

        # OBS Studio
        obs_card = VToolCard(
            "OBS Studio",
            valid_exe_names=VALID_EXE_NAMES["OBS Studio"],
            install_handler=self._install_steam_or_obs,
            download_config=download_config,
        )
        self._cards["OBS Studio"] = obs_card
        layout.addWidget(obs_card)

        # VTube Studio
        vtube_card = VToolCard(
            "VTube Studio",
            valid_exe_names=VALID_EXE_NAMES["VTube Studio"],
            install_handler=self._install_vtube_studio,
            download_config=download_config,
        )
        self._cards["VTube Studio"] = vtube_card
        layout.addWidget(vtube_card)

        layout.addStretch()

        # 首次进入自动搜索已安装的工具
        for card in self._cards.values():
            card._on_auto_search()

    # ── Steam / OBS 安装 ──────────────────────────────

    def _install_steam_or_obs(self, tool_name: str):
        install_info = {"args": "", "method": "silent", "fallback": "manual"}
        url = None
        source_type = "direct"
        winget_id = ""
        verify = None

        # 优先从下载配置文件读取
        if self._download_config:
            cfg = self._download_config.get(tool_name)
            if cfg:
                install_info = self._download_config.get_install_info(tool_name)
                url = self._download_config.get_latest_url(tool_name)
                winget_id = self._download_config.get_latest_winget_id(tool_name) or ""
                if url:
                    source_type = "direct"
                elif winget_id:
                    source_type = "winget"

        # 回退到 SoftwareRepo
        if not url and not winget_id:
            software = self._repo.get_software(tool_name)
            if not software:
                QMessageBox.warning(self, "未找到", f"软件库中未收录「{tool_name}」。")
                return
            result = self._repo.get_download_url(software)
            if not result:
                QMessageBox.warning(self, "无下载源", f"「{tool_name}」暂无可用的下载源。")
                return
            url, source_type = result
            install_info = self._repo.get_install_info(software)
            verify = self._repo.get_verify(software)
            if source_type == "winget":
                for s in software.get("sources", []):
                    if s.get("type") == "winget":
                        winget_id = s.get("id", "")
                        break

        if not url and not winget_id:
            QMessageBox.warning(self, "无下载源", f"「{tool_name}」暂无可用的下载源。")
            return

        self._event_bus.install_request.emit({
            "name": tool_name,
            "url": url,
            "source_type": source_type,
            "winget_id": winget_id,
            "install_args": install_info["args"],
            "install_method": install_info["method"],
            "fallback": install_info["fallback"],
            "verify": verify,
        })

    # ── VTube Studio 安装 ─────────────────────────────

    def _install_vtube_studio(self, tool_name: str):
        steam_card = self._cards.get("Steam")
        if not steam_card or not steam_card.is_installed():
            QMessageBox.information(
                self, "需要 Steam",
                "VTube Studio 通过 Steam 安装。\n"
                "请先在 Steam 卡片中使用「自动搜索」或「手动查找」定位 Steam，\n"
                "或点击上方 Steam 的「安装」按钮安装 Steam 客户端。",
            )
            return

        steam_path = steam_card.get_path()
        if not steam_path or not os.path.isfile(steam_path):
            QMessageBox.warning(self, "Steam 路径无效", "Steam 路径无效，请重新定位。")
            return

        try:
            webbrowser.open("steam://install/1325860")
        except Exception as e:
            QMessageBox.warning(
                self, "打开失败",
                f"无法调用 Steam 协议安装 VTube Studio。\n错误: {e}",
            )

    # ── 公开方法 ──────────────────────────────────────

    def get_card(self, tool_name: str) -> VToolCard | None:
        return self._cards.get(tool_name)
