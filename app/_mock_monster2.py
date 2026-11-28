# -*- coding: utf-8 -*-
"""怪物吃青蛙 · 两张效果图：征途页（右上角入口） + 怪物图鉴页。"""
import os, sys, math
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
os.environ.setdefault("QT_QPA_FONTDIR", r"C:\Windows\Fonts")
APP = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, APP)
from PySide6.QtWidgets import (QApplication, QWidget, QVBoxLayout, QHBoxLayout,
                               QLabel, QGridLayout, QFrame)
from PySide6.QtCore import Qt, QRectF, QPointF
from PySide6.QtGui import (QColor, QPainter, QPen, QFont, QPainterPath, QBrush,
                           QPolygonF, QLinearGradient)
import theme

app = QApplication(sys.argv)
T = theme.theme_tokens("anki-lagoon")
DEEP, PAPER, PANEL, INK, INK2, INK3, LINE = (
    T["deep"], T["page"], T["panel"], T["ink"], T["ink2"], T["ink3"], T["line"])
FONT = "KaiTi"
RED = "#D9533F"

LEVELS = [
    ("1", "青泡泡", 0, "#6FAE7A", "青"),
    ("2", "蓝泡泡", 5, "#5B8FD4", "蓝"),
    ("3", "紫泡泡", 15, "#8A6BC0", "紫"),
    ("4", "赤泡泡", 30, "#C4562E", "赤"),
    ("5", "金泡泡", 50, "#C9A227", "金"),
    ("6", "蛙群之王", 80, "#B23A5B", "王"),
]
EATEN, CUR = 2, 2
CUR_NAME = LEVELS[CUR - 1][1]
CUR_COLOR = LEVELS[CUR - 1][3]
NEED = LEVELS[CUR - 1][2]      # 当前等级所需的青蛙数
PREV = LEVELS[CUR - 2][2] if CUR >= 2 else 0
NEXT_NAME = LEVELS[CUR][1]


def f(size, weight=QFont.Normal):
    ft = QFont(FONT)
    ft.setPixelSize(int(size))
    ft.setWeight(weight)
    return ft


class Monster(QWidget):
    def __init__(self, size=150, color="#5B8FD4", dark="#3F6FB0",
                 mood="happy", parent=None):
        super().__init__(parent)
        self.setFixedSize(size, size + 14)
        self.s = size
        self.color = color
        self.dark = dark
        self.mood = mood

    def paintEvent(self, e):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        s = self.s
        cx, top = s / 2, 16
        p.setPen(Qt.NoPen)
        p.setBrush(QColor(0, 0, 0, 26))
        p.drawEllipse(QRectF(s * 0.18, top + s * 0.80, s * 0.64, s * 0.12))

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

        p.setPen(Qt.NoPen)
        p.setBrush(QColor(self.dark))
        p.drawPolygon(QPolygonF([QPointF(cx - s * 0.30, top + s * 0.18),
                                 QPointF(cx - s * 0.46, top - s * 0.06),
                                 QPointF(cx - s * 0.12, top + s * 0.10)]))
        p.drawPolygon(QPolygonF([QPointF(cx + s * 0.30, top + s * 0.18),
                                 QPointF(cx + s * 0.46, top - s * 0.06),
                                 QPointF(cx + s * 0.12, top + s * 0.10)]))

        grad = QLinearGradient(0, top, 0, top + s)
        c1 = QColor(self.color).lighter(118)
        grad.setColorAt(0, c1)
        grad.setColorAt(1, QColor(self.color))
        p.setBrush(QBrush(grad))
        p.drawPath(body)

        belly = QPainterPath()
        belly.moveTo(cx - s * 0.24, top + s * 0.62)
        belly.cubicTo(cx - s * 0.20, top + s * 0.40, cx + s * 0.20, top + s * 0.40,
                      cx + s * 0.24, top + s * 0.62)
        belly.cubicTo(cx + s * 0.16, top + s * 0.78, cx - s * 0.16, top + s * 0.78,
                      cx - s * 0.24, top + s * 0.62)
        p.setBrush(QColor(255, 255, 255, 40))
        p.drawPath(belly)

        p.setBrush(QColor(self.dark))
        for dx, dy, r in ((-0.34, 0.42, 0.030), (0.35, 0.38, 0.024),
                          (-0.30, 0.60, 0.020), (0.31, 0.58, 0.028)):
            p.drawEllipse(QPointF(cx + dx * s, top + dy * s), r * s, r * s)

        for ex in (-0.17, 0.17):
            p.setBrush(QColor("#FFFDF8"))
            p.drawEllipse(QPointF(cx + ex * s, top + s * 0.40), s * 0.105, s * 0.105)
            p.setBrush(QColor("#1E2A36"))
            p.drawEllipse(QPointF(cx + ex * s, top + s * 0.41), s * 0.052, s * 0.052)
            p.setBrush(QColor("#FFFFFF"))
            p.drawEllipse(QPointF(cx + ex * s + s * 0.018, top + s * 0.39),
                          s * 0.017, s * 0.017)

        mouth = QPainterPath()
        if self.mood == "sleep":
            mouth.moveTo(cx - s * 0.12, top + s * 0.64)
            mouth.quadTo(cx, top + s * 0.70, cx + s * 0.12, top + s * 0.64)
        else:
            mouth.moveTo(cx - s * 0.20, top + s * 0.60)
            mouth.quadTo(cx, top + s * 0.74, cx + s * 0.20, top + s * 0.60)
        p.setPen(QPen(QColor("#1E2A36"), s * 0.022, Qt.SolidLine, Qt.RoundCap))
        p.setBrush(QColor("#7A2E33") if self.mood != "sleep" else Qt.NoBrush)
        p.setBrush(QColor("#7A2E33") if self.mood != "sleep" else QColor(0, 0, 0, 0))
        p.drawPath(mouth)
        if self.mood != "sleep":
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


