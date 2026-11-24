# -*- coding: utf-8 -*-
"""生成 记忆 / 回顾 / 洞察 / 卡包 四页的效果图（A 晨雾绿）。"""
import math
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
W, H, S = 400, 860, 2

SCH = dict(
    paper="#F7F5EF", card="#FFFFFF", line="#EAE6DB",
    ink="#22261F", ink2="#6E7266", ink3="#A5A79B",
    brand="#2F6A43", brand_soft="#E9F1EA", brand_dark="#25542F",
    amber="#B8792A", amber_soft="#FBF0E1",
    red="#C0392B", red_soft="#FBEBE8",
    blue="#3D7EBB", blue_soft="#EAF1FA",
)


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


def card(p, rect, r=16):
    p.setPen(Qt.NoPen)
    p.setBrush(QColor(0, 0, 0, 20))
    p.drawRoundedRect(rect.adjusted(0, 2, 0, 3), r, r)
    rr(p, rect, r, QColor(SCH["card"]), QPen(QColor(SCH["line"]), 1))


def chip(p, rect, text, active=False, size=11):
    if active:
        rr(p, rect, rect.height() / 2, QColor(SCH["brand_dark"]))
        col = "#FFFFFF"
    else:
        rr(p, rect, rect.height() / 2, QColor(SCH["card"]), QPen(QColor(SCH["line"]), 1))
        col = SCH["ink2"]
    txt(p, rect, text, size, col, bold=active, align=Qt.AlignCenter)


def icon_folder(p, r, color):
    pen = QPen(QColor(color), 1.5, Qt.SolidLine, Qt.RoundCap, Qt.RoundJoin)
    p.setPen(pen)
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


def icon_card(p, r, color):
    pen = QPen(QColor(color), 1.5, Qt.SolidLine, Qt.RoundCap, Qt.RoundJoin)
    p.setPen(pen)
    p.setBrush(Qt.NoBrush)
    p.drawRoundedRect(r.adjusted(1, 0.5, -1, -0.5), 3, 3)
    p.drawLine(QPointF(r.left() + 3.5, r.top() + 4), QPointF(r.right() - 3.5, r.top() + 4))


def icon_clock(p, r, color):
    pen = QPen(QColor(color), 1.5, Qt.SolidLine, Qt.RoundCap, Qt.RoundJoin)
    p.setPen(pen)
    p.setBrush(Qt.NoBrush)
    p.drawEllipse(r.adjusted(0.8, 0.8, -0.8, -0.8))
    p.drawLine(r.center(), QPointF(r.center().x(), r.top() + 3.4))
    p.drawLine(r.center(), QPointF(r.center().x() + 3.2, r.center().y() + 2.0))


def header(p, title, sub=None, right=None):
    txt(p, QRectF(20, 22, 220, 38), title, 27, SCH["ink"], bold=True)
    if sub:
        txt(p, QRectF(20, 60, 260, 20), sub, 11, SCH["ink2"])
    if right == "plus_gear":
        for i, kind in enumerate(("plus", "gear")):
            r = QRectF(W - 20 - 34 - i * 40, 26, 34, 34)
            rr(p, r, 11, QColor(SCH["card"]), QPen(QColor(SCH["line"]), 1))
            p.setPen(QPen(QColor(SCH["ink2"]), 1.6, Qt.SolidLine, Qt.RoundCap))
            if kind == "plus":
                p.drawLine(QPointF(r.center().x() - 5, r.center().y()),
                           QPointF(r.center().x() + 5, r.center().y()))
                p.drawLine(QPointF(r.center().x(), r.center().y() - 5),
                           QPointF(r.center().x(), r.center().y() + 5))
            else:
                p.drawEllipse(r.center(), 5.2, 5.2)
                p.drawEllipse(r.center(), 1.6, 1.6)
    elif right == "import":
        r = QRectF(W - 20 - 64, 28, 64, 30)
        rr(p, r, 15, QColor(SCH["card"]), QPen(QColor(SCH["line"]), 1))
        txt(p, r, "导入", 11, SCH["ink"], align=Qt.AlignCenter)


