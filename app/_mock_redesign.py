# -*- coding: utf-8 -*-
"""「池塘纸感」平涂改版效果图：今日 / 记忆 / 设置·外观 + 7 套平涂主题。

设计要点：
- 不用渐变：主题深色色带 + 奶油纸底 + 主题深色 dock；
- 状态栏 / 手势条 = 主题深色，和色带、dock 完全同色（白图标）；
- 厚描边卡片（1.5px 墨线 + 硬投影）+ 奶油黄点缀 + 青蛙吉祥物 + 池塘波浪；
- 7 套平涂主题：极光 / 冰川 / 薄荷 / 香槟 / 丁香 / 珊瑚 / 潟湖。
"""
import os
import sys

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
os.environ.setdefault("QT_QPA_FONTDIR", r"C:\Windows\Fonts")
APP = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, APP)

from PySide6.QtCore import QRectF, QPointF, Qt
from PySide6.QtGui import (QColor, QFont, QFontMetrics, QImage, QLinearGradient,
                           QPainter, QPainterPath, QPen)
from PySide6.QtWidgets import QApplication

app = QApplication([])
app.setFont(QFont("Microsoft YaHei UI", 9))

FONT = "Microsoft YaHei UI"
SHOTS = os.path.join(APP, "shots")
S = 1.5
W, H = 430, 880

BUTTER = "#F2C14E"
INK = "#211B1C"
CARD = "#FFFDF8"
INK2 = "#6F5F60"
FROG = "#2F7A4F"
CORAL = "#E76F51"

THEMES = [
    ("aurora", "极光", "#B23A5B", "#F8E9E6"),
    ("ice", "冰川", "#2E5E8C", "#EAF1F7"),
    ("mint", "薄荷", "#2F7A4F", "#EAF4EC"),
    ("champ", "香槟", "#A9761C", "#F8F0E1"),
    ("lilac", "丁香", "#6B4EA8", "#F1ECF8"),
    ("coral", "珊瑚", "#C4562E", "#F9ECE4"),
    ("lagoon", "潟湖", "#0F7C86", "#E8F4F5"),
]
SEL = 0
DEEP, PAGE, NAME = THEMES[SEL][2], THEMES[SEL][3], THEMES[SEL][1]


def fnt(px, bold=False, spacing=0.0):
    f = QFont(FONT)
    f.setPixelSize(int(px))
    f.setBold(bold)
    if spacing:
        f.setLetterSpacing(QFont.AbsoluteSpacing, spacing)
    return f


def txt(p, rect, s, px, color, bold=False, align=Qt.AlignLeft | Qt.AlignVCenter,
        spacing=0.0):
    p.setFont(fnt(px, bold, spacing))
    p.setPen(QColor(color))
    p.drawText(QRectF(rect), align, s)


def rr(p, rect, r, fill, pen=None):
    p.setPen(pen if pen is not None else Qt.NoPen)
    p.setBrush(QColor(fill) if isinstance(fill, str) else fill)
    p.drawRoundedRect(QRectF(rect), r, r)


def sticker(p, rect, fill=CARD, r=18, border=INK, shadow=True):
    rect = QRectF(rect)
    if shadow:
        sh = QRectF(rect.left() + 2.5, rect.top() + 3, rect.width(), rect.height())
        p.setPen(Qt.NoPen)
        p.setBrush(QColor(33, 27, 28, 30))
        p.drawRoundedRect(sh, r, r)
    p.setPen(QPen(QColor(border), 1.5))
    p.setBrush(QColor(fill))
    p.drawRoundedRect(rect, r, r)


def wave(p, w, y, color):
    path = QPainterPath()
    path.moveTo(0, y + 14)
    for i in range(3):
        x0 = i * w / 3
        x1 = (i + 1) * w / 3
        path.cubicTo(x0 + w / 12, y - 7, x1 - w / 12, y - 7, x1, y + 14)
    path.lineTo(w, y + 42)
    path.lineTo(0, y + 42)
    path.closeSubpath()
    p.setPen(Qt.NoPen)
    p.setBrush(QColor(color))
    p.drawPath(path)


