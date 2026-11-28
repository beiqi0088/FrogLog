# -*- coding: utf-8 -*-
"""征途 · 怪物吃青蛙效果图：把青蛙勋章区换成怪物养成卡。"""
import os, sys, math
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
os.environ.setdefault("QT_QPA_FONTDIR", r"C:\Windows\Fonts")
APP = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, APP)
from PySide6.QtWidgets import QApplication, QWidget, QVBoxLayout, QHBoxLayout, QLabel
from PySide6.QtCore import Qt, QRectF, QPointF
from PySide6.QtGui import (QColor, QPainter, QPen, QFont, QPainterPath, QBrush,
                           QPolygonF, QLinearGradient)
import theme

app = QApplication(sys.argv)
T = theme.theme_tokens("anki-lagoon")
DEEP, PAPER, PANEL, INK, INK2, INK3 = T["deep"], T["page"], T["panel"], T["ink"], T["ink2"], T["ink3"]
FONT = "KaiTi"
BLUE = "#5B8FD4"
BLUE2 = "#3F6FB0"
RED = "#D9533F"


def f(size, weight=QFont.Normal):
    ft = QFont(FONT)
    ft.setPixelSize(int(size))
    ft.setWeight(weight)
    return ft


class Monster(QWidget):
    """复杂一点的怪物：角、耳朵、獠牙、斑点、爪印、肚皮、阴影。"""
    def __init__(self, size=150, parent=None):
        super().__init__(parent)
        self.setFixedSize(size, size + 16)
        self.s = size

    def paintEvent(self, e):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        s = self.s
        cx = s / 2
        top = 18
        # 地面阴影
        p.setPen(Qt.NoPen)
        p.setBrush(QColor(0, 0, 0, 28))
        p.drawEllipse(QRectF(s * 0.18, top + s * 0.80, s * 0.64, s * 0.13))

        body = QPainterPath()
        body.moveTo(cx, top + s * 0.05)
        body.cubicTo(cx + s * 0.42, top + s * 0.02, cx + s * 0.50, top + s * 0.36,
                     cx + s * 0.46, top + s * 0.58)
        body.cubicTo(cx + s * 0.42, top + s * 0.80, cx + s * 0.20, top + s * 0.86,
                     cx, top + s * 0.86)
        body.cubicTo(cx - s * 0.20, top + s * 0.86, cx - s * 0.42, top + s * 0.80,
                     cx - s * 0.46, top + s * 0.58)
        body.cubicTo(cx - s * 0.50, top + s * 0.36, cx - s * 0.42, top + s * 0.02,
                     cx, top + s * 0.05)

        # 角
        p.setPen(Qt.NoPen)
        p.setBrush(QColor(BLUE2))
        left_horn = QPolygonF([QPointF(cx - s * 0.30, top + s * 0.18),
                               QPointF(cx - s * 0.46, top - s * 0.06),
                               QPointF(cx - s * 0.12, top + s * 0.10)])
        right_horn = QPolygonF([QPointF(cx + s * 0.30, top + s * 0.18),
                                QPointF(cx + s * 0.46, top - s * 0.06),
                                QPointF(cx + s * 0.12, top + s * 0.10)])
        p.drawPolygon(left_horn)
        p.drawPolygon(right_horn)

        # 身体
        grad = QLinearGradient(0, top, 0, top + s)
        grad.setColorAt(0, QColor("#6EA0E0"))
        grad.setColorAt(1, QColor(BLUE))
        p.setBrush(QBrush(grad))
        p.drawPath(body)

        # 肚皮
        belly = QPainterPath()
        belly.moveTo(cx - s * 0.24, top + s * 0.62)
        belly.cubicTo(cx - s * 0.20, top + s * 0.40, cx + s * 0.20, top + s * 0.40,
                      cx + s * 0.24, top + s * 0.62)
        belly.cubicTo(cx + s * 0.16, top + s * 0.78, cx - s * 0.16, top + s * 0.78,
                      cx - s * 0.24, top + s * 0.62)
        p.setBrush(QColor(255, 255, 255, 42))
        p.drawPath(belly)

        # 斑点
        p.setBrush(QColor(BLUE2))
        for dx, dy, r in ((-0.34, 0.42, 0.030), (0.35, 0.38, 0.024),
                          (-0.30, 0.60, 0.020), (0.31, 0.58, 0.028)):
            p.drawEllipse(QPointF(cx + dx * s, top + dy * s), r * s, r * s)

        # 眼睛
        for ex in (-0.17, 0.17):
            p.setBrush(QColor("#FFFDF8"))
            p.drawEllipse(QPointF(cx + ex * s, top + s * 0.40), s * 0.105, s * 0.105)
            p.setBrush(QColor("#1E2A36"))
            p.drawEllipse(QPointF(cx + ex * s, top + s * 0.41), s * 0.052, s * 0.052)
            p.setBrush(QColor("#FFFFFF"))
            p.drawEllipse(QPointF(cx + ex * s + s * 0.018, top + s * 0.39),
                          s * 0.017, s * 0.017)

        # 嘴 + 獠牙 + 舌头（吃青蛙）
        mouth = QPainterPath()
        mouth.moveTo(cx - s * 0.20, top + s * 0.60)
        mouth.quadTo(cx, top + s * 0.74, cx + s * 0.20, top + s * 0.60)
        p.setPen(QPen(QColor("#1E2A36"), s * 0.022, Qt.SolidLine, Qt.RoundCap))
        p.setBrush(QColor("#7A2E33"))
        p.drawPath(mouth)
        p.setPen(Qt.NoPen)
        p.setBrush(QColor("#FFFDF8"))
        p.drawPolygon(QPolygonF([QPointF(cx - s * 0.10, top + s * 0.63),
                                 QPointF(cx - s * 0.055, top + s * 0.72),
                                 QPointF(cx - s * 0.015, top + s * 0.64)]))
        p.drawPolygon(QPolygonF([QPointF(cx + s * 0.10, top + s * 0.63),
                                 QPointF(cx + s * 0.055, top + s * 0.72),
                                 QPointF(cx + s * 0.015, top + s * 0.64)]))
        p.setBrush(QColor("#E4665E"))
        p.drawEllipse(QPointF(cx, top + s * 0.705), s * 0.055, s * 0.030)

        # 爪印
        p.setPen(QPen(QColor("#1E2A36"), s * 0.018, Qt.SolidLine, Qt.RoundCap))
        for sx in (-1, 1):
            bx = cx + sx * s * 0.30
            for k in (-1, 0, 1):
                p.drawLine(QPointF(bx + k * s * 0.016, top + s * 0.86),
                           QPointF(bx + k * s * 0.020, top + s * 0.90))


