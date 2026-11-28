# -*- coding: utf-8 -*-
"""今日页 · 手帐风格效果图：顶部色带 + 底部 dock 用厚重色块，纸面加胶带/印章/手绘边。"""
import os, sys, math
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
os.environ.setdefault("QT_QPA_FONTDIR", r"C:\Windows\Fonts")
APP = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, APP)
from PySide6.QtWidgets import QApplication, QWidget, QVBoxLayout, QHBoxLayout, QLabel
from PySide6.QtCore import Qt, QRectF, QPointF
from PySide6.QtGui import (QColor, QPainter, QPen, QBrush, QFont, QPainterPath,
                           QLinearGradient, QPolygonF)
import theme

app = QApplication(sys.argv)
T = theme.theme_tokens("anki-mint")
DEEP, PAPER, INK, INK2, INK3 = T["deep"], "#FBF6EA", T["ink"], T["ink2"], T["ink3"]
RULE = "#D9D2C0"
FONT = "KaiTi"

PAPER_TINTS = ["#FDEDEA", "#FDF1EA", "#EDF4EE", "#F1F8EA"]
TAPES = ["#F3D9A4", "#CBE3D2", "#F2C9C9", "#CFE0F0"]


def f(size, weight=QFont.Normal, family=FONT):
    ft = QFont(family)
    ft.setPixelSize(int(size))
    ft.setWeight(weight)
    return ft


class Paper(QWidget):
    """奶油纸面 + 点阵。"""
    def paintEvent(self, e):
        p = QPainter(self)
        p.fillRect(self.rect(), QColor(PAPER))
        p.setPen(QPen(QColor(RULE), 1))
        step = 18
        for y in range(step, self.height(), step):
            for x in range(step, self.width(), step):
                p.drawPoint(x, y)


class Tape(QWidget):
    """一段半透明和纸胶带。"""
    def __init__(self, color, w, h=18, angle=0, parent=None):
        super().__init__(parent)
        self.color, self.angle = color, angle
        self.setFixedSize(w, h)

    def paintEvent(self, e):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        p.translate(self.width() / 2, self.height() / 2)
        p.rotate(self.angle)
        p.translate(-self.width() / 2, -self.height() / 2)
        c = QColor(self.color)
        c.setAlpha(210)
        p.setPen(Qt.NoPen)
        p.setBrush(c)
        p.drawRect(QRectF(0, 2, self.width(), self.height() - 4))
        p.setPen(QPen(QColor(255, 255, 255, 70), 1))
        for i in range(0, self.width(), 7):
            p.drawLine(QPointF(i, 2), QPointF(i + 4, self.height() - 2))


class SketchCard(QWidget):
    """手绘感卡片：纸底 + 略抖的墨线边框。"""
    def __init__(self, fill="#FFFDF8", radius=14, parent=None):
        super().__init__(parent)
        self.fill, self.radius = fill, radius

    def paintEvent(self, e):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        r = QRectF(2, 2, self.width() - 4, self.height() - 4)
        p.setPen(Qt.NoPen)
        p.setBrush(QColor(self.fill))
        p.drawRoundedRect(r, self.radius, self.radius)
        pen = QPen(QColor(INK), 1.4, Qt.SolidLine, Qt.RoundCap, Qt.RoundJoin)
        p.setPen(pen)
        p.setBrush(Qt.NoBrush)
        p.drawRoundedRect(r, self.radius, self.radius)
        # 手绘重影：再画一圈略微错位的线，像手画的
        soft = QColor(INK)
        soft.setAlpha(90)
        p.setPen(QPen(soft, 0.9))
        p.drawRoundedRect(r.adjusted(-1.5, 1.5, 1.5, -1.0), self.radius, self.radius)