def frog(p, x, y, s, body, belly, eye="#FFFDF8", pupil=INK, smile=INK):
    p.setPen(Qt.NoPen)
    # 身体
    p.setBrush(QColor(body))
    p.drawEllipse(QRectF(x, y + s * 0.26, s, s * 0.74))
    # 肚皮
    p.setBrush(QColor(belly))
    p.drawEllipse(QRectF(x + s * 0.17, y + s * 0.46, s * 0.66, s * 0.44))
    # 眼包
    p.setBrush(QColor(body))
    p.drawEllipse(QRectF(x + s * 0.06, y + s * 0.05, s * 0.38, s * 0.38))
    p.drawEllipse(QRectF(x + s * 0.56, y + s * 0.05, s * 0.38, s * 0.38))
    # 眼白 + 瞳孔
    p.setBrush(QColor(eye))
    p.drawEllipse(QRectF(x + s * 0.13, y + s * 0.12, s * 0.24, s * 0.24))
    p.drawEllipse(QRectF(x + s * 0.63, y + s * 0.12, s * 0.24, s * 0.24))
    p.setBrush(QColor(pupil))
    p.drawEllipse(QRectF(x + s * 0.20, y + s * 0.19, s * 0.11, s * 0.13))
    p.drawEllipse(QRectF(x + s * 0.70, y + s * 0.19, s * 0.11, s * 0.13))
    # 嘴
    pen = QPen(QColor(smile), max(1.2, s * 0.055), Qt.SolidLine, Qt.RoundCap)
    p.setPen(pen)
    p.setBrush(Qt.NoBrush)
    p.drawArc(QRectF(x + s * 0.24, y + s * 0.42, s * 0.52, s * 0.32), 200 * 16, 140 * 16)
    # 腮红
    p.setPen(Qt.NoPen)
    p.setBrush(QColor(BUTTER))
    p.setOpacity(0.85)
    p.drawEllipse(QRectF(x + s * 0.06, y + s * 0.52, s * 0.14, s * 0.10))
    p.drawEllipse(QRectF(x + s * 0.80, y + s * 0.52, s * 0.14, s * 0.10))
    p.setOpacity(1.0)


def chevron(p, x, y, color, s=4.0, w=1.6):
    p.setPen(QPen(QColor(color), w, Qt.SolidLine, Qt.RoundCap, Qt.RoundJoin))
    p.setBrush(Qt.NoBrush)
    p.drawLine(QPointF(x - s / 2, y - s / 2), QPointF(x + s / 2, y))
    p.drawLine(QPointF(x + s / 2, y), QPointF(x - s / 2, y + s / 2))


def icon_clock(p, r, color):
    p.setPen(QPen(QColor(color), 1.5, Qt.SolidLine, Qt.RoundCap))
    p.setBrush(Qt.NoBrush)
    p.drawEllipse(r.adjusted(1, 1, -1, -1))
    p.drawLine(r.center(), QPointF(r.center().x(), r.top() + 4))
    p.drawLine(r.center(), QPointF(r.center().x() + 3.6, r.center().y() + 2.4))


def icon_check(p, r, color):
    p.setPen(QPen(QColor(color), 1.9, Qt.SolidLine, Qt.RoundCap, Qt.RoundJoin))
    p.setBrush(Qt.NoBrush)
    path = QPainterPath()
    path.moveTo(r.left() + 3, r.center().y())
    path.lineTo(r.center().x() - 1, r.bottom() - 4)
    path.lineTo(r.right() - 3, r.top() + 4)
    p.drawPath(path)


def icon_cards(p, r, color):
    p.setPen(QPen(QColor(color), 1.5, Qt.SolidLine, Qt.RoundCap, Qt.RoundJoin))
    p.setBrush(Qt.NoBrush)
    p.drawRoundedRect(r.adjusted(3.6, 1.2, -0.8, -2.4), 2.4, 2.4)
    p.drawRoundedRect(r.adjusted(0.8, 3.4, -3.6, -0.8), 2.4, 2.4)


def icon_cal(p, r, color):
    p.setPen(QPen(QColor(color), 1.5, Qt.SolidLine, Qt.RoundCap, Qt.RoundJoin))
    p.setBrush(Qt.NoBrush)
    p.drawRoundedRect(r.adjusted(1, 2.4, -1, -1), 2.6, 2.6)
    p.drawLine(QPointF(r.left() + 1.2, r.top() + 6.4), QPointF(r.right() - 1.2, r.top() + 6.4))
    p.drawLine(QPointF(r.left() + 4.6, r.top() + 0.8), QPointF(r.left() + 4.6, r.top() + 3.6))
    p.drawLine(QPointF(r.right() - 4.6, r.top() + 0.8), QPointF(r.right() - 4.6, r.top() + 3.6))


