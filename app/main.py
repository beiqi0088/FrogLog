# -*- coding: utf-8 -*-
"""main.py - 入口。python main.py 启动；也支持 pythonw main.py 无控制台运行。"""
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from PySide6.QtCore import Qt
from PySide6.QtGui import QFont
from PySide6.QtWidgets import QApplication

from app import MainWindow
import brand


def apply_identity(app) -> None:
    """窗口标题、任务栏、Alt-Tab 里都显示同一个名字。"""
    app.setApplicationName(brand.NAME)
    app.setApplicationDisplayName(brand.NAME)
    app.setOrganizationName(brand.NAME_EN)
    try:                     # Windows 任务栏分组用，可失败
        import ctypes
        ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID("FrogLog")
    except Exception:
        pass


ANDROID = bool(os.environ.get("ANDROID_PRIVATE") or os.environ.get("ANDROID_ARGUMENT"))


def main():
    QApplication.setHighDpiScaleFactorRoundingPolicy(
        Qt.HighDpiScaleFactorRoundingPolicy.PassThrough)
    app = QApplication(sys.argv)
    apply_identity(app)
    # 安卓没有雅黑，交给系统默认的 Noto Sans CJK
    app.setFont(QFont("Noto Sans CJK SC" if ANDROID else "Microsoft YaHei UI", 9))
    win = MainWindow()
    if ANDROID:
        win.showMaximized()          # 手机上铺满屏幕
    else:
        win.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
