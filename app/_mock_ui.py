# -*- coding: utf-8 -*-
"""生成「今日」页外观效果图（两套配色方案）。"""
import os
import sys

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
APP = r"D:\我的下载\WorkBuddy库\逆向分析\ebbinghaus\app"
sys.path.insert(0, APP)

from PySide6.QtCore import QPointF, QRectF, Qt
from PySide6.QtGui import (QColor, QFont, QImage, QLinearGradient, QPainter,
                           QPainterPath, QPen)
from PySide6.QtWidgets import QApplication

qapp = QApplication([])
FONT = "Microsoft YaHei UI"

W, H = 400, 860
S = 2  # 2 倍绘制

SCHEMES = {
    "A": dict(
        name="A · 晨雾绿（沿用品牌绿）",
        paper="#F7F5EF", card="#FFFFFF", line="#EAE6DB",
        ink="#22261F", ink2="#6E7266", ink3="#A5A79B",
        brand="#2F6A43", brand_soft="#E9F1EA", brand_dark="#25542F",
        accent="#B8792A", accent_soft="#FBF0E1",
        warn="#C0392B", warn_soft="#FBEBE8",
        info="#3D7EBB", info_soft="#EAF1FA",
    ),
    "B": dict(
        name="B · 墨青蓝（换主色，更冷静）",
        paper="#F4F6F8", card="#FFFFFF", line="#E3E8EE",
        ink="#20272E", ink2="#66707A", ink3="#9AA4AE",
        brand="#2B5F7E", brand_soft="#E6EFF5", brand_dark="#1F4A63",
        accent="#B8792A", accent_soft="#FBF0E1",
        warn="#C0392B", warn_soft="#FBEBE8",
        info="#3D7EBB", info_soft="#EAF1FA",
    ),
}


def rr(p, rect, r, fill, pen=None):
    p.setPen(pen if pen is not None else Qt.NoPen)
    p.setBrush(fill)
    p.drawRoundedRect(rect, r, r)


def txt(p, rect, s, size, color, bold=False, align=Qt.AlignLeft | Qt.AlignVCenter):
    f = QFont(FONT)
    f.setPixelSize(size)
    f.setBold(bold)
    p.setFont(f)
    p.setPen(QColor(color))
    p.drawText(rect, align, s)


def shadow(p, rect, r, alpha=26):
    p.setPen(Qt.NoPen)
    p.setBrush(QColor(0, 0, 0, alpha))
    p.drawRoundedRect(rect.adjusted(0, 2, 0, 3), r, r)


def icon_clock(p, rect, color):
    pen = QPen(QColor(color), 1.7, Qt.SolidLine, Qt.RoundCap, Qt.RoundJoin)
    p.setPen(pen)
    p.setBrush(Qt.NoBrush)
    p.drawEllipse(rect.adjusted(1, 1, -1, -1))
    p.drawLine(rect.center(), QPointF(rect.center().x(), rect.top() + 4.6))
    p.drawLine(rect.center(), QPointF(rect.center().x() + 4.2, rect.center().y() + 2.6))


def icon_check(p, rect, color):
    pen = QPen(QColor(color), 1.9, Qt.SolidLine, Qt.RoundCap, Qt.RoundJoin)
    p.setPen(pen)
    p.setBrush(Qt.NoBrush)
    path = QPainterPath()
    path.moveTo(rect.left() + 3, rect.center().y())
    path.lineTo(rect.center().x() - 1, rect.bottom() - 4)
    path.lineTo(rect.right() - 3, rect.top() + 4)
    p.drawPath(path)


def icon_cards(p, rect, color):
    pen = QPen(QColor(color), 1.6, Qt.SolidLine, Qt.RoundCap, Qt.RoundJoin)
    p.setPen(pen)
    p.setBrush(Qt.NoBrush)
    p.drawRoundedRect(rect.adjusted(3.5, 1.5, -1, -1), 2.5, 2.5)
    p.drawRoundedRect(rect.adjusted(1, 3.5, -3.5, -3.5), 2.5, 2.5)


