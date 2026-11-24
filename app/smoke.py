# -*- coding: utf-8 -*-
"""smoke.py - 真机（非 offscreen）启动自检：开窗 1.2 秒后自动退出。"""
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from PySide6.QtCore import QTimer
from PySide6.QtWidgets import QApplication

from app import MainWindow


def main():
    app = QApplication(sys.argv)
    win = MainWindow()
    win.show()
    ok = {"done": False}

    def finish():
        ok["done"] = True
        # 走一遍主要页面，确认无异常
        for key in ("library", "plan", "insights", "settings"):
            win.show_page(key)
        win.show_page("today")
        win.store.save()
        app.quit()

    QTimer.singleShot(1200, finish)
    app.exec()
    print("SMOKE OK" if ok["done"] else "SMOKE FAIL")


if __name__ == "__main__":
    main()
