# -*- coding: utf-8 -*-
"""卡包页 4 个改版效果图（自绘行，避免 QSS 命中 QLabel）。"""
import os
import sys

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
os.environ.setdefault("QT_QPA_FONTDIR", r"C:\Windows\Fonts")
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from PySide6.QtCore import Qt, QRectF
from PySide6.QtGui import QColor, QPainter, QPen
from PySide6.QtWidgets import (QApplication, QWidget, QVBoxLayout, QHBoxLayout,
                               QLabel, QGridLayout, QPushButton)

import theme
import widgets as W
from core import Store
from app import resolve_family

OUT_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "shots")
PW, PH = 430, 880


def lb(text, size=13, bold=False, color=None, wrap=False):
    x = QLabel(text)
    x.setStyleSheet(f"font-size:{size}px;font-weight:{700 if bold else 400};"
                    f"background:transparent;border:none;"
                    + (f"color:{color};" if color else ""))
    x.setWordWrap(wrap)
    return x


class Row(QWidget):
    """自绘行：底、边框、可选左侧色条、可选底部进度条。"""

    def __init__(self, height=66, radius=12, bg=None, border=None,
                 stripe=None, progress=None, sep=False):
        super().__init__()
        self.setFixedHeight(height)
        self.radius = radius
        self.bg = bg
        self.border = border
        self.stripe = stripe
        self.progress = progress
        self.sep = sep

    def paintEvent(self, e):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        r = QRectF(0, 0, self.width(), self.height())
        if self.bg:
            p.setPen(Qt.NoPen)
            p.setBrush(QColor(self.bg))
            p.drawRoundedRect(r, self.radius, self.radius)
        if self.progress is not None:
            track = QRectF(13, self.height() - 11, self.width() - 26, 4)
            p.setPen(Qt.NoPen)
            p.setBrush(QColor("#E7E3D6"))
            p.drawRoundedRect(track, 2, 2)
            w = max(0.0, track.width() * self.progress / 100.0)
            p.setBrush(QColor(W.T["brand"]))
            p.drawRoundedRect(QRectF(track.x(), track.y(), w, 4), 2, 2)
        if self.stripe:
            p.save()
            path_r = QRectF(0, 0, self.width(), self.height())
            p.setClipRect(QRectF(0, 0, 6, self.height()))
            p.setPen(Qt.NoPen)
            p.setBrush(QColor(self.stripe))
            p.drawRoundedRect(path_r, self.radius, self.radius)
            p.restore()
        if self.border:
            p.setBrush(Qt.NoBrush)
            p.setPen(QPen(QColor(self.border), 1))
            p.drawRoundedRect(r.adjusted(0.5, 0.5, -0.5, -0.5), self.radius, self.radius)
        if self.sep:
            p.setPen(QPen(QColor(W.T["line"]), 1))
            p.drawLine(0, self.height() - 1, self.width(), self.height() - 1)


def header():
    row = QWidget()
    lay = QHBoxLayout(row)
    lay.setContentsMargins(0, 6, 0, 2)
    lay.setSpacing(8)
    lay.addWidget(W.IconButton("‹", 34))
    lay.addWidget(lb("有道暗记", 25, True), 1)
    lay.addWidget(W.Chip("导入"))
    return row


def seg(active="学习记忆"):
    wrap = QWidget()
    wrap.setObjectName("segV")
    wrap.setStyleSheet(f"QWidget#segV{{background:{W.T['paper2']};border-radius:16px;}}")
    lay = QHBoxLayout(wrap)
    lay.setContentsMargins(3, 3, 3, 3)
    lay.setSpacing(3)
    for name in ("刷题练习", "学习记忆", "浏览卡片"):
        lay.addWidget(W.Chip(name, on=(name == active)), 1)
    return wrap


def overview(name, sub, pct=50):
    card = W.Card()
    top = QWidget()
    tl = QHBoxLayout(top)
    tl.setContentsMargins(0, 0, 0, 0)
    col = QVBoxLayout()
    col.setSpacing(3)
    col.addWidget(lb("125 张 · 4 个卡组", 11, False, W.T["ink2"]))
    col.addWidget(lb(name, 19, True))
    col.addWidget(lb(sub, 11, False, W.T["ink2"]))
    tl.addLayout(col, 1)
    tl.addWidget(W.Ring(pct, 70, 7))
    card.body.addWidget(top)
    btn = QPushButton("开始学习（这一组）")
    btn.setFixedHeight(44)
    btn.setStyleSheet("QPushButton{background:#2E6A43;color:#FFFFFF;border:none;"
                      "border-radius:22px;font-size:14px;font-weight:600;}")
    card.body.addWidget(btn)
    return card


def shell():
    root = QWidget()
    root.setStyleSheet(f"background:{W.T['paper']};")
    lay = QVBoxLayout(root)
    lay.setContentsMargins(20, 0, 20, 16)
    lay.setSpacing(10)
    lay.setAlignment(Qt.AlignTop)
    return root, lay


def section(title, hint):
    head = QWidget()
    hl = QHBoxLayout(head)
    hl.setContentsMargins(2, 6, 2, 0)
    hl.addWidget(lb(title, 15, True), 1)
    hl.addWidget(lb(hint, 11, False, W.T["ink2"]))
    return head


