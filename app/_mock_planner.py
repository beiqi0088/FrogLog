# -*- coding: utf-8 -*-
"""今日页 · 手帐本风格效果图 v2：深色本皮（色带/dock）+ 奶油纸页 + 彩色索引标签。"""
import os, sys, math
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
os.environ.setdefault("QT_QPA_FONTDIR", r"C:\Windows\Fonts")
APP = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, APP)
from PySide6.QtWidgets import QApplication, QWidget, QVBoxLayout, QHBoxLayout, QLabel
from PySide6.QtCore import Qt, QRectF, QPointF
from PySide6.QtGui import QColor, QPainter, QPen, QFont, QPainterPath
import theme

app = QApplication(sys.argv)
T = theme.theme_tokens("anki-mint")
DEEP, PAPER, PANEL, INK, INK2, INK3 = T["deep"], "#FBF6EA", "#FFFDF8", T["ink"], T["ink2"], T["ink3"]
RULE = "#EDE2C8"
FONT = "Noto Sans SC"

TABS = ["#C4562E", "#B45309", "#2F7A4F", "#0E9F6E"]
TINTS = ["#F6EFE3", "#F1EDE3", "#EDF1E7", "#EFEDF3"]


def f(size, weight=QFont.Normal):
    ft = QFont(FONT)
    ft.setPixelSize(int(size))
    ft.setWeight(weight)
    return ft


class Page(QWidget):
    """奶油纸页 + 淡淡的横线（笔记本内页）。"""
    def paintEvent(self, e):
        p = QPainter(self)
        p.fillRect(self.rect(), QColor(PAPER))
        p.setPen(QPen(QColor(RULE), 1))
        y = 34
        while y < self.height():
            p.drawLine(0, y, self.width(), y)
            y += 30