def page_library():
    img = QImage(W * S, H * S, QImage.Format_ARGB32)
    img.fill(QColor(SCH["paper"]))
    p = QPainter(img)
    p.setRenderHint(QPainter.Antialiasing, True)
    p.scale(S, S)
    header(p, "记忆", "3 个知识域 · 6 个卡包", "plus_gear")

    # 知识域
    x = 20
    for name, active in (("微信读书", True), ("工作", False), ("生活", False)):
        w = 76 if len(name) <= 3 else 88
        chip(p, QRectF(x, 96, w, 30), name, active)
        x += w + 8

    # 搜索
    sr = QRectF(20, 142, W - 40, 38)
    rr(p, sr, 12, QColor(SCH["paper"]))
    p.setPen(QPen(QColor(SCH["ink3"]), 1.6, Qt.SolidLine, Qt.RoundCap))
    p.drawEllipse(QPointF(sr.left() + 17, sr.center().y() - 1), 5.0, 5.0)
    p.drawLine(QPointF(sr.left() + 21, sr.center().y() + 3),
               QPointF(sr.left() + 25, sr.center().y() + 7))
    txt(p, sr.adjusted(34, 0, -10, 0), "搜索圆桌、卡包或卡片", 11.5, SCH["ink3"])

    # 列表
    rows = [
        ("folder", "考试冲刺", "2026 年 10 月 21 日 · 2 个卡包 · 7 张", "#F3E6C8", "#A98417"),
        ("folder", "有道暗记", "2026 年 10 月 11 日 · 133 张 · 133 到期", "#EFE4C6", "#A98417"),
        ("card", "—", "2026 年 11 月 11 日 · 0 张 · 0 到期", "#EFEBDE", "#8C8878"),
    ]
    y = 198
    for kind, title, meta, tint, icol in rows:
        r = QRectF(20, y, W - 40, 74)
        card(p, r, 16)
        ir = QRectF(r.left() + 14, r.top() + 16, 34, 34)
        rr(p, ir, 10, QColor(tint))
        if kind == "folder":
            icon_folder(p, ir.adjusted(9, 10, -9, -10), icol)
        else:
            icon_card(p, ir.adjusted(10, 9, -10, -9), icol)
        txt(p, QRectF(ir.right() + 14, r.top() + 12, r.width() - 90, 24), title, 14.5,
            SCH["ink"], bold=True)
        txt(p, QRectF(ir.right() + 14, r.top() + 40, r.width() - 90, 18), meta, 10.5,
            SCH["ink2"])
        # ⋯
        p.setPen(Qt.NoPen)
        p.setBrush(QColor(SCH["ink3"]))
        for i in range(3):
            p.drawEllipse(QRectF(r.right() - 26 + i * 6, r.center().y() - 1.5, 3, 3))
        y += 84

    _nav(p, 1)
    p.end()
    return img


def page_plan():
    img = QImage(W * S, H * S, QImage.Format_ARGB32)
    img.fill(QColor(SCH["paper"]))
    p = QPainter(img)
    p.setRenderHint(QPainter.Antialiasing, True)
    p.scale(S, S)
    header(p, "回顾", "随机抽 8 张 · 全部时间")

    x = 20
    for name, active in (("全部", True), ("1 年", False), ("6 月", False),
                         ("3 月", False), ("1 月", False)):
        w = 56
        chip(p, QRectF(x, 96, w, 30), name, active)
        x += w + 8

    txt(p, QRectF(20, 140, 120, 20), "抽几张", 11, SCH["ink2"])
    x = 20
    for n in (4, 8, 12, 20):
        w = 46
        chip(p, QRectF(x, 164, w, 28), str(n), n == 8, 10.5)
        x += w + 8

    rows = [
        ("文学 · 微信读书", "「人性的底色不是善恶，唯一可界定的是自私的基因。」", "11-20 21:04"),
        ("工作 · 周报", "本周把复习调度换成 FSRS，间隔更贴合遗忘曲线。", "11-19 09:12"),
        ("生活 · 随手记", "把要做的事写下来，脑子才能空出来想别的。", "11-17 22:41"),
    ]
    y = 210
    for tag, body, when in rows:
        r = QRectF(20, y, W - 40, 94)
        card(p, r, 16)
        txt(p, QRectF(r.left() + 16, r.top() + 10, r.width() - 120, 18), tag, 10,
            SCH["brand"], bold=True)
        txt(p, QRectF(r.right() - 110, r.top() + 10, 94, 18), when, 9.5,
            SCH["ink3"], align=Qt.AlignRight | Qt.AlignVCenter)
        txt(p, QRectF(r.left() + 16, r.top() + 34, r.width() - 32, 62), body, 12.5,
            SCH["ink"], align=Qt.AlignLeft | Qt.AlignTop)
        y += 106

    # 底部按钮
    b1 = QRectF(20, H - 132, 150, 44)
    rr(p, b1, 14, QColor(SCH["card"]), QPen(QColor(SCH["line"]), 1))
    txt(p, b1, "换一批", 12.5, SCH["ink"], bold=True, align=Qt.AlignCenter)
    b2 = QRectF(180, H - 132, W - 200, 44)
    rr(p, b2, 14, QColor(SCH["brand_dark"]))
    txt(p, b2, "开始回顾", 12.5, "#FFFFFF", bold=True, align=Qt.AlignCenter)

    _nav(p, 2)
    p.end()
    return img