def icon_folder(p, r, color):
    p.setPen(QPen(QColor(color), 1.5, Qt.SolidLine, Qt.RoundCap, Qt.RoundJoin))
    p.setBrush(Qt.NoBrush)
    path = QPainterPath()
    path.moveTo(r.left(), r.top() + 3)
    path.lineTo(r.left(), r.bottom() - 2)
    path.lineTo(r.right(), r.bottom() - 2)
    path.lineTo(r.right(), r.top() + 3.5)
    path.lineTo(r.center().x(), r.top() + 3.5)
    path.lineTo(r.center().x() - 2, r.top() + 1.5)
    path.lineTo(r.left(), r.top() + 1.5)
    path.closeSubpath()
    p.drawPath(path)


def icon_file(p, r, color):
    p.setPen(QPen(QColor(color), 1.5, Qt.SolidLine, Qt.RoundCap, Qt.RoundJoin))
    p.setBrush(Qt.NoBrush)
    p.drawRoundedRect(r.adjusted(2, 1, -2, -1), 2, 2)
    p.drawLine(QPointF(r.left() + 4, r.top() + 5), QPointF(r.right() - 4, r.top() + 5))
    p.drawLine(QPointF(r.left() + 4, r.center().y() + 1), QPointF(r.right() - 4, r.center().y() + 1))


def icon_search(p, r, color):
    p.setPen(QPen(QColor(color), 1.6, Qt.SolidLine, Qt.RoundCap))
    p.setBrush(Qt.NoBrush)
    p.drawEllipse(QRectF(r.left() + 1, r.top() + 1, r.width() - 6, r.height() - 6))
    p.drawLine(QPointF(r.left() + r.width() - 5, r.top() + r.height() - 5),
               QPointF(r.right(), r.bottom()))


def icon_more(p, x, y, color):
    p.setPen(Qt.NoPen)
    p.setBrush(QColor(color))
    for dx in (-5, 0, 5):
        p.drawEllipse(QPointF(x + dx, y), 1.4, 1.4)


def status(p):
    p.fillRect(QRectF(0, 0, W, 28), QColor(DEEP))
    txt(p, QRectF(16, 4, 70, 20), "20:26", 9.5, "#FFFDF8", True)
    # 信号条
    p.setPen(Qt.NoPen)
    p.setBrush(QColor("#FFFDF8"))
    for i, hh in enumerate((4, 7, 10, 13)):
        p.drawRoundedRect(QRectF(W - 118 + i * 4.2, 19 - hh, 3, hh), 1.2, 1.2)
    # wifi（小扇形）
    p.setPen(QPen(QColor("#FFFDF8"), 1.5, Qt.SolidLine, Qt.RoundCap))
    p.setBrush(Qt.NoBrush)
    for rad in (1.8, 4.2, 6.6):
        p.drawArc(QRectF(W - 95 - rad, 18 - rad, rad * 2, rad * 2), 45 * 16, 90 * 16)
    # 电池
    p.setPen(QPen(QColor("#FFFDF8"), 1.3))
    p.setBrush(Qt.NoBrush)
    p.drawRoundedRect(QRectF(W - 76, 8, 20, 11), 2.5, 2.5)
    p.setPen(Qt.NoPen)
    p.setBrush(QColor("#FFFDF8"))
    p.drawRoundedRect(QRectF(W - 74, 10, 14, 7), 1.2, 1.2)
    txt(p, QRectF(W - 52, 5, 40, 18), "46%", 8, "#FFFDF8", True)


def band_head(p, title, sub, band_bottom, height=26):
    p.fillRect(QRectF(0, 0, W, band_bottom), QColor(DEEP))
    status(p)
    # wordmark
    frog(p, 18, 40, 22, BUTTER, "#FFE9BD", "#FFFDF8", DEEP, DEEP)
    txt(p, QRectF(46, 36, 100, 14), "FROGLOG", 7.5, "#FFE9BD", True, spacing=1.8)
    txt(p, QRectF(46, 47, 80, 18), "蛙记 · 池塘纸感", 9, "#FFFDF8", True)
    # sync pill
    rr(p, QRectF(W - 138, 36, 122, 22), 11, QColor(255, 253, 248, 48))
    p.setPen(Qt.NoPen)
    p.setBrush(QColor(BUTTER))
    p.drawEllipse(QRectF(W - 128, 43, 7, 7))
    txt(p, QRectF(W - 116, 38, 96, 18), "有未同步的修改", 8, "#FFFDF8", True)
    txt(p, QRectF(20, 78, 260, 18), title, 25, "#FFFDF8", True)
    if sub:
        txt(p, QRectF(20, 106, 260, 18), sub, 9.5, "#FFE9BD")
    wave(p, W, band_bottom, PAGE)