class Band(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedHeight(88)

    def paintEvent(self, e):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        p.fillRect(self.rect(), QColor(DEEP))
        # 本皮压线
        p.setPen(QPen(QColor(255, 255, 255, 36), 1))
        p.drawLine(16, 74, self.width() - 16, 74)
        p.setPen(QColor("#FBF6EA"))
        p.setFont(f(27, QFont.Bold))
        p.drawText(QPointF(20, 46), "今日")
        p.setFont(f(11.5))
        p.setPen(QColor(251, 246, 234, 195))
        p.drawText(QPointF(22, 65), "11 月 28 日 · 星期六")
        # 索引标签
        for i, c in enumerate(TABS[:1]):
            p.setPen(Qt.NoPen)
            p.setBrush(QColor("#FBF6EA"))
            p.drawRoundedRect(QRectF(self.width() - 96, 18, 40, 20), 6, 6)
            p.setPen(QColor(DEEP))
            p.setFont(f(10, QFont.Bold))
            p.drawText(QRectF(self.width() - 96, 18, 40, 20), Qt.AlignCenter, "今天")
        # 同步螺旋
        p.setPen(QPen(QColor("#FBF6EA"), 2.2, Qt.SolidLine, Qt.RoundCap))
        cx, cy = self.width() - 30, 46
        for i in range(3):
            rad = 4 + i * 3.6
            p.drawArc(QRectF(cx - rad, cy - rad, rad * 2, rad * 2), 20 * 16, 260 * 16)
        p.setPen(Qt.NoPen)
        p.setBrush(QColor("#E0653F"))
        p.drawEllipse(QPointF(cx + 9, cy - 9), 2.6, 2.6)


class Card(QWidget):
    def __init__(self, tab, tint, parent=None):
        super().__init__(parent)
        self.tab, self.tint = tab, tint

    def paintEvent(self, e):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        r = QRectF(1, 1, self.width() - 2, self.height() - 2)
        # 硬阴影
        p.setPen(Qt.NoPen)
        p.setBrush(QColor(INK))
        p.drawRoundedRect(r.adjusted(2, 3, 2, 3), 14, 14)
        p.setBrush(QColor(PANEL))
        p.drawRoundedRect(r, 14, 14)
        # 左侧索引标签
        p.setBrush(QColor(self.tab))
        p.drawRoundedRect(QRectF(1, 16, 5, self.height() - 32), 2.5, 2.5)
        # 图标圆
        p.setBrush(QColor(self.tint))
        p.drawEllipse(QPointF(28, 28), 12, 12)
        p.setPen(QPen(QColor(self.tab), 1.6, Qt.SolidLine, Qt.RoundCap, Qt.RoundJoin))
        p.setBrush(Qt.NoBrush)
        p.drawEllipse(QPointF(28, 28), 5.5, 5.5)
        p.setPen(QPen(QColor(INK), 1.2))
        p.drawRoundedRect(r, 14, 14)


class Section(QWidget):
    def paintEvent(self, e):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        p.setPen(Qt.NoPen)
        p.setBrush(QColor(INK))
        p.drawRoundedRect(QRectF(0, 3, 4, 16), 2, 2)


class Dock(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedHeight(70)

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
                p.drawRoundedRect(QRectF(cx - 38, 12, 76, 46), 15, 15)
            col = QColor(DEEP) if active else QColor(251, 246, 234, 210)
            p.setPen(QPen(col, 1.7, Qt.SolidLine, Qt.RoundCap, Qt.RoundJoin))
            p.setBrush(Qt.NoBrush)
            if i == 0:
                p.drawEllipse(QPointF(cx, 29), 7, 7)
                for a in range(0, 360, 45):
                    p.drawLine(QPointF(cx + 9 * math.cos(math.radians(a)), 29 + 9 * math.sin(math.radians(a))),
                               QPointF(cx + 12 * math.cos(math.radians(a)), 29 + 12 * math.sin(math.radians(a))))
            elif i == 1:
                p.drawRoundedRect(QRectF(cx - 6.5, 22, 13, 15), 2, 2)
            elif i == 2:
                p.drawLine(QPointF(cx - 8, 34), QPointF(cx - 3, 24))
                p.drawLine(QPointF(cx - 3, 24), QPointF(cx + 2, 30))
                p.drawLine(QPointF(cx + 2, 30), QPointF(cx + 8, 22))
            else:
                for k, h in enumerate((6, 12, 8, 15)):
                    p.drawLine(QPointF(cx - 8 + k * 5, 36), QPointF(cx - 8 + k * 5, 36 - h))
            p.setFont(f(11.5, QFont.Bold if active else QFont.Normal))
            p.drawText(QRectF(cx - 38, 40, 76, 16), Qt.AlignCenter, name)


class Main(QWidget):
    def __init__(self):
        super().__init__()
        self.setObjectName("root")
        self.setStyleSheet("QWidget#root{background:#FBF6EA;}")
        lay = QVBoxLayout(self)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(0)
        lay.addWidget(Band())

        page = Page()
        pl = QVBoxLayout(page)
        pl.setContentsMargins(18, 16, 18, 8)
        pl.setSpacing(12)

        # 统计卡 2×2
        grid = QHBoxLayout()
        grid.setSpacing(12)
        col_l, col_r = QVBoxLayout(), QVBoxLayout()
        col_l.setSpacing(12); col_r.setSpacing(12)
        data = [("待复习卡片", "22", "张", TABS[0], TINTS[0]),
                ("今日已学", "0", "张", TABS[2], TINTS[2]),
                ("待学新卡", "131", "张", TABS[1], TINTS[1]),
                ("已到期", "153", "张", TABS[0], TINTS[0])]
        for i, (name, num, unit, tab, tint) in enumerate(data):
            card = Card(tab, tint)
            card.setFixedHeight(92)
            cl = QVBoxLayout(card)
            cl.setContentsMargins(50, 12, 14, 12)
            cl.setSpacing(1)
            lab = QLabel(name)
            lab.setStyleSheet(f"background:transparent;color:{INK2};font-size:11.5px;font-weight:600;")
            cl.addWidget(lab)
            n = QLabel(f"{num}<span style='font-size:11px;color:{INK3};'> {unit}</span>")
            n.setStyleSheet(f"background:transparent;color:{INK};font-size:29px;font-weight:700;")
            cl.addWidget(n)
            (col_l if i % 2 == 0 else col_r).addWidget(card)
        grid.addLayout(col_l, 1)
        grid.addLayout(col_r, 1)
        pl.addLayout(grid)

        # 继续学习
        sec = QHBoxLayout()
        sec.setSpacing(8)
        sec.addWidget(Section())
        t = QLabel("继续学习")
        t.setStyleSheet(f"background:transparent;color:{INK};font-size:16px;font-weight:700;")
        sec.addWidget(t)
        sec.addStretch(1)
        more = QLabel("查看全部 ›")
        more.setStyleSheet(f"background:transparent;color:{INK3};font-size:11.5px;")
        sec.addWidget(more)
        pl.addLayout(sec)

        for name, sub, tab in (("【问答题】", "到期复习 22 · 待学新卡 20 · 学习中 2", TABS[0]),
                               ("工托个", "到期复习 114 · 待学新卡 105 · 学习中 9", TABS[2]),
                               ("第一章 关于人性", "到期复习 4 · 待学新卡 2 · 学习中 2", TABS[1])):
            row = Card(tab, TINTS[0])
            row.setFixedHeight(70)
            rl = QVBoxLayout(row)
            rl.setContentsMargins(18, 10, 16, 10)
            rl.setSpacing(2)
            h = QLabel(name)
            h.setStyleSheet(f"background:transparent;color:{INK};font-size:15.5px;font-weight:700;")
            rl.addWidget(h)
            s = QLabel(sub)
            s.setStyleSheet(f"background:transparent;color:{INK2};font-size:11px;")
            rl.addWidget(s)
            pl.addWidget(row)

        pl.addStretch(1)
        lay.addWidget(page, 1)
        lay.addWidget(Dock())


w = Main()
w.resize(430, 880)
w.show()
app.processEvents()
w.grab().save(os.path.join(APP, "shots", "planner-mock.png"))
print("saved planner-mock")
