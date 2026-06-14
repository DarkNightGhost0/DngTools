# DngTools - Windows 11 工具箱

重装系统后一键装回常用软件，附带 VTuber 直播工具链管理与系统维护。

## 核心功能

- **软件商店** — 内置常用软件，分类展示，一键安装
- **静默安装** — 自动下载后静默安装，支持降级策略
- **下载管理** — Aria2 引擎，实时速度 / 进度显示
- **安装验证** — 注册表 + 路径双重检查，确认安装成功
- **多源下载** — winget → 直接链接 → Chocolatey 优先级回退
- **VTuber 工具** — OBS Studio / VTube Studio 一键安装与插件管理
- **系统维护** — 垃圾清理、启动项管理等

## 架构

```
core/               # 核心框架
  event_bus           — 全局事件总线（PySide6 Signal）
  plugin_manager      — 插件发现/加载/生命周期
  config_manager      — JSON 配置文件管理
  download_engine     — Aria2 JSON-RPC 封装

plugins/
  home_page           — 主页（终端窗口 + 命令输入）
  software_store      — 软件商店（列表 UI + 软件源管理）
  download_task       — 下载任务（进度 UI + 队列）
  install_task        — 静默安装（subprocess + 降级策略）
  vtuber_tools        — VTuber 直播工具链
  system_maintenance  — 系统维护

ui/
  main_window         — 主窗口（插件容器 + 全局状态栏）
  sidebar             — 侧边栏导航
```

插件通过 `event_bus` 松耦合通信：`install_request → download_complete → install_result`。

## VTuber 工具

为 OBS Studio 和 VTube Studio 提供一站式管理：

| 工具 | OBS Studio | VTube Studio |
|------|-----------|--------------|
| 自动搜索 | 注册表 + 多路径探测 | Steam + 多路径探测 |
| 安装 | Steam / winget / 直接下载 | Steam / 直接下载 |
| Spout2 插件 | ZIP / EXE 安装，自动匹配 OBS 版本 | — |
| NDI 插件 | winget 安装 DistroAV / NDI Runtime / NDI Tools（多选） | — |
| 虚拟摄像头 | — | Unity Capture 安装 |
| 去水印 | — | 代理 / SelfHook / Koaloader 三种模式 |
| 插件管理 | — | BepInEx / XYPlugin / HD Screenshot / HD Spout / NDI to ArtMesh |

配置目录 `plugins/vtuber_tools/config/plugin_list.json` 可扩展插件列表。

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