class LevelRow(QWidget):
    def __init__(self, lv, name, need, current=False, done=False, parent=None):
        super().__init__(parent)
        self.lv, self.name, self.need = lv, name, need
        self.current, self.done = current, done

    def paintEvent(self, e):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        y = self.height() / 2
        col = QColor(DEEP) if (self.current or self.done) else QColor(INK3)
        p.setPen(Qt.NoPen)
        p.setBrush(QColor(DEEP) if self.done else (QColor(DEEP) if self.current else QColor(PAPER)))
        p.drawEllipse(QPointF(12, y), 6, 6)
        if self.done:
            p.setPen(QPen(QColor("#FFFDF8"), 1.4))
            p.drawLine(QPointF(9, y), QPointF(11, y + 2))
            p.drawLine(QPointF(11, y + 2), QPointF(15, y - 2))
        p.setPen(col)
        p.setFont(f(11, QFont.Bold if self.current else QFont.Normal))
        p.drawText(QRectF(26, 0, 190, self.height()), Qt.AlignVCenter, f"Lv.{self.lv} {self.name}")
        p.setFont(f(10))
        p.setPen(QColor(INK3))
        p.drawText(QRectF(0, 0, self.width() - 4, self.height()), Qt.AlignRight | Qt.AlignVCenter,
                   self.need)


class Card(QWidget):
    def paintEvent(self, e):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        r = QRectF(1, 1, self.width() - 2, self.height() - 2)
        p.setPen(QPen(QColor(INK), 1.4))
        p.setBrush(QColor(PANEL))
        p.drawRoundedRect(r, 16, 16)