class RoundCard(QFrame):
    def __init__(self, radius=16, parent=None):
        super().__init__(parent)
        self.radius = radius

    def paintEvent(self, e):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        r = QRectF(1, 1, self.width() - 2, self.height() - 2)
        p.setPen(QPen(QColor(INK), 1.3))
        p.setBrush(QColor(PANEL))
        p.drawRoundedRect(r, self.radius, self.radius)


def chip(text, bg, fg="#FFFDF8", size=10):
    lab = QLabel(text)
    lab.setStyleSheet(f"background:{bg};color:{fg};border-radius:9px;"
                      f"font-size:{size}px;font-weight:700;padding:2px 9px;")
    return lab


class Journey(QWidget):
    """图 1：征途页，怪物卡右上角是「等级 ›」入口。"""
    def __init__(self):
        super().__init__()
        self.setObjectName("root")
        self.setStyleSheet(f"QWidget#root{{background:{PAPER};}}")
        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        band = QWidget()
        band.setFixedHeight(86)
        band.setStyleSheet(f"background:{DEEP};")
        bl = QHBoxLayout(band)
        bl.setContentsMargins(18, 8, 18, 8)
        t = QLabel("征途")
        t.setStyleSheet("color:#FFFDF8;font-family:'KaiTi';font-size:26px;font-weight:700;")
        bl.addWidget(t)
        bl.addStretch(1)
        sw = QLabel("")
        sw.setFixedSize(56, 30)
        sw.setStyleSheet("background:#FFF3D6;border-radius:15px;")
        bl.addWidget(sw)
        root.addWidget(band)

        page = QWidget()
        pl = QVBoxLayout(page)
        pl.setContentsMargins(16, 12, 16, 10)
        pl.setSpacing(10)

        task = RoundCard()
        task.setFixedHeight(64)
        tl = QHBoxLayout(task)
        tl.setContentsMargins(16, 8, 16, 8)
        tl.addWidget(QLabel("今日任务 · 00:00 已完成"))
        pl.addWidget(task)

        card = RoundCard()
        card.setFixedHeight(372)
        cl = QVBoxLayout(card)
        cl.setContentsMargins(16, 12, 16, 12)
        cl.setSpacing(6)

        head = QHBoxLayout()
        name = QLabel(CUR_NAME)
        name.setStyleSheet(f"color:{INK};font-family:'{FONT}';font-size:20px;font-weight:700;")
        head.addWidget(name)
        head.addWidget(chip(f"Lv.{CUR}", CUR_COLOR))
        head.addStretch(1)
        entry = QLabel("等级 ›")
        entry.setStyleSheet(f"background:{T['brand_soft']};color:{DEEP};border-radius:11px;"
                            "font-size:11px;font-weight:700;padding:3px 10px;")
        head.addWidget(entry)
        cl.addLayout(head)

        mon = Monster(140, CUR_COLOR, LEVELS[CUR - 1][3])
        cl.addWidget(mon, 0, Qt.AlignHCenter)

        bar = QWidget()
        bar.setFixedHeight(9)
        bar.setStyleSheet(f"background:{LINE};border-radius:4px;")
        bl2 = QHBoxLayout(bar)
        bl2.setContentsMargins(0, 0, 0, 0)
        fill = QWidget()
        fill.setStyleSheet(f"background:{RED};border-radius:4px;")
        fill.setFixedWidth(int(350 * (EATEN - PREV) / (NEED - PREV)))
        bl2.addWidget(fill)
        bl2.addStretch(1)
        cl.addWidget(bar)

        hint = QLabel(f"已吃 {EATEN} / {NEED} 只 · 再吃 {NEED - EATEN} 只升级为「{NEXT_NAME}」")
        hint.setAlignment(Qt.AlignCenter)
        hint.setStyleSheet(f"color:{INK2};font-size:10.5px;")
        cl.addWidget(hint)

        stats = QHBoxLayout()
        for k, v in (("已吃青蛙", "2 只"), ("累计学习", "30 分钟"), ("今日", "2 只")):
            box = QWidget()
            bx = QVBoxLayout(box)
            bx.setContentsMargins(0, 0, 0, 0)
            bx.setSpacing(0)
            vv = QLabel(v)
            vv.setStyleSheet(f"color:{INK};font-family:'{FONT}';font-size:17px;font-weight:700;")
            bx.addWidget(vv)
            kk = QLabel(k)
            kk.setStyleSheet(f"color:{INK3};font-size:9.5px;")
            bx.addWidget(kk)
            stats.addWidget(box, 1)
        cl.addLayout(stats)
        pl.addWidget(card)
        pl.addStretch(1)
        root.addWidget(page, 1)

        dock = QWidget()
        dock.setFixedHeight(66)
        dock.setStyleSheet(f"background:{DEEP};")
        dl = QHBoxLayout(dock)
        dl.setContentsMargins(20, 8, 20, 8)
        for i, nm in enumerate(("今日", "记忆", "征途", "战果")):
            lab = QLabel(nm)
            lab.setAlignment(Qt.AlignCenter)
            if i == 2:
                lab.setStyleSheet(f"color:{DEEP};background:#FFFDF8;border-radius:14px;"
                                  "font-size:12px;font-weight:700;padding:8px 18px;")
            else:
                lab.setStyleSheet("color:rgba(255,253,248,0.75);font-size:12px;")
            dl.addWidget(lab, 1)
        root.addWidget(dock)