def ring(p, rect, frac, track_alpha=52, label="5/8", cap="今日"):
    p.setPen(QPen(QColor(255, 253, 248, track_alpha), 6))
    p.setBrush(Qt.NoBrush)
    p.drawArc(QRectF(rect).adjusted(4, 4, -4, -4), 0, 360 * 16)
    p.setPen(QPen(QColor(BUTTER), 6, Qt.SolidLine, Qt.RoundCap))
    p.drawArc(QRectF(rect).adjusted(4, 4, -4, -4), 90 * 16, -int(360 * 16 * frac))
    txt(p, rect, label, 13, "#FFFDF8", True, Qt.AlignCenter)
    txt(p, QRectF(rect.left(), rect.bottom() - 15, rect.width(), 14), cap, 7.5,
        "#FFE9BD", False, Qt.AlignCenter)


def dock(p, active):
    p.fillRect(QRectF(0, 798, W, 82), QColor(DEEP))
    # 顶部圆角
    path = QPainterPath()
    path.addRoundedRect(QRectF(0, 798, W, 64), 22, 22)
    p.fillRect(QRectF(0, 822, W, 58), QColor(DEEP))
    p.setPen(Qt.NoPen)
    p.setBrush(QColor(DEEP))
    p.drawPath(path)
    items = [("today", "今日"), ("library", "记忆"), ("plan", "征途"), ("insights", "细数")]
    cw = W / 4
    for i, (key, name) in enumerate(items):
        cx = cw * i + cw / 2
        if key == active:
            rr(p, QRectF(cx - 31, 808, 62, 40), 14, "#FFF3D6")
            col = DEEP
        else:
            col = "#FFFDF8"
        # icons
        r = QRectF(cx - 7, 814, 14, 14)
        p.setPen(QPen(QColor(col), 1.5, Qt.SolidLine, Qt.RoundCap, Qt.RoundJoin))
        p.setBrush(Qt.NoBrush)
        if key == "today":
            p.drawEllipse(r.adjusted(2, 2, -2, -2))
            for a in range(8):
                import math
                ang = a * math.pi / 4
                p.drawLine(QPointF(cx + math.cos(ang) * 7.4, r.center().y() + math.sin(ang) * 7.4),
                           QPointF(cx + math.cos(ang) * 9.2, r.center().y() + math.sin(ang) * 9.2))
        elif key == "library":
            p.drawRoundedRect(r.adjusted(1, 0.4, -1, -0.4), 2.2, 2.2)
            p.drawLine(QPointF(r.left() + 4, r.center().y()), QPointF(r.right() - 4, r.center().y()))
        elif key == "plan":
            path2 = QPainterPath()
            path2.moveTo(cx - 6, r.bottom())
            path2.lineTo(cx - 2, r.top() + 2)
            path2.lineTo(cx + 3, r.top() + 2)
            path2.lineTo(cx + 6, r.bottom())
            path2.closeSubpath()
            p.drawPath(path2)
        else:
            for k, hh in enumerate((4, 8, 12)):
                xx = r.left() + 2 + k * 4
                p.drawLine(QPointF(xx, r.bottom()), QPointF(xx, r.bottom() - hh))
        txt(p, QRectF(cx - cw / 2, 834, cw, 16), name, 9, col, key == active, Qt.AlignCenter)
    # 手势条
    rr(p, QRectF(W / 2 - 50, 870, 100, 4), 2, QColor(255, 253, 248, 190))