def icon_cal(p, rect, color):
    pen = QPen(QColor(color), 1.6, Qt.SolidLine, Qt.RoundCap, Qt.RoundJoin)
    p.setPen(pen)
    p.setBrush(Qt.NoBrush)
    p.drawRoundedRect(rect.adjusted(1, 2.5, -1, -1), 3, 3)
    p.drawLine(QPointF(rect.left() + 1.4, rect.top() + 6.6),
               QPointF(rect.right() - 1.4, rect.top() + 6.6))
    p.drawLine(QPointF(rect.left() + 5, rect.top() + 1), QPointF(rect.left() + 5, rect.top() + 4))
    p.drawLine(QPointF(rect.right() - 5, rect.top() + 1), QPointF(rect.right() - 5, rect.top() + 4))


def chevron(p, cx, cy, color, s=4.2):
    pen = QPen(QColor(color), 1.6, Qt.SolidLine, Qt.RoundCap, Qt.RoundJoin)
    p.setPen(pen)
    p.setBrush(Qt.NoBrush)
    path = QPainterPath()
    path.moveTo(cx - s / 2, cy - s / 2)
    path.lineTo(cx + s / 2, cy)
    path.lineTo(cx - s / 2, cy + s / 2)
    p.drawPath(path)


def stat_card(p, sch, rect, icon, label, num, unit, tint, ink_num, tint_bg):
    shadow(p, rect, 18)
    rr(p, rect, 18, QColor(sch["card"]), QPen(QColor(sch["line"]), 1))
    # 图标底座
    ib = QRectF(rect.left() + 14, rect.top() + 14, 26, 26)
    rr(p, ib, 9, QColor(tint_bg))
    icon(p, ib.adjusted(6.5, 6.5, -6.5, -6.5), tint)
    txt(p, QRectF(ib.right() + 8, ib.top() - 1, 100, 28), label, 11.5, sch["ink2"])
    chevron(p, rect.right() - 16, rect.top() + 27, sch["ink3"])
    # 数字
    p.setFont(QFont(FONT, 0))
    f = QFont(FONT)
    f.setPixelSize(29)
    f.setBold(True)
    p.setFont(f)
    p.setPen(QColor(ink_num))
    num_rect = QRectF(rect.left() + 14, ib.bottom() + 6, 130, 34)
    p.drawText(num_rect, Qt.AlignLeft | Qt.AlignVCenter, num)
    nw = p.fontMetrics().horizontalAdvance(num)
    txt(p, QRectF(num_rect.left() + nw + 5, num_rect.top() + 4, 40, 28), unit, 11.5, sch["ink3"])


def deck_card(p, sch, rect, name, sub, pct):
    shadow(p, rect, 16)
    rr(p, rect, 16, QColor(sch["card"]), QPen(QColor(sch["line"]), 1))

    # 标题行：色点 + 名称（左侧主导），查看卡组靠最右
    ghost_w = 76
    gx = rect.right() - 16 - ghost_w
    p.setPen(Qt.NoPen)
    p.setBrush(QColor(sch["brand"]))
    p.drawEllipse(QRectF(rect.left() + 16, rect.top() + 18, 7, 7))
    txt(p, QRectF(rect.left() + 30, rect.top() + 8, gx - rect.left() - 36, 28),
        name, 17, sch["ink"], bold=True)
    txt(p, QRectF(gx, rect.top() + 8, ghost_w, 28), "查看卡组 ›", 11, sch["ink2"],
        align=Qt.AlignRight | Qt.AlignVCenter)

    # 副标题
    txt(p, QRectF(rect.left() + 16, rect.top() + 38, rect.width() - 32, 16), sub, 11, sch["ink2"])

    # 底部：细进度条 + 小号「继续学习」
    bh = 26
    b = QRectF(rect.right() - 16 - 78, rect.bottom() - 12 - bh, 78, bh)
    bar = QRectF(rect.left() + 16, b.center().y() - 1.5, b.left() - 14 - (rect.left() + 16), 3)
    rr(p, bar, 1.5, QColor(sch["line"]))
    rr(p, QRectF(bar.left(), bar.top(), bar.width() * pct, 3), 1.5, QColor(sch["brand"]))
    rr(p, b, 13, QColor(sch["brand_dark"]))
    txt(p, b, "继续学习", 11.5, "#FFFFFF", bold=True, align=Qt.AlignCenter)


