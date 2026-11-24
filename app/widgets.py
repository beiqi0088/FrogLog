# -*- coding: utf-8 -*-
"""
widgets.py - 可复用控件（对齐浮卡的 widgets.py 角色）
所有颜色从 theme.T 取，主题切换时由 app 调 set_tokens() 刷新。
"""
from __future__ import annotations

import math

from PySide6.QtCore import (Qt, QRectF, QPointF, Signal, QEvent, QTimer,
                            QPropertyAnimation, Property, QEasingCurve)
from PySide6.QtGui import (QGuiApplication, QColor, QPainter, QPen, QBrush, QFont,
                           QPainterPath, QLinearGradient)
from PySide6.QtWidgets import (QFrame, QLabel, QWidget, QVBoxLayout, QHBoxLayout,
                               QPushButton, QSizePolicy, QGraphicsDropShadowEffect,
                               QProgressBar)

import theme
from theme import LIGHT

T = dict(LIGHT)


def set_tokens(t: dict):
    global T
    T = dict(t)


def _c(key: str, alpha: int | None = None) -> QColor:
    col = QColor(T[key])
    if alpha is not None:
        col.setAlpha(alpha)
    return col


# ---------------------------------------------------------------- 容器

class Card(QFrame):
    def __init__(self, flat=False, parent=None):
        super().__init__(parent)
        self.setObjectName("flatCard" if flat else "card")
        self.body = QVBoxLayout(self)
        self.body.setContentsMargins(16, 14, 16, 14)
        self.body.setSpacing(8)


class ClickFrame(QFrame):
    clicked = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setCursor(Qt.PointingHandCursor)

    def mouseReleaseEvent(self, e):
        if e.button() == Qt.LeftButton and self.rect().contains(e.position().toPoint()):
            self.clicked.emit()
        super().mouseReleaseEvent(e)


class ListRow(ClickFrame):
    """一行：类型徽标 + 标题 + 副标题 + 右箭头。"""

    def __init__(self, badge: str, badge_kind: str, title: str, sub: str, parent=None):
        super().__init__(parent)
        self.setObjectName("card")
        lay = QHBoxLayout(self)
        lay.setContentsMargins(13, 11, 13, 11)
        lay.setSpacing(11)
        lay.addWidget(TypeBadge(badge, badge_kind))
        col = QVBoxLayout()
        col.setSpacing(3)
        t = QLabel(title)
        t.setObjectName("h3")
        t.setWordWrap(True)
        s = QLabel(sub)
        s.setObjectName("sub")
        col.addWidget(t)
        col.addWidget(s)
        lay.addLayout(col, 1)
        chev = QLabel("›")
        chev.setStyleSheet(f"color:{T['ink3']};font-size:18px;")
        lay.addWidget(chev)


class TypeBadge(QLabel):
    COLORS = {
        "qa":     ("问", "green"),
        "single": ("单", "blue"),
        "multi":  ("多", "accent"),
    }

    def __init__(self, text: str, kind: str, parent=None):
        super().__init__(text, parent)
        self._kind = None
        self.setFixedSize(22, 22)
        self.setAlignment(Qt.AlignCenter)
        self.set_kind(text, kind)

    def set_kind(self, text: str, kind: str):
        if text != self.text():
            self.setText(text)
        if kind == self._kind:
            return
        self._kind = kind
        key = {"qa": "green", "single": "blue", "multi": "accent"}.get(kind, "ink2")
        soft = {"qa": "green_soft", "single": "blue_soft", "multi": "accent_soft"}.get(kind, "paper2")
        self.setStyleSheet(
            f"background:{T[soft]};color:{T[key]};border-radius:7px;"
            f"font-size:10px;font-weight:700;"
        )


class Pill(QLabel):
    def __init__(self, text: str, kind: str = "plain", parent=None):
        super().__init__(text, parent)
        self._kind = None
        self.setSizePolicy(QSizePolicy.Maximum, QSizePolicy.Fixed)
        self.set_kind(kind)

    def set_kind(self, kind: str = "plain"):
        if kind == self._kind:
            return
        self._kind = kind
        fg, bg = {
            "plain":  (T["ink2"], T["paper2"]),
            "brand":  (T["brand"], T["brand_soft"]),
            "accent": (T["accent"], T["accent_soft"]),
            "green":  (T["green"], T["green_soft"]),
            "red":    (T["red"], T["red_soft"]),
        }.get(kind, (T["ink2"], T["paper2"]))
        self.setStyleSheet(
            f"background:{bg};color:{fg};border-radius:9px;padding:3px 8px;"
            f"font-size:10.5px;font-weight:600;"
        )


