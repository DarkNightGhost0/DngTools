"""静默安装引擎 - 尝试静默安装，失败后降级，安装后验证"""

import os
import subprocess
import time
import winreg
from pathlib import Path
from typing import Optional

from PySide6.QtCore import QObject, Signal, QThread


class InstallWorker(QThread):
    """后台安装工作线程"""

    finished = Signal(dict)  # {success, message}

    def __init__(self, file_path: str, args: str, timeout: int = 120):
        super().__init__()
        self.file_path = file_path
        self.args = args
        self.timeout = timeout

    def run(self):
        ext = Path(self.file_path).suffix.lower()

        try:
            if ext in (".exe", ".msi"):
                self._install_exe()
            elif ext == ".msix" or ext == ".msixbundle" or ext == ".appx":
                self._install_msix()
            else:
                # 未知格式，直接打开让用户手动安装
                os.startfile(self.file_path)
                self.finished.emit({
                    "success": True,
                    "message": "已打开安装程序（未知格式，需手动完成）",
                    "need_manual": True,
                })
        except Exception as e:
            self.finished.emit({
                "success": False,
                "message": str(e),
            })

    def _install_exe(self):
        """尝试静默安装 exe/msi"""
        # 构建命令行
        cmd = [self.file_path]
        if self.args:
            # 支持多个参数
            cmd.extend(self.args.split())

        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=self.timeout,
            )

            if result.returncode == 0:
                self.finished.emit({
                    "success": True,
                    "message": "安装完成",
                })
            else:
                # 非零返回码：可能是参数问题，尝试手动打开
                raise subprocess.CalledProcessError(
                    result.returncode, cmd,
                    output=result.stdout,
                    stderr=result.stderr,
                )

        except subprocess.TimeoutExpired:
            # 超时：可能是 GUI 安装程序卡住了
            self.finished.emit({
                "success": False,
                "message": "静默安装超时，请手动完成安装",
                "need_fallback": True,
            })
        except subprocess.CalledProcessError as e:
            self.finished.emit({
                "success": False,
                "message": f"安装程序返回错误码 {e.returncode}",
                "need_fallback": True,
                "stderr": e.stderr or "",
            })

    def _install_msix(self):
        """使用 Add-AppxPackage 安装 msix/appx"""
        try:
            result = subprocess.run(
                ["powershell", "-Command",
                 f"Add-AppxPackage -Path '{self.file_path}'"],
                capture_output=True,
                text=True,
                timeout=self.timeout,
            )
            if result.returncode == 0:
                self.finished.emit({
                    "success": True,
                    "message": "应用包安装完成",
                })
            else:
                self.finished.emit({
                    "success": False,
                    "message": f"安装失败: {result.stderr.strip()}",
                    "need_fallback": True,
                })
        except subprocess.TimeoutExpired:
            self.finished.emit({
                "success": False,
                "message": "安装超时",
                "need_fallback": True,
            })


class SilentInstaller(QObject):
    """静默安装器 - 管理安装队列，处理降级"""

    install_result = Signal(dict)  # {name, success, message}

    # 注册表搜索路径（x64 系统有 WOW6432Node 重定向）
    UNINSTALL_KEYS = [
        r"SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall",
        r"SOFTWARE\WOW6432Node\Microsoft\Windows\CurrentVersion\Uninstall",
    ]

    def __init__(self, parent=None):
        super().__init__(parent)
        self._worker: Optional[InstallWorker] = None
        self._verify_data: Optional[dict] = None

    def install(self, name: str, file_path: str, args: str, method: str, fallback: str, verify: Optional[dict] = None):
        """
        开始安装。

        Args:
            name: 软件名
            file_path: 安装程序路径
            args: 静默安装参数（如 /S /D=...）
            method: 安装方法 (silent / manual)
            fallback: 失败后行为 (manual)
            verify: 验证规则 {registry, paths}
        """
        self._verify_data = verify
        if method == "manual":
            # 直接打开让用户手动装
            try:
                os.startfile(file_path)
                self.install_result.emit({
                    "name": name,
                    "success": True,
                    "message": "已打开安装程序，请手动完成安装",
                })
            except Exception as e:
                self.install_result.emit({
                    "name": name,
                    "success": False,
                    "message": f"打开安装程序失败: {e}",
                })
            return

        # 尝试静默安装
        self._worker = InstallWorker(file_path, args)
        self._worker.finished.connect(
            lambda result: self._on_worker_finished(name, file_path, fallback, result)
        )
        self._worker.start()

    def _on_worker_finished(self, name: str, file_path: str, fallback: str, result: dict):
        """安装完成回调 — 不再自动降级，调用方自行决定重试"""
        if result.get("success"):
            verified = SilentInstaller.check_installed(self._verify_data)
            if verified:
                self.install_result.emit({
                    "name": name,
                    "success": True,
                    "message": "安装完成",
                })
            else:
                self.install_result.emit({
                    "name": name,
                    "success": False,
                    "message": "安装程序返回成功但验证未通过",
                })
        else:
            self.install_result.emit({
                "name": name,
                "success": False,
                "message": result.get("message", "安装失败"),
            })

    @staticmethod
    def check_installed(verify: dict | None) -> bool:
        """验证软件是否已安装（注册表 + 路径双重检查）"""
        if not verify:
            return False

        # 1. 查注册表 Uninstall 条目
        registry_kw = verify.get("registry", "")
        if registry_kw:
            try:
                for key_path in SilentInstaller.UNINSTALL_KEYS:
                    try:
                        key = winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, key_path)
                        i = 0
                        while True:
                            try:
                                subkey_name = winreg.EnumKey(key, i)
                                subkey = winreg.OpenKey(key, subkey_name)
                                try:
                                    display_name, _ = winreg.QueryValueEx(subkey, "DisplayName")
                                    if registry_kw.lower() in display_name.lower():
                                        winreg.CloseKey(subkey)
                                        winreg.CloseKey(key)
                                        return True
                                except FileNotFoundError:
                                    pass
                                finally:
                                    winreg.CloseKey(subkey)
                                i += 1
                            except OSError:
                                break
                        winreg.CloseKey(key)
                    except FileNotFoundError:
                        continue
            except Exception:
                pass

        # 2. 检查已知路径
        paths = verify.get("paths", [])
        for p in paths:
            expanded = os.path.expandvars(p).replace("{USER}", os.environ.get("USERNAME", ""))
            if os.path.exists(expanded):
                return True

        return False

    @staticmethod
    def install_winget(package_id: str) -> dict:
        """使用 winget 命令安装软件包。返回 {success, message}"""
        try:
            result = subprocess.run(
                ["winget", "install", "--id", package_id,
                 "--accept-source-agreements", "--accept-package-agreements"],
                capture_output=True,
                text=True,
                timeout=300,
            )
            if result.returncode == 0:
                return {"success": True, "message": "winget 安装完成"}
            else:
                error_msg = result.stderr.strip() or result.stdout.strip()
                return {"success": False, "message": error_msg or f"winget 返回码 {result.returncode}"}
        except subprocess.TimeoutExpired:
            return {"success": False, "message": "winget 安装超时（5 分钟）"}
        except FileNotFoundError:
            return {"success": False, "message": "winget 未安装或不在 PATH 中"}
