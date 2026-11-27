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
        self.content_lay = QVBoxLayout(self.content)
        self.content_lay.setContentsMargins(0, 0, 0, 0)
        self.content_lay.setSpacing(0)

        # 顶部深色色带（全宽、不跟 body 的 20px 边距走）
        self.band_host = QWidget()
        self.band_lay = QVBoxLayout(self.band_host)
        self.band_lay.setContentsMargins(0, 0, 0, 0)
        self.band_lay.setSpacing(0)
        self.band_host.hide()
        self.content_lay.addWidget(self.band_host)

        # 页面正文（浅纸底 + 20px 边距）
        self.body_host = QWidget()
        self.body = QVBoxLayout(self.body_host)
        self.body.setContentsMargins(20, 4, 20, 24)
        self.body.setSpacing(12)
        self.body.setAlignment(Qt.AlignTop)
        self.content_lay.addWidget(self.body_host, 1)
        self.scroll.setWidget(self.content)
        outer.addWidget(self.scroll)

    def on_show(self):
        self.build()

    def build(self):
        W.clear_layout(self.body)
        self._clear_band()
        self.band_host.hide()
        self.body_host.show()

    def _clear_band(self):
        if hasattr(self, "band_lay"):
            W.clear_layout(self.band_lay)

    def set_band(self, band: QWidget):
        self._clear_band()
        self.band_lay.addWidget(band)
        self.band_host.show()

    # ---------- 通用排版 ----------
    def appbar(self, title: str, eyebrow: str | None = None,
               back=None, right: QWidget | None = None):
        band = W.BandHeader()
        row = QWidget()
        lay = QHBoxLayout(row)
        lay.setContentsMargins(0, 4, 0, 0)
        lay.setSpacing(8)
        if back:
            btn = W.BackButton(30)
            btn.set_light(True)
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
        band.lay.addWidget(row)
        self.set_band(band)
        return row

    def hero(self, title: str, sub: str | None = None,
             right: QWidget | None = None):
        """大标题 + 下方副标题（放在深色色带里）。"""
        band = W.BandHeader()
        row = QWidget()
        lay = QHBoxLayout(row)
        lay.setContentsMargins(0, 4, 0, 0)
        lay.setSpacing(8)
        col = QVBoxLayout()
        col.setSpacing(1)
        h = QLabel(title)
        h.setObjectName("h1")
        col.addWidget(h)
        if sub:
            sb = QLabel(sub)
            sb.setStyleSheet("font-size:9.5px;color:#FFE9BD;")
            col.addWidget(sb)
        lay.addLayout(col, 1)
        if right is not None:
            lay.addWidget(right, 0, Qt.AlignTop)
        band.lay.addWidget(row)
        self.set_band(band)
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