class HeroCard(QFrame):
    """今日页主卡（渐变）。"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("hero")
        self.body = QVBoxLayout(self)
        self.body.setContentsMargins(22, 20, 22, 20)
        self.body.setSpacing(6)


class HLine(QFrame):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("line")
        self.setFixedHeight(1)


# ---------------------------------------------------------------- 按钮

class IconButton(QPushButton):
    def __init__(self, glyph: str, size=40, parent=None):
        super().__init__(glyph, parent)
        self.setObjectName("iconBtn")
        self.setFixedSize(size, size)
        self.setCursor(Qt.PointingHandCursor)


class BackButton(QPushButton):
    """返回：只有一个「<」箭头（圆头笔画），没有横杆、没有底色、悬停不变色。"""

    def __init__(self, size: int = 36, parent=None):
        super().__init__(parent)
        self.setCursor(Qt.PointingHandCursor)
        self.setFixedSize(size, size)
        self.setStyleSheet("QPushButton{background:transparent;border:none;}")
        self._stroke = max(2.4, size * 0.085)      # 36px → 3.1px
        self._span = size * 0.30

    def paintEvent(self, e):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing, True)
        pen = QPen(QColor(T["ink"]), self._stroke)
        pen.setCapStyle(Qt.RoundCap)
        pen.setJoinStyle(Qt.RoundJoin)
        p.setPen(pen)
        cx, cy = self.width() / 2, self.height() / 2
        head = self._span                      # 两翼的长度
        tip_x = cx - head * 0.55               # 让整个箭头在按钮里居中
        path = QPainterPath()
        path.moveTo(tip_x + head, cy - head)   # 上翼
        path.lineTo(tip_x, cy)
        path.lineTo(tip_x + head, cy + head)   # 下翼
        p.drawPath(path)


class Chip(QPushButton):
    def __init__(self, text: str, on=False, parent=None):
        super().__init__(text, parent)
        self.setObjectName("chip")
        self.setCursor(Qt.PointingHandCursor)
        self.set_on(on)

    def set_on(self, on: bool):
        self.setProperty("on", "true" if on else "false")
        self.style().unpolish(self)
        self.style().polish(self)


class PrimaryButton(QPushButton):
    def __init__(self, text, parent=None):
        super().__init__(text, parent)
        self.setObjectName("primary")
        self.setCursor(Qt.PointingHandCursor)
        self.setMinimumHeight(44)


class GhostButton(QPushButton):
    def __init__(self, text, parent=None):
        super().__init__(text, parent)
        self.setObjectName("ghost")
        self.setCursor(Qt.PointingHandCursor)
        self.setMinimumHeight(40)


class ThemeDot(QWidget):
    """主题色点：外圈 paper、内圈 brand。"""

    def __init__(self, tokens: dict, size: int = 20, parent=None):
        super().__init__(parent)
        self.tokens = tokens
        self.setFixedSize(size, size)

    def paintEvent(self, e):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        r = self.rect().adjusted(1, 1, -1, -1)
        p.setPen(QPen(QColor(self.tokens.get("line", "#DDD")), 1))
        p.setBrush(QColor(self.tokens.get("paper", "#FFF")))
        p.drawEllipse(r)
        p.setPen(Qt.NoPen)
        p.setBrush(QColor(self.tokens.get("brand", "#333")))
        p.drawEllipse(r.adjusted(6, 6, -6, -6))


class ThemeChip(ClickFrame if "ClickFrame" in globals() else QWidget):
    """主题选项：色点 + 名称 + 选中态。"""

    clicked = Signal(str)

    def __init__(self, tid: str, name: str, tokens: dict, selected: bool = False,
                 parent=None):
        super().__init__(parent)
        self.tid = tid
        self.setObjectName("themeChip")
        self.setCursor(Qt.PointingHandCursor)
        self.setFixedHeight(46)
        lay = QHBoxLayout(self)
        lay.setContentsMargins(12, 6, 12, 6)
        lay.setSpacing(9)
        lay.addWidget(ThemeDot(tokens, 20), 0, Qt.AlignVCenter)
        lb = QLabel(name)
        lb.setStyleSheet(
            f"font-size:12.5px;font-weight:600;color:"
            f"{(tokens.get('brand') if selected else tokens.get('ink'))};")
        lay.addWidget(lb, 1)
        if selected:
            tick = QLabel("✓")
            tick.setStyleSheet(f"color:{tokens.get('brand')};font-size:12px;")
            lay.addWidget(tick)
        border = tokens.get("brand") if selected else tokens.get("line")
        bg = tokens.get("brand_soft") if selected else tokens.get("panel")
        self.setStyleSheet(
            f"QWidget#themeChip{{background:{bg};border:1px solid {border};"
            f"border-radius:12px;}}")

    def mouseReleaseEvent(self, e):
        if e.button() == Qt.LeftButton:
            self.clicked.emit(self.tid)
        super().mouseReleaseEvent(e)


class MoreButton(QPushButton):
    """细线灰色三点按钮：透明底，悬停浮一层浅色圆底（和「＋」图标同一套语言）。"""

    def __init__(self, size: int = 36, parent=None):
        super().__init__("", parent)
        self.setFixedSize(size, size)
        self.setCursor(Qt.PointingHandCursor)
        self.setAttribute(Qt.WA_Hover, True)
        self.setStyleSheet("background:transparent;border:none;")

    def enterEvent(self, e):
        self.update()
        super().enterEvent(e)

    def leaveEvent(self, e):
        self.update()
        super().leaveEvent(e)

    def paintEvent(self, e):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        w, h = self.width(), self.height()
        cx, cy = w / 2, h / 2
        if self.underMouse():
            p.setPen(Qt.NoPen)
            p.setBrush(QColor(T["panel"]))
            p.drawRoundedRect(QRectF(0, 0, w, h), w / 2, h / 2)
        p.setPen(Qt.NoPen)
        p.setBrush(QColor(T["ink3"]))
        for dx in (-6.6, 0.0, 6.6):
            p.drawEllipse(QPointF(cx + dx, cy), 2.0, 2.0)


class StackBars(QWidget):
    """堆叠柱状图。labels 与 series 段数对应，colors 为各段颜色。"""

    def __init__(self, labels: list[str], series: list[list[float]],
                 colors: list[str], height: int = 150, unit: str = "",
                 parent=None):
        super().__init__(parent)
        self.labels = labels or []
        self.series = series or []
        self.colors = colors or []
        self.unit = unit
        self.setFixedHeight(height)

    def paintEvent(self, e):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        w, h = self.width(), self.height()
        left, right, top, bottom = 30, 6, 10, 20
        plot_w = max(10, w - left - right)
        plot_h = max(10, h - top - bottom)
        n = len(self.labels)
        if n == 0:
            return
        totals = [sum(seg[i] for seg in self.series) for i in range(n)] if self.series             else [0] * n
        mx = max(totals) or 1
        # 取整刻度
        step = 10 ** max(0, len(str(int(mx))) - 1)
        top_val = max(step, int((mx + step - 1) // step * step))
        # 网格
        p.setPen(QPen(QColor(T["line"]), 1, Qt.DotLine))
        p.setFont(QFont(theme.FONT, 7))
        for k in range(4):
            y = top + plot_h * k / 3
            p.setPen(QPen(QColor(T["line"]), 1, Qt.DotLine))
            p.drawLine(QPointF(left, y), QPointF(left + plot_w, y))
            p.setPen(QColor(T["ink3"]))
            p.drawText(QRectF(0, y - 7, left - 5, 14),
                       Qt.AlignRight | Qt.AlignVCenter,
                       str(int(top_val * (3 - k) / 3)))
        # 柱
        slot = plot_w / n
        bw = max(3.0, slot * 0.58)
        for i in range(n):
            x = left + slot * i + (slot - bw) / 2
            y = top + plot_h
            for si, seg in enumerate(self.series):
                v = seg[i]
                if v <= 0:
                    continue
                hh = plot_h * v / top_val
                r = QRectF(x, y - hh, bw, hh)
                p.setBrush(QColor(self.colors[si] if si < len(self.colors)
                                  else T["brand"]))
                p.setPen(Qt.NoPen)
                p.drawRect(r)
                y -= hh
        # x 轴标签
        p.setPen(QColor(T["ink3"]))
        p.setFont(QFont(theme.FONT, 7))
        every = max(1, n // 6)
        for i in range(0, n, every):
            x = left + slot * i + slot / 2
            p.drawText(QRectF(x - 24, h - bottom + 2, 48, 14),
                       Qt.AlignHCenter | Qt.AlignTop, self.labels[i])


class SparkBars(QWidget):
    """迷你堆叠柱：无坐标轴，柱顶圆角，适合放卡片里。"""

    def __init__(self, series: list[list[float]], colors: list[str],
                 height: int = 86, parent=None):
        super().__init__(parent)
        self.series = series or []
        self.colors = colors or []
        self.setFixedHeight(height)

    def paintEvent(self, e):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        w, h = self.width(), self.height()
        n = len(self.series[0]) if self.series else 0
        if n == 0:
            return
        totals = [sum(seg[i] for seg in self.series) for i in range(n)]
        mx = max(totals) or 1
        slot = w / n
        bw = max(2.0, slot * 0.58)
        base = h - 1
        for i in range(n):
            x = slot * i + (slot - bw) / 2
            y = base
            for si, seg in enumerate(self.series):
                v = seg[i]
                if v <= 0:
                    continue
                hh = (h - 6) * v / mx
                r = QRectF(x, y - hh, bw, hh)
                p.setBrush(QColor(self.colors[si] if si < len(self.colors)
                                  else T["brand"]))
                p.setPen(Qt.NoPen)
                p.drawRoundedRect(r, min(3.0, bw / 2), min(3.0, bw / 2))
                y -= hh


class StackBar(QWidget):
    """单条 100% 堆叠条（分布用）。"""

    def __init__(self, parts: list[tuple[str, float, str]], height: int = 14,
                 parent=None):
        super().__init__(parent)
        self.parts = parts
        self.setFixedHeight(height)

    def paintEvent(self, e):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        w, h = self.width(), self.height()
        total = sum(v for _, v, _ in self.parts) or 1
        x = 0.0
        for _, v, color in self.parts:
            seg = w * v / total
            if seg <= 0:
                continue
            p.setBrush(QColor(color))
            p.setPen(Qt.NoPen)
            p.drawRect(QRectF(x, 0, max(1.0, seg - 1), h))
            x += seg


class NavButton(QPushButton):
    """底部导航：图标 + 文字，选中态用品牌色。"""

    def __init__(self, key: str, label: str, parent=None):
        super().__init__("", parent)
        self.key = key
        self.label = label
        self.setObjectName("tab")
        self.setCursor(Qt.PointingHandCursor)
        self.setCheckable(True)
        self.setFixedHeight(56)

    def paintEvent(self, e):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        active = self.isChecked()
        col = QColor(T["brand"]) if active else QColor(T["ink2"])
        w, h = self.width(), self.height()
        cx = w / 2

        # 选中：浅底胶囊
        if active:
            p.setPen(Qt.NoPen)
            p.setBrush(QColor(T["brand_soft"]))
            p.drawRoundedRect(QRectF(cx - 31, 7, 62, h - 12), 14, 14)

        pen = QPen(col, 1.8)
        pen.setCapStyle(Qt.RoundCap)
        pen.setJoinStyle(Qt.RoundJoin)
        p.setPen(pen)
        p.setBrush(Qt.NoBrush)
        r = QRectF(cx - 9, 10, 18, 18)
        self._icon(p, self.key, r)

        p.setPen(col)
        f = QFont(theme.FONT, 8)
        f.setBold(active)
        p.setFont(f)
        p.drawText(QRectF(0, h - 19, w, 16), Qt.AlignHCenter | Qt.AlignVCenter, self.label)

    @staticmethod
    def _icon(p: QPainter, key: str, r: QRectF):
        c = r.center()
        if key == "today":
            # 太阳：今日
            p.drawEllipse(c, 4.0, 4.0)
            for i in range(8):
                a = math.radians(i * 45)
                p.drawLine(
                    QPointF(c.x() + math.cos(a) * 6.3, c.y() + math.sin(a) * 6.3),
                    QPointF(c.x() + math.cos(a) * 8.4, c.y() + math.sin(a) * 8.4))
        elif key == "library":
            # 单张卡片 + 顶部一条横线
            p.drawRoundedRect(QRectF(r.left() + 2.5, r.top() + 1.5, 13.0, 15.5), 3.0, 3.0)
            p.drawLine(QPointF(r.left() + 5.6, r.top() + 5.6),
                       QPointF(r.left() + 12.4, r.top() + 5.6))
        elif key == "plan":
            # 征途：折页地图（外轮廓一圈 + 两道折痕）
            def _p(fx, fy):
                return QPointF(r.left() + fx * r.width(), r.top() + fy * r.height())
            outline = [_p(0.10, 0.26), _p(0.36, 0.14), _p(0.64, 0.26), _p(0.90, 0.14),
                       _p(0.90, 0.74), _p(0.64, 0.86), _p(0.36, 0.74), _p(0.10, 0.86)]
            for i, pt in enumerate(outline):
                p.drawLine(pt, outline[(i + 1) % len(outline)])
            p.drawLine(_p(0.36, 0.14), _p(0.36, 0.74))
            p.drawLine(_p(0.64, 0.26), _p(0.64, 0.86))
        elif key == "insights":
            # 柱状图
            base = r.top() + 16
            for i, hh in enumerate((5.5, 9.5, 13.5)):
                x = r.left() + 3.5 + i * 5.5
                p.drawLine(QPointF(x, base), QPointF(x, base - hh))

class Bar(QProgressBar):
    """细进度条（QProgressBar 样式化，自动跟随宽度）。"""

    def __init__(self, pct: float, color: str | None = None, height=7, parent=None):
        super().__init__(parent)
        self.setMaximum(100)
        self.setValue(int(max(0, min(100, pct))))
        self.setTextVisible(False)
        self.setFixedHeight(height)
        c = color or T["brand"]
        self.setStyleSheet(
            "QProgressBar{background:%s;border:none;border-radius:%dpx;}"
            "QProgressBar::chunk{background:%s;border-radius:%dpx;}"
            % (T["paper2"], height // 2, c, height // 2)
        )


class Ring(QWidget):
    def __init__(self, pct: float, size=76, width=7, track=None, fill=None, parent=None):
        super().__init__(parent)
        self.pct = max(0, min(100, pct))
        self.lw = width
        self.track = track or T["paper2"]
        self.fill = fill or T["brand"]
        self.setFixedSize(size, size)

    def paintEvent(self, e):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        rect = QRectF(self.lw / 2, self.lw / 2, self.width() - self.lw, self.height() - self.lw)
        p.setPen(QPen(QColor(self.track), self.lw))
        p.drawArc(rect, 0, 360 * 16)
        p.setPen(QPen(QColor(self.fill), self.lw, Qt.SolidLine, Qt.RoundCap))
        p.drawArc(rect, 90 * 16, -int(360 * 16 * self.pct / 100))
        p.setPen(QColor(T["ink"]))
        f = QFont(theme.FONT, max(9, int(self.width() / 5)))
        f.setBold(True)
        p.setFont(f)
        p.drawText(self.rect(), Qt.AlignCenter, f"{int(self.pct)}%")


class Bars(QWidget):
    def __init__(self, values: list[int], parent=None):
        super().__init__(parent)
        self.values = values or [0]
        self.setFixedHeight(96)

    def paintEvent(self, e):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        n = len(self.values)
        mx = max(self.values) or 1
        gap = 5
        bw = (self.width() - gap * (n - 1)) / n
        base = self.height() - 14
        for i, v in enumerate(self.values):
            h = max(6, (v / mx) * (base - 4))
            x = i * (bw + gap)
            r = QRectF(x, base - h, bw, h)
            if i == 0:
                g = QLinearGradient(r.topLeft(), r.bottomLeft())
                g.setColorAt(0, QColor(T["brand"]))
                g.setColorAt(1, QColor(T["brand2"]))
                p.setBrush(QBrush(g))
                p.setPen(Qt.NoPen)
            else:
                p.setBrush(QColor(T["paper2"]))
                p.setPen(Qt.NoPen)
            p.drawRoundedRect(r, 3, 3)
            if i == 0:
                p.setPen(QColor(T["ink2"]))
                p.setFont(QFont(theme.FONT, 7))
                p.drawText(QRectF(x - 6, base + 2, bw + 12, 12), Qt.AlignCenter, "今天")


class Heat(QWidget):
    """活跃热力：正方形格子、每行固定列数、最后一行可不满；四周留白尽量小。"""

    def __init__(self, values: list[int], cols: int = 8, gap: int = 4,
                 inset: int = 4, parent=None):
        super().__init__(parent)
        self.values = values
        self.cols = max(1, cols)
        self.gap = gap
        self.inset = inset
        sp = QSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.setSizePolicy(sp)
        self.setMinimumHeight(60)

    def _rows(self) -> int:
        n = len(self.values)
        return max(1, (n + self.cols - 1) // self.cols)

    def _cell(self) -> float:
        n = len(self.values)
        if not n:
            return 10.0
        cols, rows, g, p = self.cols, self._rows(), self.gap, self.inset
        w = max(1.0, float(self.width())) - 2 * p
        h = max(1.0, float(self.height())) - 2 * p
        wf = (w - g * (cols - 1)) / cols
        hf = (h - g * (rows - 1)) / rows
        return max(4.0, min(wf, hf))

    def paintEvent(self, e):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        n = len(self.values)
        if n == 0:
            return
        cols, rows, g = self.cols, self._rows(), self.gap
        cell = self._cell()
        grid_w = cols * cell + (cols - 1) * g
        grid_h = rows * cell + (rows - 1) * g
        x0 = max(0.0, (self.width() - grid_w) / 2)
        y0 = max(0.0, (self.height() - grid_h) / 2)
        mx = max(self.values) or 1
        for i, v in enumerate(self.values):
            r, c = divmod(i, cols)
            x = x0 + c * (cell + g)
            y = y0 + r * (cell + g)
            a = 0.10 + 0.85 * (v / mx)
            col = QColor(T["brand"])
            col.setAlphaF(a if v else 0.08)
            p.setBrush(col)
            p.setPen(Qt.NoPen)
            p.drawRoundedRect(QRectF(x, y, cell, cell), 3, 3)


class Radar(QWidget):
    def __init__(self, metrics: list[tuple[str, int]], size=220, parent=None):
        super().__init__(parent)
        self.metrics = metrics
        self.setFixedSize(size, size)

    def paintEvent(self, e):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        cx, cy = self.width() / 2, self.height() / 2
        R = min(cx, cy) * 0.66
        n = len(self.metrics)
        if not n:
            return

        def pt(i, ratio):
            a = math.radians(-90 + i * 360 / n)
            return QPointF(cx + math.cos(a) * R * ratio, cy + math.sin(a) * R * ratio)

        p.setPen(QPen(QColor(T["line"]), 1))
        for ratio in (0.33, 0.66, 1.0):
            path = QPainterPath(pt(0, ratio))
            for i in range(1, n):
                path.lineTo(pt(i, ratio))
            path.closeSubpath()
            p.drawPath(path)
        for i in range(n):
            p.drawLine(QPointF(cx, cy), pt(i, 1.0))

        poly = QPainterPath(pt(0, max(0.05, self.metrics[0][1] / 100)))
        for i in range(1, n):
            poly.lineTo(pt(i, max(0.05, self.metrics[i][1] / 100)))
        poly.closeSubpath()
        fill = QColor(T["brand"])
        fill.setAlpha(48)
        p.setBrush(fill)
        p.setPen(QPen(QColor(T["brand"]), 1.8))
        p.drawPath(poly)

        p.setPen(QColor(T["ink2"]))
        f = QFont(theme.FONT, 8)
        p.setFont(f)
        for i, (name, val) in enumerate(self.metrics):
            q = pt(i, 1.22)
            p.drawText(QRectF(q.x() - 20, q.y() - 8, 40, 16), Qt.AlignCenter, name)


# ---------------------------------------------------------------- 复习

class OptionRow(ClickFrame):
    clicked_index = Signal(int)

    def __init__(self, index: int, text: str, multi=False, parent=None):
        super().__init__(parent)
        self.index = index
        self.multi = multi
        self.state = "idle"
        lay = QHBoxLayout(self)
        lay.setContentsMargins(12, 10, 12, 10)
        lay.setSpacing(10)
        self.key = QLabel("ABCD"[index] if not multi else "")
        self.key.setFixedSize(20, 20)
        self.key.setAlignment(Qt.AlignCenter)
        lay.addWidget(self.key)
        self.label = QLabel(text)
        self.label.setWordWrap(True)
        self.label.setStyleSheet("font-size:13px;")
        self.label.setMinimumHeight(wrap_height(text, 13, 286))
        lay.addWidget(self.label, 1)
        self._apply()
        self.clicked.connect(lambda: self.clicked_index.emit(self.index))

    def set_state(self, state: str):
        self.state = state
        self._apply()

    def _apply(self):
        bg, border, fg = T["panel"], T["line"], T["ink"]
        if self.state == "picked":
            border, bg = T["ink"], T["panel"]
        elif self.state == "correct":
            border, bg, fg = T["green"], T["green_soft"], T["green"]
        elif self.state == "wrong":
            border, bg, fg = T["red"], T["red_soft"], T["red"]
        elif self.state == "dim":
            bg, fg = T["paper2"], T["ink3"]
        self.setObjectName("optRow")
        self.setStyleSheet(
            f"QFrame#optRow{{background:{bg};border:1px solid {border};border-radius:13px;}}"
        )
        key_bg = T["paper2"] if self.state in ("idle", "dim") else (
            T["green"] if self.state == "correct" else T["red"] if self.state == "wrong" else T["ink"])
        key_fg = T["ink2"] if self.state in ("idle", "dim") else T["panel"]
        if self.multi:
            self.key.setText("✓" if self.state in ("picked", "correct") else ("✕" if self.state == "wrong" else ""))
        self.key.setStyleSheet(
            f"background:{key_bg};color:{key_fg};border-radius:6px;font-size:10px;font-weight:700;"
        )
        self.label.setStyleSheet(f"font-size:13px;color:{fg};")


class RatingButton(ClickFrame):
    clicked_rating = Signal(int)

    def __init__(self, idx: int, label: str, hint: str, color: str,
                 bg: str | None = None, fg: str | None = None,
                 edge: str | None = None, parent=None):
        super().__init__(parent)
        self.idx = idx
        self.setObjectName("rateBtn")
        bg = bg or T["panel"]
        fg = fg or T["ink"]
        edge = edge or T["line"]
        self.setStyleSheet(
            f"QFrame#rateBtn{{background:{bg};border:1px solid {edge};border-radius:14px;}}"
            f"QFrame#rateBtn:hover{{border-color:{color};}}")
        lay = QVBoxLayout(self)
        lay.setContentsMargins(4, 10, 4, 9)
        lay.setSpacing(3)
        t = QLabel(label)
        t.setAlignment(Qt.AlignCenter)
        t.setStyleSheet(f"font-size:14.5px;font-weight:700;color:{fg};")
        h = QLabel(hint)
        h.setAlignment(Qt.AlignCenter)
        h.setStyleSheet(f"font-size:10.5px;color:{T['ink3']};")
        lay.addWidget(t)
        lay.addWidget(h)
        self._hint = h
        self.clicked.connect(lambda: self.clicked_rating.emit(self.idx))

    def set_hint(self, text: str):
        """只换下面那行间隔预览（换卡时复用按钮，不再重建）。"""
        self._hint.setText(text)


class SelectBox(QWidget):
    """卡组前的勾选框（单选，只靠外部保证唯一）。"""

    toggled = Signal(bool)

    def __init__(self, checked=False, parent=None):
        super().__init__(parent)
        self._checked = checked
        self.setFixedSize(20, 20)
        self.setCursor(Qt.PointingHandCursor)

    def isChecked(self) -> bool:
        return self._checked

    def setChecked(self, v: bool):
        self._checked = bool(v)
        self.update()

    def mouseReleaseEvent(self, e):
        if e.button() == Qt.LeftButton:
            self.setChecked(not self._checked)
            self.toggled.emit(self._checked)
            e.accept()
            return
        super().mouseReleaseEvent(e)

    def paintEvent(self, e):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        r = QRectF(1, 1, 18, 18)
        if self._checked:
            p.setPen(Qt.NoPen)
            p.setBrush(QColor(T["brand"]))
            p.drawRoundedRect(r, 5, 5)
            p.setPen(QPen(QColor("#FFFFFF"), 2.0, Qt.SolidLine, Qt.RoundCap, Qt.RoundJoin))
            path = QPainterPath()
            c = r.center()
            path.moveTo(c.x() - 3.6, c.y() + 0.2)
            path.lineTo(c.x() - 1.0, c.y() + 3.0)
            path.lineTo(c.x() + 3.8, c.y() - 3.0)
            p.drawPath(path)
        else:
            p.setPen(QPen(QColor("#C9C4B8"), 1.6))
            p.setBrush(QColor("#FFFFFF"))
            p.drawRoundedRect(r, 5, 5)


class SwipeRow(QWidget):
    """一行内容 + 左滑从右侧滑入的操作按钮（内容不位移，标题始终可见）。

    - 轻点 → clicked
    - 左滑 → 按钮滑入
    - 右滑 / 点一下 → 收回
    """

    clicked = Signal()
    action = Signal(str)
    drag_started = Signal()
    drag_moved = Signal(float)      # 全局 y
    drag_finished = Signal()

    def __init__(self, body: QWidget, actions, height=66, parent=None):
        super().__init__(parent)
        self._offset = 0.0        # 已露出的宽度
        self._dragging = False
        self._press = None
        self._start = 0.0
        self._moved = False

        self.body = body
        self.body.setParent(self)
        # 整行由 SwipeRow 自己处理鼠标（子控件穿透），否则按下事件会被子控件吞掉
        self.body.setAttribute(Qt.WA_TransparentForMouseEvents, True)
        self.body.show()

        self.panel = QWidget(self)
        pl = QHBoxLayout(self.panel)
        pl.setContentsMargins(0, 0, 0, 0)
        pl.setSpacing(6)
        pl.addStretch(1)
        self.buttons = {}
        for key, text, color in actions:
            b = QPushButton(text)
            b.setFixedSize(58, 46)
            b.setCursor(Qt.PointingHandCursor)
            b.setStyleSheet(
                f"QPushButton{{background:{color};color:#FFFFFF;border:none;"
                f"border-radius:12px;font-size:12px;font-weight:600;}}"
            )
            b.clicked.connect(lambda _, k=key: self.action.emit(k))
            pl.addWidget(b, 0, Qt.AlignVCenter)
            self.buttons[key] = b
        self.panel_w = 58 * len(actions) + 6 * (len(actions) - 1)
        self.setFixedHeight(height)

        self._anim = QPropertyAnimation(self, b"offset", self)
        self._anim.setDuration(170)
        self._anim.setEasingCurve(QEasingCurve.OutCubic)

        # 长按 320ms 进入拖动排序
        self._lp = QTimer(self)
        self._lp.setSingleShot(True)
        self._lp.setInterval(320)
        self._lp.timeout.connect(self._enter_drag)

    # ---- 位移属性：0 = 收起，panel_w = 完全露出 ----
    def get_offset(self) -> float:
        return self._offset

    def set_offset(self, v: float):
        self._offset = max(0.0, min(float(self.panel_w), float(v)))
        self._layout_children()

    offset = Property(float, get_offset, set_offset)

    def _layout_children(self):
        w, h = self.width(), self.height()
        self.body.setGeometry(0, 0, w, h)
        self.body.lower()
        self.panel.setGeometry(int(w - self._offset), 0, self.panel_w, h)
        self.panel.raise_()

    def resizeEvent(self, e):
        super().resizeEvent(e)
        self._layout_children()

    # ---- 开合 ----
    def open(self):
        self._animate_to(self.panel_w)

    def close(self):
        self._animate_to(0.0)

    def is_open(self) -> bool:
        return self._offset > 4

    def _animate_to(self, target: float):
        self._anim.stop()
        self._anim.setStartValue(self._offset)
        self._anim.setEndValue(float(target))
        self._anim.start()

    # ---- 手势 ----
    def _enter_drag(self):
        if self._press is None:
            return
        self._dragging = True
        self.setCursor(Qt.ClosedHandCursor)
        self.drag_started.emit()

    # ---- 鼠标 ----
    def mousePressEvent(self, e):
        if e.button() == Qt.LeftButton:
            self._press = e.position().x()
            self._press_y = e.position().y()
            self._start = self._offset
            self._moved = False
            self._dragging = False
            self._lp.start()
            e.accept()
            return
        super().mousePressEvent(e)

    def mouseMoveEvent(self, e):
        if self._press is None:
            return super().mouseMoveEvent(e)
        dx = e.position().x() - self._press
        dy = e.position().y() - self._press_y
        if self._dragging:
            self.drag_moved.emit(e.globalPosition().y())
            e.accept()
            return
        if abs(dx) > 6 or abs(dy) > 6:
            self._moved = True
            self._lp.stop()
        if self._moved:
            self.set_offset(self._start - dx)
        e.accept()

    def mouseReleaseEvent(self, e):
        self._lp.stop()
        if self._press is None:
            return super().mouseReleaseEvent(e)
        if self._dragging:
            self._dragging = False
            self.setCursor(Qt.PointingHandCursor)
            self.drag_finished.emit()
        elif not self._moved:
            if self.is_open():
                self.close()
            else:
                self.clicked.emit()
        else:
            self._animate_to(self.panel_w if self._offset > self.panel_w * 0.5 else 0.0)
        self._press = None
        e.accept()

    def eventFilter(self, obj, ev):
        if obj is not self.body:
            return False
        t = ev.type()
        if t == QEvent.MouseButtonPress and ev.button() == Qt.LeftButton:
            self._press = ev.position().x()
            self._press_y = ev.position().y()
            self._start = self._offset
            self._moved = False
            self._dragging = False
            self._lp.start()
            return False
        if t == QEvent.MouseMove and self._press is not None:
            dx = ev.position().x() - self._press
            dy = ev.position().y() - self._press_y
            if self._dragging:
                self.drag_moved.emit(ev.globalPosition().y())
                return True
            if abs(dx) > 6 or abs(dy) > 6:
                self._moved = True
                self._lp.stop()
            if self._moved:
                self.set_offset(self._start - dx)
            return True
        if t == QEvent.MouseButtonRelease and self._press is not None:
            self._lp.stop()
            if self._dragging:
                self._dragging = False
                self.setCursor(Qt.PointingHandCursor)
                self.drag_finished.emit()
                self._press = None
                return True
            if not self._moved:
                if self.is_open():
                    self.close()
                else:
                    self.clicked.emit()
            else:
                self._animate_to(self.panel_w if self._offset > self.panel_w * 0.5 else 0.0)
            self._press = None
            return True
        return False


class TemplateTile(ClickFrame):
    """模板缩略图：按模板真实配色画一张迷你卡（页面底 / 卡片底 / 书签）。"""

    clicked_tpl = Signal(str)

    def __init__(self, key: str, pal: dict, selected=False, parent=None):
        super().__init__(parent)
        self.key = key
        self.pal = pal
        self.selected = selected
        self.setFixedHeight(104)
        self.setMinimumWidth(96)
        self.setCursor(Qt.PointingHandCursor)
        self.clicked.connect(lambda: self.clicked_tpl.emit(self.key))

    def paintEvent(self, e):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        w, h = self.width(), self.height()
        r = QRectF(0, 0, w, h)
        pal = self.pal

        p.setPen(Qt.NoPen)
        p.setBrush(QColor(pal["page"]))
        p.drawRoundedRect(r, 12, 12)

        card = QRectF(7, 7, w - 14, h - 34)
        p.setBrush(QColor(pal["front"]))
        p.drawRoundedRect(card, 8, 8)

        rb = QRectF(card.x() + 7, card.y() + 7, 40, 13)
        p.setBrush(QColor(pal["label"]))
        p.drawRoundedRect(rb, 3, 3)
        p.setBrush(QColor("#FFFFFF"))
        p.drawEllipse(QPointF(rb.x() + 4.5, rb.center().y()), 1.5, 1.5)
        p.setPen(QColor("#FFFFFF"))
        f = QFont(theme.FONT, 6)
        f.setBold(True)
        p.setFont(f)
        p.drawText(QRectF(rb.x() + 9, rb.y(), rb.width() - 9, rb.height()),
                   Qt.AlignLeft | Qt.AlignVCenter, "问题")

        p.setPen(QColor(pal["fg"]))
        f2 = QFont(theme.FONT, 7)
        p.setFont(f2)
        p.drawText(QRectF(card.x() + 8, card.y() + 25, card.width() - 16, 24),
                   Qt.AlignLeft | Qt.TextWordWrap, "降低期待能带来哪些好处？")

        p.setPen(QColor(T["brand"] if self.selected else T["ink"]))
        f3 = QFont(theme.FONT, 9)
        f3.setBold(True)
        p.setFont(f3)
        p.drawText(QRectF(8, h - 26, w - 14, 20), Qt.AlignLeft | Qt.AlignVCenter,
                   ("✓ " if self.selected else "") + pal["name"])

        if self.selected:
            p.setBrush(Qt.NoBrush)
            p.setPen(QPen(QColor(T["brand"]), 2))
            p.drawRoundedRect(r.adjusted(1, 1, -1, -1), 12, 12)


def shadow(w: QWidget, radius=24, alpha=38, dy=8):
    eff = QGraphicsDropShadowEffect(w)
    eff.setBlurRadius(radius)
    eff.setOffset(0, dy)
    c = QColor(T["ink"])
    c.setAlpha(alpha)
    eff.setColor(c)
    w.setGraphicsEffect(eff)


def center_on_screen(win):
    """把窗口放到屏幕正中间。"""
    try:
        screen = win.screen() or QGuiApplication.primaryScreen()
        if not screen:
            return
        g = screen.availableGeometry()
        fg = win.frameGeometry()
        fg.moveCenter(g.center())
        win.move(fg.topLeft())
    except Exception:
        pass


def center_dialog(dlg, parent):
    """把弹窗放到父窗口正中间（show 之后再校正一次，拿到真实边框）。"""
    def _do():
        try:
            p = parent.window() if parent is not None else None
            if p is not None:
                fg = dlg.frameGeometry()
                fg.moveCenter(p.frameGeometry().center())
                dlg.move(fg.topLeft())
        except Exception:
            pass

    _do()
    QTimer.singleShot(0, _do)


def clear_layout(lay):
    while lay.count():
        item = lay.takeAt(0)
        w = item.widget()
        if w is not None:
            w.hide()
            w.setParent(None)
            w.deleteLater()
        elif item.layout() is not None:
            clear_layout(item.layout())