class Band(QWidget):
    """顶部厚重色块 + 胶带 + 标题/日期/同步。"""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedHeight(96)

    def paintEvent(self, e):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        p.fillRect(self.rect(), QColor(DEEP))
        # 手帐胶带
        p.save()
        p.translate(28, 8)
        p.rotate(-4)
        p.setPen(Qt.NoPen)
        p.setBrush(QColor(243, 217, 164, 220))
        p.drawRect(QRectF(0, 0, 92, 16))
        p.setBrush(QColor(255, 255, 255, 60))
        for i in range(0, 92, 8):
            p.drawRect(QRectF(i, 0, 3, 16))
        p.restore()
        # 标题
        p.setPen(QColor("#FBF6EA"))
        p.setFont(f(30, QFont.Bold))
        p.drawText(QPointF(28, 54), "今日")
        p.setFont(f(12, QFont.Normal))
        p.setPen(QColor(251, 246, 234, 200))
        p.drawText(QPointF(30, 76), "11 月 28 日 · 星期六")
        # 印章
        p.setPen(QPen(QColor("#F3D9A4"), 1.4))
        p.setBrush(Qt.NoBrush)
        p.drawEllipse(QPointF(320, 42), 20, 20)
        p.drawEllipse(QPointF(320, 42), 16, 16)
        p.setFont(f(7, QFont.Bold))
        p.setPen(QColor("#F3D9A4"))
        p.drawText(QRectF(300, 34, 40, 16), Qt.AlignCenter, "11·28")
        # 同步螺旋
        p.setPen(QPen(QColor("#FBF6EA"), 2.2, Qt.SolidLine, Qt.RoundCap))
        cy = 42
        for i in range(4):
            rad = 5 + i * 4
            p.drawArc(QRectF(352 - rad, cy - rad, rad * 2, rad * 2), 0, 240 * 16)
        p.setPen(Qt.NoPen)
        p.setBrush(QColor("#E0653F"))
        p.drawEllipse(QPointF(374, 28), 3, 3)


class Dock(QWidget):
    """底部厚重色块 + 奶油导航。"""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedHeight(72)

    def paintEvent(self, e):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        p.fillRect(self.rect(), QColor(DEEP))
        names = ["今日", "记忆", "征途", "战果"]
        w = self.width()
        for i, name in enumerate(names):
            cx = w * (i + 0.5) / 4
            active = i == 0
            if active:
                p.setPen(Qt.NoPen)
                p.setBrush(QColor("#FBF6EA"))
                p.drawRoundedRect(QRectF(cx - 40, 12, 80, 48), 16, 16)
            col = QColor(DEEP) if active else QColor(251, 246, 234, 215)
            p.setPen(QPen(col, 1.8, Qt.SolidLine, Qt.RoundCap, Qt.RoundJoin))
            p.setBrush(Qt.NoBrush)
            # 简单几何图标
            if i == 0:
                p.drawEllipse(QPointF(cx, 30), 8, 8)
                for a in range(0, 360, 45):
                    p.drawLine(QPointF(cx + 10 * math.cos(math.radians(a)), 30 + 10 * math.sin(math.radians(a))),
                               QPointF(cx + 13 * math.cos(math.radians(a)), 30 + 13 * math.sin(math.radians(a))))
            elif i == 1:
                p.drawRoundedRect(QRectF(cx - 7, 23, 14, 15), 2, 2)
                p.drawLine(QPointF(cx - 4, 27), QPointF(cx + 4, 27))
            elif i == 2:
                p.drawPolyline(QPolygonF([QPointF(cx - 9, 35), QPointF(cx - 3, 26),
                                          QPointF(cx + 2, 31), QPointF(cx + 9, 22)]))
            else:
                for k, h in enumerate((7, 13, 9, 16)):
                    p.drawLine(QPointF(cx - 9 + k * 5, 38), QPointF(cx - 9 + k * 5, 38 - h))
            p.setFont(f(12, QFont.Bold if active else QFont.Normal))
            p.drawText(QRectF(cx - 40, 42, 80, 18), Qt.AlignCenter, name)


