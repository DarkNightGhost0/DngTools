"""Aria2 下载引擎 - 进程管理 + JSON-RPC 通信"""

import json
import os
import subprocess
import time
import urllib.request
from pathlib import Path
from threading import Thread

from PySide6.QtCore import QObject, Signal, QTimer


class DownloadEngine(QObject):
    """封装 Aria2 进程管理和 JSON-RPC 通信"""

    aria2_started = Signal()
    aria2_stopped = Signal()

    # 下载完成信号 (gid, file_path)
    download_finished = Signal(str, str)

    # 下载进度 (gid, name, percent, speed)
    download_progress = Signal(str, str, int, str)

    def __init__(self, rpc_port=6800, rpc_secret=""):
        super().__init__()
        self.rpc_port = rpc_port
        self.rpc_secret = rpc_secret
        self.rpc_url = f"http://localhost:{rpc_port}/jsonrpc"
        self._process: subprocess.Popen | None = None
        self._poll_timer: QTimer | None = None
        self._active_tasks: dict[str, dict] = {}  # gid -> task_info

    # ─── 进程管理 ───────────────────────────────────────

    def start(self, aria2c_path: str, download_dir: str):
        """启动 Aria2 守护进程"""
        if self._process and self._process.poll() is None:
            return  # 已经在运行

        os.makedirs(download_dir, exist_ok=True)

        args = [
            aria2c_path,
            "--enable-rpc",
            f"--rpc-listen-port={self.rpc_port}",
            "--rpc-allow-origin-all=true",
            "--rpc-listen-all=false",
            f"--dir={download_dir}",
            "--check-certificate=false",
            "--max-concurrent-downloads=5",
            "--max-connection-per-server=8",
            "--split=8",
            "--continue=true",
            "--file-allocation=none",
            "--console-log-level=warn",
        ]

        if self.rpc_secret:
            args.append(f"--rpc-secret={self.rpc_secret}")

        self._process = subprocess.Popen(
            args,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            creationflags=subprocess.CREATE_NO_WINDOW,
        )

        # 等待 RPC 就绪
        for _ in range(30):
            time.sleep(0.2)
            if self._ping():
                self.aria2_started.emit()
                self._start_polling()
                return

        raise RuntimeError("Aria2 启动超时")

    def stop(self):
        """停止 Aria2 进程"""
        if self._poll_timer:
            self._poll_timer.stop()
            self._poll_timer = None

        if self._process and self._process.poll() is None:
            try:
                self._call("aria2.shutdown")
            except Exception:
                pass
            try:
                self._process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                self._process.kill()
        self.aria2_stopped.emit()

    # ─── RPC 通信 ────────────────────────────────────────

    def _ping(self) -> bool:
        try:
            self._call("aria2.getVersion", [])
            return True
        except Exception:
            return False

    def _call(self, method: str, params=None, timeout=10):
        """JSON-RPC HTTP 调用"""
        payload = {
            "jsonrpc": "2.0",
            "id": "toolbox",
            "method": method,
            "params": params or [],
        }
        data = json.dumps(payload).encode("utf-8")
        req = urllib.request.Request(
            self.rpc_url,
            data=data,
            headers={"Content-Type": "application/json"},
        )
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            result = json.loads(resp.read().decode("utf-8"))
            if "error" in result:
                raise RuntimeError(result["error"].get("message", "RPC error"))
            return result.get("result")

    # ─── 下载 API ────────────────────────────────────────

    def add_download(self, url: str, name: str, out_dir: str = "") -> str:
        """
        添加下载任务，返回 gid。

        Args:
            url: 下载链接
            name: 显示名称
            out_dir: 输出目录（留空使用默认）
        """
        options = {}
        if out_dir:
            options["dir"] = out_dir

        gid = self._call("aria2.addUri", [[url], options])
        self._active_tasks[gid] = {"name": name, "url": url}
        return gid

    def pause_download(self, gid: str):
        self._call("aria2.pause", [gid])

    def resume_download(self, gid: str):
        self._call("aria2.unpause", [gid])

    def remove_download(self, gid: str):
        self._call("aria2.remove", [gid])
        self._active_tasks.pop(gid, None)

    def get_status(self, gid: str) -> dict:
        return self._call("aria2.tellStatus", [gid])

    # ─── 轮询更新 ────────────────────────────────────────

    def _start_polling(self):
        """每秒轮询活动任务状态，推送进度和完成事件"""
        self._poll_timer = QTimer(self)
        self._poll_timer.timeout.connect(self._poll_active_tasks)
        self._poll_timer.start(1000)

    def _poll_active_tasks(self):
        for gid in list(self._active_tasks.keys()):
            try:
                status = self.get_status(gid)
                task = self._active_tasks[gid]

                total = int(status.get("totalLength", 0))
                completed = int(status.get("completedLength", 0))
                percent = int(completed / total * 100) if total > 0 else -1
                speed = self._format_speed(int(status.get("downloadSpeed", 0)))

                state = status.get("status", "")
                if state == "complete":
                    files = status.get("files", [])
                    file_path = files[0].get("path", "") if files else ""

                    self.download_finished.emit(gid, file_path)
                    self._active_tasks.pop(gid, None)
                elif state in ("error", "removed"):
                    self._active_tasks.pop(gid, None)
                else:
                    self.download_progress.emit(gid, task["name"], percent, speed)

            except Exception:
                continue

    @staticmethod
    def _format_speed(bytes_per_sec: int) -> str:
        if bytes_per_sec >= 1024 * 1024:
            return f"{bytes_per_sec / (1024 * 1024):.1f} MB/s"
        elif bytes_per_sec >= 1024:
            return f"{bytes_per_sec / 1024:.0f} KB/s"
        return f"{bytes_per_sec} B/s"
