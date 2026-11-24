# -*- coding: utf-8 -*-
"""生成外观主题效果图（参考 闪卡exe/template/选择题模版 的配色与结构）。"""
import os
import sys

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
APP = r"D:\我的下载\WorkBuddy库\逆向分析\ebbinghaus\app"
sys.path.insert(0, APP)

from PySide6.QtCore import QRectF, Qt
from PySide6.QtGui import (QColor, QFont, QImage, QLinearGradient, QPainter,
                           QPainterPath, QPen)
from PySide6.QtWidgets import QApplication

qapp = QApplication([])

FONT = "Microsoft YaHei UI"
W, H = 380, 470

THEMES = [
    dict(
        key="ice", name="冰蓝轻语",
        page="#E8EDF2", card=("#FFFFFF", "#F7FBFE"),
        accent=("#4BB8FA", "#7FCBF7"), ink="#2F3B47", sub="#7A8896",
        ribbon_text="#FFFFFF",
        opts=[("#F2F7FB", "#3E6C8F"), ("#E3F3E5", "#2E6B3A"),
              ("#FCE9EC", "#A8434F"), ("#F4F1FA", "#6A5E8C")],
        correct="#A8DF8E", wrong="#FFAAB8",
        analysis=("#EFF6FB", "#FBFDFF"),
    ),
    dict(
        key="leaf", name="淡绿微风",
        page="#E5EEE4", card=("#FFFFFF", "#EAF3E5"),
        accent=("#A2CB8B", "#7BA668"), ink="#354033", sub="#7C8A78",
        ribbon_text="#FFFFFF",
        opts=[("#F3F8EE", "#4B6B41"), ("#E4F3DD", "#2F6B34"),
              ("#FBE9EC", "#A54B57"), ("#F1F5F7", "#5C6E63")],
        correct="#A8DF8E", wrong="#FFAAB8",
        analysis=("#F2F8EE", "#FBFDF8"),
    ),
    dict(
        key="lemon", name="柠檬金辉",
        page="#F5F0E8", card=("#FFFDF5", "#FBF4E4"),
        accent=("#F5C842", "#FFD54F"), ink="#463C2B", sub="#8A7C63",
        ribbon_text="#5A4708",
        opts=[("#FBF6E9", "#7A6524"), ("#EDF5E3", "#3F6A33"),
              ("#FCEBEA", "#A64A45"), ("#F3F1EA", "#6B6353")],
        correct="#BFE39A", wrong="#FFB4AE",
        analysis=("#FAF5E7", "#FFFDF7"),
    ),
    dict(
        key="sakura", name="樱粉烟紫",
        page="#FFE5F1", card=("#F5F5FF", "#FBEEF6"),
        accent=("#F3B6D8", "#B79CE8"), ink="#4B3A52", sub="#8D7B96",
        ribbon_text="#FFFFFF",
        opts=[("#F7F2FB", "#5A4870"), ("#E7F4E8", "#33683D"),
              ("#FBE7EF", "#A64B6B"), ("#F1EFFB", "#5C5691")],
        correct="#A8DF8E", wrong="#FFAAB8",
        analysis=("#F7F1FA", "#FDF7FB"),
    ),
    dict(
        key="sand", name="暖沙陶韵",
        page="#F2EFEA", card=("#FAF8F5", "#F5F0EB"),
        accent=("#C89A6B", "#A9764C"), ink="#4A3B2E", sub="#8C7A67",
        ribbon_text="#FFFFFF",
        opts=[("#F7F1EA", "#6B4F35"), ("#EEF3E6", "#4A6234"),
              ("#F8ECE8", "#9C4F3C"), ("#F2EEE9", "#655A4B")],
        correct="#C7DFA8", wrong="#F0B0A2",
        analysis=("#F7F2EB", "#FCF9F5"),
    ),
    dict(
        key="glass", name="彩虹琉璃",
        page="#F7F5F2", card=("#FFFFFF", "#FAF8FF"),
        accent=("#FF6F91", "#9B5DE5"), ink="#33333A", sub="#7D7D8A",
        ribbon_text="#FFFFFF", rainbow=("#FF6F91", "#FFC75F", "#8AC926", "#4EA8DE", "#9B5DE5"),
        opts=[("#FFF3F5", "#8E3A50"), ("#EFF6E9", "#3F6B36"),
              ("#FDEEF1", "#A5475C"), ("#F2F1FB", "#5A5391")],
        correct="#A8DF8E", wrong="#FFAAB8",
        analysis=("#F6F3FF", "#FDFBFF"),
    ),
]


def rr(p, rect, r, fill, pen=None):
    p.setPen(pen if pen is not None else Qt.NoPen)
    p.setBrush(fill)
    p.drawRoundedRect(rect, r, r)


def text(p, rect, s, size, color, bold=False, spacing=1.55, align=Qt.AlignLeft):
    f = QFont(FONT)
    f.setPixelSize(size)
    f.setBold(bold)
    p.setFont(f)
    p.setPen(QColor(color))
    p.drawText(rect, align | Qt.TextWordWrap | Qt.AlignTop, s)


