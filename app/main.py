# -*- coding: utf-8 -*-
"""main.py - 入口。python main.py 启动；也支持 pythonw main.py 无控制台运行。"""
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from PySide6.QtCore import Qt, QTimer
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


def _mark(msg) -> None:
    """安卓上启动闪退时，靠这些打点定位死在哪一步（桌面无副作用）。"""
    logger = getattr(sys, "froglog_log", None)
    if logger:
        logger("main: " + msg)


def main():
    _mark("设置 DPI 策略")
    QApplication.setHighDpiScaleFactorRoundingPolicy(
        Qt.HighDpiScaleFactorRoundingPolicy.PassThrough)
    _mark("创建 QApplication")
    app = QApplication(sys.argv)
    _mark("QApplication 创建完成")
    apply_identity(app)
    # 安卓没有雅黑，交给系统默认的 Noto Sans CJK
    app.setFont(QFont("Noto Sans CJK SC" if ANDROID else "Microsoft YaHei UI", 9))
    _mark("创建主窗口")
    win = MainWindow()
    _mark("主窗口创建完成，准备显示")
    if ANDROID:
        # 先把窗口切到全屏铺满（decor 不再为系统栏预留空间），再显示，
        # 否则首帧会按「避让系统栏」的尺寸排版，随后才跳变成正确布局。
        paper, deep = "#F3EEDF", "#6B2C3B"
        try:
            import theme as _theme
            t = _theme.theme_tokens(getattr(win, "theme_id", None) or _theme.DEFAULT_THEME)
            paper = t.get("paper", paper)
            deep = t.get("deep", deep)
            from app import _android_edge_to_edge
            _android_edge_to_edge(paper, deep)
        except Exception:
            pass
        win.showMaximized()          # 手机上铺满屏幕

        def _fixup(_p=paper, _d=deep):
            """Qt 首次 show / 尺寸变化会重置系统栏，显示后再补几次。"""
            try:
                from app import _android_edge_to_edge
                _android_edge_to_edge(_p, _d)
                win._sync_system_insets()
                win._sync_bg()
            except Exception:
                pass

        for _ms in (0, 120, 400, 1000, 2200):
            QTimer.singleShot(_ms, _fixup)
    else:
        win.show()
    _mark("已显示，进入事件循环")
    rc = app.exec()
    _mark(f"事件循环退出 {rc}")
    sys.exit(rc)


if __name__ == "__main__":
    main()