def page_insights():
    img = QImage(W * S, H * S, QImage.Format_ARGB32)
    img.fill(QColor(SCH["paper"]))
    p = QPainter(img)
    p.setRenderHint(QPainter.Antialiasing, True)
    p.scale(S, S)
    header(p, "洞察", "最近 30 天")

    # 主卡：准确率环 + 两个数字
    r = QRectF(20, 96, W - 40, 132)
    card(p, r, 18)
    ring = QRectF(r.left() + 22, r.top() + 24, 84, 84)
    p.setPen(QPen(QColor(SCH["brand_soft"]), 9))
    p.drawArc(ring, 0, 360 * 16)
    p.setPen(QPen(QColor(SCH["brand"]), 9, Qt.SolidLine, Qt.RoundCap))
    p.drawArc(ring, 90 * 16, -int(360 * 16 * 0.78))
    txt(p, ring, "78%", 16, SCH["ink"], bold=True, align=Qt.AlignCenter)
    txt(p, QRectF(ring.right() + 18, r.top() + 30, 160, 18), "平均准确率", 11, SCH["ink2"])
    txt(p, QRectF(ring.right() + 18, r.top() + 52, 160, 26), "1,284 张", 20, SCH["ink"], bold=True)
    txt(p, QRectF(ring.right() + 18, r.top() + 84, 160, 18), "连续学习 12 天 · 今天 8 张", 10.5,
        SCH["ink3"])

    # 柱状图
    r2 = QRectF(20, 244, W - 40, 150)
    card(p, r2, 18)
    txt(p, QRectF(r2.left() + 16, r2.top() + 12, 200, 18), "最近 7 天复习量", 11.5,
        SCH["ink2"], bold=True)
    vals = [12, 20, 8, 26, 18, 30, 14]
    base = r2.bottom() - 22
    bw = 18
    gap = (r2.width() - 32 - bw * 7) / 6
    for i, v in enumerate(vals):
        h = v * 2.0
        x = r2.left() + 16 + i * (bw + gap)
        bar = QRectF(x, base - h, bw, h)
        rr(p, bar, 6, QColor(SCH["brand_soft"] if i < 6 else SCH["brand"]))
        if i == 5:
            rr(p, bar, 6, QColor(SCH["brand"]))
        txt(p, QRectF(x - 6, base + 4, bw + 12, 16), "一二三四五六日"[i], 10, SCH["ink3"],
            align=Qt.AlignCenter)

    # 题型分布
    r3 = QRectF(20, 410, W - 40, 150)
    card(p, r3, 18)
    txt(p, QRectF(r3.left() + 16, r3.top() + 12, 200, 18), "题型分布", 11.5, SCH["ink2"], bold=True)
    items = [("问答", "62%", SCH["brand"], 0.62), ("单选", "24%", SCH["blue"], 0.24),
             ("多选", "14%", SCH["amber"], 0.14)]
    y = r3.top() + 42
    for name, pct, col, ratio in items:
        p.setPen(Qt.NoPen)
        p.setBrush(QColor(col))
        p.drawEllipse(QRectF(r3.left() + 16, y + 6, 7, 7))
        txt(p, QRectF(r3.left() + 30, y, 60, 18), name, 11, SCH["ink"])
        bar = QRectF(r3.left() + 92, y + 7, r3.width() - 160, 6)
        rr(p, bar, 3, QColor(SCH["paper"]))
        rr(p, QRectF(bar.left(), bar.top(), bar.width() * ratio, 6), 3, QColor(col))
        txt(p, QRectF(r3.right() - 52, y, 46, 18), pct, 10.5, SCH["ink2"],
            align=Qt.AlignRight | Qt.AlignVCenter)
        y += 34

    # 完成卡包
    r4 = QRectF(20, 576, W - 40, 92)
    card(p, r4, 18)
    rr(p, QRectF(r4.left() + 16, r4.top() + 26, 34, 34), 10, QColor(SCH["amber_soft"]))
    icon_card(p, QRectF(r4.left() + 26, r4.top() + 35, 14, 16), SCH["amber"])
    txt(p, QRectF(r4.left() + 62, r4.top() + 22, 200, 22), "已完成卡包", 13, SCH["ink"], bold=True)
    txt(p, QRectF(r4.left() + 62, r4.top() + 46, 220, 18), "2 个卡包 · 卡片不再进复习队列", 10.5,
        SCH["ink2"])

    _nav(p, 3)
    p.end()
    return img


