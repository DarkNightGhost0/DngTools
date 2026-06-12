"""插件基类 - 所有插件必须继承此类"""


class BasePlugin:
    """插件基类，定义插件生命周期接口"""

    name: str = "BasePlugin"
    version: str = "0.1.0"

    def register(self, main_window, event_bus):
        """
        注册阶段：插件向主窗口注册 UI 页面、向事件总线注册监听。
        在 UI 显示之前调用。

        Args:
            main_window: 主窗口实例，用于注册导航项和内容页面
            event_bus: 事件总线实例，用于订阅/发布事件
        """
        raise NotImplementedError

    def start(self):
        """启动阶段：主窗口显示后调用，用于启动后台任务（如 Aria2 进程）"""
        pass

    def stop(self):
        """停止阶段：应用退出前调用，用于清理资源"""
        pass