def nav_bar(p, sch, rect):
    shadow(p, rect, 24, 34)
    rr(p, rect, 24, QColor(sch["card"]), QPen(QColor(sch["line"]), 1))
    items = [("今日", True), ("记忆", False), ("回顾", False), ("洞察", False)]
    cw = rect.width() / 4
    for i, (name, active) in enumerate(items):
        cx = rect.left() + cw * i + cw / 2
        if active:
            pill = QRectF(cx - 32, rect.top() + 8, 64, 46)
            rr(p, pill, 16, QColor(sch["brand_soft"]))
        col = sch["brand"] if active else sch["ink3"]
        # 图标
        r = QRectF(cx - 7, rect.top() + 15, 14, 14)
        pen = QPen(QColor(col), 1.6, Qt.SolidLine, Qt.RoundCap, Qt.RoundJoin)
        p.setPen(pen)
        p.setBrush(Qt.NoBrush)
        if i == 0:
            p.drawEllipse(r.adjusted(1.5, 1.5, -1.5, -1.5))
            for a in range(8):
                import math
                ang = a * math.pi / 4
                p.drawLine(QPointF(cx + math.cos(ang) * 8.4, r.center().y() + math.sin(ang) * 8.4),
                           QPointF(cx + math.cos(ang) * 10.4, r.center().y() + math.sin(ang) * 10.4))
        elif i == 1:
            p.drawRoundedRect(r.adjusted(1, 0.5, -1, -0.5), 2, 2)
            p.drawLine(QPointF(r.left() + 4, r.center().y()), QPointF(r.right() - 4, r.center().y()))
        elif i == 2:
            p.drawEllipse(r.adjusted(1.2, 1.2, -1.2, -1.2))
            p.drawLine(QPointF(cx, r.top() + 3), QPointF(cx, r.center().y()))
            p.drawLine(QPointF(cx, r.center().y()), QPointF(cx + 3.6, r.center().y() + 3.2))
        else:
            for k, hh in enumerate((5, 9, 13)):
                x = r.left() + 2 + k * 4.4
                p.drawLine(QPointF(x, r.bottom() - 1), QPointF(x, r.bottom() - 1 - hh))
        txt(p, QRectF(cx - cw / 2, rect.top() + 33, cw, 16), name, 10.5, col,
            bold=active, align=Qt.AlignCenter)