def page_deck():
    img = QImage(W * S, H * S, QImage.Format_ARGB32)
    img.fill(QColor(SCH["paper"]))
    p = QPainter(img)
    p.setRenderHint(QPainter.Antialiasing, True)
    p.scale(S, S)

    # 顶栏：返回 + 标题 + 导入
    pen = QPen(QColor(SCH["ink"]), 2.2, Qt.SolidLine, Qt.RoundCap, Qt.RoundJoin)
    p.setPen(pen)
    p.drawLine(QPointF(30, 40), QPointF(22, 46))
    p.drawLine(QPointF(30, 52), QPointF(22, 46))
    txt(p, QRectF(46, 26, 220, 40), "有道暗记", 24, SCH["ink"], bold=True)
    ir = QRectF(W - 20 - 64, 32, 64, 30)
    rr(p, ir, 15, QColor(SCH["card"]), QPen(QColor(SCH["line"]), 1))
    txt(p, ir, "导入", 11, SCH["ink"], align=Qt.AlignCenter)

    # 三档
    seg = QRectF(20, 92, W - 40, 40)
    rr(p, seg, 20, QColor(SCH["paper2"] if "paper2" in SCH else SCH["brand_soft"]).lighter(103))
    cw = seg.width() / 3
    for i, name in enumerate(("刷题练习", "学习记忆", "浏览卡片")):
        r = QRectF(seg.left() + i * cw + 3, seg.top() + 3, cw - 6, seg.height() - 6)
        if i == 1:
            rr(p, r, 17, QColor(SCH["brand_dark"]))
            txt(p, r, name, 12, "#FFFFFF", bold=True, align=Qt.AlignCenter)
        else:
            txt(p, r, name, 12, SCH["ink2"], align=Qt.AlignCenter)

    # 概览卡
    r = QRectF(20, 148, W - 40, 118)
    card(p, r, 18)
    pr = QRectF(r.left() + 16, r.top() + 14, 132, 21)
    rr(p, pr, 10, QColor(SCH["paper"]))
    txt(p, pr, "133 张 · 5 个卡组", 9.5, SCH["ink2"], align=Qt.AlignCenter)
    txt(p, QRectF(r.left() + 16, r.top() + 40, 220, 28), "工托个", 19, SCH["ink"], bold=True)
    txt(p, QRectF(r.left() + 16, r.top() + 74, 240, 20),
        "104 卡片 · 2 待复习 · 102 待新学", 10.5, SCH["ink2"])
    ring = QRectF(r.right() - 16 - 52, r.top() + 33, 52, 52)
    p.setPen(QPen(QColor(SCH["brand_soft"]), 6))
    p.drawArc(ring, 0, 360 * 16)
    p.setPen(QPen(QColor(SCH["brand"]), 6, Qt.SolidLine, Qt.RoundCap))
    p.drawArc(ring, 90 * 16, -int(360 * 16 * 0.02))
    txt(p, ring, "2%", 11, SCH["ink"], bold=True, align=Qt.AlignCenter)

    # 卡组列表
    txt(p, QRectF(20, 286, 120, 24), "卡组", 15, SCH["ink"], bold=True)
    plus = QRectF(W - 20 - 40, 282, 40, 30)
    rr(p, plus, 10, QColor(SCH["paper"]))
    p.setPen(QPen(QColor(SCH["ink2"]), 1.6, Qt.SolidLine, Qt.RoundCap))
    p.drawLine(QPointF(plus.center().x() - 5, plus.center().y()),
               QPointF(plus.center().x() + 5, plus.center().y()))
    p.drawLine(QPointF(plus.center().x(), plus.center().y() - 5),
               QPointF(plus.center().x(), plus.center().y() + 5))

    groups = [("第一章 关于人性", "4 张 · 单选 / 多选 / 问答", "4 到期", False),
              ("第二章 让人喜欢你", "2 张 · 单选 / 问答", "2 到期", False),
              ("【问答题】", "22 张 · 问答", "22 到期", False),
              ("工托个", "104 张 · 单选 / 多选 / 问答", "104 到期", True)]
    y = 322
    for name, meta, due, active in groups:
        r = QRectF(20, y, W - 40, 64)
        if active:
            rr(p, r, 14, QColor(SCH["brand_soft"]), QPen(QColor(SCH["brand"]), 1.4))
        else:
            rr(p, r, 14, QColor(SCH["card"]), QPen(QColor(SCH["line"]), 1))
        txt(p, QRectF(r.left() + 14, r.top() + 10, r.width() - 110, 22), name, 13,
            SCH["ink"], bold=True)
        txt(p, QRectF(r.left() + 14, r.top() + 34, r.width() - 110, 18), meta, 10,
            SCH["ink2"])
        dr = QRectF(r.right() - 82, r.center().y() - 12, 68, 24)
        rr(p, dr, 12, QColor(SCH["amber_soft"]))
        txt(p, dr, due, 9.5, SCH["amber"], bold=True, align=Qt.AlignCenter)
        y += 74

    _nav(p, -1, show=False)
    p.end()
    return img