class Main(QWidget):
    def __init__(self):
        super().__init__()
        self.setObjectName("root")
        self.setStyleSheet("QWidget#root{background:#FBF6EA;}")
        lay = QVBoxLayout(self)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(0)
        lay.addWidget(Band())

        paper = Paper()
        pl = QVBoxLayout(paper)
        pl.setContentsMargins(16, 16, 16, 8)
        pl.setSpacing(12)

        # 顶部胶带 + 4 个统计卡
        tape_row = QHBoxLayout()
        tape_row.addWidget(Tape(TAPES[0], 120, 18, -3))
        tape_row.addStretch(1)
        tape_row.addWidget(Tape(TAPES[2], 78, 18, 4))
        pl.addLayout(tape_row)

        grid = QHBoxLayout()
        grid.setSpacing(12)
        data = [("待复习卡片", "22", "张", "#EAF0FB"),
                ("今日已学", "0", "张", "#EDF4EE"),
                ("待学新卡", "131", "张", "#FDF1EA"),
                ("已到期", "153", "张", "#FDEDEA")]
        left = QVBoxLayout(); left.setSpacing(12)
        right = QVBoxLayout(); right.setSpacing(12)
        for i, (name, num, unit, tint) in enumerate(data):
            card = SketchCard(tint, 14)
            card.setFixedHeight(94)
            cl = QVBoxLayout(card)
            cl.setContentsMargins(14, 10, 14, 10)
            cl.setSpacing(2)
            lab = QLabel(name)
            lab.setStyleSheet(f"background:transparent;color:{INK2};font-family:'{FONT}';font-size:12px;font-weight:600;")
            cl.addWidget(lab)
            n = QLabel(f"{num}<span style='font-size:12px;color:{INK3};'> {unit}</span>")
            n.setStyleSheet(f"background:transparent;color:{INK};font-family:'{FONT}';font-size:30px;font-weight:700;")
            cl.addWidget(n)
            (left if i % 2 == 0 else right).addWidget(card)
        grid.addLayout(left, 1)
        grid.addLayout(right, 1)
        pl.addLayout(grid)

        # 继续学习
        sec = QHBoxLayout()
        tape = Tape(TAPES[1], 64, 16, 2)
        sec.addWidget(tape, 0, Qt.AlignVCenter)
        t = QLabel("继续学习")
        t.setStyleSheet(f"background:transparent;color:{INK};font-family:'{FONT}';font-size:17px;font-weight:700;")
        sec.addWidget(t)
        sec.addStretch(1)
        more = QLabel("查看全部 ›")
        more.setStyleSheet(f"background:transparent;color:{INK3};font-family:'{FONT}';font-size:12px;")
        sec.addWidget(more)
        pl.addLayout(sec)

        for name, sub, tint in (("【问答题】", "到期复习 22 · 待学新卡 20 · 学习中 2", "#FDF1EA"),
                                ("工托个", "到期复习 114 · 待学新卡 105 · 学习中 9", "#EDF4EE"),
                                ("第一章 关于人性", "到期复习 4 · 待学新卡 2 · 学习中 2", "#FDEDEA")):
            row = SketchCard("#FFFDF8", 12)
            row.setFixedHeight(74)
            rl = QVBoxLayout(row)
            rl.setContentsMargins(16, 10, 16, 10)
            rl.setSpacing(3)
            h = QLabel(name)
            h.setStyleSheet(f"background:transparent;color:{INK};font-family:'{FONT}';font-size:16px;font-weight:700;")
            rl.addWidget(h)
            s = QLabel(sub)
            s.setStyleSheet(f"background:transparent;color:{INK2};font-family:'{FONT}';font-size:11.5px;")
            rl.addWidget(s)
            pl.addWidget(row)

        pl.addStretch(1)
        lay.addWidget(paper, 1)
        lay.addWidget(Dock())


w = Main()
w.resize(430, 880)
w.show()
app.processEvents()
w.grab().save(os.path.join(APP, "shots", "journal-mock.png"))
print("saved journal-mock")
