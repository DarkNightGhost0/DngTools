"""软件源管理 - 加载内置列表、winget、Chocolatey、云端源"""

import json
import subprocess
from pathlib import Path
from typing import Optional


class SoftwareRepo:
    """
    软件源管理器，按优先级获取软件信息：
    1. 内置 JSON 列表（software_list.json）
    2. winget
    3. Chocolatey
    4. 云端同步源（预留）
    """

    def __init__(self, data_dir: Path):
        self.data_dir = data_dir
        self._builtin: list[dict] = []
        self._software_map: dict[str, dict] = {}  # name -> software定义

    def load(self):
        """加载内置软件列表"""
        builtin_path = self.data_dir / "software_list.json"
        if builtin_path.exists():
            try:
                with open(builtin_path, "r", encoding="utf-8") as f:
                    self._builtin = json.load(f)
            except (json.JSONDecodeError, OSError):
                self._builtin = []

        self._software_map.clear()
        for sw in self._builtin:
            name = sw.get("name", "")
            if name:
                self._software_map[name] = sw

    def list_all(self, category: str = "") -> list[dict]:
        """列出所有软件（可按分类过滤）"""
        if category:
            return [s for s in self._builtin if s.get("category") == category]
        return list(self._builtin)

    def get_categories(self) -> list[str]:
        """获取所有分类"""
        cats = set()
        for s in self._builtin:
            c = s.get("category")
            if c:
                cats.add(c)
        return sorted(cats)

    def get_software(self, name: str) -> Optional[dict]:
        """按名称获取软件定义"""
        return self._software_map.get(name)

    def get_download_url(self, software: dict) -> Optional[tuple[str, str]]:
        """
        按优先级获取最佳下载源。
        返回 (url, source_type) 或 None。
        """
        sources = software.get("sources", [])

        for source in sources:
            stype = source.get("type")

            if stype == "direct":
                url = source.get("url", "")
                if url:
                    return (url, "direct")

            elif stype == "winget":
                winget_id = source.get("id", "")
                if winget_id:
                    url = self._resolve_winget(winget_id)
                    if url:
                        return (url, "winget")

            elif stype == "choco":
                choco_id = source.get("id", "")
                if choco_id:
                    url = self._resolve_choco(choco_id)
                    if url:
                        return (url, "choco")

        return None

    def get_install_info(self, software: dict) -> dict:
        """获取安装信息"""
        install = software.get("install", {})
        return {
            "method": install.get("method", "silent"),
            "args": install.get("args", ""),
            "fallback": install.get("fallback", "manual"),
        }

    def get_verify(self, software: dict) -> dict | None:
        """获取安装验证规则"""
        return software.get("verify")

    # ─── winget / choco 解析 ─────────────────────────────

    @staticmethod
    def _resolve_winget(package_id: str) -> Optional[str]:
        """使用 winget 获取下载 URL（需要 winget 已安装）"""
        try:
            result = subprocess.run(
                ["winget", "download", "--id", package_id, "--url"],
                capture_output=True,
                text=True,
                timeout=30,
            )
            for line in result.stdout.splitlines():
                if line.startswith("http"):
                    return line.strip()
        except (subprocess.TimeoutExpired, FileNotFoundError):
            pass
        return None

    @staticmethod
    def _resolve_choco(package_id: str) -> Optional[str]:
        """使用 choco 获取下载 URL（需要 choco 已安装）"""
        try:
            result = subprocess.run(
                ["choco", "download", package_id, "--noop", "--force"],
                capture_output=True,
                text=True,
                timeout=30,
            )
            for line in result.stdout.splitlines():
                if line.startswith("http"):
                    return line.strip()
        except (subprocess.TimeoutExpired, FileNotFoundError):
            pass
        return None
