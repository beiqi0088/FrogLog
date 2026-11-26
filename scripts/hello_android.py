# -*- coding: utf-8 -*-
"""最小 Qt 示例应用（打包成 HelloQt APK）。

用途：FrogLog 装到手机上打开就闪退时，用这个最小应用区分两类问题：
- HelloQt 也闪退 → 是打包链路（Qt/PySide6/NDK/p4a）的问题；
- HelloQt 正常显示 → 是 FrogLog 应用自身的代码问题。
"""
import sys

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QApplication, QLabel


def main():
    app = QApplication(sys.argv)
    label = QLabel("Hello FrogLog\nQt 6.11.1 / Android 16\n已成功启动")
    label.setAlignment(Qt.AlignCenter)
    label.setStyleSheet(
        "background:#F6F1E3;color:#2B3245;font-size:30px;padding:24px;")
    label.setMinimumSize(480, 800)
    label.showMaximized()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
