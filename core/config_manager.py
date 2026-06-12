"""配置管理器 - 全局配置读写"""

import json
import os
from pathlib import Path


class ConfigManager:
    """JSON 配置文件读写，自动创建默认值"""

    def __init__(self, config_dir: Path):
        self.config_dir = config_dir
        self.config_path = config_dir / "user_config.json"
        self._data = {}
        self._load()

    def _load(self):
        os.makedirs(self.config_dir, exist_ok=True)
        if self.config_path.exists():
            try:
                with open(self.config_path, "r", encoding="utf-8") as f:
                    self._data = json.load(f)
            except (json.JSONDecodeError, OSError):
                self._data = {}

    def _save(self):
        os.makedirs(self.config_dir, exist_ok=True)
        with open(self.config_path, "w", encoding="utf-8") as f:
            json.dump(self._data, f, indent=2, ensure_ascii=False)

    def get(self, key, default=None):
        return self._data.get(key, default)

    def set(self, key, value):
        self._data[key] = value
        self._save()

    def delete(self, key):
        if key in self._data:
            del self._data[key]
            self._save()

    @property
    def download_dir(self) -> str:
        return self.get("download_dir", str(self.config_dir / "downloads"))

    @property
    def install_dir(self) -> str:
        return self.get("install_dir", "C:\\Program Files\\ToolboxApps")