def _nav(p, active, show=True):
    if not show:
        return
    bar = QRectF(16, H - 80, W - 32, 62)
    p.setPen(Qt.NoPen)
    p.setBrush(QColor(0, 0, 0, 26))
    p.drawRoundedRect(bar.adjusted(0, 2, 0, 3), 24, 24)
    rr(p, bar, 24, QColor(SCH["card"]), QPen(QColor(SCH["line"]), 1))
    items = ["今日", "记忆", "回顾", "洞察"]
    cw = bar.width() / 4
    for i, name in enumerate(items):
        cx = bar.left() + cw * i + cw / 2
        if i == active:
            rr(p, QRectF(cx - 31, bar.top() + 7, 62, bar.height() - 12), 14,
               QColor(SCH["brand_soft"]))
        col = SCH["brand"] if i == active else SCH["ink2"]
        txt(p, QRectF(cx - cw / 2, bar.bottom() - 22, cw, 16), name, 10, col,
            bold=(i == active), align=Qt.AlignCenter)


imgs = [page_library(), page_plan(), page_insights(), page_deck()]
titles = ["记忆 · 知识域 / 卡包列表", "回顾 · 每日随机回顾",
          "洞察 · 数据概览", "卡包 · 三档 + 卡组列表"]
cols, rows = 2, 2
sheet = QImage(cols * (W * S + 24 * S) + 24 * S, rows * (H * S + 40 * S) + 24 * S,
               QImage.Format_ARGB32)
sheet.fill(QColor("#FFFFFF"))
sp = QPainter(sheet)
for i, im in enumerate(imgs):
    cx, cy = i % cols, i // cols
    x = 24 * S + cx * (W * S + 24 * S)
    y = 30 * S + cy * (H * S + 40 * S)
    sp.drawImage(x, y, im)
    f = QFont(FONT)
    f.setPixelSize(13 * S)
    f.setBold(True)
    sp.setFont(f)
    sp.setPen(QColor("#333B33"))
    sp.drawText(QRectF(x, y - 26 * S, W * S, 20 * S), Qt.AlignHCenter | Qt.AlignVCenter,
                titles[i])
sp.end()
out = os.path.join(APP, "shots", "_ui-mock2.png")
sheet.save(out)
print("saved", out, sheet.width(), sheet.height())
