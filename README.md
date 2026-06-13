---
AIGC:
    Label: "1"
    ContentProducer: 001191440300708461136T1XGW3
    ProduceID: 6e13dd71adeb46b2c8b27ab5508ca0b9_85167a9566b611f1a99c5254007bceed
    ReservedCode1: sd73yhM2/Z7ebiCmpYO/kP20qgaHxna/6r7DxnL3YnGef2PdCMOtBpDKgiGejsq97OL3pn2VmyygzlX38Hp1jtkwlravX07cGab8PquTzjK5dUhq8UQJPc40FMtzBwLeI5KQ5jdlJh+iFaigpIztYkmQleT+ON215O8Fcvyi5p0e2IOQR5U0S7vr7qA=
    ContentPropagator: 001191440300708461136T1XGW3
    PropagateID: 6e13dd71adeb46b2c8b27ab5508ca0b9_85167a9566b611f1a99c5254007bceed
    ReservedCode2: sd73yhM2/Z7ebiCmpYO/kP20qgaHxna/6r7DxnL3YnGef2PdCMOtBpDKgiGejsq97OL3pn2VmyygzlX38Hp1jtkwlravX07cGab8PquTzjK5dUhq8UQJPc40FMtzBwLeI5KQ5jdlJh+iFaigpIztYkmQleT+ON215O8Fcvyi5p0e2IOQR5U0S7vr7qA=
---

# DngTools - Windows 11 工具箱

重装系统后一键装回常用软件。

## 核心功能

- **软件商店** — 内置 16 款常用软件，分类展示，一键安装
- **静默安装** — 自动下载后静默安装，2 分钟超时降级为手动
- **下载管理** — Aria2 引擎，实时速度 / 进度显示
- **安装验证** — 注册表 + 路径双重检查，确认安装成功
- **多源下载** — winget → 直接链接 → Chocolatey 优先级回退

## 架构

```
core/           # 核心框架
  event_bus       — 全局事件总线（PySide6 Signal）
  plugin_manager  — 插件发现/加载/生命周期
  config_manager  — JSON 配置文件管理
  download_engine — Aria2 JSON-RPC 封装

plugins/
  software_store — 软件商店（列表 UI + 软件源管理）
  download_task  — 下载任务（进度 UI + 队列）
  install_task   — 静默安装（subprocess + 降级策略）
```

插件通过 `event_bus` 松耦合通信：`install_request → download_complete → install_result`。

## 运行

```bash
pip install PySide6
python main.py
```

首次启动会自动下载 Aria2 到 `data/aria2c.exe`。

## 添加软件

编辑 `data/software_list.json`：

```json
{
  "name": "软件名",
  "category": "分类",
  "sources": [
    { "type": "winget", "id": "包名" },
    { "type": "direct", "url": "下载地址" }
  ],
  "install": { "method": "silent", "args": "/S", "fallback": "manual" },
  "verify": { "registry": "显示名", "paths": ["路径\\程序.exe"] }
}
```

## 打包

```bash
pip install pyinstaller
pyinstaller --onefile --windowed --add-data "data;data" main.py
```

## 技术栈

Python 3.11 + PySide6 + Aria2
*（内容由AI生成，仅供参考）*
