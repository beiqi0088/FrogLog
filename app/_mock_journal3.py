# -*- coding: utf-8 -*-
"""今日页 · 手帐风格 v3：保留胶带/点阵/厚重色带，同步改回奶油圆底螺旋+红点图标。"""
import os, sys, math
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
os.environ.setdefault("QT_QPA_FONTDIR", r"C:\Windows\Fonts")
APP = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, APP)
from PySide6.QtWidgets import QApplication, QWidget, QVBoxLayout, QHBoxLayout, QLabel
from PySide6.QtCore import Qt, QRectF, QPointF
from PySide6.QtGui import QColor, QPainter, QPen, QFont, QPainterPath, QPolygonF
import theme

app = QApplication(sys.argv)
T = theme.theme_tokens("anki-mint")
DEEP, PAPER, INK, INK2, INK3 = T["deep"], "#FBF6EA", T["ink"], T["ink2"], T["ink3"]
RULE = "#D9D2C0"
FONT = "KaiTi"
TAPES = ["#F3D9A4", "#CBE3D2", "#F2C9C9", "#CFE0F0"]
TINTS = ["#F7EEE3", "#F3EEE2", "#EDF2E8", "#EFEDF4"]


def f(size, weight=QFont.Normal, family=FONT):
    ft = QFont(family)
    ft.setPixelSize(int(size))
    ft.setWeight(weight)
    return ft


class Paper(QWidget):
    def paintEvent(self, e):
        p = QPainter(self)
        p.fillRect(self.rect(), QColor(PAPER))
        p.setPen(QPen(QColor(RULE), 1))
        for y in range(18, self.height(), 18):
            for x in range(18, self.width(), 18):
                p.drawPoint(x, y)


class Tape(QWidget):
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
        p.setPen(QPen(QColor(INK), 1.4, Qt.SolidLine, Qt.RoundCap, Qt.RoundJoin))
        p.setBrush(Qt.NoBrush)
        p.drawRoundedRect(r, self.radius, self.radius)
        soft = QColor(INK)
        soft.setAlpha(80)
        p.setPen(QPen(soft, 0.9))
        p.drawRoundedRect(r.adjusted(-1.5, 1.5, 1.5, -1.0), self.radius, self.radius)


class SyncIcon(QWidget):
    """奶油圆底 + 深色螺旋 + 右上红点。"""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedSize(52, 52)

    def paintEvent(self, e):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        cx, cy = 26, 26
        p.setPen(Qt.NoPen)
        p.setBrush(QColor("#FBF6EA"))
        p.drawEllipse(QPointF(cx, cy), 25, 25)
        p.setPen(QPen(QColor(DEEP), 2.6, Qt.SolidLine, Qt.RoundCap))
        p.setBrush(Qt.NoBrush)
        path = QPainterPath()
        pts = []
        for t in range(0, 660, 8):
            a = math.radians(t)
            r = 2.4 + 17 * t / 660
            pts.append(QPointF(cx + r * math.cos(a), cy + r * math.sin(a)))
        path.moveTo(pts[0])
        for pt in pts[1:]:
            path.lineTo(pt)
        p.drawPath(path)
        p.setPen(QPen(QColor("#FBF6EA"), 1.4))
        p.setBrush(QColor("#C25A3A"))
        p.drawEllipse(QPointF(cx + 18, cy - 18), 4.6, 4.6)


class Band(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedHeight(96)

    def paintEvent(self, e):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        p.fillRect(self.rect(), QColor(DEEP))
        p.save()
        p.translate(28, 10)
        p.rotate(-4)
        p.setPen(Qt.NoPen)
        p.setBrush(QColor(243, 217, 164, 220))
        p.drawRect(QRectF(0, 0, 92, 16))
        p.setBrush(QColor(255, 255, 255, 60))
        for i in range(0, 92, 8):
            p.drawRect(QRectF(i, 0, 3, 16))
        p.restore()
        p.setPen(QColor("#FBF6EA"))
        p.setFont(f(30, QFont.Bold))
        p.drawText(QPointF(28, 54), "今日")
        p.setFont(f(12))
        p.setPen(QColor(251, 246, 234, 200))
        p.drawText(QPointF(30, 76), "11 月 28 日 · 星期六")
        p.setPen(QPen(QColor("#F3D9A4"), 1.4))
        p.setBrush(Qt.NoBrush)
        p.drawEllipse(QPointF(300, 44), 20, 20)
        p.drawEllipse(QPointF(300, 44), 16, 16)
        p.setFont(f(7, QFont.Bold))
        p.setPen(QColor("#F3D9A4"))
        p.drawText(QRectF(280, 36, 40, 16), Qt.AlignCenter, "11·28")


class Dock(QWidget):
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
            if i == 0:
                p.drawEllipse(QPointF(cx, 30), 8, 8)
                for a in range(0, 360, 45):
                    p.drawLine(QPointF(cx + 10 * math.cos(math.radians(a)), 30 + 10 * math.sin(math.radians(a))),
                               QPointF(cx + 13 * math.cos(math.radians(a)), 30 + 13 * math.sin(math.radians(a))))
            elif i == 1:
                p.drawRoundedRect(QRectF(cx - 7, 23, 14, 15), 2, 2)
                p.drawLine(QPointF(cx - 4, 27), QPointF(cx + 4, 27))
            elif i == 2:
                p.drawLine(QPointF(cx - 9, 35), QPointF(cx - 3, 26))
                p.drawLine(QPointF(cx - 3, 26), QPointF(cx + 2, 31))
                p.drawLine(QPointF(cx + 2, 31), QPointF(cx + 9, 22))
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

        tape_row = QHBoxLayout()
        tape_row.addWidget(Tape(TAPES[0], 120, 18, -3))
        tape_row.addStretch(1)
        tape_row.addWidget(Tape(TAPES[2], 78, 18, 4))
        pl.addLayout(tape_row)

        grid = QHBoxLayout()
        grid.setSpacing(12)
        left, right = QVBoxLayout(), QVBoxLayout()
        left.setSpacing(12); right.setSpacing(12)
        data = [("待复习卡片", "22", "张", TINTS[0]),
                ("今日已学", "0", "张", TINTS[2]),
                ("待学新卡", "131", "张", TINTS[1]),
                ("已到期", "153", "张", TINTS[3])]
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

        sec = QHBoxLayout()
        sec.addWidget(Tape(TAPES[1], 64, 16, 2), 0, Qt.AlignVCenter)
        t = QLabel("继续学习")
        t.setStyleSheet(f"background:transparent;color:{INK};font-family:'{FONT}';font-size:17px;font-weight:700;")
        sec.addWidget(t)
        sec.addStretch(1)
        more = QLabel("查看全部 ›")
        more.setStyleSheet(f"background:transparent;color:{INK3};font-family:'{FONT}';font-size:12px;")
        sec.addWidget(more)
        pl.addLayout(sec)

        for name, sub in (("【问答题】", "到期复习 22 · 待学新卡 20 · 学习中 2"),
                          ("工托个", "到期复习 114 · 待学新卡 105 · 学习中 9"),
                          ("第一章 关于人性", "到期复习 4 · 待学新卡 2 · 学习中 2")):
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

        # 同步图标浮在色带右侧
        self.sync = SyncIcon(self)
        self.sync.move(430 - 76, 22)
        self.sync.raise_()


w = Main()
w.resize(430, 880)
w.show()
app.processEvents()
w.sync.raise_()
app.processEvents()
w.grab().save(os.path.join(APP, "shots", "journal-mock3.png"))
print("saved journal-mock3")