def panel_today():
    img = QImage(int(W * S), int(H * S), QImage.Format_ARGB32)
    img.fill(QColor(PAGE))
    p = QPainter(img)
    p.setRenderHint(QPainter.Antialiasing)
    p.setRenderHint(QPainter.TextAntialiasing)
    p.scale(S, S)

    band_head(p, "今天，吃掉那只青蛙", "11 月 27 日 · 周五 · 今天还差 3 张", 210)
    # 标题最后四个字奶油黄
    fm = QFontMetrics(fnt(25, True))
    x = 20 + fm.horizontalAdvance("今天，吃掉")
    txt(p, QRectF(x, 78, 180, 30), "那只青蛙", 25, BUTTER, True)
    ring(p, QRectF(W - 104, 74, 78, 78), 0.62, 52, "5/8", "今日")

    # 今日青蛙卡
    sticker(p, QRectF(16, 226, W - 32, 98), CARD, 18)
    frog(p, 30, 242, 46, FROG, BUTTER, "#FFFDF8", INK, INK)
    txt(p, QRectF(90, 240, 210, 24), "今天还差 3 张", 17, INK, True)
    txt(p, QRectF(90, 266, 200, 18), "待复习 2 · 待学新卡 1", 9.5, INK2)
    rr(p, QRectF(298, 252, 104, 34), 17, DEEP)
    txt(p, QRectF(298, 252, 104, 34), "继续学习", 10.5, "#FFFDF8", True, Qt.AlignCenter)
    rr(p, QRectF(90, 290, 250, 6), 3, "#EBD9D6")
    rr(p, QRectF(90, 290, 155, 6), 3, BUTTER)

    # 四宫格
    metrics = [
        ("clock", "待复习卡片", "2", "张", "#F6DCE0", DEEP),
        ("check", "今日已学", "6", "张", "#FCEBC4", "#9A6B12"),
        ("cards", "待学新卡", "5", "张", "#DCEFE2", FROG),
        ("cal", "已到期", "0", "张", "#F7DFD3", CORAL),
    ]
    cw, ch, gap = (W - 32 - 10) / 2, 86, 10
    for i, (ic, label, num, unit, tint, icol) in enumerate(metrics):
        x0 = 16 + (i % 2) * (cw + gap)
        y0 = 336 + (i // 2) * (ch + gap)
        sticker(p, QRectF(x0, y0, cw, ch), CARD, 16)
        rr(p, QRectF(x0 + 12, y0 + 12, 28, 28), 9, tint)
        r = QRectF(x0 + 19, y0 + 19, 14, 14)
        if ic == "clock":
            icon_clock(p, r, icol)
        elif ic == "check":
            icon_check(p, r, icol)
        elif ic == "cards":
            icon_cards(p, r, icol)
        else:
            icon_cal(p, r, icol)
        txt(p, QRectF(x0 + 48, y0 + 12, cw - 64, 18), label, 9.5, INK2)
        chevron(p, x0 + cw - 16, y0 + 21, INK2, 3.4, 1.4)
        txt(p, QRectF(x0 + 12, y0 + 44, 110, 34), num, 27, INK, True)
        txt(p, QRectF(x0 + 50, y0 + 54, 24, 18), unit, 8.5, INK2)

    # 最近 7 天
    txt(p, QRectF(16, 530, 180, 18), "最近 7 天", 10.5, INK, True)
    txt(p, QRectF(W - 136, 530, 120, 18), "连续 12 天 · 今天 6 张", 8.5, INK2, False,
        Qt.AlignRight)
    for i in range(7):
        x = 24 + i * 56
        active = i == 6
        frog(p, x, 552, 20, BUTTER if active else FROG, "#FFFDF8" if active else BUTTER,
             "#FFFDF8", INK, INK)
        txt(p, QRectF(x - 4, 576, 30, 14), "一二三四五六日"[i], 7.5,
            INK if active else INK2, active, Qt.AlignCenter)

    # 继续学习
    txt(p, QRectF(16, 606, 160, 20), "继续学习", 12.5, INK, True)
    txt(p, QRectF(W - 126, 606, 110, 18), "查看全部 ›", 8.5, DEEP, True, Qt.AlignRight)
    rows = [
        ("第一章 关于人性", "到期复习 3 · 待学新卡 2 · 学习中 2", "3 到期"),
        ("手冲", "到期复习 0 · 待学新卡 0 · 学习中 1", "1 学习中"),
    ]
    for i, (name, meta, due) in enumerate(rows):
        y0 = 630 + i * 72
        sticker(p, QRectF(16, y0, W - 32, 64), CARD, 15)
        rr(p, QRectF(16, y0 + 14, 4, 36), 2, DEEP)
        txt(p, QRectF(30, y0 + 10, 220, 22), name, 12.5, INK, True)
        txt(p, QRectF(30, y0 + 35, 260, 18), meta, 8.5, INK2)
        rr(p, QRectF(W - 100, y0 + 20, 62, 24), 12, "#FCEBC4")
        txt(p, QRectF(W - 100, y0 + 20, 62, 24), due, 8, "#9A6B12", True, Qt.AlignCenter)
        chevron(p, W - 26, y0 + 32, INK2, 3.6, 1.5)

    dock(p, "today")
    p.end()
    return img


def panel_memory():
    img = QImage(int(W * S), int(H * S), QImage.Format_ARGB32)
    img.fill(QColor(PAGE))
    p = QPainter(img)
    p.setRenderHint(QPainter.Antialiasing)
    p.setRenderHint(QPainter.TextAntialiasing)
    p.scale(S, S)

    p.fillRect(QRectF(0, 0, W, 200), QColor(DEEP))
    status(p)
    frog(p, 18, 40, 22, BUTTER, "#FFE9BD", "#FFFDF8", DEEP, DEEP)
    txt(p, QRectF(46, 36, 100, 14), "FROGLOG", 7.5, "#FFE9BD", True, spacing=1.8)
    txt(p, QRectF(46, 47, 80, 18), "蛙记 · 池塘纸感", 9, "#FFFDF8", True)
    txt(p, QRectF(20, 78, 240, 34), "记忆", 26, "#FFFDF8", True)
    txt(p, QRectF(20, 112, 320, 18), "3 个知识域 · 4 个文件 · 150 张卡片", 9.5, "#FFE9BD")
    # 右上角新建
    rr(p, QRectF(W - 52, 38, 34, 34), 17, QColor(255, 253, 248, 52),
       QPen(QColor(255, 253, 248, 150), 1.2))
    p.setPen(QPen(QColor("#FFFDF8"), 1.8, Qt.SolidLine, Qt.RoundCap))
    p.drawLine(QPointF(W - 44, 55), QPointF(W - 26, 55))
    p.drawLine(QPointF(W - 35, 46), QPointF(W - 35, 64))
    wave(p, W, 200, PAGE)

    # 知识域
    chips = [("微信读书", True), ("工作", False), ("生活", False)]
    x = 16
    for name, active in chips:
        wid = 78 if name == "微信读书" else 60
        rr(p, QRectF(x, 214, wid, 30), 15, "#FFF3D6" if active else CARD,
           QPen(QColor(INK), 1.4))
        txt(p, QRectF(x, 214, wid, 30), name, 10, INK if active else INK2,
            active, Qt.AlignCenter)
        x += wid + 8

    # 搜索
    sticker(p, QRectF(16, 256, W - 32, 38), CARD, 13, shadow=False)
    icon_search(p, QRectF(30, 265, 18, 18), INK2)
    txt(p, QRectF(56, 262, 300, 24), "搜索圆桌、文件或卡片", 10, INK2)

    rows = [
        ("folder", "考试冲刺", "2026年10月21日 · 2 个文件", "#FCEBC4", "#9A6B12"),
        ("file", "有道暗记", "2026年10月11日 · 143 张卡片", "#F6DCE0", DEEP),
        ("file", "—", "2026年11月11日 · 0 张卡片", "#EFEBDE", "#8C8878"),
    ]
    y = 310
    for kind, title, meta, tint, icol in rows:
        sticker(p, QRectF(16, y, W - 32, 74), CARD, 16)
        rr(p, QRectF(24, y + 13, 44, 44), 12, tint)
        ir = QRectF(34, y + 23, 24, 24)
        if kind == "folder":
            icon_folder(p, ir, icol)
        else:
            icon_file(p, ir, icol)
        txt(p, QRectF(82, y + 13, 250, 24), title, 13, INK, True)
        txt(p, QRectF(82, y + 41, 270, 18), meta, 9, INK2)
        icon_more(p, W - 30, y + 37, INK2)
        y += 84

    # 新建文件（虚线卡）
    p.setPen(QPen(QColor(INK2), 1.5, Qt.DashLine))
    p.setBrush(Qt.NoBrush)
    p.drawRoundedRect(QRectF(16, y + 10, W - 32, 76), 16, 16)
    rr(p, QRectF(32, y + 28, 36, 36), 12, "#FCEBC4")
    p.setPen(QPen(QColor("#9A6B12"), 1.8, Qt.SolidLine, Qt.RoundCap))
    p.drawLine(QPointF(50, y + 37), QPointF(50, y + 55))
    p.drawLine(QPointF(41, y + 46), QPointF(59, y + 46))
    txt(p, QRectF(82, y + 26, 240, 22), "新建文件", 11.5, INK, True)
    txt(p, QRectF(82, y + 48, 260, 18), "新建卡包 / 导入 Word", 8.5, INK2)

    dock(p, "library")
    p.end()
    return img


def theme_card(p, rect, deep, page, name, selected):
    sticker(p, rect, CARD, 14, shadow=not selected)
    # 迷你色带
    path = QPainterPath()
    path.addRoundedRect(QRectF(rect.left() + 4, rect.top() + 4, rect.width() - 8,
                               rect.height() - 8), 11, 11)
    p.save()
    p.setClipPath(path)
    p.fillRect(QRectF(rect.left(), rect.top(), rect.width(), 30), QColor(deep))
    p.fillRect(QRectF(rect.left(), rect.top() + 30, rect.width(), rect.height() - 30),
               QColor(page))
    # 迷你白卡 + dock
    p.setPen(Qt.NoPen)
    p.setBrush(QColor(CARD))
    p.drawRoundedRect(QRectF(rect.left() + 12, rect.top() + 36, rect.width() - 24, 22), 6, 6)
    p.setBrush(QColor(deep))
    p.drawRoundedRect(QRectF(rect.left() + 12, rect.bottom() - 20, rect.width() - 24, 10),
                      5, 5)
    p.restore()
    # 顶栏文字
    txt(p, QRectF(rect.left() + 10, rect.top() + 5, rect.width() - 30, 20), name, 9,
        "#FFFDF8", True)
    frog(p, rect.right() - 30, rect.top() + 7, 16, BUTTER, "#FFE9BD", "#FFFDF8", deep, deep)
    if selected:
        p.setPen(QPen(QColor(INK), 2.2))
        p.setBrush(Qt.NoBrush)
        p.drawRoundedRect(QRectF(rect).adjusted(0.5, 0.5, -0.5, -0.5), 14, 14)
        p.setPen(Qt.NoPen)
        p.setBrush(QColor(BUTTER))
        p.drawEllipse(QRectF(rect.right() - 27, rect.top() + 6, 18, 18))
        txt(p, QRectF(rect.right() - 27, rect.top() + 6, 18, 18), "✓", 9, INK, True,
            Qt.AlignCenter)


def panel_settings():
    img = QImage(int(W * S), int(H * S), QImage.Format_ARGB32)
    img.fill(QColor(PAGE))
    p = QPainter(img)
    p.setRenderHint(QPainter.Antialiasing)
    p.setRenderHint(QPainter.TextAntialiasing)
    p.scale(S, S)

    p.fillRect(QRectF(0, 0, W, 180), QColor(DEEP))
    status(p)
    frog(p, 18, 40, 22, BUTTER, "#FFE9BD", "#FFFDF8", DEEP, DEEP)
    txt(p, QRectF(46, 36, 100, 14), "FROGLOG", 7.5, "#FFE9BD", True, spacing=1.8)
    txt(p, QRectF(46, 47, 80, 18), "蛙记 · 池塘纸感", 9, "#FFFDF8", True)
    txt(p, QRectF(20, 78, 240, 34), "设置", 26, "#FFFDF8", True)
    txt(p, QRectF(20, 112, 320, 18), "外观 · 7 套平涂主题", 9.5, "#FFE9BD")
    wave(p, W, 180, PAGE)

    txt(p, QRectF(20, 196, 120, 18), "外观", 10, INK2, True, spacing=1.2)
    # 主题卡
    sticker(p, QRectF(16, 218, W - 32, 398), CARD, 18)
    txt(p, QRectF(32, 230, 160, 22), "主题", 13, INK, True)
    rr(p, QRectF(W - 74, 231, 42, 20), 10, "#FCEBC4")
    txt(p, QRectF(W - 74, 231, 42, 20), "7 套", 8, "#9A6B12", True, Qt.AlignCenter)
    for i, (key, name, deep, page) in enumerate(THEMES):
        x0 = 32 + (i % 2) * 182
        y0 = 260 + (i // 2) * 84
        theme_card(p, QRectF(x0, y0, 168, 74), deep, page, name, key == THEMES[SEL][0])
    txt(p, QRectF(32, 588, W - 64, 16),
        "7 套平涂主题；状态栏 / 手势条 = 主题深色；无渐变。", 8, INK2)

    txt(p, QRectF(20, 632, 120, 18), "每日节奏", 10, INK2, True, spacing=1.2)
    for i, (title, sub) in enumerate((("学习调度", "学习步骤 / 间隔 / 每日上限 / 保持率"),
                                     ("今日进度", "新卡 20 · 复习 1 · 保持率 90%"))):
        sticker(p, QRectF(16, 654 + i * 60, W - 32, 50), CARD, 13)
        txt(p, QRectF(30, 662 + i * 60, 200, 18), title, 10, INK, True)
        txt(p, QRectF(30, 680 + i * 60, 280, 16), sub, 8, INK2)
        chevron(p, W - 28, 679 + i * 60, INK2, 3.4, 1.4)

    # 系统手势条（settings 没有 dock）
    p.fillRect(QRectF(0, 862, W, 18), QColor(DEEP))
    rr(p, QRectF(W / 2 - 50, 869, 100, 4), 2, QColor(255, 253, 248, 190))
    p.end()
    return img


def theme_swatch(p, rect, deep, page, name, selected):
    sticker(p, rect, CARD, 14, shadow=not selected)
    path = QPainterPath()
    path.addRoundedRect(QRectF(rect.left() + 4, rect.top() + 4, rect.width() - 8,
                               rect.height() - 8), 11, 11)
    p.save()
    p.setClipPath(path)
    p.fillRect(QRectF(rect.left(), rect.top(), rect.width(), 38), QColor(deep))
    p.fillRect(QRectF(rect.left(), rect.top() + 38, rect.width(), rect.height() - 38),
               QColor(page))
    p.setPen(Qt.NoPen)
    p.setBrush(QColor(CARD))
    p.drawRoundedRect(QRectF(rect.left() + 12, rect.top() + 46, rect.width() - 24, 22), 6, 6)
    p.restore()
    txt(p, QRectF(rect.left() + 10, rect.top() + 8, rect.width() - 30, 22), name, 10,
        "#FFFDF8", True)
    frog(p, rect.right() - 32, rect.top() + 9, 18, BUTTER, "#FFE9BD", "#FFFDF8", deep, deep)
    if selected:
        p.setPen(QPen(QColor(INK), 2.2))
        p.setBrush(Qt.NoBrush)
        p.drawRoundedRect(QRectF(rect).adjusted(0.5, 0.5, -0.5, -0.5), 14, 14)


# ------------------------------------------------------------------ 拼图
today = panel_today()
memory = panel_memory()
settings = panel_settings()

W_SHEET = 1442
H_SHEET = 1260
sheet = QImage(int(W_SHEET * S), int(H_SHEET * S), QImage.Format_ARGB32)
sheet.fill(QColor("#F3EEE2"))
sp = QPainter(sheet)
sp.setRenderHint(QPainter.Antialiasing)
sp.scale(S, S)

# 页眉
frog(sp, 40, 22, 30, FROG, BUTTER, "#FFFDF8", INK, INK)
txt(sp, QRectF(80, 18, 700, 34), "FrogLog · 蛙记 — 池塘纸感改版", 25, INK, True)
txt(sp, QRectF(80, 52, 900, 20),
    "去掉渐变 · 主题深色色带 / dock · 奶油纸底 · 厚描边卡片 · 奶油黄 + 青蛙吉祥物",
    10.5, INK2)
txt(sp, QRectF(1000, 34, 402, 20), "设计提案 · 2026-11-27", 10, "#8C8478", False,
    Qt.AlignRight)

titles = ["01　今日 · 新首页", "02　记忆 · 文件列表", "03　设置 · 外观（7 套平涂）"]
for i, t in enumerate(titles):
    txt(sp, QRectF(40 + i * 466, 96, 430, 20), t, 12, INK, True)

for x, img in zip((40, 506, 972), (today, memory, settings)):
    sp.drawImage(QRectF(x, 124, W, H), img)
    sp.setPen(QPen(QColor(33, 27, 28, 40), 1))
    sp.setBrush(Qt.NoBrush)
    sp.drawRoundedRect(QRectF(x - 1, 123, W + 2, H + 2), 6, 6)

# 7 套主题
txt(sp, QRectF(40, 1032, 600, 24), "7 套平涂主题 · 状态栏 / dock / 手势条同色", 12,
    INK, True)
txt(sp, QRectF(1000, 1034, 402, 18), "白图标 · 无渐变 · 深色主题色", 9, INK2, False,
    Qt.AlignRight)
tw, th, gap = 180, 96, 16
start = (W_SHEET - (7 * tw + 6 * gap)) / 2
for i, (key, name, deep, page) in enumerate(THEMES):
    x = start + i * (tw + gap)
    theme_swatch(sp, QRectF(x, 1064, tw, th), deep, page, name, key == THEMES[SEL][0])

txt(sp, QRectF(40, 1196, 1362, 18),
    "状态栏 / 手势条 = 主题深色，和顶部色带、底部 dock 完全同色；卡片 1.5px 墨线 + 硬投影；"
    "主色 #B23A5B（极光）· 奶油黄 #F2C14E · 纸底 #F8E9E6 · 墨 #211B1C。",
    9.5, INK2)
sp.end()

out = os.path.join(SHOTS, "redesign-pond-flat.png")
sheet.save(out)
print("saved", out, sheet.width(), sheet.height())
