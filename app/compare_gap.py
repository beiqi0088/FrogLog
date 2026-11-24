# -*- coding: utf-8 -*-
"""生成段间距对比图：6 / 12 / 18 / 24 px。"""
import os
import sys

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
os.environ.setdefault("QT_QPA_FONTDIR", r"C:\Windows\Fonts")
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from PySide6.QtGui import QColor, QPainter
from PySide6.QtWidgets import (QApplication, QWidget, QVBoxLayout, QHBoxLayout, QLabel)

import theme
import card_render as CR
from core import Store
from app import resolve_family

OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "shots", "28-para-gap-compare.png")


class Bg(QWidget):
    def paintEvent(self, e):
        p = QPainter(self)
        p.fillRect(self.rect(), QColor("#B3E5FC"))


def build(card, gap, width=300):
    CR.PARA_GAP = gap
    theme.set_font(resolve_family())
    pal = CR.palette("sky")
    box = QVBoxLayout()
    box.setContentsMargins(0, 0, 0, 0)
    box.setSpacing(8)
    t = QLabel(f"段间距 {gap}px")
    t.setStyleSheet("font-size:12px;font-weight:700;color:#2b3a3c;background:transparent;")
    box.addWidget(t)
    box.addWidget(CR.build_back(card, pal, None, width))
    box.addStretch(1)
    w = QWidget()
    w.setLayout(box)
    w.setFixedWidth(width + 16)
    return w


def main():
    app = QApplication(sys.argv)
    theme.set_font(resolve_family())
    store = Store()
    card = next(c for c in store.cards if c["type"] == "qa" and "自私的基因" in c["q"])

    root = Bg()
    outer = QVBoxLayout(root)
    outer.setContentsMargins(20, 18, 20, 18)
    outer.setSpacing(16)

    title = QLabel("同一段答案，四种段间距（正文 18px / 行高 1.65）")
    title.setStyleSheet("font-size:15px;font-weight:700;color:#1f3a33;background:transparent;")
    outer.addWidget(title)

    for gaps in ((6, 12), (18, 24)):
        row = QHBoxLayout()
        row.setSpacing(16)
        for g in gaps:
            row.addWidget(build(card, g))
        outer.addLayout(row)

    root.resize(2 * (300 + 16) + 16 + 40, 980)
    root.show()
    app.processEvents()
    for _ in range(3):
        app.processEvents()
    root.grab().save(OUT)
    print("saved", OUT)


if __name__ == "__main__":
    main()
