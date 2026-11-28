# -*- coding: utf-8 -*-
"""文具小图标：铅笔 / 书本 / 尺子 / 橡皮 / 剪刀 / 回形针，画在色带右侧。"""
from __future__ import annotations

import math

from PySide6.QtCore import Qt, QRectF, QPointF
from PySide6.QtGui import QColor, QPainter, QPen, QBrush, QPolygonF


def draw_stationery(p: QPainter, kind: str, rect: QRectF, ink: str, cream: str, rotate: float = -8):
    """在 rect 内画一件文具；ink = 深色描边，cream = 奶油/纸色。"""
    p.save()
    p.setRenderHint(QPainter.Antialiasing)
    x, y, w, h = rect.x(), rect.y(), rect.width(), rect.height()
    # 统一轻微倾斜，像随手放在桌上
    p.translate(x + w / 2, y + h / 2)
    p.rotate(rotate)
    p.translate(-(x + w / 2), -(y + h / 2))
    pen = QPen(QColor(ink), max(1.4, w * 0.045), Qt.SolidLine, Qt.RoundCap, Qt.RoundJoin)
    p.setPen(pen)
    p.setBrush(Qt.NoBrush)

    if kind == "pencil":
        # 笔杆
        body = QPolygonF([QPointF(x + w * 0.16, y + h * 0.40),
                          QPointF(x + w * 0.78, y + h * 0.40),
                          QPointF(x + w * 0.78, y + h * 0.62),
                          QPointF(x + w * 0.16, y + h * 0.62)])
        p.setBrush(QColor("#F3C969"))
        p.drawPolygon(body)
        # 笔尖
        p.setBrush(QColor(cream))
        p.drawPolygon(QPolygonF([QPointF(x + w * 0.16, y + h * 0.40),
                                 QPointF(x + w * 0.04, y + h * 0.51),
                                 QPointF(x + w * 0.16, y + h * 0.62)]))
        p.setBrush(QColor(ink))
        p.drawPolygon(QPolygonF([QPointF(x + w * 0.08, y + h * 0.47),
                                 QPointF(x + w * 0.04, y + h * 0.51),
                                 QPointF(x + w * 0.08, y + h * 0.55)]))
        # 橡皮头
        p.setBrush(QColor("#E8A3A8"))
        p.drawRoundedRect(QRectF(x + w * 0.78, y + h * 0.42, w * 0.12, h * 0.18), 2, 2)
        p.drawLine(QPointF(x + w * 0.32, y + h * 0.40), QPointF(x + w * 0.32, y + h * 0.62))
    elif kind == "book":
        p.setBrush(QColor("#6E9BC4"))
        p.drawRoundedRect(QRectF(x + w * 0.16, y + h * 0.22, w * 0.66, h * 0.58), 2.5, 2.5)
        p.setBrush(QColor(cream))
        p.drawRoundedRect(QRectF(x + w * 0.22, y + h * 0.28, w * 0.54, h * 0.46), 1.5, 1.5)
        p.setPen(QPen(QColor(ink), 1.1))
        for k in range(3):
            yy = y + h * (0.36 + k * 0.10)
            p.drawLine(QPointF(x + w * 0.28, yy), QPointF(x + w * 0.70, yy))
        p.setPen(pen)
        p.drawLine(QPointF(x + w * 0.20, y + h * 0.22), QPointF(x + w * 0.20, y + h * 0.80))
    elif kind == "ruler":
        p.setBrush(QColor(cream))
        p.drawRoundedRect(QRectF(x + w * 0.10, y + h * 0.34, w * 0.80, h * 0.30), 3, 3)
        p.setPen(QPen(QColor(ink), 1.0))
        for k in range(6):
            xx = x + w * (0.18 + k * 0.12)
            p.drawLine(QPointF(xx, y + h * 0.34), QPointF(xx, y + h * (0.42 if k % 2 else 0.47)))
    elif kind == "eraser":
        p.setBrush(QColor("#E8A3A8"))
        p.drawRoundedRect(QRectF(x + w * 0.22, y + h * 0.32, w * 0.50, h * 0.36), 4, 4)
        p.setBrush(QColor("#F6D6D9"))
        p.drawRoundedRect(QRectF(x + w * 0.22, y + h * 0.32, w * 0.50, h * 0.14), 4, 4)
    elif kind == "scissors":
        # 两片刀刃 + 两个指环 + 转轴
        p.setBrush(QColor("#C9D4DE"))
        p.drawPolygon(QPolygonF([QPointF(x + w * 0.24, y + h * 0.34),
                                 QPointF(x + w * 0.82, y + h * 0.20),
                                 QPointF(x + w * 0.86, y + h * 0.29),
                                 QPointF(x + w * 0.28, y + h * 0.44)]))
        p.drawPolygon(QPolygonF([QPointF(x + w * 0.24, y + h * 0.66),
                                 QPointF(x + w * 0.82, y + h * 0.80),
                                 QPointF(x + w * 0.86, y + h * 0.71),
                                 QPointF(x + w * 0.28, y + h * 0.56)]))
        p.setBrush(QColor(cream))
        p.drawEllipse(QRectF(x + w * 0.10, y + h * 0.30, w * 0.26, h * 0.24))
        p.drawEllipse(QRectF(x + w * 0.10, y + h * 0.46, w * 0.26, h * 0.24))
        p.setBrush(QColor(ink))
        p.drawEllipse(QPointF(x + w * 0.34, y + h * 0.50), w * 0.045, w * 0.045)
    elif kind == "clip":
        p.drawArc(QRectF(x + w * 0.30, y + h * 0.18, w * 0.34, h * 0.64), 20 * 16, 300 * 16)
        p.drawArc(QRectF(x + w * 0.38, y + h * 0.24, w * 0.20, h * 0.52), 20 * 16, 300 * 16)
    else:  # 星星 / 便签
        p.setBrush(QColor("#F3C969"))
        path = QPolygonF()
        cx, cy, r = x + w / 2, y + h / 2, min(w, h) * 0.32
        for k in range(10):
            a = math.radians(-90 + k * 36)
            rr = r if k % 2 == 0 else r * 0.45
            path.append(QPointF(cx + rr * math.cos(a), cy + rr * math.sin(a)))
        p.drawPolygon(path)
    p.restore()