class Book(QWidget):
    """图 2：右上角打开的怪物图鉴页。"""
    def __init__(self):
        super().__init__()
        self.setObjectName("book")
        self.setStyleSheet(f"QWidget#book{{background:{PAPER};}}")
        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        band = QWidget()
        band.setFixedHeight(76)
        band.setStyleSheet(f"background:{DEEP};")
        bl = QHBoxLayout(band)
        bl.setContentsMargins(18, 8, 18, 8)
        back = QLabel("‹")
        back.setFixedSize(30, 30)
        back.setAlignment(Qt.AlignCenter)
        back.setStyleSheet("color:#FFFDF8;border:1.4px solid rgba(255,253,248,0.6);"
                           "border-radius:15px;font-size:18px;")
        bl.addWidget(back)
        t = QLabel("怪物图鉴")
        t.setStyleSheet("color:#FFFDF8;font-family:'KaiTi';font-size:23px;font-weight:700;")
        bl.addWidget(t)
        bl.addStretch(1)
        cnt = QLabel("2 / 6")
        cnt.setStyleSheet("color:rgba(255,253,248,0.8);font-size:12px;")
        bl.addWidget(cnt)
        root.addWidget(band)

        page = QWidget()
        pl = QVBoxLayout(page)
        pl.setContentsMargins(16, 12, 16, 10)
        pl.setSpacing(10)

        # 当前怪物 + 进度
        cur = RoundCard()
        cur.setFixedHeight(210)
        cl = QVBoxLayout(cur)
        cl.setContentsMargins(14, 10, 14, 10)
        cl.setSpacing(4)
        head = QHBoxLayout()
        n = QLabel(CUR_NAME)
        n.setStyleSheet(f"color:{INK};font-family:'{FONT}';font-size:19px;font-weight:700;")
        head.addWidget(n)
        head.addWidget(chip(f"Lv.{CUR}", CUR_COLOR))
        head.addStretch(1)
        head.addWidget(chip("出战中", DEEP, size=9))
        cl.addLayout(head)

        row = QHBoxLayout()
        mon = Monster(96, CUR_COLOR)
        row.addWidget(mon, 0, Qt.AlignTop)
        info = QVBoxLayout()
        info.setSpacing(3)
        for k, v in (("已吃青蛙", f"{EATEN} 只"),
                     ("累计学习", "30 分钟"),
                     ("下一级", f"Lv.{CUR + 1} {NEXT_NAME}"),
                     ("还差", f"{NEED - EATEN} 只 / 约 {(NEED - EATEN) * 45} 分钟")):
            line = QLabel(f"{k}  {v}")
            line.setStyleSheet(f"color:{INK2 if k != '还差' else DEEP};font-size:11px;"
                               f"font-weight:{600 if k == '还差' else 400};")
            info.addWidget(line)
        info.addStretch(1)
        row.addLayout(info, 1)
        cl.addLayout(row)
        pl.addWidget(cur)

        # 图鉴列表
        grid = QGridLayout()
        grid.setHorizontalSpacing(10)
        grid.setVerticalSpacing(10)
        for i, (lv, name, need, color, short) in enumerate(LEVELS):
            box = RoundCard(14)
            box.setFixedHeight(118)
            bx = QVBoxLayout(box)
            bx.setContentsMargins(10, 8, 10, 8)
            bx.setSpacing(2)
            top = QHBoxLayout()
            nn = QLabel(name)
            nn.setStyleSheet(f"color:{INK if i <= 1 else INK2};font-family:'{FONT}';"
                             "font-size:12.5px;font-weight:700;")
            top.addWidget(nn)
            top.addStretch(1)
            if i == 0:
                top.addWidget(chip("已解锁", "#6FAE7A", size=8))
            elif i == 1:
                top.addWidget(chip("当前", CUR_COLOR, size=8))
            else:
                top.addWidget(chip("未解锁", LINE, INK3, size=8))
            bx.addLayout(top)
            mon2 = Monster(44, color, color, mood="sleep" if i > 1 else "happy")
            bx.addWidget(mon2, 0, Qt.AlignHCenter)
            cost = QLabel(f"需要 {need} 只 · 约 {need * 45 // 60} 小时")
            cost.setAlignment(Qt.AlignCenter)
            cost.setStyleSheet(f"color:{INK3};font-size:9px;")
            bx.addWidget(cost)
            grid.addWidget(box, i // 3, i % 3)
        pl.addLayout(grid)

        # 记录
        rec = RoundCard(14)
        rec.setFixedHeight(96)
        rl = QVBoxLayout(rec)
        rl.setContentsMargins(14, 8, 14, 8)
        rl.setSpacing(2)
        rt = QLabel("吃青蛙记录")
        rt.setStyleSheet(f"color:{INK};font-family:'{FONT}';font-size:12px;font-weight:700;")
        rl.addWidget(rt)
        for txt in ("11·28  吃掉 2 只 · 学习 30 分钟",
                    "11·27  吃掉 1 只 · 学习 45 分钟"):
            lab = QLabel(txt)
            lab.setStyleSheet(f"color:{INK2};font-size:10px;")
            rl.addWidget(lab)
        pl.addWidget(rec)

        pl.addStretch(1)
        root.addWidget(page, 1)


a = Journey(); a.resize(430, 880); a.show()
app.processEvents()
a.grab().save(os.path.join(APP, "shots", "journey-monster.png"))
b = Book(); b.resize(430, 880); b.show()
app.processEvents()
b.grab().save(os.path.join(APP, "shots", "monster-book.png"))
print("saved both")