def render(theme, question, options, analysis, correct_idx):
    img = QImage(W, H, QImage.Format_ARGB32)
    img.fill(QColor(theme["page"]))
    p = QPainter(img)
    p.setRenderHint(QPainter.Antialiasing, True)

    # 卡片
    card = QRectF(16, 16, W - 32, H - 32)
    grad = QLinearGradient(card.topLeft(), card.bottomLeft())
    grad.setColorAt(0, QColor(theme["card"][0]))
    grad.setColorAt(1, QColor(theme["card"][1]))
    p.setPen(Qt.NoPen)
    p.setBrush(QColor(0, 0, 0, 18))
    p.drawRoundedRect(card.adjusted(0, 3, 0, 3), 22, 22)
    p.setBrush(grad)
    p.drawRoundedRect(card, 22, 22)

    # 顶部渐变细条（彩虹琉璃用多彩）
    bar = QRectF(card.left() + 20, card.top() + 14, card.width() - 40, 4)
    if theme.get("rainbow"):
        seg = bar.width() / len(theme["rainbow"])
        for i, c in enumerate(theme["rainbow"]):
            p.setBrush(QColor(c))
            p.drawRoundedRect(QRectF(bar.left() + i * seg, bar.top(), seg, 4), 2, 2)
    else:
        g2 = QLinearGradient(bar.topLeft(), bar.topRight())
        g2.setColorAt(0, QColor(theme["accent"][0]))
        g2.setColorAt(1, QColor(theme["accent"][1]))
        p.setBrush(g2)
        p.drawRoundedRect(bar, 2, 2)

    # 书签式标签
    lab = QRectF(card.left() + 20, card.top() + 30, 68, 24)
    g3 = QLinearGradient(lab.topLeft(), lab.topRight())
    g3.setColorAt(0, QColor(theme["accent"][0]))
    g3.setColorAt(1, QColor(theme["accent"][1]))
    p.setBrush(g3)
    path = QPainterPath()
    path.moveTo(lab.left(), lab.top())
    path.lineTo(lab.right() - 6, lab.top())
    path.lineTo(lab.right(), lab.center().y())
    path.lineTo(lab.right() - 6, lab.bottom())
    path.lineTo(lab.left(), lab.bottom())
    path.closeSubpath()
    p.drawPath(path)
    p.setPen(QColor(theme["ribbon_text"]))
    f = QFont(FONT)
    f.setPixelSize(12)
    f.setBold(True)
    p.setFont(f)
    p.drawText(lab.adjusted(10, 0, -6, 0), Qt.AlignVCenter | Qt.AlignLeft, "问题")

    # 题干
    text(p, QRectF(card.left() + 20, card.top() + 62, card.width() - 40, 74),
         question, 17, theme["ink"], bold=True, spacing=1.6)

    # 选项
    y = card.top() + 142
    labels = "ABCD"
    for i, (o, (bg, fg)) in enumerate(zip(options, theme["opts"])):
        row = QRectF(card.left() + 20, y, card.width() - 40, 52)
        p.setPen(QPen(QColor(bg).darker(104), 1))
        p.setBrush(QColor(bg))
        p.drawRoundedRect(row, 12, 12)
        # 字母徽章
        badge = QRectF(row.left() + 10, row.center().y() - 13, 26, 26)
        if i == correct_idx:
            p.setPen(Qt.NoPen)
            p.setBrush(QColor(theme["correct"]))
            p.drawRoundedRect(badge, 8, 8)
            p.setPen(QColor("#2F4F1F"))
        else:
            p.setPen(Qt.NoPen)
            p.setBrush(QColor(255, 255, 255, 210))
            p.drawRoundedRect(badge, 8, 8)
            p.setPen(QColor(fg))
        f = QFont(FONT)
        f.setPixelSize(13)
        f.setBold(True)
        p.setFont(f)
        p.drawText(badge, Qt.AlignCenter, labels[i])
        # 选项文字
        text(p, QRectF(badge.right() + 12, row.top() + 6, row.width() - 60, 40),
             o, 13.5, theme["ink"], bold=(i == correct_idx), spacing=1.4)
        y += 60

    # 解析块
    ana = QRectF(card.left() + 20, card.bottom() - 78, card.width() - 40, 58)
    g4 = QLinearGradient(ana.topLeft(), ana.bottomRight())
    g4.setColorAt(0, QColor(theme["analysis"][0]))
    g4.setColorAt(1, QColor(theme["analysis"][1]))
    p.setPen(QPen(QColor(theme["accent"][1]).lighter(150), 1))
    p.setBrush(g4)
    p.drawRoundedRect(ana, 12, 12)
    text(p, ana.adjusted(12, 8, -12, -8), analysis, 11.5, theme["sub"], spacing=1.5)

    p.end()
    return img


Q = "关于人性本善还是本恶，几千年来都没有一个明确的答案。"
OPTIONS = [
    "人性本善，恶只是后天环境造成的",
    "人性本恶，善是教化与约束的结果",
    "人性无善恶，只有立场与选择",
    "人性善恶并存，取决于具体情境",
]
ANA = "解析：人性的底色不是善恶，唯一可界定的是自私的基因。"

sheet_w, sheet_h = 3 * (W + 24) + 24, 2 * (H + 56) + 24
sheet = QImage(sheet_w, sheet_h, QImage.Format_ARGB32)
sheet.fill(QColor("#FFFFFF"))
sp = QPainter(sheet)
sp.setRenderHint(QPainter.Antialiasing, True)
for i, t in enumerate(THEMES):
    col, row = i % 3, i // 3
    x = 24 + col * (W + 24)
    y = 24 + row * (H + 56)
    img = render(t, Q, OPTIONS, ANA, correct_idx=1)
    sp.drawImage(x, y, img)
    f = QFont(FONT)
    f.setPixelSize(16)
    f.setBold(True)
    sp.setFont(f)
    sp.setPen(QColor("#2F3B47"))
    sp.drawText(QRectF(x, y + H + 8, W, 28), Qt.AlignHCenter | Qt.AlignTop,
                f'{t["name"]}　{", ".join(t["accent"])}')
sp.end()

out = os.path.join(APP, "shots", "_themes-mock.png")
sheet.save(out)
print("saved", out, sheet.width(), sheet.height())
