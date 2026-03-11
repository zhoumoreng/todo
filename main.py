import sys
import ctypes
import ctypes.wintypes
from PyQt6.QtWidgets import QApplication
from PyQt6.QtCore import Qt
from db.database import init_db
from ui.floating_panel import (
    FloatingPanel, load_settings,
    apply_app_font, DEFAULT_FONT_FAMILY, DEFAULT_FONT_SIZE
)
from ui.todo_widget import TodoWidget

MUTEX_NAME = "TodoFloat_SingleInstance_Mutex"


def acquire_single_instance_lock():
    """创建命名互斥体，返回句柄；若已存在则返回 None 表示已有实例在运行。"""
    handle = ctypes.windll.kernel32.CreateMutexW(None, True, MUTEX_NAME)
    if ctypes.windll.kernel32.GetLastError() == 183:  # ERROR_ALREADY_EXISTS
        ctypes.windll.kernel32.CloseHandle(handle)
        return None
    return handle


def main():
    mutex = acquire_single_instance_lock()
    if mutex is None:
        sys.exit(0)  # 已有实例，静默退出

    QApplication.setHighDpiScaleFactorRoundingPolicy(
        Qt.HighDpiScaleFactorRoundingPolicy.PassThrough
    )
    app = QApplication(sys.argv)
    app.setLayoutDirection(Qt.LayoutDirection.LeftToRight)
    app.setQuitOnLastWindowClosed(False)

    # 应用保存的字体
    settings = load_settings()
    apply_app_font(
        settings.get('font_family', DEFAULT_FONT_FAMILY),
        settings.get('font_size', DEFAULT_FONT_SIZE)
    )

    init_db()

    panel = FloatingPanel(TodoWidget)
    panel.show()

    sys.exit(app.exec())


if __name__ == '__main__':
    main()
