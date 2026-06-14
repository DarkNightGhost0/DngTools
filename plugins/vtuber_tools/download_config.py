"""VTuber Tools 下载配置加载器。

读取 downloads.json，提供按名称获取版本信息的方法。
versions 数组按优先级排列（最新在前），默认取第一个。
"""

import json
from pathlib import Path
from typing import Optional


def _version_key(version: str) -> tuple:
    """将版本号转为可比较的元组，"latest" 排最前，"winget" 排最后。"""
    if version == "latest":
        return (9999,)
    if version == "winget":
        return (-1,)
    parts = []
    for p in version.split("."):
        try:
            parts.append(int(p))
        except ValueError:
            parts.append(0)
    return tuple(parts)


def _is_numeric_version(version: str) -> bool:
    """是否为纯数字版本号（如 32.1.2），排除 latest/winget 等标记。"""
    if not version or version in ("latest", "winget"):
        return False
    for p in version.split("."):
        if not p.isdigit():
            return False
    return True


class DownloadConfig:
    """下载配置，按名称索引，versions 数组的第一项即为当前选用版本。"""

    def __init__(self, config_path: Path):
        self._config_path = config_path
        self._data: dict[str, dict] = {}
        self.load()

    def load(self):
        if self._config_path.exists():
            try:
                with open(self._config_path, "r", encoding="utf-8") as f:
                    raw = json.load(f)
            except (json.JSONDecodeError, OSError):
                raw = {}

            # 对每个工具的 versions 按版本号降序排列
            for name, entry in raw.items():
                if isinstance(entry, dict) and "versions" in entry:
                    entry["versions"].sort(
                        key=lambda v: _version_key(v.get("version", "0")),
                        reverse=True,
                    )
            self._data = raw
        else:
            self._data = {}

    def get(self, name: str) -> Optional[dict]:
        """获取工具的完整配置（含 versions、install_args 等）。"""
        return self._data.get(name)

    def get_latest_url(self, name: str) -> Optional[str]:
        """获取工具最新版本的 direct 下载 URL。"""
        entry = self._data.get(name)
        if not entry:
            return None
        for ver in entry.get("versions", []):
            if ver.get("source_type") == "direct" and ver.get("url"):
                return ver["url"]
        return None

    def get_install_info(self, name: str) -> dict:
        """获取安装参数。"""
        entry = self._data.get(name)
        if not entry:
            return {}
        return {
            "args": entry.get("install_args", ""),
            "method": "silent",
            "fallback": "manual",
        }

    def get_latest_winget_id(self, name: str) -> Optional[str]:
        """获取 winget 源 ID。"""
        entry = self._data.get(name)
        if not entry:
            return None
        for ver in entry.get("versions", []):
            if ver.get("source_type") == "winget":
                return ver.get("winget_id")
        return None

    def get_latest_direct_version(self, name: str) -> Optional[str]:
        """获取最新 direct 类型的纯数字版本号，跳过 latest/winget 等标记。"""
        entry = self._data.get(name)
        if not entry:
            return None
        for ver in entry.get("versions", []):
            v = ver.get("version", "")
            if ver.get("source_type") == "direct" and _is_numeric_version(v):
                return v
        return None

    def is_newer_than(self, name: str, local_version: str) -> bool:
        """判断配置中最新的 numeric direct 版本是否高于本地版本。
        若最新 direct 版本不是纯数字（如 latest），则始终返回 False。"""
        latest = self.get_latest_direct_version(name)
        if not latest or not local_version:
            return False
        if not _is_numeric_version(local_version):
            return False
        return _version_key(latest) > _version_key(local_version)