def render(sch):
    img = QImage(W * S, H * S, QImage.Format_ARGB32)
    img.fill(QColor(sch["paper"]))
    p = QPainter(img)
    p.setRenderHint(QPainter.Antialiasing, True)
    p.scale(S, S)

    # ---- 顶部 ----
    # 同步状态胶囊
    chip = QRectF(20, 16, 138, 22)
    rr(p, chip, 11, QColor(sch["warn_soft"]))
    p.setPen(Qt.NoPen)
    p.setBrush(QColor(sch["warn"]))
    p.drawEllipse(QRectF(chip.left() + 9, chip.center().y() - 3, 6, 6))
    txt(p, QRectF(chip.left() + 20, chip.top(), chip.width() - 24, chip.height()),
        "有未同步的修改", 10.5, sch["warn"], bold=True)

    # 标题 + 日期
    f = QFont(FONT)
    f.setPixelSize(30)
    f.setBold(True)
    p.setFont(f)
    p.setPen(QColor(sch["ink"]))
    p.drawText(QRectF(20, 44, 220, 40), Qt.AlignLeft | Qt.AlignVCenter, "今日")
    txt(p, QRectF(20, 84, 250, 20), "11 月 21 日 周五 · 今天还差 14 张", 11, sch["ink2"])

    # 右侧进度环
    ring = QRectF(W - 78, 40, 56, 56)
    p.setPen(QPen(QColor(sch["brand_soft"]), 7))
    p.drawArc(ring.adjusted(3.5, 3.5, -3.5, -3.5), 0, 360 * 16)
    p.setPen(QPen(QColor(sch["brand"]), 7, Qt.SolidLine, Qt.RoundCap))
    p.drawArc(ring.adjusted(3.5, 3.5, -3.5, -3.5), 90 * 16, -int(360 * 16 * 0.36))
    txt(p, ring, "36%", 13, sch["ink"], bold=True, align=Qt.AlignCenter)
    # 未同步红点
    p.setPen(Qt.NoPen)
    p.setBrush(QColor(sch["warn"]))
    p.drawEllipse(QRectF(ring.right() - 6, ring.top() - 2, 8, 8))

    # ---- 四宫格统计 ----
    cw, ch, gap = (W - 20 * 2 - 12) / 2, 92, 12
    x0, y0 = 20, 120
    stat_card(p, sch, QRectF(x0, y0, cw, ch), icon_clock, "待复习卡片", "14", "张",
              sch["info"], sch["ink"], sch["info_soft"])
    stat_card(p, sch, QRectF(x0 + cw + gap, y0, cw, ch), icon_check, "今日已学", "8", "张",
              sch["brand"], sch["ink"], sch["brand_soft"])
    stat_card(p, sch, QRectF(x0, y0 + ch + gap, cw, ch), icon_cards, "待学新卡", "129", "张",
              sch["accent"], sch["ink"], sch["accent_soft"])
    stat_card(p, sch, QRectF(x0 + cw + gap, y0 + ch + gap, cw, ch), icon_cal, "已到期", "141", "张",
              sch["warn"], sch["warn"], sch["warn_soft"])

    # ---- 继续学习 ----
    txt(p, QRectF(20, 330, 160, 26), "继续学习", 17, sch["ink"], bold=True)
    txt(p, QRectF(W - 120, 330, 100, 26), "查看全部 ›", 11.5, sch["brand"], bold=True,
        align=Qt.AlignRight | Qt.AlignVCenter)

    deck_card(p, sch, QRectF(20, 360, W - 40, 92), "工托个",
              "到期复习 104 · 待学新卡 102 · 学习中 2", 0.42)
    deck_card(p, sch, QRectF(20, 460, W - 40, 92), "【问答题】",
              "到期复习 22 · 待学新卡 21 · 学习中 1", 0.28)
    deck_card(p, sch, QRectF(20, 560, W - 40, 92), "第一章 关于人性",
              "到期复习 4 · 待学新卡 2 · 学习中 2", 0.55)
    deck_card(p, sch, QRectF(20, 660, W - 40, 92), "托",
              "到期复习 1 · 待学新卡 0 · 学习中 0", 0.08)

    # ---- 底部导航 ----
    nav_bar(p, sch, QRectF(16, H - 86, W - 32, 62))

    p.end()
    return img


imgs = [render(SCHEMES[k]) for k in ("A", "B")]
sheet = QImage(W * S * 2 + 48 * S, H * S + 64 * S, QImage.Format_ARGB32)
sheet.fill(QColor("#FFFFFF"))
sp = QPainter(sheet)
for i, im in enumerate(imgs):
    sp.drawImage(24 * S + i * (W * S + 24 * S), 28 * S, im)
    f = QFont(FONT)
    f.setPixelSize(13 * S)
    f.setBold(True)
    sp.setFont(f)
    sp.setPen(QColor("#333B33"))
    key = ("A", "B")[i]
    sp.drawText(QRectF(24 * S + i * (W * S + 24 * S), 4 * S, W * S, 20 * S),
                Qt.AlignHCenter | Qt.AlignVCenter, SCHEMES[key]["name"])
sp.end()
out = os.path.join(APP, "shots", "_ui-mock.png")
sheet.save(out)
print("saved", out, sheet.width(), sheet.height())
