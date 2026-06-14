# DngTools

Windows 11 桌面工具箱 — 软件管理 + VTuber 直播工具链 + 系统维护。

## 功能

**软件商店**
分类浏览常用软件，一键下载安装。支持 winget / 直链 / Chocolatey 多源回退，Aria2 引擎实时速度显示，注册表 + 路径双重验证安装结果。

**VTuber 工具**
OBS Studio 与 VTube Studio 专用管理页：

- 自动扫描本机安装路径，一键启动
- OBS：Spout2 插件安装（ZIP / EXE，自动匹配版本）、NDI 套件安装（DistroAV / Runtime / Tools 多选）
- VTube Studio：虚拟摄像头安装、去水印（代理 / SelfHook / Koaloader 三种模式）、插件管理器（BepInEx / XYPlugin / HD Screenshot / HD Spout / NDI to ArtMesh，支持安装检测与卸载）
- 插件列表外部化 JSON 配置，可自行扩展

**系统维护**
垃圾清理、启动项管理等。

**终端主页**
类终端风格主页，展示系统信息，支持命令输入。

## 结构

```
core/                   # 框架层
  event_bus             # 全局事件总线
  plugin_manager        # 插件发现与生命周期
  config_manager        # JSON 配置读写
  download_engine       # Aria2 JSON-RPC 封装

plugins/
  home_page             # 终端主页
  software_store        # 软件商店
  download_task         # 下载队列 UI
  install_task          # 静默安装引擎
  vtuber_tools          # VTuber 工具链
  system_maintenance    # 系统维护

ui/
  main_window           # 主窗口
  sidebar               # 侧边栏导航
```

## 运行

```bash
pip install PySide6
python main.py
```

首次启动自动下载 Aria2 到 `data/aria2c.exe`。

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