class Main(QWidget):
    def __init__(self):
        super().__init__()
        self.setStyleSheet(f"background:{PAPER};")
        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        # 顶部色带
        band = QWidget()
        band.setFixedHeight(86)
        band.setStyleSheet(f"background:{DEEP};")
        bl = QHBoxLayout(band)
        bl.setContentsMargins(18, 8, 18, 8)
        title = QLabel("征途")
        title.setStyleSheet("color:#FFFDF8;font-family:'KaiTi';font-size:26px;font-weight:700;")
        bl.addWidget(title)
        bl.addStretch(1)
        sw = QLabel("")
        sw.setFixedSize(56, 30)
        sw.setStyleSheet("background:#FFF3D6;border-radius:15px;")
        bl.addWidget(sw)
        root.addWidget(band)

        page = QWidget()
        pl = QVBoxLayout(page)
        pl.setContentsMargins(16, 14, 16, 10)
        pl.setSpacing(12)

        # 任务条
        task = Card()
        task.setFixedHeight(74)
        tl = QHBoxLayout(task)
        tl.setContentsMargins(16, 10, 16, 10)
        tl.addWidget(QLabel("今日任务 · 00:00 已完成"))
        pl.addWidget(task)

        # 怪物卡
        mcard = Card()
        mcard.setFixedHeight(430)
        ml = QVBoxLayout(mcard)
        ml.setContentsMargins(16, 14, 16, 14)
        ml.setSpacing(8)

        head = QHBoxLayout()
        t = QLabel("蓝泡泡")
        t.setStyleSheet(f"color:{INK};font-family:'{FONT}';font-size:20px;font-weight:700;")
        head.addWidget(t)
        lv = QLabel("Lv.2")
        lv.setStyleSheet(f"color:#FFFDF8;background:{BLUE2};border-radius:9px;"
                         "font-size:12px;font-weight:700;padding:2px 10px;")
        head.addWidget(lv)
        head.addStretch(1)
        eaten = QLabel("已吃 2 / 5 只")
        eaten.setStyleSheet(f"color:{INK3};font-size:11px;")
        head.addWidget(eaten)
        ml.addLayout(head)

        mon = Monster(150)
        ml.addWidget(mon, 0, Qt.AlignHCenter)

        bar = QWidget()
        bar.setFixedHeight(10)
        bar.setStyleSheet(f"background:{T['line']};border-radius:5px;")
        bar_l = QHBoxLayout(bar)
        bar_l.setContentsMargins(0, 0, 0, 0)
        fill = QWidget()
        fill.setStyleSheet(f"background:{RED};border-radius:5px;")
        fill.setFixedWidth(int(360 * 0.4))
        bar_l.addWidget(fill)
        bar_l.addStretch(1)
        ml.addWidget(bar)

        hint = QLabel("再吃 3 只青蛙升级 · 吃掉一只青蛙 = 累计学习 45 分钟")
        hint.setStyleSheet(f"color:{INK2};font-size:11px;")
        hint.setAlignment(Qt.AlignCenter)
        ml.addWidget(hint)

        stats = QHBoxLayout()
        for name, val in (("已吃青蛙", "2 只"), ("累计学习", "30 分钟"), ("今日", "2 只")):
            box = QWidget()
            bl2 = QVBoxLayout(box)
            bl2.setContentsMargins(0, 0, 0, 0)
            bl2.setSpacing(0)
            v = QLabel(val)
            v.setStyleSheet(f"color:{INK};font-family:'{FONT}';font-size:18px;font-weight:700;")
            bl2.addWidget(v)
            k = QLabel(name)
            k.setStyleSheet(f"color:{INK3};font-size:10px;")
            bl2.addWidget(k)
            stats.addWidget(box, 1)
        ml.addLayout(stats)

        # 升级阶梯
        ladder = QWidget()
        ll = QVBoxLayout(ladder)
        ll.setContentsMargins(0, 2, 0, 0)
        ll.setSpacing(2)
        rows = [("1", "青泡泡", "0 只", False, True),
                ("2", "蓝泡泡", "5 只", True, False),
                ("3", "紫泡泡", "15 只", False, False),
                ("4", "赤泡泡", "30 只", False, False),
                ("5", "金泡泡", "50 只", False, False),
                ("6", "蛙群之王", "80 只", False, False)]
        for lv, name, need, cur, done in rows:
            r = LevelRow(lv, name, need, current=cur, done=done)
            r.setFixedHeight(22)
            ll.addWidget(r)
        ml.addWidget(ladder)
        pl.addWidget(mcard)

        pl.addStretch(1)
        root.addWidget(page, 1)

        # 底部 dock
        dock = QWidget()
        dock.setFixedHeight(66)
        dock.setStyleSheet(f"background:{DEEP};")
        dl = QHBoxLayout(dock)
        dl.setContentsMargins(20, 8, 20, 8)
        for i, name in enumerate(("今日", "记忆", "征途", "战果")):
            lab = QLabel(name)
            lab.setAlignment(Qt.AlignCenter)
            if i == 2:
                lab.setStyleSheet("color:%s;background:#FFFDF8;border-radius:14px;"
                                  "font-size:12px;font-weight:700;padding:8px 18px;" % DEEP)
            else:
                lab.setStyleSheet("color:rgba(255,253,248,0.75);font-size:12px;")
            dl.addWidget(lab, 1)
        root.addWidget(dock)


w = Main()
w.resize(430, 880)
w.show()
app.processEvents()
w.grab().save(os.path.join(APP, "shots", "monster-mock.png"))
print("saved monster-mock")
