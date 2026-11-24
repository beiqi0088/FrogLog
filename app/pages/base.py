# -*- coding: utf-8 -*-
"""pages/base.py - 页面基类与通用排版件。"""
from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel,
                               QScrollArea)

import widgets as W


class Page(QWidget):
    """可滚动页面基类：内容放在 self.body 里。"""

    def __init__(self, app, parent=None):
        super().__init__(parent)
        self.app = app
        self.store = app.store
        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.setSpacing(0)

        self.scroll = QScrollArea()
        self.scroll.setWidgetResizable(True)
        self.scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.content = QWidget()
        self.body = QVBoxLayout(self.content)
        self.body.setContentsMargins(20, 4, 20, 24)
        self.body.setSpacing(12)
        self.body.setAlignment(Qt.AlignTop)
        self.scroll.setWidget(self.content)
        outer.addWidget(self.scroll)

    def on_show(self):
        self.build()

    def build(self):
        W.clear_layout(self.body)

    # ---------- 通用排版 ----------
    def appbar(self, title: str, eyebrow: str | None = None,
               back=None, right: QWidget | None = None):
        row = QWidget()
        lay = QHBoxLayout(row)
        lay.setContentsMargins(0, 10, 0, 2)
        lay.setSpacing(10)
        if back:
            btn = W.BackButton(36)
            btn.clicked.connect(back)
            lay.addWidget(btn, 0, Qt.AlignTop)
        col = QVBoxLayout()
        col.setSpacing(2)
        if eyebrow:
            eb = QLabel(eyebrow)
            eb.setObjectName("eyebrow")
            col.addWidget(eb)
        h = QLabel(title)
        h.setObjectName("h1")
        col.addWidget(h)
        lay.addLayout(col, 1)
        if right is not None:
            lay.addWidget(right, 0, Qt.AlignTop)
        self.body.addWidget(row)
        return row

    def hero(self, title: str, sub: str | None = None,
             right: QWidget | None = None):
        """大标题 + 下方副标题（今日页同款）。"""
        row = QWidget()
        lay = QHBoxLayout(row)
        lay.setContentsMargins(0, 14, 0, 2)
        lay.setSpacing(10)
        col = QVBoxLayout()
        col.setSpacing(3)
        h = QLabel(title)
        h.setObjectName("h1")
        col.addWidget(h)
        if sub:
            sb = QLabel(sub)
            sb.setStyleSheet(
                f"font-size:11.5px;color:{W.T['ink2']};")
            col.addWidget(sb)
        lay.addLayout(col, 1)
        if right is not None:
            lay.addWidget(right, 0, Qt.AlignTop)
        self.body.addWidget(row)
        return row

    def section(self, title: str, action: QWidget | None = None):
        row = QWidget()
        lay = QHBoxLayout(row)
        lay.setContentsMargins(2, 10, 2, 0)
        lay.setSpacing(8)
        t = QLabel(title)
        t.setObjectName("h2")
        lay.addWidget(t, 1)
        if action is not None:
            lay.addWidget(action)
        self.body.addWidget(row)
        return row

    def add(self, w: QWidget):
        self.body.addWidget(w)
        return w

    def stretch(self):
        self.body.addStretch(1)

    def line(self):
        self.body.addWidget(W.HLine())


def hrow(*widgets_, spacing=8, margins=(0, 0, 0, 0)):
    w = QWidget()
    lay = QHBoxLayout(w)
    lay.setContentsMargins(*margins)
    lay.setSpacing(spacing)
    for x in widgets_:
        if isinstance(x, int):
            lay.addStretch(x)
        else:
            lay.addWidget(x)
    return w


def vrow(*widgets_, spacing=6, margins=(0, 0, 0, 0)):
    w = QWidget()
    lay = QVBoxLayout(w)
    lay.setContentsMargins(*margins)
    lay.setSpacing(spacing)
    for x in widgets_:
        if isinstance(x, int):
            lay.addStretch(x)
        else:
            lay.addWidget(x)
    return w


def label(text: str, kind: str | None = None, wrap=False, size=None):
    lb = QLabel(text)
    if kind:
        lb.setObjectName(kind)
    if wrap:
        lb.setWordWrap(True)
    if size:
        lb.setStyleSheet(f"font-size:{size}px;")
    return lb


def metric(value: str, caption: str) -> QWidget:
    box = QWidget()
    lay = QVBoxLayout(box)
    lay.setContentsMargins(0, 0, 0, 0)
    lay.setSpacing(1)
    v = QLabel(value)
    v.setStyleSheet("font-size:20px;font-weight:600;")
    c = QLabel(caption)
    c.setObjectName("sub")
    lay.addWidget(v)
    lay.addWidget(c)
    return box