def variant_a(rows):
    root, lay = shell()
    lay.addWidget(header()); lay.addWidget(seg())
    lay.addWidget(overview(rows[0][0], "4 张 · 4 到期 · 只学这一组"))
    lay.addWidget(section("卡组", "点选 · 左滑 · 长按拖动"))
    for g, sub, due, sel, _d in rows:
        bg = W.T["brand_soft"] if sel else W.T["panel"]
        border = W.T["brand"] if sel else W.T["line"]
        stripe = W.T["brand"] if sel else ("#C4553D" if due else "#CFC9BA")
        row = Row(70, 12, bg, border, stripe)
        rl = QHBoxLayout(row)
        rl.setContentsMargins(16, 10, 12, 10)
        rl.setSpacing(8)
        col = QVBoxLayout()
        col.setSpacing(2)
        col.addWidget(lb(g, 13.5, True))
        col.addWidget(lb(sub, 11, False, W.T["ink2"]))
        rl.addLayout(col, 1)
        rl.addWidget(W.Pill(f"{due} 到期" if due else "已完成",
                            "accent" if due else "plain"), 0, Qt.AlignVCenter)
        lay.addWidget(row)
    lay.addStretch(1)
    return root


def variant_b(rows):
    root, lay = shell()
    lay.addWidget(header()); lay.addWidget(seg())
    lay.addWidget(overview(rows[0][0], "4 张 · 4 到期 · 只学这一组"))
    lay.addSpacing(2)
    for g, sub, due, sel, _d in rows:
        row = Row(60, 0, W.T["brand_soft"] if sel else None, None, None, None, sep=True)
        rl = QHBoxLayout(row)
        rl.setContentsMargins(10, 8, 10, 8)
        col = QVBoxLayout(); col.setSpacing(2)
        col.addWidget(lb(g, 13.5, True))
        col.addWidget(lb(sub, 11, False, W.T["ink2"]))
        rl.addLayout(col, 1)
        rl.addWidget(lb(f"{due} 到期", 12, True, "#C4553D"))
        lay.addWidget(row)
    lay.addStretch(1)
    return root


def variant_c(rows):
    root, lay = shell()
    lay.addWidget(header()); lay.addWidget(seg())
    lay.addWidget(overview(rows[0][0], "4 张 · 4 到期 · 只学这一组"))
    lay.addSpacing(2)
    for g, sub, due, sel, done in rows:
        row = Row(64, 12, W.T["panel"],
                  W.T["brand"] if sel else W.T["line"], None, done)
        rl = QHBoxLayout(row)
        rl.setContentsMargins(13, 9, 13, 18)
        rl.addWidget(lb(g, 13.5, True), 1)
        rl.addWidget(lb(f"{done}%", 12, True, W.T["brand"]))
        lay.addWidget(row)
    lay.addStretch(1)
    return root


def variant_d(rows):
    root, lay = shell()
    lay.addWidget(header()); lay.addWidget(seg())
    lay.addWidget(overview(rows[0][0], "4 张 · 4 到期 · 只学这一组"))
    grid_host = QWidget()
    grid = QGridLayout(grid_host)
    grid.setContentsMargins(0, 6, 0, 0)
    grid.setHorizontalSpacing(10)
    grid.setVerticalSpacing(10)
    for i, (g, sub, due, sel, _d) in enumerate(rows):
        tile = Row(86, 14, W.T["brand_soft"] if sel else W.T["panel"],
                   W.T["brand"] if sel else W.T["line"])
        tl = QVBoxLayout(tile)
        tl.setContentsMargins(12, 10, 12, 10)
        tl.setSpacing(2)
        tl.addWidget(lb(g, 12.5, True, wrap=True), 1)
        foot = QHBoxLayout()
        foot.addWidget(lb(sub, 10, False, W.T["ink2"]), 1)
        foot.addWidget(lb(f"{due} 到期", 10, True, "#C4553D"))
        tl.addLayout(foot)
        grid.addWidget(tile, i // 2, i % 2)
    lay.addWidget(grid_host)
    lay.addStretch(1)
    return root


def main():
    app = QApplication(sys.argv)
    theme.set_font(resolve_family())
    st = Store()
    groups = st.ordered_groups("renxing")
    cards = st.cards_of("renxing")
    rows = []
    for g in groups[:4]:
        items = [c for c in cards if c.get("group") == g]
        due = len(items)
        done = round(sum(1 for c in items if c["reps"] > 0) / max(1, len(items)) * 100)
        sub = f"{len(items)} 张 · 单选 / 多选 / 问答"
        rows.append((g, sub, due, g.startswith("第一章 关于人") and "\u3000" not in g, done))

    pages = [
        ("A｜左侧色条卡片", variant_a(rows)),
        ("B｜紧凑分隔线", variant_b(rows)),
        ("C｜进度条", variant_c(rows)),
        ("D｜两列磁贴", variant_d(rows)),
    ]
    for label, page in pages:
        page.resize(PW, PH)
        page.show()
        app.processEvents()
        for _ in range(3):
            app.processEvents()

    sheet = QWidget()
    sheet.setStyleSheet("background:#FFFFFF;")
    gl = QGridLayout(sheet)
    gl.setContentsMargins(18, 18, 18, 18)
    gl.setSpacing(16)
    for i, (label, page) in enumerate(pages):
        wrap = QWidget()
        vl = QVBoxLayout(wrap)
        vl.setContentsMargins(0, 0, 0, 0)
        vl.setSpacing(6)
        vl.addWidget(lb(label, 13, True))
        img = QLabel()
        img.setPixmap(page.grab())
        img.setStyleSheet("border:1px solid #DEDAD0;")
        vl.addWidget(img)
        gl.addWidget(wrap, i // 2, i % 2)
        page.hide()
    sheet.adjustSize()
    sheet.show()
    app.processEvents()
    for _ in range(3):
        app.processEvents()
    out = os.path.join(OUT_DIR, "design_variants.png")
    sheet.grab().save(out)
    print("saved", out)


if __name__ == "__main__":
    main()
